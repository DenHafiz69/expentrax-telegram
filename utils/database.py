from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Uncomment to enable SQLAlchemy logging
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Setup
engine = create_engine("sqlite:///data/expentrax.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)

# User table
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    username = Column(String)
    
# Transaction table
class Transactions(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Float)
    category = Column(String)
    description = Column(String)
    date = Column(DateTime)
    
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
    
def save_transaction(user_id, amount, category, description, date):
    session = Session()
    transaction = Transactions(
        user_id=user_id, 
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

def read_transactions(user_id):
    session = Session()
    transactions = session.query(Transactions).filter_by(user_id=user_id).all()
    session.close()
    return transactions
    
# Create the table
def init_db():
    Base.metadata.create_all(bind=engine)