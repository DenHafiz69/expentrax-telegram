# populate_db.py

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, create_engine
from sqlalchemy.orm import (
    Mapped,
    Session,
    declarative_base,
    mapped_column,
    relationship,
)

# --- 1. Database Setup and Model Definitions (Assuming your models are in this file) ---

# Define the Base for declarative models
Base = declarative_base()

# Define the database engine (Using SQLite in memory for this example)
# For persistence, change to: "sqlite:///expentrax.db"
Engine = create_engine("sqlite:///data/expentrax.db", echo=False)


# --- Define Models (Schema from previous conversation) ---

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    custom_categories: Mapped[list["CustomCategory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
class DefaultCategory(Base):
    __tablename__ = 'default_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10)) 
    
class CustomCategory(Base):
    __tablename__ = 'custom_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    user: Mapped["User"] = relationship(back_populates="custom_categories")

class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type_of_transaction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    
    # Polymorphic category link columns
    category_id: Mapped[int] = mapped_column() 
    category_type: Mapped[str] = mapped_column(String(10)) 
    
    user: Mapped["User"] = relationship(back_populates="transactions")

# --- 2. Sample Data (from CSV format) ---

USER_DATA = [
    {'id': 1, 'chat_id': 111222333, 'username': 'alice'},
    {'id': 2, 'chat_id': 444555666, 'username': 'bob'},
]

# Using a subset of IDs to match transaction data
DEFAULT_CATEGORY_DATA = [
    {'id': 1, 'name': 'Food', 'type_of_transaction': 'expense'},
    {'id': 2, 'name': 'Transport', 'type_of_transaction': 'expense'},
    {'id': 4, 'name': 'Bills', 'type_of_transaction': 'expense'},
    {'id': 7, 'name': 'Entertainment', 'type_of_transaction': 'expense'},
    {'id': 8, 'name': 'Salary', 'type_of_transaction': 'income'},
    {'id': 10, 'name': 'Investment', 'type_of_transaction': 'income'},
]

CUSTOM_CATEGORY_DATA = [
    {'id': 101, 'user_id': 1, 'name': 'Side Hustle', 'type_of_transaction': 'income'},
    {'id': 102, 'user_id': 1, 'name': 'Gaming', 'type_of_transaction': 'expense'},
    {'id': 103, 'user_id': 2, 'name': 'Groceries', 'type_of_transaction': 'expense'},
    {'id': 104, 'user_id': 2, 'name': 'Freelance', 'type_of_transaction': 'income'},
]

TRANSACTION_DATA = [
    # Alice (user_id 1) transactions
    {'id': 1, 'user_id': 1, 'type_of_transaction': 'income', 'amount': 4500.00, 'description': 'Monthly Salary', 'timestamp': '2025-09-25 09:00:00', 'category_id': 8, 'category_type': 'default'},
    {'id': 2, 'user_id': 1, 'type_of_transaction': 'expense', 'amount': 25.50, 'description': 'Lunch with colleagues', 'timestamp': '2025-09-25 12:30:00', 'category_id': 1, 'category_type': 'default'},
    {'id': 3, 'user_id': 1, 'type_of_transaction': 'expense', 'amount': 55.00, 'description': 'Weekly bus pass', 'timestamp': '2025-09-28 08:00:00', 'category_id': 2, 'category_type': 'default'},
    {'id': 4, 'user_id': 1, 'type_of_transaction': 'income', 'amount': 350.00, 'description': 'Web design project', 'timestamp': '2025-09-29 18:00:00', 'category_id': 101, 'category_type': 'custom'},
    {'id': 5, 'user_id': 1, 'type_of_transaction': 'expense', 'amount': 79.90, 'description': 'New video game', 'timestamp': '2025-09-30 20:00:00', 'category_id': 102, 'category_type': 'custom'},
    {'id': 8, 'user_id': 1, 'type_of_transaction': 'expense', 'amount': 120.00, 'description': 'Electricity bill', 'timestamp': '2025-10-05 11:00:00', 'category_id': 4, 'category_type': 'default'},
    {'id': 11, 'user_id': 1, 'type_of_transaction': 'expense', 'amount': 45.00, 'description': 'Movie tickets', 'timestamp': '2025-10-08 21:00:00', 'category_id': 7, 'category_type': 'default'},
    
    # Bob (user_id 2) transactions
    {'id': 6, 'user_id': 2, 'type_of_transaction': 'income', 'amount': 5200.00, 'description': 'October salary', 'timestamp': '2025-10-01 09:05:00', 'category_id': 8, 'category_type': 'default'},
    {'id': 7, 'user_id': 2, 'type_of_transaction': 'expense', 'amount': 250.75, 'description': 'Weekly grocery run', 'timestamp': '2025-10-03 17:45:00', 'category_id': 103, 'category_type': 'custom'},
    {'id': 9, 'user_id': 2, 'type_of_transaction': 'income', 'amount': 750.00, 'description': 'Logo design work', 'timestamp': '2025-10-06 15:20:00', 'category_id': 104, 'category_type': 'custom'},
    {'id': 10, 'user_id': 2, 'type_of_transaction': 'expense', 'amount': 150.00, 'description': 'Internet bill', 'timestamp': '2025-10-07 10:00:00', 'category_id': 4, 'category_type': 'default'},
]


# --- 3. Population Functions ---

def populate_database():
    """Drops tables, recreates them, and populates with sample data."""
    print("Starting database population script...")
    
    # 1. Drop and Create Tables
    print("Dropping and recreating all tables...")
    Base.metadata.drop_all(Engine)
    Base.metadata.create_all(Engine)
    
    # 2. Populate Data (Must respect foreign key order)
    with Session(Engine) as session:
        # A. Users
        session.add_all([User(**data) for data in USER_DATA])
        print(f"  -> Added {len(USER_DATA)} users.")

        # B. Default Categories
        session.add_all([DefaultCategory(**data) for data in DEFAULT_CATEGORY_DATA])
        print(f"  -> Added {len(DEFAULT_CATEGORY_DATA)} default categories.")
        
        # C. Custom Categories
        session.add_all([CustomCategory(**data) for data in CUSTOM_CATEGORY_DATA])
        print(f"  -> Added {len(CUSTOM_CATEGORY_DATA)} custom categories.")

        # D. Transactions (Requires date parsing)
        transactions = []
        date_format = '%Y-%m-%d %H:%M:%S'
        for data in TRANSACTION_DATA:
            # Convert string timestamp to datetime object
            data['timestamp'] = datetime.strptime(
                data['timestamp'], date_format
            ).replace(tzinfo=UTC)
            transactions.append(Transaction(**data))
        
        session.add_all(transactions)
        print(f"  -> Added {len(transactions)} transactions.")

        # Final Commit
        session.commit()
        print("Database population complete. All data committed. ✅")

# --- 4. Execution ---

if __name__ == "__main__":
    populate_database()