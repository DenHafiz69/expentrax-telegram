# database/database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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

# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)
