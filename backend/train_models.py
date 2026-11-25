import argparse
import csv
import json
from pathlib import Path

from backend.modeling import train_models


def records_from_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as dataset_file:
        rows = csv.DictReader(dataset_file)
        required = {
            "Data_Source",
            "Task_Type",
            "Number_of_Active_Users",
            "Process_Count",
            "VM_CPU_Cores",
            "CPU_Speed_GHz",
            "VM_Memory_Capacity_MB",
            "Memory_Requested_MB",
            "CPU_Utilization (%)",
            "Memory_Consumption (MB)",
        }
        missing = required.difference(rows.fieldnames or [])
        if missing:
            raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}.")
        records = []
        for line_number, row in enumerate(rows, start=2):
            try:
                records.append({
                    "dataSource": row["Data_Source"].strip(),
                    "taskType": row["Task_Type"].strip(),
                    "activeUsers": float(row["Number_of_Active_Users"]),
                    "processCount": float(row["Process_Count"]),
                    "vmCpuCores": float(row["VM_CPU_Cores"]),
                    "cpuSpeedGHz": float(row["CPU_Speed_GHz"]),
                    "vmMemoryGb": float(row["VM_Memory_Capacity_MB"]) / 1024,
                    "memoryRequestedGb": float(row["Memory_Requested_MB"]) / 1024,
                    "cpuTarget": float(row["CPU_Utilization (%)"]),
                    "memoryTargetGb": float(row["Memory_Consumption (MB)"]) / 1024,
                })
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid numeric value on CSV line {line_number}.") from error
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Train workload CPU and memory regressors from a CSV dataset."
    )
    parser.add_argument("--dataset", required=True, help="Path to the workload CSV file.")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).with_name("models")),
        help="Directory for model files and validation metrics.",
    )
    args = parser.parse_args()
    records = records_from_csv(args.dataset)
    metrics = train_models(records, args.output_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
