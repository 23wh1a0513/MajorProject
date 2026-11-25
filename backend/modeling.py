import json
import math
from pathlib import Path

import xgboost as xgb


MODEL_FILES = ("cpu_model.json", "memory_model.json")
SCHEMA_FILE = "feature_schema.json"
METRICS_FILE = "metrics.json"
NUMERIC_FEATURES = (
    "activeUsers",
    "processCount",
    "vmCpuCores",
    "cpuSpeedGHz",
    "vmMemoryGb",
    "memoryRequestedGb",
)
CATEGORICAL_FEATURES = ("dataSource", "taskType")
FEATURE_SCALES = {"vmMemoryGb": 1024, "memoryRequestedGb": 1024}


def _encode(record, categories):
    features = []
    for field in NUMERIC_FEATURES:
        value = float(record[field])
        features.append(value * FEATURE_SCALES.get(field, 1))
    for field in CATEGORICAL_FEATURES:
        category = record[field]
        if category not in categories[field]:
            raise ValueError(f"Unsupported {field} value: {category}.")
        features.extend(float(category == option) for option in categories[field])
    return features


def _regression_metrics(actual, predicted):
    errors = [float(target) - float(value) for target, value in zip(actual, predicted)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    actual_mean = sum(actual) / len(actual)
    total_variation = sum((target - actual_mean) ** 2 for target in actual)
    residual_variation = sum(error * error for error in errors)
    r2 = 1 - residual_variation / total_variation if total_variation else 0
    percentage_errors = [
        abs(error / target) * 100
        for target, error in zip(actual, errors)
        if target != 0
    ]
    mape = sum(percentage_errors) / len(percentage_errors) if percentage_errors else 0
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "mape": round(mape, 4),
    }


def train_models(records, directory):
    if not 20 <= len(records) <= 10000:
        raise ValueError("Provide between 20 and 10000 workload records.")

    split = max(2, int(len(records) * 0.8))
    if split >= len(records):
        split = len(records) - 1
    training = records[:split]
    validation = records[split:]
    categories = {
        field: sorted({record[field] for record in training})
        for field in CATEGORICAL_FEATURES
    }
    if any(not values for values in categories.values()):
        raise ValueError("Training records must include task and data-source categories.")

    train_features = [_encode(record, categories) for record in training]
    validation_features = [_encode(record, categories) for record in validation]
    cpu_training_targets = [float(record["cpuTarget"]) for record in training]
    memory_training_targets = [float(record["memoryTargetGb"]) for record in training]
    cpu_validation_targets = [float(record["cpuTarget"]) for record in validation]
    memory_validation_targets = [float(record["memoryTargetGb"]) for record in validation]

    options = {
        "objective": "reg:squarederror",
        "max_depth": 4,
        "eta": 0.05,
        "nthread": 1,
        "seed": 42,
        "verbosity": 0,
    }
    cpu_model = xgb.train(
        options,
        xgb.DMatrix(train_features, label=cpu_training_targets),
        num_boost_round=200,
    )
    memory_model = xgb.train(
        options,
        xgb.DMatrix(train_features, label=memory_training_targets),
        num_boost_round=200,
    )

    cpu_predictions = cpu_model.predict(xgb.DMatrix(validation_features))
    memory_predictions = memory_model.predict(xgb.DMatrix(validation_features))
    cpu_mean = sum(cpu_training_targets) / len(cpu_training_targets)
    memory_mean = sum(memory_training_targets) / len(memory_training_targets)
    metrics = {
        "trainingRecords": len(training),
        "validationRecords": len(validation),
        "targetDefinition": "resource consumption for the same workload record",
        "cpu": _regression_metrics(cpu_validation_targets, cpu_predictions),
        "memory": _regression_metrics(memory_validation_targets, memory_predictions),
        "meanBaseline": {
            "cpu": _regression_metrics(cpu_validation_targets, [cpu_mean] * len(validation)),
            "memory": _regression_metrics(memory_validation_targets, [memory_mean] * len(validation)),
        },
    }

    schema = {
        "categories": categories,
        "numericRanges": {
            field: [
                min(float(record[field]) for record in training),
                max(float(record[field]) for record in training),
            ]
            for field in NUMERIC_FEATURES
        },
        "targetRanges": {
            "cpu": [
                min(cpu_training_targets),
                max(cpu_training_targets),
            ],
            "memory": [
                min(memory_training_targets),
                max(memory_training_targets),
            ],
        },
    }
    model_directory = Path(directory)
    model_directory.mkdir(parents=True, exist_ok=True)
    cpu_model.save_model(str(model_directory / MODEL_FILES[0]))
    memory_model.save_model(str(model_directory / MODEL_FILES[1]))
    (model_directory / SCHEMA_FILE).write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (model_directory / METRICS_FILE).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def predict_workload(record, directory):
    model_directory = Path(directory)
    schema = json.loads((model_directory / SCHEMA_FILE).read_text(encoding="utf-8"))
    metrics = json.loads((model_directory / METRICS_FILE).read_text(encoding="utf-8"))
    features = xgb.DMatrix([_encode(record, schema["categories"])])

    cpu_model = xgb.Booster()
    memory_model = xgb.Booster()
    cpu_model.load_model(str(model_directory / MODEL_FILES[0]))
    memory_model.load_model(str(model_directory / MODEL_FILES[1]))

    cpu_min, cpu_max = schema["targetRanges"]["cpu"]
    memory_min, memory_max = schema["targetRanges"]["memory"]
    cpu_prediction = float(cpu_model.predict(features)[0])
    memory_prediction = float(memory_model.predict(features)[0])
    out_of_training_range = [
        field
        for field in NUMERIC_FEATURES
        if not schema["numericRanges"][field][0]
        <= float(record[field])
        <= schema["numericRanges"][field][1]
    ]
    return {
        "model": "xgboost",
        "cpu": round(min(cpu_max, max(cpu_min, cpu_prediction)), 1),
        "memory": round(min(memory_max, max(memory_min, memory_prediction)), 1),
        "trainingRecords": metrics["trainingRecords"],
        "validationRecords": metrics["validationRecords"],
        "validationMetrics": {
            "cpuMae": metrics["cpu"]["mae"],
            "memoryMae": metrics["memory"]["mae"],
        },
        "outOfTrainingRange": out_of_training_range,
        "method": "Estimated from workload and VM characteristics using the saved XGBoost models.",
    }
