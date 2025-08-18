# database/database.py

from sqlalchemy import create_engine, extract, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from collections import defaultdict
from config import DEFAULT_CURRENCY, DEFAULT_TIMEZONE, DATABASE_URL
import logging

# Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Setup
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Transaction model
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    transaction_type = Column(String)  # "income" or "expense"
    description = Column(String)
    amount = Column(Float)
    category = Column(String)
    chat_id = Column(Integer)

# User settings model
class UserSettings(Base):
    __tablename__ = "user_settings"
    chat_id = Column(Integer, primary_key=True)
    currency = Column(String, default=DEFAULT_CURRENCY)
    timezone = Column(String, default=DEFAULT_TIMEZONE)

# Budget model
class Budget(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False)
    period = Column(String, nullable=False)  # e.g., "2025-07"
    amount = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint('chat_id', 'period', name='_chat_id_period_uc'),)

# Create tables
Base.metadata.create_all(engine)

# Save function
def save_transaction(chat_id, transaction_type, description, amount, category):
    session = Session()
    transaction = Transaction(
        chat_id=chat_id,
        transaction_type=transaction_type,
        description=description,
        amount=amount,
        category=category,
    )
    session.add(transaction)
    session.commit()
    session.close()

# View function
def get_recent_expenses(chat_id, limit=3):
    session = Session()
    expenses = (
        session.query(Transaction)
        .filter_by(chat_id=chat_id, transaction_type="expense")
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )
    session.close()
    return expenses

def get_user_settings(chat_id: int):
    """Gets user settings, creating them with defaults if they don't exist."""
    session = Session()
    settings = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not settings:
        settings = UserSettings(
            chat_id=chat_id,
            currency=DEFAULT_CURRENCY,
            timezone=DEFAULT_TIMEZONE
        )
        session.add(settings)
        session.commit()
    session.close()
    return settings

def update_user_setting(chat_id: int, key: str, value: str):
    """Updates a specific user setting."""
    session = Session()
    settings = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if settings:
        setattr(settings, key, value)
        session.commit()
    session.close()

def get_search_results(chat_id: int, query: str, page: int = 1, page_size: int = 5):
    """Searches for transactions by description with pagination."""
    session = Session()
    search_query = f"%{query}%"

    # Get total count for pagination
    total_count = (
        session.query(Transaction)
        .filter(Transaction.chat_id == chat_id, Transaction.description.ilike(search_query))
        .count()
    )

    # Get paginated results
    offset = (page - 1) * page_size
    results = (
        session.query(Transaction)
        .filter(Transaction.chat_id == chat_id, Transaction.description.ilike(search_query))
        .order_by(Transaction.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    session.close()
    return results, total_count

def get_summary_periods(chat_id: int, period: str):
    with Session() as session:
        query = session.query(Transaction.timestamp).filter(Transaction.chat_id == chat_id)

        if period == "yearly":
            years = query.distinct(extract("year", Transaction.timestamp)).all()
            return sorted({str(d[0].year) for d in years}, reverse=True)

        elif period == "monthly":
            months = query.distinct(
                extract("year", Transaction.timestamp),
                extract("month", Transaction.timestamp)
            ).all()
            return sorted({f"{d[0].year}-{d[0].month:02d}" for d in months}, reverse=True)

        elif period == "weekly":
            weeks = defaultdict(list)
            for (d,) in query:
                iso_year, iso_week, _ = d.isocalendar()
                weeks[(iso_year, iso_week)].append(d)
            # return formatted like: "2025-W30 (Jul 22 - Jul 28)"
            formatted = []
            for (year, week), dates in weeks.items():
                # Calculate the start date of the week
                start_of_week = datetime.strptime(f"{year}-W{week}-1", "%G-W%V-%u")
                # Calculate the end date of the week (Sunday)
                end_of_week = start_of_week + timedelta(days=6)
                formatted.append(f"{year}-W{week} ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')})")
            return sorted(formatted, reverse=True)

def get_summary_data(chat_id: int, period: str, option: str):
    with Session() as session:
        start_of_week = None
        end_of_week = None

        query = session.query(Transaction).filter(Transaction.chat_id == chat_id).order_by(Transaction.timestamp.asc())

        if period == "yearly":
            year = int(option)
            query = query.filter(extract("year", Transaction.timestamp) == year)

        elif period == "monthly":
            year, month = map(int, option.split("-"))
            query = query.filter(
                extract("year", Transaction.timestamp) == year,
                extract("month", Transaction.timestamp) == month
            )

        elif period == "weekly":
            # option like: "2025-W30"
            week_str = option.split(" ")[0]  # "2025-W30"
            year, week = map(int, week_str.split("-W"))
            # get dates in that ISO week
            start_of_week = datetime.strptime(f"{year}-W{week}-1", "%G-W%V-%u")
            # Go to the start of the next week to make the range exclusive at the end
            end_of_week = start_of_week + timedelta(days=7)

            query = query.filter(Transaction.timestamp >= start_of_week)
            query = query.filter(Transaction.timestamp < end_of_week)

        logging.info(f"get_summary_data: start_of_week={start_of_week}, end_of_week={end_of_week}" if start_of_week and end_of_week else "get_summary_data: No weekly dates")

        logging.info(f"get_summary_data: chat_id={chat_id}, period={period}, option={option}, transaction count={query.count()}")        
        
        return query.all()

def set_or_update_budget(chat_id: int, period: str, amount: float):
    """Sets or updates the budget for a given user and period."""
    with Session() as session:
        budget = session.query(Budget).filter_by(chat_id=chat_id, period=period).first()
        if budget:
            budget.amount = amount
        else:
            budget = Budget(chat_id=chat_id, period=period, amount=amount)
            session.add(budget)
        session.commit()

def get_budget_for_month(chat_id: int, period: str):
    """Retrieves the budget for a given user and period."""
    with Session() as session:
        return session.query(Budget).filter_by(chat_id=chat_id, period=period).first()

def get_all_user_chat_ids():
    """Retrieves all unique chat_ids that have interacted with the bot."""
    with Session() as session:
        # Querying UserSettings is a good way to find active users
        user_chat_ids = session.query(UserSettings.chat_id).distinct().all()
        # .all() returns a list of tuples, so we extract the first element
        return [chat_id[0] for chat_id in user_chat_ids]

# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)
