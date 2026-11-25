from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from backend.forecasting import MIN_HISTORY_POINTS, PERIOD_SECONDS, forecast_cpu
from backend.modeling import METRICS_FILE, MODEL_FILES, SCHEMA_FILE, predict_workload, train_models
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

db = SQLAlchemy()

WORKLOAD_TYPES = {"batch", "service", "inference", "database"}
SLA_TIERS = {"basic", "standard", "premium"}
DEFAULT_VMS = (
    {"name": "vm-burst-01", "type": "t3.medium", "zone": "us-east-1", "total_cpu": 2, "total_memory": 4, "cost": 0.04, "tier": "basic"},
    {"name": "vm-compute-01", "type": "c5.xlarge", "zone": "ap-south-1", "total_cpu": 4, "total_memory": 8, "cost": 0.31, "tier": "premium"},
    {"name": "vm-general-01", "type": "t3.large", "zone": "ap-south-1", "total_cpu": 2, "total_memory": 8, "cost": 0.08, "tier": "standard"},
    {"name": "vm-memory-01", "type": "r5.xlarge", "zone": "ap-south-1", "total_cpu": 4, "total_memory": 32, "cost": 0.25, "tier": "premium"},
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class VM(db.Model):
    name = db.Column(db.String(80), primary_key=True)
    type = db.Column(db.String(80), nullable=False)
    zone = db.Column(db.String(80), nullable=False)
    total_cpu = db.Column(db.Float, nullable=False)
    total_memory = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    tier = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="running")


class Workload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    cpu = db.Column(db.Float, nullable=False)
    memory = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    sla = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Normal")
    allocated = db.Column(db.String(80), nullable=False, default="Pending")
    status = db.Column(db.String(20), nullable=False, default="Queued")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    scheduled_at = db.Column(db.DateTime(timezone=True))


class SchedulingDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    workload_id = db.Column(db.Integer, db.ForeignKey("workload.id"), nullable=False)
    outcome = db.Column(db.String(20), nullable=False)
    vm_name = db.Column(db.String(80))
    score = db.Column(db.Float)
    reason = db.Column(db.String(240))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def _number(value, label, minimum, maximum):
    if isinstance(value, bool):
        return None, f"{label} must be a number."
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None, f"{label} must be a number."
    if not minimum <= parsed <= maximum:
        return None, f"{label} must be between {minimum} and {maximum}."
    return parsed, None


def _workload_data(payload):
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        return None, "Name must contain 1 to 80 characters."
    if payload.get("type") not in WORKLOAD_TYPES:
        return None, "Type must be batch, service, inference, or database."
    if payload.get("sla") not in SLA_TIERS:
        return None, "SLA must be basic, standard, or premium."

    cpu, error = _number(payload.get("cpu"), "CPU", 0.01, 256)
    if error:
        return None, error
    memory, error = _number(payload.get("memory"), "Memory", 0.01, 1024)
    if error:
        return None, error
    duration, error = _number(payload.get("duration"), "Duration", 1, 10080)
    if error:
        return None, error

    return {
        "name": name.strip(),
        "type": payload["type"],
        "cpu": cpu,
        "memory": memory,
        "duration": duration,
        "sla": payload["sla"],
        "priority": "High" if payload.get("priority") == "High" else "Normal",
    }, None


def _serialize_workload(workload):
    return {
        "id": workload.id,
        "name": workload.name,
        "type": workload.type,
        "cpu": workload.cpu,
        "memory": workload.memory,
        "duration": workload.duration,
        "sla": workload.sla,
        "priority": workload.priority,
        "allocated": workload.allocated,
        "status": workload.status,
        "createdAt": workload.created_at.isoformat() if workload.created_at else None,
        "scheduledAt": workload.scheduled_at.isoformat() if workload.scheduled_at else None,
    }


