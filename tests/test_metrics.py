import asyncio
import unittest
from prometheus_client import REGISTRY

from utils.metrics import (
    DB_QUERY_DURATION,
    HANDLER_DURATION,
    TELEGRAM_ERRORS,
    TELEGRAM_UPDATES,
    TRANSACTIONS_LOGGED,
    track_handler,
)


class TestMetrics(unittest.TestCase):
    def test_metrics_registration(self):
        registered_metric_names = [m.name for m in REGISTRY.collect()]
        self.assertIn("expentrax_telegram_updates", registered_metric_names)
        self.assertIn("expentrax_telegram_errors", registered_metric_names)
        self.assertIn("expentrax_transactions_logged", registered_metric_names)
        self.assertIn("expentrax_telegram_handler_duration_seconds", registered_metric_names)
        self.assertIn("expentrax_db_query_duration_seconds", registered_metric_names)

    def test_transactions_logged_metric(self):
        before = TRANSACTIONS_LOGGED.labels(type="expense", category="Food")._value.get()
        TRANSACTIONS_LOGGED.labels(type="expense", category="Food").inc()
        after = TRANSACTIONS_LOGGED.labels(type="expense", category="Food")._value.get()
        self.assertEqual(after, before + 1)

    def test_track_handler_decorator_success(self):
        @track_handler("test_success_handler")
        async def sample_handler():
            await asyncio.sleep(0.01)
            return "ok"

        res = asyncio.run(sample_handler())
        self.assertEqual(res, "ok")
        count = TELEGRAM_UPDATES.labels(handler="test_success_handler", status="success")._value.get()
        self.assertGreaterEqual(count, 1)

    def test_track_handler_decorator_error(self):
        @track_handler("test_error_handler")
        async def failing_handler():
            raise ValueError("Test failure")

        with self.assertRaises(ValueError):
            asyncio.run(failing_handler())

        err_count = TELEGRAM_ERRORS.labels(
            handler="test_error_handler", error_type="ValueError"
        )._value.get()
        self.assertGreaterEqual(err_count, 1)


if __name__ == "__main__":
    unittest.main()
