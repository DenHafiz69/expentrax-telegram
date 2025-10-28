import schedule
import time
import threading
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from utils.database import engine, RecurringTransaction, Transaction, save_transaction

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def check_recurring_transactions():
    with Session(engine) as session:
        today = datetime.now().date()
        stmt = select(RecurringTransaction).where(
            RecurringTransaction.start_date <= today)
        recurring_transactions = session.execute(stmt).scalars().all()

        for trans in recurring_transactions:
            if trans.end_date and trans.end_date.date() < today:
                continue

            last_transaction_stmt = select(Transaction).where(
                Transaction.description == trans.description
            ).order_by(Transaction.timestamp.desc())
            last_transaction = session.execute(
                last_transaction_stmt).scalar_one_or_none()

            should_create = False
            if not last_transaction:
                should_create = True
            else:
                last_transaction_date = last_transaction.timestamp.date()
                if trans.frequency == "daily" and (today - last_transaction_date).days >= 1:
                    should_create = True
                elif trans.frequency == "weekly" and (today - last_transaction_date).days >= 7:
                    should_create = True
                elif trans.frequency == "monthly" and (today.month != last_transaction_date.month or today.year != last_transaction_date.year):
                    should_create = True

            if should_create:
                save_transaction(
                    user_id=trans.user_id,
                    type_of_transaction=trans.type_of_transaction,
                    amount=trans.amount,
                    description=trans.description,
                    timestamp=datetime.now(),
                    category_id=trans.category_id,
                    category_type=trans.category_type
                )
                logger.info(
                    f"Created recurring transaction for user {trans.user_id}")


def run_scheduler():
    schedule.every().day.at("00:00").do(check_recurring_transactions)
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_scheduler():
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