def _vm_inventory():
    vms = VM.query.order_by(VM.name).all()
    running = Workload.query.filter_by(status="Running").all()
    assigned = {}
    for workload in running:
        if workload.allocated != "Pending":
            totals = assigned.setdefault(workload.allocated, {"cpu": 0.0, "memory": 0.0, "minutes": 0.0})
            totals["cpu"] += workload.cpu
            totals["memory"] += workload.memory
            totals["minutes"] += workload.duration * workload.cpu

    inventory = []
    for vm in vms:
        used = assigned.get(vm.name, {"cpu": 0.0, "memory": 0.0, "minutes": 0.0})
        inventory.append({
            "name": vm.name,
            "type": vm.type,
            "zone": vm.zone,
            "totalCpu": vm.total_cpu,
            "totalMemory": vm.total_memory,
            "availableCpu": max(0, vm.total_cpu - used["cpu"]),
            "availableMemory": max(0, vm.total_memory - used["memory"]),
            "cpu": min(100, round(used["cpu"] / vm.total_cpu * 100)),
            "memory": min(100, round(used["memory"] / vm.total_memory * 100)),
            "queueMinutes": used["minutes"] / vm.total_cpu,
            "cost": vm.cost,
            "tier": vm.tier,
            "status": vm.status,
        })
    return inventory


def _rank_vms(cpu, memory, sla, inventory, duration=30):
    max_cost = max((vm["cost"] for vm in inventory), default=0)
    ranked = []
    for vm in inventory:
        feasible = (
            vm["status"] == "running"
            and vm["availableCpu"] >= cpu
            and vm["availableMemory"] >= memory
            and (sla != "premium" or vm["tier"] == "premium")
        )
        cpu_fit = cpu / vm["availableCpu"] if feasible else 0
        memory_fit = memory / vm["availableMemory"] if feasible else 0
        load_fit = 1 - (vm["cpu"] / 100 + vm["memory"] / 100) / 2
        cost_fit = 1 - vm["cost"] / max_cost if max_cost else 0
        score = 0.35 * cpu_fit + 0.35 * memory_fit + 0.15 * load_fit + 0.15 * cost_fit if feasible else 0
        ranked.append({
            "vm": vm["name"],
            "feasible": feasible,
            "cpuFit": round(cpu_fit * 100),
            "memoryFit": round(memory_fit * 100),
            "score": round(score, 3),
            "cost": vm["cost"],
            "remainingMemory": vm["availableMemory"] - memory,
            "estimatedFinish": vm["queueMinutes"] + duration * cpu / vm["totalCpu"],
        })
    return sorted(
        ranked,
        key=lambda item: (
            not item["feasible"],
            -item["score"],
            item["estimatedFinish"] if item["feasible"] else float("inf"),
            item["remainingMemory"],
        ),
    )


