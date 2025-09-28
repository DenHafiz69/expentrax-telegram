from ast import stmt
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, String, Float, DateTime, Text, select, ForeignKey, extract, desc
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, Mapped, relationship


# Uncomment to enable SQLAlchemy logging
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

import logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# Setup
engine = create_engine("sqlite:///data/expentrax.db")

class Base(DeclarativeBase):
    pass

# User table
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"User(id={self.id}, chat_id={self.chat_id}, username={self.username})"
    
# Transaction table
class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    
    user: Mapped["User"] = relationship(back_populates="transactions")
    
    def __repr__(self):
        return f"Transaction(id={self.id}, user_id={self.user_id}"
    
# Create tables
Base.metadata.create_all(engine)

def save_user(chat_id, username):
    with Session(engine) as session:
        user = User(
            chat_id=chat_id, 
            username=username
        )
        session.add(user)
        session.commit()
        
    logger.info("User saved to database: %s", user)
    
def save_transaction(user_id: int, type_of_transaction: str, amount: float, category: str, description: str, timestamp: datetime):
    with Session(engine) as session:
        transaction = Transaction(
            user_id=user_id,
            type_of_transaction=type_of_transaction,
            amount=amount, 
            category=category, 
            description=description, 
            timestamp=timestamp
        )
        session.add(transaction)
        session.commit()
    
def read_user(chat_id):
    
    stmt = select(User).where(User.chat_id == chat_id)
    
    with Session(engine) as session:
        user = session.execute(stmt).scalar_one_or_none()
        return user

def get_recent_transactions(user_id: int, limit=3):
    
    stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.timestamp.desc()).limit(limit)
    
    with Session(engine) as session:
        transactions = session.execute(stmt).scalars().all()
        return transactions

def get_summary_periods(user_id: int, period: str):
    with Session(engine) as session:
        
        stmt = select(Transaction.timestamp).distinct().where(Transaction.user_id == user_id)
        distinct_timestamp = session.execute(stmt).scalars().all()

        if period == "yearly":
            return sorted({d.strftime('%Y') for d in distinct_timestamp}, reverse=True)

        elif period == "monthly":
            return sorted({d.strftime('%B %Y') for d in distinct_timestamp}, reverse=True)
        
        elif period == "weekly":
            return sorted({d.strftime('%U %Y') for d in distinct_timestamp}, reverse=True)

    
# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)