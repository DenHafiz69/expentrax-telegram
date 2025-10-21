from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, String, Float, Integer, DateTime, Text, select, delete, update, ForeignKey, func, case, extract, and_
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
    username: Mapped[Optional[str]] = mapped_column(String, unique=True)
    
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Add this relationship to link to user's custom categories
    custom_categories: Mapped[List["CustomCategory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    budget: Mapped[List["Budget"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"
    
# Transaction table
class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    
    # Links to an ID in either default_categories or custom_categories
    category_id: Mapped[int] = mapped_column() 
    # Specifies which table to look in: 'default' or 'custom'
    category_type: Mapped[str] = mapped_column(String(10)) 
    
    user: Mapped["User"] = relationship(back_populates="transactions")
    
    def __repr__(self):
        return f"Transaction(id={self.id}, user_id={self.user_id})"
    
# Default categories
class DefaultCategory(Base):
    __tablename__ = 'default_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10))  # 'income' or 'expense'

    def __repr__(self):
        return f"DefaultCategory(id={self.id}, name='{self.name}')"

# Custom category
class CustomCategory(Base):
    __tablename__ = 'custom_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    user: Mapped["User"] = relationship(back_populates="custom_categories")

    def __repr__(self):
        return f"CustomCategory(id={self.id}, name='{self.name}', user_id={self.user_id})"

# Budget
class Budget(Base):
    __tablename__ = 'budget'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    budgeted_amount: Mapped[float] = mapped_column(Float)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[int] = mapped_column(Integer)
    category_type: Mapped[str] = mapped_column(String(10))

    user: Mapped["User"] = relationship(back_populates="budget")

    def __repr__(self):
        return f"Budget(id={self.id}, user_id={self.user_id})"
    
# Create tables
Base.metadata.create_all(engine)

def save_user(id, username):
    with Session(engine) as session:
        user = User(
            id=id,
            username=username
        )
        session.add(user)
        session.commit()
        
    logger.info("User saved to database: %s", user)
    
def save_transaction(
    user_id: int, 
    type_of_transaction: str, 
    amount: float,
    description: str, 
    timestamp: datetime,
    category_id: int,
    category_type: str
    ):
    
    transaction = Transaction(
            user_id=user_id,
            type_of_transaction=type_of_transaction,
            amount=amount,
            description=description, 
            timestamp=timestamp,
            category_id=category_id,
            category_type=category_type
        )
    
    with Session(engine) as session:
        session.add(transaction)
        session.commit()
    
def read_user(id: int):
    
    stmt = select(User).where(User.id == id)
    
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
    
def add_custom_category(user_id: int, name: str, type_of_transaction: str):
    '''Add custom category to user'''
    category = CustomCategory(
        user_id=user_id,
        name=name,
        type_of_transaction=type_of_transaction
    )
    
    with Session(engine) as session:
        session.add(category)
        session.commit()
        
def get_category_id(category_name: str):
    '''Get category ID from category name'''
    
    stmt = select(DefaultCategory.id).where(DefaultCategory.name == category_name)

    with Session(engine) as session:
        result = session.execute(stmt).scalar_one_or_none()

    if result:
        return result

    else:
        stmt = select(CustomCategory.id).where(CustomCategory.name == category_name)
        with Session(engine) as session:
            result = session.execute(stmt).scalar_one()

        return result

def get_categories_name(type_of_transaction: str, user_id: int = 0):
    '''Get all categories'''
    
    # SQL query for default and custom categories
    stmt_default = select(DefaultCategory.name).where(DefaultCategory.type_of_transaction == type_of_transaction)
    stmt_custom = select(CustomCategory.name).where(CustomCategory.type_of_transaction == type_of_transaction)
    
    # Run the query
    with Session(engine) as session:
        default_categories = session.execute(stmt_default).scalars().all()
        custom_categories = session.execute(stmt_custom).scalars().all()
    
    categories_name = default_categories + custom_categories
    
    return categories_name

def get_category_type(category_id: int):

    stmt_default = select(DefaultCategory.type_of_transaction).where(DefaultCategory.id == category_id)

    with Session(engine) as session:
        result = session.execute(stmt_default).scalar_one_or_none()

    if result:
        return result

    else:
        stmt_custom = select(CustomCategory.type_of_transaction).where(CustomCategory.id == category_id)

        with Session(engine) as session:
            result = session.execute(stmt_custom).scalar_one_or_none()
            return result
        

def get_category_name_by_id(id: int):
    '''Get category name with id'''

    stmt_default = select(DefaultCategory.name).where(DefaultCategory.id == id)
    stmt_custom = select(CustomCategory.name).where(CustomCategory.id == id)

    with Session(engine) as session:
        result = session.execute(stmt_default).scalar_one_or_none()

    if result:
        return result
    else:
        with Session(engine) as session:
            result = session.execute(stmt_custom).scalar_one_or_none()
            return result

def get_custom_categories_name_and_id(user_id: int, type_of_transaction: str):

    stmt = select(CustomCategory.name).where(CustomCategory.user_id == user_id).where(CustomCategory.type_of_transaction == type_of_transaction)

    with Session(engine) as session:
        result = session.execute(stmt).scalars().all()

    return result

def delete_category(user_id: int, category_id: int):
    '''Delete category'''
    stmt = delete(CustomCategory).where(CustomCategory.id == category_id).where(CustomCategory.user_id == user_id) # Only CustomCategory can be deleted
    
    with Session(engine) as session:
        session.execute(stmt)
        session.commit()

# Budget queries

def set_budget(user_id: int, budgeted_amount:float, category_id: int, category_type: str, month: int, year: int):
    '''Set budget for a user for a category'''
    budget = Budget(
        user_id=user_id,
        budgeted_amount=budgeted_amount,
        year=year,
        month=month,
        category_id=category_id,
        category_type=category_type
    )

    with Session(engine) as session:
        session.add(budget)
        session.commit()

def change_budget(user_id:int, budgeted_amount:float, category_id: int, category_type: str, changed_month: int):
    '''Change budget for this month or next month'''
    stmt = (
        update(Budget.budgeted_amount)
        .where(Budget.user_id == user_id)
        .where(Budget.category_id == category_id)
        .where(Budget.category_type == category_type)
    )

    with Session(engine) as session:
        session.execute(stmt)
        session.commit()

def check_budget(user_id: int):
    '''Send the whole budget for the user'''
    stmt = (
        select(Budget)
        .where(Budget.user_id == user_id)
    )

    with Session(engine) as session:
        session.execute(stmt)
        session.commit()
    
# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)
