# seed_database.py

from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, DeclarativeBase, mapped_column, Mapped, String
# Import your configured engine, SessionLocal, and the DefaultCategory model
# from your_project.database import engine, SessionLocal
# from your_project.models import DefaultCategory

engine = create_engine("sqlite:///data/expentrax.db")

# --- Paste the DEFAULT_CATEGORIES list from Step 1 here ---
DEFAULT_CATEGORIES = [
    {'name': 'Food', 'type_of_transaction': 'expense'},
    {'name': 'Transport', 'type_of_transaction': 'expense'},
    {'name': 'Housing', 'type_of_transaction': 'expense'},
    {'name': 'Bills', 'type_of_transaction': 'expense'},
    {'name': 'Health', 'type_of_transaction': 'expense'},
    {'name': 'Shopping', 'type_of_transaction': 'expense'},
    {'name': 'Entertainment', 'type_of_transaction': 'expense'},
    {'name': 'Salary', 'type_of_transaction': 'income'},
    {'name': 'Bonus', 'type_of_transaction': 'income'},
    {'name': 'Investment', 'type_of_transaction': 'income'},
]

class Base(DeclarativeBase):
    pass

# New table for default categories
class DefaultCategory(Base):
    __tablename__ = 'default_categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type_of_transaction: Mapped[str] = mapped_column(String(10))  # 'income' or 'expense'

    def __repr__(self):
        return f"DefaultCategory(id={self.id}, name='{self.name}')"

def seed_default_categories():
    """
    Populates the default_categories table with initial data.
    Checks if a category already exists before adding it.
    """
    print("Seeding default categories...")
    
    
    
    with Session(engine) as session:
        for cat_data in DEFAULT_CATEGORIES:
            # Check if the category already exists
            stmt = select(DefaultCategory).where(DefaultCategory.name == cat_data['name'])
            existing_category = session.execute(stmt).first()
            
            if not existing_category:
                # If it doesn't exist, create and add it
                new_category = DefaultCategory(
                    name=cat_data['name'],
                    type_of_transaction=cat_data['type_of_transaction']
                )
                session.add(new_category)
                print(f"  -> Added category: {cat_data['name']}")
            else:
                print(f"  -> Category '{cat_data['name']}' already exists, skipping.")
        
        # Commit all the changes at once
        session.commit()
    
    print("Default categories seeding complete. ✅")

# This allows you to run the script directly from the command line
if __name__ == "__main__":
    seed_default_categories()