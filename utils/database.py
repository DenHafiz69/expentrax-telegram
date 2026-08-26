from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    create_engine,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    select,
    delete,
    update,
    ForeignKey,
    func,
    case,
    extract,
    and_,
)
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, Mapped, relationship
import os
import logging

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Database Connection Setup ---

# Function to initialize the database connection pool


def init_connection_pool() -> create_engine:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        logger.info("Using external database configuration.")
        engine = create_engine(database_url)
    else:
        db_host = os.environ.get("DB_HOST")
        if db_host:
            import boto3
            import json
            from sqlalchemy.engine import URL

            db_port = os.environ.get("DB_PORT", "5432")
            db_name = os.environ.get("DB_NAME")
            db_secret_arn = os.environ.get("DB_SECRET_ARN")

            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=db_secret_arn)
            credentials = json.loads(response["SecretString"])

            url = URL.create(
                drivername="postgresql",
                username=credentials["username"],
                password=credentials["password"],
                host=db_host,
                port=int(db_port),
                database=db_name,
            )
            logger.info("Using RDS PostgreSQL database.")
            engine = create_engine(url)
        else:
            logger.info("Local environment detected. Using SQLite.")
            os.makedirs("data", exist_ok=True)
            engine = create_engine("sqlite:///data/expentrax.db")

    return engine


# Initialize the engine
engine = init_connection_pool()


class Base(DeclarativeBase):
    pass


