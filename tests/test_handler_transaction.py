import unittest
from unittest.mock import patch

from telegram.ext import ConversationHandler

from handlers.transaction import (
    AMOUNT,
    CATEGORY,
    DESCRIPTION,
    TYPE,
    amount_handler,
    back_handler,
    cancel_transaction,
    category_handler,
    description_handler,
    start_transaction,
    type_handler,
)
from tests.helpers import (
    create_mock_callback_update,
    create_mock_context,
    create_mock_message_update,
)


class TestTransactionHandler(unittest.IsolatedAsyncioTestCase):
    async def test_start_transaction(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await start_transaction(update, context)

        self.assertEqual(state, TYPE)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("What kind of transaction", args[0])
        self.assertIn("reply_markup", kwargs)

    async def test_type_handler(self):
        update = create_mock_callback_update(data="Expense")
        context = create_mock_context()

        state = await type_handler(update, context)

        self.assertEqual(state, AMOUNT)
        self.assertEqual(context.user_data["type"], "Expense")
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("How much was this transaction?", kwargs["text"])

    async def test_amount_handler_valid(self):
        update = create_mock_message_update(text="125.50")
        context = create_mock_context(user_data={"type": "Expense"})

        state = await amount_handler(update, context)

        self.assertEqual(state, DESCRIPTION)
        self.assertEqual(context.user_data["amount"], "125.50")
        args, _ = update.message.reply_text.call_args
        self.assertIn("short description for this expense", args[0])

    async def test_amount_handler_invalid(self):
        update = create_mock_message_update(text="abc")
        context = create_mock_context(user_data={"type": "Expense"})

        state = await amount_handler(update, context)

        self.assertEqual(state, AMOUNT)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("Invalid amount", args[0])

    @patch("handlers.transaction.get_categories_name")
    async def test_description_handler_expense(self, mock_get_categories):
        mock_get_categories.return_value = ["Food", "Transport", "Rent"]
        update = create_mock_message_update(user_id=123, text="Dinner with friends")
        context = create_mock_context(
            user_data={"type": "Expense", "amount": "50.00"}
        )

        state = await description_handler(update, context)

        self.assertEqual(state, CATEGORY)
        self.assertEqual(context.user_data["description"], "Dinner with friends")
        mock_get_categories.assert_called_once_with("expense", 123)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("Which category best describes this expense?", args[0])
        self.assertIn("reply_markup", kwargs)

    @patch("handlers.transaction.get_categories_name")
    async def test_description_handler_income(self, mock_get_categories):
        mock_get_categories.return_value = ["Salary", "Bonus"]
        update = create_mock_message_update(user_id=456, text="Monthly Salary")
        context = create_mock_context(
            user_data={"type": "Income", "amount": "5000.00"}
        )

        state = await description_handler(update, context)

        self.assertEqual(state, CATEGORY)
        self.assertEqual(context.user_data["description"], "Monthly Salary")
        mock_get_categories.assert_called_once_with("income", 456)
        update.message.reply_text.assert_called_once()

    @patch("handlers.transaction.save_transaction")
    @patch("handlers.transaction.get_currency")
    @patch("handlers.transaction.get_category_type")
    @patch("handlers.transaction.get_category_id")
    async def test_category_handler(
        self,
        mock_get_category_id,
        mock_get_category_type,
        mock_get_currency,
        mock_save_transaction,
    ):
        mock_get_category_id.return_value = 1
        mock_get_category_type.return_value = "custom"
        mock_get_currency.return_value = "$"
        update = create_mock_callback_update(chat_id=123, data="Food")
        context = create_mock_context(
            user_data={
                "type": "Expense",
                "amount": "45.00",
                "description": "Lunch",
            }
        )

        state = await category_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_get_category_id.assert_called_once_with("Food")
        mock_get_category_type.assert_called_once_with(1)
        mock_get_currency.assert_called_once_with(123)
        mock_save_transaction.assert_called_once_with(
            user_id=123,
            type_of_transaction="expense",
            amount=45.00,
            description="Lunch",
            timestamp=update.callback_query.message.date,
            category_id=1,
            category_type="custom",
        )
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Expense added", kwargs["text"])

    async def test_back_handler_description(self):
        update = create_mock_callback_update(data="back_to_description")
        context = create_mock_context(user_data={"type": "Expense"})

        state = await back_handler(update, context)

        self.assertEqual(state, DESCRIPTION)
        update.callback_query.edit_message_text.assert_called_once()

    async def test_back_handler_other(self):
        update = create_mock_callback_update(data="back_to_something_else")
        context = create_mock_context(user_data={"type": "Expense"})

        state = await back_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)

    async def test_cancel_transaction(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await cancel_transaction(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.message.reply_text.assert_called_once_with("❌ Transaction cancelled.")


if __name__ == "__main__":
    unittest.main()
