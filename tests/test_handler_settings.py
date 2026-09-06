import unittest
from unittest.mock import patch

from telegram.ext import ConversationHandler

from handlers.settings import (
    ADD_CATEGORY,
    CHOICE,
    DATABASE_ACTION,
    DELETE_CATEGORIES,
    RESET_DATA_CONFIRM,
    SET_CURRENCY,
    VIEW_CATEGORIES,
    add_category,
    back_settings_handler,
    cancel_settings,
    categories_handler,
    database_action,
    delete_categories,
    reset_data_confirm_handler,
    set_currency_handler,
    start_settings,
    view_categories,
)
from tests.helpers import (
    create_mock_callback_update,
    create_mock_context,
    create_mock_message_update,
)


class TestSettingsHandler(unittest.IsolatedAsyncioTestCase):
    async def test_start_settings(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await start_settings(update, context)

        self.assertEqual(state, CHOICE)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("Welcome to Settings!", args[0])
        self.assertIn("reply_markup", kwargs)

    async def test_categories_handler_add_category(self):
        update = create_mock_callback_update(data="add_category")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, ADD_CATEGORY)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("What type of category you want to add?", kwargs["text"])

    async def test_categories_handler_view_categories(self):
        update = create_mock_callback_update(data="view_categories")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, VIEW_CATEGORIES)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("What would you like to view?", kwargs["text"])

    async def test_categories_handler_delete_categories(self):
        update = create_mock_callback_update(data="delete_categories")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, DELETE_CATEGORIES)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Which would you like to delete?", kwargs["text"])

    async def test_categories_handler_set_currency(self):
        update = create_mock_callback_update(data="set_currency")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, SET_CURRENCY)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Please enter the currency symbol", kwargs["text"])

    async def test_categories_handler_reset_data(self):
        update = create_mock_callback_update(data="reset_data")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, RESET_DATA_CONFIRM)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Are you sure you want to reset all your data?", kwargs["text"])

    async def test_categories_handler_invalid(self):
        update = create_mock_callback_update(data="invalid")
        context = create_mock_context()

        state = await categories_handler(update, context)

        self.assertEqual(state, CHOICE)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Invalid choice", kwargs["text"])

    async def test_add_category(self):
        update = create_mock_callback_update(data="Expense")
        context = create_mock_context()

        state = await add_category(update, context)

        self.assertEqual(state, DATABASE_ACTION)
        self.assertEqual(context.user_data["action"], "add_category")
        self.assertEqual(context.user_data["type_of_transaction"], "Expense")
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Adding a new Expense category!", kwargs["text"])

    @patch("handlers.settings.get_custom_categories_name_and_id")
    async def test_delete_categories(self, mock_get_custom):
        mock_get_custom.return_value = ["Freelance", "Consulting"]
        update = create_mock_callback_update(chat_id=123, data="Income")
        context = create_mock_context()

        state = await delete_categories(update, context)

        self.assertEqual(state, DATABASE_ACTION)
        self.assertEqual(context.user_data["action"], "delete_category")
        mock_get_custom.assert_called_once_with(123, "income")
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Which category would you like to delete?", kwargs["text"])

    @patch("handlers.settings.get_categories_name")
    async def test_database_action_add_category_already_exists(self, mock_get_categories):
        mock_get_categories.return_value = ["Groceries", "Rent"]
        update = create_mock_message_update(chat_id=123, text="Groceries")
        context = create_mock_context(
            user_data={"action": "add_category", "type_of_transaction": "Expense"}
        )

        state = await database_action(update, context)

        self.assertEqual(state, DATABASE_ACTION)
        mock_get_categories.assert_called_once_with("expense", 123)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("already exists", args[0])

    @patch("handlers.settings.add_custom_category")
    @patch("handlers.settings.get_categories_name")
    async def test_database_action_add_category_success(
        self, mock_get_categories, mock_add_category
    ):
        mock_get_categories.return_value = ["Groceries"]
        update = create_mock_message_update(chat_id=123, text="Utilities")
        context = create_mock_context(
            user_data={"action": "add_category", "type_of_transaction": "Expense"}
        )

        state = await database_action(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_add_category.assert_called_once_with(
            user_id=123, name="Utilities", type_of_transaction="expense"
        )
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("has been successfully added", args[0])

    @patch("handlers.settings.add_custom_category")
    @patch("handlers.settings.get_categories_name")
    async def test_database_action_add_category_exception(
        self, mock_get_categories, mock_add_category
    ):
        mock_get_categories.return_value = ["Groceries"]
        mock_add_category.side_effect = RuntimeError("DB connection error")
        update = create_mock_message_update(chat_id=123, text="Utilities")
        context = create_mock_context(
            user_data={"action": "add_category", "type_of_transaction": "Expense"}
        )

        state = await database_action(update, context)

        self.assertEqual(state, ConversationHandler.END)

    @patch("handlers.settings.delete_category")
    @patch("handlers.settings.get_category_id")
    async def test_database_action_delete_category(
        self, mock_get_category_id, mock_delete_category
    ):
        mock_get_category_id.return_value = 10
        update = create_mock_callback_update(chat_id=123, data="OldCategory")
        context = create_mock_context(user_data={"action": "delete_category"})

        state = await database_action(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_get_category_id.assert_called_once_with("OldCategory")
        mock_delete_category.assert_called_once_with(123, 10)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("has been successfully deleted", kwargs["text"])

    @patch("handlers.settings.get_categories_name")
    async def test_view_categories(self, mock_get_categories):
        mock_get_categories.return_value = ["Food", "Transport"]
        update = create_mock_callback_update(chat_id=123, data="Expense")
        context = create_mock_context()

        state = await view_categories(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_get_categories.assert_called_once_with("expense", 123)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Food", kwargs["text"])
        self.assertIn("Transport", kwargs["text"])

    async def test_set_currency_handler_invalid(self):
        update = create_mock_message_update(chat_id=123, text="TOOLONG")
        context = create_mock_context()

        state = await set_currency_handler(update, context)

        self.assertEqual(state, SET_CURRENCY)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("Invalid currency symbol", args[0])

    @patch("handlers.settings.set_currency")
    async def test_set_currency_handler_valid(self, mock_set_currency):
        update = create_mock_message_update(chat_id=123, text="USD")
        context = create_mock_context()

        state = await set_currency_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_set_currency.assert_called_once_with(123, "USD")
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("Your currency has been set to USD", args[0])

    @patch("handlers.settings.delete_user_data")
    async def test_reset_data_confirm_handler_confirm(self, mock_delete_data):
        update = create_mock_callback_update(chat_id=123, data="confirm_reset")
        context = create_mock_context()

        state = await reset_data_confirm_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_delete_data.assert_called_once_with(123)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("All your data has been successfully reset", kwargs["text"])

    @patch("handlers.settings.delete_user_data")
    async def test_reset_data_confirm_handler_cancel(self, mock_delete_data):
        update = create_mock_callback_update(chat_id=123, data="cancel_reset")
        context = create_mock_context()

        state = await reset_data_confirm_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_delete_data.assert_not_called()
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Data reset cancelled", kwargs["text"])

    async def test_back_settings_handler_start(self):
        update = create_mock_callback_update(data="start_settings")
        update.message = update.callback_query.message
        context = create_mock_context()

        state = await back_settings_handler(update, context)

        self.assertEqual(state, CHOICE)

    async def test_back_settings_handler_delete(self):
        update = create_mock_callback_update(data="back_to_delete_choice")
        context = create_mock_context()

        state = await back_settings_handler(update, context)

        self.assertEqual(state, DELETE_CATEGORIES)
        update.callback_query.edit_message_text.assert_called_once()

    async def test_cancel_settings(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await cancel_settings(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.message.reply_text.assert_called_once_with("❌ Settings operation cancelled.")


if __name__ == "__main__":
    unittest.main()