# --- Model Definitions ---


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String, unique=True)
    currency: Mapped[Optional[str]] = mapped_column(String(5), default="RM")

    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recurring_transactions: Mapped[List["RecurringTransaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    custom_categories: Mapped[List["CustomCategory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    budget: Mapped[List["Budget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    category_id: Mapped[int] = mapped_column()
    category_type: Mapped[str] = mapped_column(String(10))
    user: Mapped["User"] = relationship(back_populates="transactions")

    def __repr__(self):
        return f"Transaction(id={self.id}, user_id={self.user_id})"


class DefaultCategory(Base):
    __tablename__ = "default_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10))

    def __repr__(self):
        return f"DefaultCategory(id={self.id}, name='{self.name}')"


class CustomCategory(Base):
    __tablename__ = "custom_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="custom_categories")

    def __repr__(self):
        return (
            f"CustomCategory(id={self.id}, name='{self.name}', user_id={self.user_id})"
        )


class Budget(Base):
    __tablename__ = "budget"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    budgeted_amount: Mapped[float] = mapped_column(Float)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[int] = mapped_column(Integer)
    category_type: Mapped[str] = mapped_column(String(10))
    user: Mapped["User"] = relationship(back_populates="budget")

    def __repr__(self):
        return f"Budget(id={self.id}, user_id={self.user_id})"


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(Integer)
    category_type: Mapped[str] = mapped_column(String(10))
    frequency: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    user: Mapped["User"] = relationship(back_populates="recurring_transactions")

    def __repr__(self):
        return f"RecurringTransaction(id={self.id}, user_id={self.user_id})"


# --- Database Initialization ---
_db_initialized = False


def init_db():
    """
    Initializes the database by creating all tables if they don't exist.
    This function is idempotent and safe to call multiple times.
    """
    global _db_initialized
    if not _db_initialized:
        Base.metadata.create_all(bind=engine)
        _db_initialized = True


# --- Database Functions (unchanged) ---


def save_user(id, username):
    with Session(engine) as session:
        user = User(id=id, username=username)
        session.add(user)
        session.commit()
    logger.info("User saved to database: %s", user.username)


def save_transaction(
    user_id: int,
    type_of_transaction: str,
    amount: float,
    description: str,
    timestamp: datetime,
    category_id: int,
    category_type: str,
):
    transaction = Transaction(
        user_id=user_id,
        type_of_transaction=type_of_transaction,
        amount=amount,
        description=description,
        timestamp=timestamp,
        category_id=category_id,
        category_type=category_type,
    )
    with Session(engine) as session:
        session.add(transaction)
        session.commit()


def save_recurring_transaction(
    user_id: int,
    type_of_transaction: str,
    amount: float,
    description: str,
    category_id: int,
    category_type: str,
    frequency: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
):
    recurring_transaction = RecurringTransaction(
        user_id=user_id,
        type_of_transaction=type_of_transaction,
        amount=amount,
        description=description,
        category_id=category_id,
        category_type=category_type,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
    )
    with Session(engine) as session:
        session.add(recurring_transaction)
        session.commit()


def read_user(id: int):
    stmt = select(User).where(User.id == id)
    with Session(engine) as session:
        user = session.execute(stmt).scalar_one_or_none()
        return user


def get_recent_transactions(user_id: int, limit=3):
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
    )
    with Session(engine) as session:
        transactions = session.execute(stmt).scalars().all()
        return transactions


def get_summary_periods(user_id: int, period: str):
    stmt = (
        select(Transaction.timestamp).distinct().where(Transaction.user_id == user_id)
    )
    with Session(engine) as session:
        distinct_timestamp = session.execute(stmt).scalars().all()
        if period == "yearly":
            return sorted({d.strftime("%Y") for d in distinct_timestamp}, reverse=True)
        elif period == "monthly":
            return sorted(
                {d.strftime("%b %Y") for d in distinct_timestamp}, reverse=True
            )
        elif period == "weekly":
            return sorted(
                {d.strftime("Week %U %Y") for d in distinct_timestamp}, reverse=True
            )


def get_period_total(
    user_id: int,
    period_type: str,
    target_year: int,
    target_month: int = None,
    target_week: int = None,
):
    income_amount = case(
        (Transaction.type_of_transaction == "income", Transaction.amount), else_=0
    )
    expense_amount = case(
        (Transaction.type_of_transaction == "expense", Transaction.amount), else_=0
    )
    stmt = select(
        extract("year", Transaction.timestamp).label("year"),
        func.sum(income_amount).label("total_income"),
        func.sum(expense_amount).label("total_expense"),
    )
    where_conditions = [
        Transaction.user_id == user_id,
        extract("year", Transaction.timestamp) == target_year,
    ]
    group_by_columns = [extract("year", Transaction.timestamp)]
    if period_type == "month":
        if not target_month:
            raise ValueError("target_month is required for 'month' period type")
        stmt = stmt.add_columns(extract("month", Transaction.timestamp).label("month"))
        where_conditions.append(extract("month", Transaction.timestamp) == target_month)
        group_by_columns.append(extract("month", Transaction.timestamp))
    elif period_type == "week":
        if not target_week:
            raise ValueError("target_week is required for 'week' period type")
        stmt = stmt.add_columns(extract("week", Transaction.timestamp).label("week"))
        where_conditions.append(extract("week", Transaction.timestamp) == target_week)
        group_by_columns.append(extract("week", Transaction.timestamp))
    elif period_type != "year":
        raise ValueError("Invalid period_type. Choose from 'week', 'month', or 'year'.")
    stmt = stmt.where(and_(*where_conditions)).group_by(*group_by_columns)
    with Session(engine) as session:
        result = session.execute(stmt).first()
        return result


def add_custom_category(user_id: int, name: str, type_of_transaction: str):
    category = CustomCategory(
        user_id=user_id, name=name, type_of_transaction=type_of_transaction
    )
    with Session(engine) as session:
        session.add(category)
        session.commit()


def get_category_id(category_name: str):
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
    stmt_default = select(DefaultCategory.name).where(
        DefaultCategory.type_of_transaction == type_of_transaction
    )
    stmt_custom = select(CustomCategory.name).where(
        CustomCategory.type_of_transaction == type_of_transaction
    )
    with Session(engine) as session:
        default_categories = session.execute(stmt_default).scalars().all()
        custom_categories = session.execute(stmt_custom).scalars().all()
    categories_name = default_categories + custom_categories
    return categories_name


def get_category_type(category_id: int):
    stmt_default = select(DefaultCategory.type_of_transaction).where(
        DefaultCategory.id == category_id
    )
    with Session(engine) as session:
        result = session.execute(stmt_default).scalar_one_or_none()
    if result:
        return result
    else:
        stmt_custom = select(CustomCategory.type_of_transaction).where(
            CustomCategory.id == category_id
        )
        with Session(engine) as session:
            result = session.execute(stmt_custom).scalar_one_or_none()
            return result


def get_category_name_by_id(id: int):
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
    stmt = (
        select(CustomCategory.name)
        .where(CustomCategory.user_id == user_id)
        .where(CustomCategory.type_of_transaction == type_of_transaction)
    )
    with Session(engine) as session:
        result = session.execute(stmt).scalars().all()
    return result


def delete_category(user_id: int, category_id: int):
    stmt = (
        delete(CustomCategory)
        .where(CustomCategory.id == category_id)
        .where(CustomCategory.user_id == user_id)
    )
    with Session(engine) as session:
        session.execute(stmt)
        session.commit()


def set_budget(
    user_id: int,
    budgeted_amount: float,
    category_id: int,
    category_type: str,
    month: int,
    year: int,
):
    with Session(engine) as session:
        existing_budget = session.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == user_id,
                    Budget.category_id == category_id,
                    Budget.month == month,
                    Budget.year == year,
                )
            )
        ).scalar_one_or_none()
        if existing_budget:
            existing_budget.budgeted_amount = budgeted_amount
        else:
            new_budget = Budget(
                user_id=user_id,
                budgeted_amount=budgeted_amount,
                year=year,
                month=month,
                category_id=category_id,
                category_type=category_type,
            )
            session.add(new_budget)
        session.commit()


def get_budget_by_month(user_id: int, month: int, year: int):
    stmt = select(Budget).where(
        and_(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
    )
    with Session(engine) as session:
        return session.execute(stmt).scalars().all()


def get_spend_by_month(user_id: int, month: int, year: int):
    stmt = (
        select(
            Transaction.category_id, func.sum(Transaction.amount).label("total_spent")
        )
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type_of_transaction == "expense",
                extract("month", Transaction.timestamp) == month,
                extract("year", Transaction.timestamp) == year,
            )
        )
        .group_by(Transaction.category_id)
    )
    with Session(engine) as session:
        return session.execute(stmt).all()


def set_currency(user_id: int, currency_symbol: str):
    stmt = update(User).where(User.id == user_id).values(currency=currency_symbol)
    with Session(engine) as session:
        session.execute(stmt)
        session.commit()


def get_currency(user_id: int) -> str:
    stmt = select(User.currency).where(User.id == user_id)
    with Session(engine) as session:
        return session.execute(stmt).scalar_one()


def delete_user_data(user_id: int):
    with Session(engine) as session:
        session.execute(delete(Transaction).where(Transaction.user_id == user_id))
        session.execute(delete(CustomCategory).where(CustomCategory.user_id == user_id))
        session.execute(delete(Budget).where(Budget.user_id == user_id))
        session.commit()
