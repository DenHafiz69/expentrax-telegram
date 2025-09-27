from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, String, Text, select, ForeignKey, extract, desc
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, Mapped, relationship


# Uncomment to enable SQLAlchemy logging
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Setup
engine = create_engine("sqlite:///data/expentrax.db")

class Base(DeclarativeBase):
    pass


# User table
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    username: Mapped[str]
    
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    
# Transaction table
class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_of_transaction: Mapped[str]
    amount: Mapped[float]
    category: Mapped[str]
    description: Mapped[str]
    timestamp: Mapped[datetime]
    
    user: Mapped["User"] = relationship(back_populates="transactions")
    
# Create tables
Base.metadata.create_all(engine)

def save_user(chat_id, username):
    session = Session()
    user = User(
        chat_id=chat_id, 
        username=username
    )
    session.add(user)
    session.commit()
    session.close()
    
def save_transaction(user_id: int, type_of_transaction: str, amount: float, category: str, description: str, date: datetime):
    session = Session()
    transaction = Transaction(
        user_id=user_id,
        type_of_transaction=type_of_transaction,
        amount=amount, 
        category=category, 
        description=description, 
        date=date
    )
    session.add(transaction)
    session.commit()
    session.close()
    
def read_user(chat_id):
    session = Session()
    user = session.query(User).filter_by(chat_id=chat_id).first()
    session.close()
    return user

def get_recent_transactions(user_id: int, limit=3):
    session = Session()
    transactions = (
        session.query(Transaction)
        .filter_by(user_id=user_id)
        .order_by(Transaction.date.desc())
        .limit(limit)
        .all()
    )
    
    session.close()
    return transactions

def get_summary_periods(chat_id: int, period: str):
    with Session() as session:
        query = session.query(Transaction.timestamp).filter(Transaction.chat_id == chat_id)

        if period == "yearly":
            years = query.distinct(extract("year", Transaction.timestamp)).all()
            return sorted({str(d.strftime('%Y')) for d in years}, reverse=True)

        elif period == "monthly":
            months = query.distinct(
                extract("year", Transaction.timestamp),
                extract("month", Transaction.timestamp)
            ).all()
            return sorted({f"{str(d.strftime('%B %Y'))}" for d in months}, reverse=True)
        
        elif period == "weekly":
            weeks = query.distinct(
                extract("week", Transaction.timestamp),
                extract("year", Transaction.timestamp)
            ).order_by(desc("year"), desc("week")).limit(3).all()

            return sorted({f"{str(d.strftime('%B %Y'))}" for d in weeks}, reverse=True)

    
# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)