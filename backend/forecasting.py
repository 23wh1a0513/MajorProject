import math


PERIOD_SECONDS = 300
MIN_HISTORY_POINTS = 120
MIN_BACKTEST_POINTS = 20
CPU_MAE_LIMIT = 10
CPU_R2_LIMIT = 0.8


def _forecast(values, method):
    history = values[-6:]
    if method == "last_value":
        prediction = history[-1]
    elif method == "mean_3":
        prediction = sum(history[-3:]) / min(3, len(history))
    elif method == "mean_6":
        prediction = sum(history) / len(history)
    elif method == "trend_6":
        count = len(history)
        x_mean = (count - 1) / 2
        y_mean = sum(history) / count
        denominator = sum((index - x_mean) ** 2 for index in range(count))
        slope = sum(
            (index - x_mean) * (value - y_mean)
            for index, value in enumerate(history)
        ) / denominator
        prediction = y_mean + slope * (count - x_mean)
    else:
        raise ValueError(f"Unknown forecast method: {method}.")
    return min(100, max(0, prediction))


def _metrics(actual, predicted):
    errors = [target - value for target, value in zip(actual, predicted)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mean = sum(actual) / len(actual)
    total_variation = sum((target - mean) ** 2 for target in actual)
    residual_variation = sum(error * error for error in errors)
    r2 = 1 - residual_variation / total_variation if total_variation else None
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4) if r2 is not None else None,
    }


def forecast_cpu(values):
    series = [float(value) for value in values]
    if any(not math.isfinite(value) or not 0 <= value <= 100 for value in series):
        raise ValueError("CPU utilization readings must be finite percentages from 0 to 100.")
    if len(series) < MIN_HISTORY_POINTS:
        raise ValueError(f"At least {MIN_HISTORY_POINTS} consecutive readings are required.")

    calibration_start = int(len(series) * 0.6)
    test_start = int(len(series) * 0.8)
    methods = ("last_value", "mean_3", "mean_6", "trend_6")
    calibration_losses = {}
    for method in methods:
        predictions = [
            _forecast(series[:index], method)
            for index in range(calibration_start, test_start)
        ]
        actual = series[calibration_start:test_start]
        calibration_losses[method] = sum(
            abs(target - prediction)
            for target, prediction in zip(actual, predictions)
        ) / len(actual)

    selected_method = min(methods, key=lambda method: calibration_losses[method])
    test_predictions = [
        _forecast(series[:index], selected_method)
        for index in range(test_start, len(series))
    ]
    test_actual = series[test_start:]
    backtest = _metrics(test_actual, test_predictions)
    backtest["samples"] = len(test_actual)
    backtest["baselineMae"] = _metrics(
        test_actual,
        [series[index - 1] for index in range(test_start, len(series))],
    )["mae"]
    meets_acceptance = (
        len(test_actual) >= MIN_BACKTEST_POINTS
        and backtest["mae"] <= CPU_MAE_LIMIT
        and backtest["r2"] is not None
        and backtest["r2"] >= CPU_R2_LIMIT
    )
    return {
        "forecastCpu": round(_forecast(series, selected_method), 1),
        "method": selected_method,
        "backtest": backtest,
        "meetsAcceptance": meets_acceptance,
        "historyCount": len(series),
    }
