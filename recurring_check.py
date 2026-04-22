import logging
from utils.database import init_db
from utils.scheduler import check_recurring_transactions

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def check_transactions_cron(request):
    """
    Cloud Function entry point for checking recurring transactions.
    Triggered by Google Cloud Scheduler.
    """
    logger.info("Starting recurring transaction check...")
    init_db()
    check_recurring_transactions()
    logger.info("Recurring transaction check finished.")
    return "OK", 200
