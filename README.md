# Smart Cloud Orchestrator

A responsive React dashboard for workload planning, VM selection, scheduling, monitoring, and analytics. Workbook data can be imported directly into the app for sheet-by-sheet exploration.

## Requirements

- Python 3.10+
- Node.js 20.19+ or 22.12+
- npm

## Run locally

Install Python and JavaScript dependencies once:

```sh
python -m pip install -r requirements.txt
npm install
```

Then start the API and frontend in separate terminals:

```sh
python -m backend.app
```

```sh
npm run dev
```

Open the local URL printed by Vite. The Vite development server proxies `/api` requests to `http://127.0.0.1:5000`.

The Flask backend uses SQLite by default and stores local data in `backend/orchestrator.db`. Set `DATABASE_URL` to a MySQL SQLAlchemy URL to use Amazon RDS/MySQL.

It exposes:

- `POST /api/auth/register` and `POST /api/auth/login` for password-hashed accounts and signed bearer tokens
- Public `GET /api/health`; authenticated `GET /api/workloads` and `GET /api/vms`
- `POST /api/workloads` to validate and queue a workload
- `POST /api/vm-selection` to rank available VMs using weighted best-fit scoring
- `POST /api/schedule` to prioritize and place queued workloads using HEFT-style ranking and earliest-finish-time selection
- `POST /api/predictions` and `GET /api/predictions/metrics` for workload-specific XGBoost estimates and validation metrics
- `POST /api/predictions/train` to train the workload estimator from supplied records
- `GET /api/predictions/forecast` for an optional five-minute EC2 CPU forecast and chronological backtest from CloudWatch history
- `GET /api/monitoring` for opt-in CloudWatch CPU metrics

The optional AWS forecast uses the latest five days of consecutive `AWS/EC2` `CPUUtilization` readings at five-minute intervals. It selects a simple forecast method on earlier readings and evaluates it on the most recent 20%. It requires `AWS_REGION`, `EC2_INSTANCE_IDS`, and CloudWatch permissions; EC2's default metrics do not include memory. The workload estimator is separate: it estimates resource consumption for one workload from its task and VM characteristics and does not require AWS configuration. The HEFT scheduler treats submissions as independent jobs because the dashboard does not define task dependencies. Scheduling records placements; it does not start processes or provision EC2 instances.

Copy `.env.example` to `.env` and set `SECRET_KEY` before exposing the service beyond local development. Set `DATABASE_URL` for MySQL, `AWS_REGION` and comma-separated `EC2_INSTANCE_IDS` for CloudWatch, and `MODEL_S3_BUCKET` for optional model artifact uploads. The AWS identity used by boto3 needs permission to call `cloudwatch:GetMetricStatistics` for the configured instances. Credentials are loaded through the normal AWS SDK credential chain; do not commit them to `.env` or source control. The development API listens on `127.0.0.1:5000`.

## Test the backend

```sh
npm test
```

The workload-specific model can be trained from the supplied CSV format with:

```sh
python -m backend.train_models --dataset path/to/workload-dataset.csv
```

This trainer uses task type, data source, active users, process count, VM CPU and memory characteristics, and requested memory to estimate resource consumption for the same workload record. The Workloads page accepts only workload basics and automatically uses a sample profile for prediction; it then derives vCPU and memory requests from the estimate. These are assumptions, not measurements. The Predictions page supports a standalone estimate with explicit model inputs and reports validation metrics. On the supplied dataset, CPU MAE is 12.783 percentage points (R² 0.5269) and memory MAE is 0.1796 GB (R² 0.987); treat CPU estimates as approximate. The optional AWS forecast is not required for these workload predictions.

## Build for production

```sh
npm run build
npm run preview
```

## Import a workbook

Use **Import workbook** in the top bar to load `.xlsx` files. The browser parses workbook sheets locally and shows a preview of each sheet. Imported workbook content is kept in the current page session and is not uploaded to a server.

## Dashboard sections

- Dashboard: cluster metrics, monitoring readings, utilization history, and recent workloads
- Workloads: create jobs from workload basics and get an automatic sample-profile estimate
- Predictions: estimate one workload's CPU and memory consumption and inspect model validation metrics
- VM Manager: inspect VM capacity and compare workload fit
- Scheduler: schedule queued workloads
- Monitoring: inspect live CloudWatch CPU readings and clearly labeled sample VM data
- Analytics: view prediction deviation and scheduling mix
- Dataset: inspect imported workbook sheet summaries
