# Smart Cloud Orchestrator

A responsive React dashboard for workload planning, VM selection, scheduling, monitoring, and analytics. Workbook data can be imported directly into the app for sheet-by-sheet exploration.

## Requirements

- Node.js 20.19+ or 22.12+
- npm

## Run locally

```sh
npm install
npm run dev
```

Open the local URL printed by Vite.

## Build for production

```sh
npm run build
npm run preview
```

## Import a workbook

Use **Import workbook** in the top bar to load `.xlsx` files. The browser parses workbook sheets locally and shows a preview of each sheet. Imported workbook content is kept in the current page session and is not uploaded to a server.

## Dashboard sections

- Dashboard: cluster metrics, monitoring readings, utilization history, and recent workloads
- Workloads: submit and view queued or running workloads
- Predictions: estimate next-window CPU and memory demand
- VM Manager: inspect VM capacity and compare workload fit
- Scheduler: schedule queued workloads
- Monitoring: inspect sample cluster readings and feedback controls
- Analytics: view prediction deviation and scheduling mix
- Dataset: inspect imported workbook sheet summaries
