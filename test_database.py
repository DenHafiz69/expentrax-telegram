import unittest
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.database import (
    Base,
    Transaction,
    save_transaction,
    get_recent_expenses,
    get_summary_periods,
    get_summary_data,
    engine,
    Session,
)
from datetime import datetime, timedelta

TEST_DATABASE_URL = "sqlite:///test_transactions.db"

class TestDatabaseFunctions(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing
        self.engine = create_engine(TEST_DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        # Remove the test database file after the tests
        if os.path.exists("test_transactions.db"):
            os.remove("test_transactions.db")

    def test_save_transaction(self):
        chat_id = 123456
        transaction_type = "income"
        description = "Test income"
        amount = 100.00
        category = "Salary"

        save_transaction(chat_id, transaction_type, description, amount, category)

        # Query the database to verify the transaction was saved
        transaction = self.session.query(Transaction).filter_by(chat_id=chat_id).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.transaction_type, transaction_type)
        self.assertEqual(transaction.description, description)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.category, category)
        
    def test_get_recent_expenses(self):
        # Create some test expenses
        expense1 = Transaction(chat_id=123, transaction_type='expense', description='Coffee', amount=5.0, category='Food')
        expense2 = Transaction(chat_id=123, transaction_type='expense', description='Lunch', amount=15.0, category='Food')
        expense3 = Transaction(chat_id=456, transaction_type='expense', description='Movie', amount=20.0, category='Entertainment')  # Different chat_id
        self.session.add_all([expense1, expense2, expense3])
        self.session.commit()

        # Retrieve recent expenses for chat_id 123
        expenses = get_recent_expenses(123, limit=2)
        
        # Assert that we only get the recent expenses for the specified chat_id
        self.assertEqual(len(expenses), 2)
        self.assertEqual(expenses[0].description, 'Lunch')
        self.assertEqual(expenses[1].description, 'Coffee')

if __name__ == '__main__':
    unittest.main()