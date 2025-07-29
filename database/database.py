# database/database.py

from sqlalchemy import create_engine, extract, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from collections import defaultdict

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
                start_of_week = min(dates)
                end_of_week = max(dates)
                formatted.append(f"{year}-W{week} ({start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')})")
            return sorted(formatted, reverse=True)

def get_summary_data(chat_id: int, period: str, option: str):
    with Session() as session:
        query = session.query(Transaction).filter(Transaction.chat_id == chat_id)

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
            week_str = option.split()[0]  # "2025-W30"
            year, week = map(int, week_str.split("-W"))
            # get dates in that ISO week
            query = query.all()
            filtered = []
            for t in query:
                if t.timestamp.isocalendar()[0] == year and t.timestamp.isocalendar()[1] == week:
                    filtered.append(t)
            return filtered

        return query.order_by(Transaction.timestamp.asc()).all()

# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)
