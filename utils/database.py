from datetime import datetime
from typing import List
from sqlalchemy import create_engine, String, Float, DateTime, Text, select, ForeignKey, func, case, extract, and_
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
    
    stmt = select(Transaction.timestamp).distinct().where(Transaction.user_id == user_id)
    
    with Session(engine) as session:
        distinct_timestamp = session.execute(stmt).scalars().all()

        if period == "yearly":
            return sorted({d.strftime('%Y') for d in distinct_timestamp}, reverse=True)

        elif period == "monthly":
            return sorted({d.strftime('%b %Y') for d in distinct_timestamp}, reverse=True)
        
        elif period == "weekly":
            return sorted({d.strftime('Week %U %Y') for d in distinct_timestamp}, reverse=True)
    
def get_period_total(user_id: int, period_type: str, target_year: int, target_month: int = None, target_week: int = None):
    """
    Calculates the total income and expense for a given user over a specified
    period (week, month, or year).

    Args:
        user_id: The ID of the user.
        period_type: The time period ('week', 'month', or 'year').
        target_year: The target year (e.g., 2025).
        target_month: The target month (1-12), required for 'month'.
        target_week: The target week number, required for 'week'.
    """
    
    # --- 1. Common Logic: Define income and expense cases ---
    income_amount = case(
        (Transaction.type_of_transaction == "income", Transaction.amount),
        else_=0
    )
    
    expense_amount = case(
        (Transaction.type_of_transaction == "expense", Transaction.amount),
        else_=0
    )

    # --- 2. Dynamic Query Building ---
    # Start with the base select statement
    stmt = select(
        extract('year', Transaction.timestamp).label("year"),
        func.sum(income_amount).label("total_income"),
        func.sum(expense_amount).label("total_expense")
    )

    # Base where and group_by clauses
    where_conditions = [
        Transaction.user_id == user_id,
        extract('year', Transaction.timestamp) == target_year
    ]
    group_by_columns = [extract('year', Transaction.timestamp)]

    # Dynamically add clauses based on the period_type
    if period_type == 'month':
        if not target_month:
            raise ValueError("target_month is required for 'month' period type")
        # Add month extraction to select, where, and group_by
        stmt = stmt.add_columns(extract('month', Transaction.timestamp).label("month"))
        where_conditions.append(extract('month', Transaction.timestamp) == target_month)
        group_by_columns.append(extract('month', Transaction.timestamp))

    elif period_type == 'week':
        if not target_week:
            raise ValueError("target_week is required for 'week' period type")
        # Add week extraction to select, where, and group_by
        stmt = stmt.add_columns(extract('week', Transaction.timestamp).label("week"))
        where_conditions.append(extract('week', Transaction.timestamp) == target_week)
        group_by_columns.append(extract('week', Transaction.timestamp))

    elif period_type != 'year':
        raise ValueError("Invalid period_type. Choose from 'week', 'month', or 'year'.")

    # Finalize the statement with the dynamic clauses
    stmt = stmt.where(and_(*where_conditions)).group_by(*group_by_columns)

    # --- 3. Execute the Query ---
    with Session(engine) as session:
        result = session.execute(stmt).first()
        return result

    
# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)