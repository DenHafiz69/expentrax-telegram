import base64
import json
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram.ext import PersistenceInput

import main
from utils.database import Base
from utils.persistence import SQLAlchemyPersistence


class TestStatelessLambda(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Using StaticPool with check_same_thread=False allows in-memory SQLite sharing across threads
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.test_engine)

    async def test_sqlalchemy_persistence_user_data(self):
        persistence = SQLAlchemyPersistence(
            db_engine=self.test_engine,
            store_data=PersistenceInput(
                bot_data=True, chat_data=True, user_data=True, callback_data=False
            ),
        )

        user_id = 12345
        sample_data = {"type": "Expense", "amount": "45.50", "description": "Coffee"}

        # Update user data
        await persistence.update_user_data(user_id, sample_data)

        # Get all user data
        all_data = await persistence.get_user_data()
        self.assertIn(user_id, all_data)
        self.assertEqual(all_data[user_id]["type"], "Expense")
        self.assertEqual(all_data[user_id]["amount"], "45.50")

        # Test refresh user data in-place
        active_dict = {}
        await persistence.refresh_user_data(user_id, active_dict)
        self.assertEqual(active_dict["description"], "Coffee")

        # Test drop user data
        await persistence.drop_user_data(user_id)
        all_data_after = await persistence.get_user_data()
        self.assertNotIn(user_id, all_data_after)

    async def test_sqlalchemy_persistence_conversations(self):
        persistence = SQLAlchemyPersistence(
            db_engine=self.test_engine,
            store_data=PersistenceInput(
                bot_data=True, chat_data=True, user_data=True, callback_data=False
            ),
        )

        handler_name = "transaction_handler"
        conv_key = (98765, 12345)
        state = 1  # AMOUNT state

        # Update conversation
        await persistence.update_conversation(handler_name, conv_key, state)

        # Retrieve conversations
        convs = await persistence.get_conversations(handler_name)
        self.assertIn(conv_key, convs)
        self.assertEqual(convs[conv_key], 1)

        # Update to another state
        await persistence.update_conversation(handler_name, conv_key, 2)
        convs = await persistence.get_conversations(handler_name)
        self.assertEqual(convs[conv_key], 2)

        # End conversation (new_state is None)
        await persistence.update_conversation(handler_name, conv_key, None)
        convs = await persistence.get_conversations(handler_name)
        self.assertNotIn(conv_key, convs)

    async def test_multi_step_transaction_flow_stateless(self):
        persistence = SQLAlchemyPersistence(
            db_engine=self.test_engine,
            store_data=PersistenceInput(
                bot_data=True, chat_data=True, user_data=True, callback_data=False
            ),
        )

        user_id = 112233
        chat_id = 112233

        # Step 1: User starts transaction -> sets state & user_data
        await persistence.update_conversation("transaction_handler", (chat_id, user_id), 1)
        await persistence.update_user_data(
            user_id, {"type": "Expense", "amount": "25.00", "description": "Groceries"}
        )

        # Step 2: Next invocation simulates a brand new instance accessing the database
        new_persistence = SQLAlchemyPersistence(
            db_engine=self.test_engine,
            store_data=PersistenceInput(
                bot_data=True, chat_data=True, user_data=True, callback_data=False
            ),
        )
        restored_convs = await new_persistence.get_conversations("transaction_handler")
        self.assertEqual(restored_convs.get((chat_id, user_id)), 1)
        restored_u_data = await new_persistence.get_user_data()
        self.assertEqual(restored_u_data[user_id]["description"], "Groceries")

        # Step 3: Conversation completes
        await new_persistence.update_conversation("transaction_handler", (chat_id, user_id), None)
        final_convs = await new_persistence.get_conversations("transaction_handler")
        self.assertNotIn((chat_id, user_id), final_convs)

    def test_lambda_handler_secret_token_validation(self):
        saved_token = os.environ.get("SECRET_TOKEN")
        try:
            os.environ["SECRET_TOKEN"] = "super_secret_123"

            # Unauthorized request (wrong token)
            event_invalid = {
                "headers": {"X-Telegram-Bot-Api-Secret-Token": "wrong_token"},
                "body": json.dumps({"update_id": 1001}),
            }
            response = main.handler(event_invalid, None)
            self.assertEqual(response["statusCode"], 403)

            # Authorized request (correct token)
            event_valid = {
                "headers": {"x-telegram-bot-api-secret-token": "super_secret_123"},
                "body": json.dumps({"update_id": 1002}),
            }
            response = main.handler(event_valid, None)
            self.assertEqual(response["statusCode"], 200)
        finally:
            if saved_token is not None:
                os.environ["SECRET_TOKEN"] = saved_token
            else:
                os.environ.pop("SECRET_TOKEN", None)

    def test_lambda_handler_base64_decoding(self):
        saved_token = os.environ.pop("SECRET_TOKEN", None)
        try:
            raw_body = json.dumps({"update_id": 1003})
            b64_body = base64.b64encode(raw_body.encode("utf-8")).decode("utf-8")

            event = {
                "isBase64Encoded": True,
                "body": b64_body,
            }
            response = main.handler(event, None)
            self.assertEqual(response["statusCode"], 200)
        finally:
            if saved_token is not None:
                os.environ["SECRET_TOKEN"] = saved_token

    def test_lambda_handler_missing_body(self):
        saved_token = os.environ.pop("SECRET_TOKEN", None)
        try:
            event = {"headers": {}}
            response = main.handler(event, None)
            self.assertEqual(response["statusCode"], 400)
        finally:
            if saved_token is not None:
                os.environ["SECRET_TOKEN"] = saved_token

    def test_lambda_handler_invalid_json(self):
        saved_token = os.environ.pop("SECRET_TOKEN", None)
        try:
            event = {"body": "{not valid json"}
            response = main.handler(event, None)
            self.assertEqual(response["statusCode"], 400)
        finally:
            if saved_token is not None:
                os.environ["SECRET_TOKEN"] = saved_token


if __name__ == "__main__":
    unittest.main()
