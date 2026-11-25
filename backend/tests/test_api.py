from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app, db


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MODEL_DIR": os.path.join(self.temp_dir.name, "models"),
        })
        self.client = self.app.test_client()
        response = self.client.post("/api/auth/register", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "correct horse battery",
        })
        self.assertEqual(response.status_code, 201)
        self.token = response.json["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def create_workload(self, **overrides):
        payload = {
            "name": "unit-test-job",
            "type": "batch",
            "cpu": 1,
            "memory": 2,
            "duration": 10,
            "sla": "standard",
        }
        payload.update(overrides)
        return self.client.post("/api/workloads", json=payload, headers=self.headers)

    def test_authentication_and_owner_scoped_workloads(self):
        self.assertEqual(self.client.get("/api/workloads").status_code, 401)
        created = self.create_workload()
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["workload"]["status"], "Queued")

        second_user = self.client.post("/api/auth/register", json={
            "name": "Other User",
            "email": "other@example.com",
            "password": "another secure password",
        })
        other_headers = {"Authorization": f"Bearer {second_user.json['token']}"}
        self.assertEqual(self.client.get("/api/workloads", headers=other_headers).json["workloads"], [])

    def test_workload_validation_rejects_invalid_capacity(self):
        response = self.create_workload(cpu=-2)
        self.assertEqual(response.status_code, 400)
        self.assertIn("CPU", response.json["error"])

    def test_prediction_requires_saved_trained_models(self):
        response = self.client.post(
            "/api/predictions",
            json={
                "dataSource": "Cloud",
                "taskType": "Cloud Service",
                "activeUsers": 300,
                "processCount": 8,
                "vmCpuCores": 4,
                "cpuSpeedGHz": 2.5,
                "vmMemoryGb": 8,
                "memoryRequestedGb": 4,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("models are unavailable", response.json["error"])

    def test_xgboost_training_persists_models_for_prediction(self):
        records = [
            {
                "dataSource": "Cloud" if index % 2 else "IoT",
                "taskType": "Cloud Service" if index % 2 else "Data Processing",
                "activeUsers": 100 + index * 20,
                "processCount": 1 + index % 20,
                "vmCpuCores": 2 + index % 4 * 2,
                "cpuSpeedGHz": 2.2 + index % 6 * 0.2,
                "vmMemoryGb": 4 + index % 4 * 4,
                "memoryRequestedGb": 0.5 + index % 20 * 0.25,
                "cpuTarget": min(100, 10 + index * 1.5),
                "memoryTargetGb": 0.5 + index % 20 * 0.2,
            }
            for index in range(50)
        ]
        trained = self.client.post(
            "/api/predictions/train",
            json={"records": records},
            headers=self.headers,
        )
        self.assertEqual(trained.status_code, 201, trained.get_data(as_text=True))
        self.assertEqual(trained.json["metrics"]["trainingRecords"], 40)
        self.assertEqual(trained.json["metrics"]["validationRecords"], 10)
        self.assertIn("rmse", trained.json["metrics"]["cpu"])
        self.assertIn("r2", trained.json["metrics"]["memory"])

        model_metrics = self.client.get("/api/predictions/metrics", headers=self.headers)
        self.assertEqual(model_metrics.status_code, 200)
        self.assertEqual(model_metrics.json["metrics"]["trainingRecords"], 40)

        prediction = self.client.post(
            "/api/predictions",
            json={
                "dataSource": "Cloud",
                "taskType": "Cloud Service",
                "activeUsers": 300,
                "processCount": 8,
                "vmCpuCores": 4,
                "cpuSpeedGHz": 2.5,
                "vmMemoryGb": 8,
                "memoryRequestedGb": 4,
            },
            headers=self.headers,
        )
        self.assertEqual(prediction.status_code, 200)
        self.assertEqual(prediction.json["model"], "xgboost")
        self.assertEqual(prediction.json["trainingRecords"], 40)
        self.assertGreaterEqual(prediction.json["cpu"], 0)
        self.assertLessEqual(prediction.json["cpu"], 100)
        self.assertGreaterEqual(prediction.json["memory"], 0)

        out_of_range = self.client.post(
            "/api/predictions",
            json={
                "dataSource": "Cloud",
                "taskType": "Cloud Service",
                "activeUsers": 100000,
                "processCount": 8,
                "vmCpuCores": 4,
                "cpuSpeedGHz": 2.5,
                "vmMemoryGb": 8,
                "memoryRequestedGb": 4,
            },
            headers=self.headers,
        )
        self.assertEqual(out_of_range.status_code, 200)
        self.assertIn("activeUsers", out_of_range.json["outOfTrainingRange"])

    def test_vm_selection_respects_capacity_and_premium_sla(self):
        response = self.client.post(
            "/api/vm-selection",
            json={"cpu": 1, "memory": 2, "sla": "premium"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        feasible = [item for item in response.json["recommendations"] if item["feasible"]]
        self.assertTrue(feasible)
        self.assertTrue(all(item["vm"] in {"vm-compute-01", "vm-memory-01"} for item in feasible))

    def test_scheduler_records_placements_and_keeps_unfittable_jobs_queued(self):
        self.create_workload(name="fits")
        self.create_workload(name="too-large", cpu=256, memory=1024)

        response = self.client.post("/api/schedule", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["scheduled"], 1)
        self.assertEqual(response.json["unscheduled"], 1)
        states = {item["name"]: item["status"] for item in response.json["workloads"]}
        self.assertEqual(states["fits"], "Running")
        self.assertEqual(states["too-large"], "Queued")
        self.assertTrue(any(decision["status"] == "scheduled" for decision in response.json["decisions"]))

    def test_cloudwatch_is_explicitly_disabled_without_configuration(self):
        with patch.dict(os.environ, {"AWS_REGION": "", "EC2_INSTANCE_IDS": ""}):
            response = self.client.get("/api/monitoring", headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["configured"])

    def test_cloudwatch_forecast_uses_real_metric_history_and_backtests(self):
        now = datetime.now(timezone.utc)
        datapoints = [
            {
                "Timestamp": now - timedelta(minutes=5 * (120 - index)),
                "Average": 10 + index * 0.25,
            }
            for index in range(120)
        ]
        cloudwatch = MagicMock()
        cloudwatch.get_metric_statistics.return_value = {"Datapoints": datapoints}
        with patch.dict(os.environ, {"AWS_REGION": "us-east-1", "EC2_INSTANCE_IDS": "i-test"}):
            with patch("boto3.client", return_value=cloudwatch):
                response = self.client.get("/api/predictions/forecast", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["source"], "AWS/EC2 CloudWatch")
        self.assertEqual(response.json["horizonMinutes"], 5)
        instance = response.json["forecasts"][0]
        self.assertEqual(instance["status"], "ready")
        self.assertAlmostEqual(instance["forecastCpu"], 40.0, places=1)
        self.assertTrue(instance["meetsAcceptance"])
        cloudwatch.get_metric_statistics.assert_called_once()

    def test_cloudwatch_forecast_requires_instance_configuration(self):
        with patch.dict(os.environ, {"AWS_REGION": "", "EC2_INSTANCE_IDS": ""}):
            response = self.client.get("/api/predictions/forecast", headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["configured"])

    def test_cloudwatch_forecast_does_not_forecast_stale_history(self):
        now = datetime.now(timezone.utc)
        datapoints = [
            {
                "Timestamp": now - timedelta(hours=12) + timedelta(minutes=5 * index),
                "Average": 35 + index * 0.1,
            }
            for index in range(120)
        ]
        cloudwatch = MagicMock()
        cloudwatch.get_metric_statistics.return_value = {"Datapoints": datapoints}
        with patch.dict(os.environ, {"AWS_REGION": "us-east-1", "EC2_INSTANCE_IDS": "i-test"}):
            with patch("boto3.client", return_value=cloudwatch):
                response = self.client.get("/api/predictions/forecast", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        instance = response.json["forecasts"][0]
        self.assertEqual(instance["status"], "stale_data")
        self.assertIsNone(instance["forecastCpu"])


if __name__ == "__main__":
    unittest.main()
