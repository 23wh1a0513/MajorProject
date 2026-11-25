import unittest

from backend.forecasting import forecast_cpu


class CpuForecastTests(unittest.TestCase):
    def test_linear_cpu_history_forecasts_next_window_and_passes_backtest(self):
        readings = [10 + index * 0.25 for index in range(120)]

        result = forecast_cpu(readings)

        self.assertAlmostEqual(result["forecastCpu"], 40.0, places=1)
        self.assertEqual(result["backtest"]["samples"], 24)
        self.assertAlmostEqual(result["backtest"]["mae"], 0.0, places=4)
        self.assertAlmostEqual(result["backtest"]["r2"], 1.0, places=4)
        self.assertTrue(result["meetsAcceptance"])

    def test_forecast_requires_sufficient_valid_percentages(self):
        with self.assertRaisesRegex(ValueError, "At least 120"):
            forecast_cpu([20.0] * 119)

        with self.assertRaisesRegex(ValueError, "from 0 to 100"):
            forecast_cpu([20.0] * 119 + [101.0])


if __name__ == "__main__":
    unittest.main()
