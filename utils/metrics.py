import functools
import logging
import time
from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)

# --- Metrics Definitions ---

TELEGRAM_UPDATES = Counter(
    "expentrax_telegram_updates_total",
    "Total Telegram updates processed",
    ["handler", "status"],
)

HANDLER_DURATION = Histogram(
    "expentrax_telegram_handler_duration_seconds",
    "Duration of Telegram handler execution in seconds",
    ["handler"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TELEGRAM_ERRORS = Counter(
    "expentrax_telegram_errors_total",
    "Total errors encountered during update or handler processing",
    ["handler", "error_type"],
)

TRANSACTIONS_LOGGED = Counter(
    "expentrax_transactions_logged_total",
    "Total transactions logged by users",
    ["type", "category"],
)

DB_QUERY_DURATION = Histogram(
    "expentrax_db_query_duration_seconds",
    "Database query execution duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 3.0),
)


def track_handler(handler_name: str):
    """Decorator to measure handler execution time and track success/error counts."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                TELEGRAM_UPDATES.labels(handler=handler_name, status="success").inc()
                return result
            except Exception as e:
                TELEGRAM_UPDATES.labels(handler=handler_name, status="error").inc()
                TELEGRAM_ERRORS.labels(
                    handler=handler_name, error_type=type(e).__name__
                ).inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                HANDLER_DURATION.labels(handler=handler_name).observe(duration)

        return wrapper

    return decorator


_server_started = False


def start_metrics_server(port: int = 9090) -> bool:
    """Starts the Prometheus HTTP metrics exporter server in a background daemon thread."""
    global _server_started
    if _server_started:
        return True
    try:
        start_http_server(port)
        _server_started = True
        logger.info("Prometheus metrics server started on port %s", port)
        return True
    except Exception as e:
        logger.warning("Could not start Prometheus metrics server on port %s: %s", port, e)
        return False