def _priority(workload):
    sla_value = {"premium": 30, "standard": 20, "basic": 10}.get(workload.sla, 0)
    wait_minutes = (datetime.now(timezone.utc) - workload.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
    return sla_value + (20 if workload.priority == "High" else 0) + min(wait_minutes / 60, 10)


def _heft_rank(workload, inventory):
    compatible = [
        vm for vm in inventory
        if vm["status"] == "running"
        and (workload.sla != "premium" or vm["tier"] == "premium")
    ]
    if not compatible:
        return 0
    return sum(workload.duration * workload.cpu / vm["totalCpu"] for vm in compatible) / len(compatible)


def _model_directory(app):
    configured = app.config.get("MODEL_DIR")
    return Path(configured) if configured else Path(app.root_path) / "models"


def _trained_models(app):
    directory = _model_directory(app)
    required_files = (*MODEL_FILES, SCHEMA_FILE, METRICS_FILE)
    return all((directory / filename).is_file() for filename in required_files)


def _prediction_input(payload):
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    rules = {
        "activeUsers": ("Active users", 0, 1000000),
        "processCount": ("Process count", 1, 100000),
        "vmCpuCores": ("VM CPU cores", 1, 4096),
        "cpuSpeedGHz": ("CPU speed", 0.1, 10),
        "vmMemoryGb": ("VM memory", 0.1, 100000),
        "memoryRequestedGb": ("Requested memory", 0.1, 100000),
    }
    record = {}
    for field, (label, minimum, maximum) in rules.items():
        value, error = _number(payload.get(field), label, minimum, maximum)
        if error:
            return None, error
        record[field] = value

    for field, label in (("dataSource", "Data source"), ("taskType", "Task type")):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
            return None, f"{label} is required."
        record[field] = value.strip()
    return record, None


def _training_record(payload, index):
    record, error = _prediction_input(payload)
    if error:
        return None, f"Record {index + 1}: {error}"
    cpu_target, error = _number(payload.get("cpuTarget"), f"Record {index + 1} CPU target", 0, 100)
    if error:
        return None, error
    memory_target, error = _number(payload.get("memoryTargetGb"), f"Record {index + 1} memory target", 0, 100000)
    if error:
        return None, error
    record["cpuTarget"] = cpu_target
    record["memoryTargetGb"] = memory_target
    return record, None


def _bearer_token():
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY") or "local-development-only-change-before-deploy",
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL") or f"sqlite:///{Path(__file__).with_name('orchestrator.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TOKEN_MAX_AGE_SECONDS=12 * 60 * 60,
        MAX_CONTENT_LENGTH=1024 * 1024,
        MODEL_DIR=os.getenv("MODEL_DIR") or str(Path(__file__).with_name("models")),
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    tokens = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="smart-cloud-session")

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    def authenticated(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            token = _bearer_token()
            if not token:
                return jsonify(error="Authentication required."), 401
            try:
                payload = tokens.loads(token, max_age=app.config["TOKEN_MAX_AGE_SECONDS"])
                user_id = int(payload["user_id"])
            except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
                return jsonify(error="Session is invalid or expired. Sign in again."), 401
            user = db.session.get(User, user_id)
            if user is None:
                return jsonify(error="Account no longer exists. Sign in again."), 401
            g.current_user = user
            return handler(*args, **kwargs)
        return wrapped

    def auth_response(user):
        return jsonify(
            token=tokens.dumps({"user_id": user.id}),
            user={"id": user.id, "name": user.name, "email": user.email},
        )

    @app.get("/api/health")
    def health():
        return jsonify(
            status="ok",
            algorithms=["priority-queue", "heft-independent-task-list", "weighted-best-fit", "xgboost"],
            predictionModel="xgboost" if _trained_models(app) else "unavailable",
            integrations={
                "cloudWatch": bool(os.getenv("AWS_REGION") and os.getenv("EC2_INSTANCE_IDS")),
                "s3ModelStorage": bool(os.getenv("MODEL_S3_BUCKET")),
                "mysql": app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"),
            },
        )

    @app.post("/api/auth/register")
    def register():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        name = payload.get("name")
        email = payload.get("email")
        password = payload.get("password")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            return jsonify(error="Name must contain 1 to 100 characters."), 400
        if not isinstance(email, str) or len(email.strip()) > 254 or "@" not in email:
            return jsonify(error="Enter a valid email address."), 400
        if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
            return jsonify(error="Password must contain 8 to 256 characters."), 400
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(error="An account with this email already exists."), 409
        return auth_response(user), 201

    @app.post("/api/auth/login")
    def login():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        email = payload.get("email")
        password = payload.get("password")
        if not isinstance(email, str) or not isinstance(password, str):
            return jsonify(error="Email and password are required."), 400
        user = User.query.filter_by(email=email.strip().lower()).first()
        if user is None or not check_password_hash(user.password_hash, password):
            return jsonify(error="Email or password is incorrect."), 401
        return auth_response(user)

    @app.get("/api/workloads")
    @authenticated
    def list_workloads():
        workloads = Workload.query.filter_by(owner_id=g.current_user.id).order_by(
            Workload.created_at.desc(), Workload.id.desc()
        ).all()
        return jsonify(workloads=[_serialize_workload(workload) for workload in workloads])

    @app.post("/api/workloads")
    @authenticated
    def create_workload():
        payload, error = _workload_data(request.get_json(silent=True))
        if error:
            return jsonify(error=error), 400
        workload = Workload(owner_id=g.current_user.id, **payload)
        db.session.add(workload)
        db.session.commit()
        return jsonify(workload=_serialize_workload(workload)), 201

    @app.get("/api/vms")
    @authenticated
    def list_vms():
        return jsonify(vms=_vm_inventory())

    @app.post("/api/vm-selection")
    @authenticated
    def select_vm():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("sla") not in SLA_TIERS:
            return jsonify(error="Request must include CPU, memory, and a valid SLA tier."), 400
        cpu, error = _number(payload.get("cpu"), "CPU", 0.01, 256)
        if error:
            return jsonify(error=error), 400
        memory, error = _number(payload.get("memory"), "Memory", 0.01, 1024)
        if error:
            return jsonify(error=error), 400
        recommendations = _rank_vms(cpu, memory, payload["sla"], _vm_inventory())
        return jsonify(recommendations=recommendations)

    @app.post("/api/schedule")
    @authenticated
    def schedule_queue():
        queued = Workload.query.filter_by(owner_id=g.current_user.id, status="Queued").all()
        inventory = _vm_inventory()
        ordered = sorted(
            queued,
            key=lambda workload: (
                -_priority(workload),
                -_heft_rank(workload, inventory),
                workload.created_at,
                workload.id,
            ),
        )
        decisions = []
        for workload in ordered:
            inventory = _vm_inventory()
            candidates = _rank_vms(workload.cpu, workload.memory, workload.sla, inventory, workload.duration)
            feasible = [candidate for candidate in candidates if candidate["feasible"]]
            best = min(
                feasible,
                key=lambda candidate: (
                    candidate["estimatedFinish"],
                    -candidate["score"],
                    candidate["remainingMemory"],
                ),
                default=None,
            )
            if best is None:
                reason = "No VM has sufficient available capacity for this workload and SLA."
                decisions.append({
                    "workloadId": workload.id,
                    "workload": workload.name,
                    "status": "unscheduled",
                    "reason": reason,
                })
                db.session.add(SchedulingDecision(
                    owner_id=g.current_user.id,
                    workload_id=workload.id,
                    outcome="unscheduled",
                    reason=reason,
                ))
                continue

            workload.status = "Running"
            workload.allocated = best["vm"]
            workload.scheduled_at = datetime.now(timezone.utc)
            decisions.append({
                "workloadId": workload.id,
                "workload": workload.name,
                "status": "scheduled",
                "vm": best["vm"],
                "score": best["score"],
            })
            db.session.add(SchedulingDecision(
                owner_id=g.current_user.id,
                workload_id=workload.id,
                outcome="scheduled",
                vm_name=best["vm"],
                score=best["score"],
            ))
            db.session.flush()

        db.session.commit()
        current_workloads = Workload.query.filter_by(owner_id=g.current_user.id).order_by(
            Workload.created_at.desc(), Workload.id.desc()
        ).all()
        return jsonify(
            workloads=[_serialize_workload(workload) for workload in current_workloads],
            decisions=decisions,
            scheduled=sum(decision["status"] == "scheduled" for decision in decisions),
            unscheduled=sum(decision["status"] == "unscheduled" for decision in decisions),
        )

    @app.post("/api/predictions")
    @authenticated
    def predict_demand():
        if not _trained_models(app):
            return jsonify(error="Trained workload models are unavailable. Train them from the dataset first."), 503
        record, error = _prediction_input(request.get_json(silent=True))
        if error:
            return jsonify(error=error), 400
        try:
            prediction = predict_workload(record, _model_directory(app))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        return jsonify(prediction)

    @app.get("/api/predictions/metrics")
    @authenticated
    def prediction_metrics():
        if not _trained_models(app):
            return jsonify(error="Trained workload models are unavailable. Train them from the dataset first."), 503
        metrics_path = _model_directory(app) / METRICS_FILE
        return jsonify(model="xgboost", metrics=json.loads(metrics_path.read_text(encoding="utf-8")))

    @app.post("/api/predictions/train")
    @authenticated
    def train_prediction_models():
        payload = request.get_json(silent=True)
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list) or not 20 <= len(records) <= 10000:
            return jsonify(error="Provide between 20 and 10000 workload records."), 400

        training_records = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                return jsonify(error=f"Record {index + 1} must be an object."), 400
            training_record, error = _training_record(record, index)
            if error:
                return jsonify(error=error), 400
            training_records.append(training_record)

        try:
            metrics = train_models(training_records, _model_directory(app))
        except ValueError as error:
            return jsonify(error=str(error)), 400

        directory = _model_directory(app)
        bucket = os.getenv("MODEL_S3_BUCKET")
        if bucket:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            try:
                s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION") or None)
                for filename in (*MODEL_FILES, SCHEMA_FILE, METRICS_FILE):
                    s3.upload_file(str(directory / filename), bucket, f"models/{filename}")
            except (BotoCoreError, ClientError) as error:
                app.logger.exception("Model training succeeded but S3 upload failed.")
                return jsonify(error=f"Models were trained locally, but S3 upload failed: {error}"), 502

        return jsonify(model="xgboost", metrics=metrics), 201

    @app.get("/api/monitoring")
    @authenticated
    def cloudwatch_metrics():
        region = os.getenv("AWS_REGION")
        instance_ids = [value.strip() for value in os.getenv("EC2_INSTANCE_IDS", "").split(",") if value.strip()]
        if not region or not instance_ids:
            return jsonify(error="CloudWatch is not configured. Set AWS_REGION and EC2_INSTANCE_IDS.", configured=False), 503

        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=15)
        client = boto3.client("cloudwatch", region_name=region)
        readings = []
        try:
            for instance_id in instance_ids:
                response = client.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=["Average"],
                )
                datapoints = sorted(response.get("Datapoints", []), key=lambda point: point["Timestamp"])
                readings.append({
                    "instanceId": instance_id,
                    "cpu": round(datapoints[-1]["Average"], 1) if datapoints else None,
                    "timestamp": datapoints[-1]["Timestamp"].isoformat() if datapoints else None,
                    "source": "AWS/EC2 CloudWatch",
                })
        except (BotoCoreError, ClientError) as error:
            app.logger.exception("CloudWatch metric request failed.")
            return jsonify(error=f"CloudWatch request failed: {error}"), 502
        return jsonify(region=region, readings=readings, note="EC2 memory metrics require the CloudWatch agent.")

    @app.get("/api/predictions/forecast")
    @authenticated
    def forecast_ec2_cpu():
        region = os.getenv("AWS_REGION")
        instance_ids = [value.strip() for value in os.getenv("EC2_INSTANCE_IDS", "").split(",") if value.strip()]
        if not region or not instance_ids:
            return jsonify(
                error="CPU forecasting requires AWS_REGION and EC2_INSTANCE_IDS.",
                configured=False,
            ), 503

        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=5)
        forecasts = []
        try:
            client = boto3.client("cloudwatch", region_name=region)
            for instance_id in instance_ids:
                response = client.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=PERIOD_SECONDS,
                    Statistics=["Average"],
                )
                try:
                    datapoints = [
                        {
                            "Timestamp": point["Timestamp"],
                            "Average": float(point["Average"]),
                        }
                        for point in response.get("Datapoints", [])
                    ]
                except (KeyError, TypeError, ValueError, OverflowError) as error:
                    forecasts.append({
                        "instanceId": instance_id,
                        "status": "invalid_data",
                        "forecastCpu": None,
                        "forecastTimestamp": None,
                        "historyCount": 0,
                        "history": [],
                        "error": f"CloudWatch returned an invalid CPU datapoint: {error}",
                    })
                    continue
                if any(
                    not isinstance(point["Timestamp"], datetime)
                    or not math.isfinite(point["Average"])
                    or not 0 <= point["Average"] <= 100
                    for point in datapoints
                ):
                    forecasts.append({
                        "instanceId": instance_id,
                        "status": "invalid_data",
                        "forecastCpu": None,
                        "forecastTimestamp": None,
                        "historyCount": 0,
                        "history": [],
                        "error": "CloudWatch returned a CPU reading outside 0-100%.",
                    })
                    continue
                datapoints.sort(key=lambda point: point["Timestamp"])
                contiguous = []
                for point in datapoints:
                    if contiguous and (
                        point["Timestamp"] - contiguous[-1]["Timestamp"]
                    ).total_seconds() > PERIOD_SECONDS * 1.5:
                        contiguous = []
                    contiguous.append(point)

                history = [
                    {
                        "timestamp": point["Timestamp"].isoformat(),
                        "cpu": round(float(point["Average"]), 1),
                    }
                    for point in contiguous[-72:]
                    if "Average" in point
                ]
                if len(contiguous) < MIN_HISTORY_POINTS:
                    forecasts.append({
                        "instanceId": instance_id,
                        "status": "insufficient_data",
                        "latestCpu": history[-1]["cpu"] if history else None,
                        "latestTimestamp": history[-1]["timestamp"] if history else None,
                        "forecastCpu": None,
                        "forecastTimestamp": None,
                        "historyCount": len(contiguous),
                        "requiredHistory": MIN_HISTORY_POINTS,
                        "history": history,
                        "error": (
                            f"Need at least {MIN_HISTORY_POINTS} consecutive "
                            "five-minute CPU readings."
                        ),
                    })
                    continue

                latest = contiguous[-1]
                if end_time - latest["Timestamp"] > timedelta(minutes=15):
                    forecasts.append({
                        "instanceId": instance_id,
                        "status": "stale_data",
                        "latestCpu": round(float(latest["Average"]), 1),
                        "latestTimestamp": latest["Timestamp"].isoformat(),
                        "forecastCpu": None,
                        "forecastTimestamp": None,
                        "historyCount": len(contiguous),
                        "history": history,
                        "error": "Latest CloudWatch CPU reading is more than 15 minutes old.",
                    })
                    continue

                try:
                    forecast = forecast_cpu([
                        float(point["Average"]) for point in contiguous
                    ])
                except (KeyError, TypeError, ValueError) as error:
                    forecasts.append({
                        "instanceId": instance_id,
                        "status": "invalid_data",
                        "forecastCpu": None,
                        "forecastTimestamp": None,
                        "historyCount": len(contiguous),
                        "history": history,
                        "error": str(error),
                    })
                    continue

                forecasts.append({
                    "instanceId": instance_id,
                    "status": "ready",
                    "latestCpu": round(float(latest["Average"]), 1),
                    "latestTimestamp": latest["Timestamp"].isoformat(),
                    "forecastTimestamp": (
                        latest["Timestamp"] + timedelta(seconds=PERIOD_SECONDS)
                    ).isoformat(),
                    "history": history,
                    **forecast,
                })
        except (BotoCoreError, ClientError) as error:
            app.logger.exception("CloudWatch forecast request failed.")
            return jsonify(error=f"CloudWatch forecast request failed: {error}"), 502

        return jsonify(
            source="AWS/EC2 CloudWatch",
            region=region,
            metric="CPUUtilization",
            periodSeconds=PERIOD_SECONDS,
            horizonMinutes=PERIOD_SECONDS // 60,
            forecasts=forecasts,
            note=(
                "Forecasts use consecutive five-minute EC2 CPU readings. "
                "Memory is not included in the default EC2 CloudWatch metrics."
            ),
        )

    with app.app_context():
        db.create_all()
        if VM.query.count() == 0:
            db.session.add_all(VM(**vm) for vm in DEFAULT_VMS)
            db.session.commit()

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
