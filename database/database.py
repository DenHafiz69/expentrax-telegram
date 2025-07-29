# database/database.py

from sqlalchemy import create_engine, extract, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from collections import defaultdict
import logging

# Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Setup
DATABASE_URL = "sqlite:///transactions.db"
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
def get_recent_expenses(chat_id, limit=10):
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

# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)
