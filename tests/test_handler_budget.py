import unittest
from types import SimpleNamespace
from unittest.mock import patch

from telegram.ext import ConversationHandler

from handlers.budget import (
    AMOUNT_INPUT,
    CATEGORY_SELECTION,
    CHOICE,
    MONTH_SELECTION,
    amount_input_handler,
    back_budget_handler,
    cancel_budget,
    category_selection_handler,
    check_budget_handler,
    choice_handler,
    month_selection_handler,
    start_budget,
)
from tests.helpers import (
    create_mock_callback_update,
    create_mock_context,
    create_mock_message_update,
)


class TestBudgetHandler(unittest.IsolatedAsyncioTestCase):
    async def test_start_budget(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await start_budget(update, context)

        self.assertEqual(state, CHOICE)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("Welcome to the budget manager!", args[0])
        self.assertIn("reply_markup", kwargs)

    async def test_choice_handler_set_change(self):
        update = create_mock_callback_update(data="set_change_budget")
        context = create_mock_context()

        state = await choice_handler(update, context)

        self.assertEqual(state, MONTH_SELECTION)
        self.assertEqual(context.user_data["budget_choice"], "set_change_budget")
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Which month are you setting or changing the budget for?", kwargs["text"])

    @patch("handlers.budget.check_budget_handler")
    async def test_choice_handler_check_budget(self, mock_check_budget):
        update = create_mock_callback_update(data="check_budget")
        context = create_mock_context()

        state = await choice_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_check_budget.assert_called_once_with(update, context)

    @patch("handlers.budget.get_categories_name")
    async def test_month_selection_handler(self, mock_get_categories):
        mock_get_categories.return_value = ["Groceries", "Utilities"]
        update = create_mock_callback_update(chat_id=123, data="January 2026")
        context = create_mock_context()

        state = await month_selection_handler(update, context)

        self.assertEqual(state, CATEGORY_SELECTION)
        self.assertEqual(context.user_data["budget_month"], 1)
        self.assertEqual(context.user_data["budget_year"], 2026)
        mock_get_categories.assert_called_once_with("expense", 123)
        update.callback_query.edit_message_text.assert_called_once()

    async def test_category_selection_handler(self):
        update = create_mock_callback_update(data="Groceries")
        context = create_mock_context()

        state = await category_selection_handler(update, context)

        self.assertEqual(state, AMOUNT_INPUT)
        self.assertEqual(context.user_data["budget_category_name"], "Groceries")
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("What is the budget amount for *Groceries*?", kwargs["text"])

    async def test_amount_input_handler_invalid(self):
        update = create_mock_message_update(text="invalid_amount")
        context = create_mock_context(
            user_data={"budget_category_name": "Groceries"}
        )

        state = await amount_input_handler(update, context)

        self.assertEqual(state, AMOUNT_INPUT)
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("Invalid amount", args[0])

    @patch("handlers.budget.set_budget")
    @patch("handlers.budget.get_currency")
    @patch("handlers.budget.get_category_type")
    @patch("handlers.budget.get_category_id")
    async def test_amount_input_handler_valid(
        self,
        mock_get_category_id,
        mock_get_category_type,
        mock_get_currency,
        mock_set_budget,
    ):
        mock_get_category_id.return_value = 5
        mock_get_category_type.return_value = "custom"
        mock_get_currency.return_value = "$"
        update = create_mock_message_update(user_id=123, chat_id=123, text="350.00")
        context = create_mock_context(
            user_data={
                "budget_category_name": "Groceries",
                "budget_month": 3,
                "budget_year": 2026,
            }
        )

        state = await amount_input_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        self.assertEqual(context.user_data["budget_amount"], 350.00)
        mock_get_category_id.assert_called_once_with("Groceries")
        mock_get_category_type.assert_called_once_with(5)
        mock_get_currency.assert_called_once_with(123)
        mock_set_budget.assert_called_once_with(
            user_id=123,
            budgeted_amount=350.00,
            category_id=5,
            category_type="custom",
            month=3,
            year=2026,
        )
        update.message.reply_text.assert_called_once()
        args, _ = update.message.reply_text.call_args
        self.assertIn("Budget for *Groceries*", args[0])

    @patch("handlers.budget.get_currency")
    @patch("handlers.budget.get_spend_by_month")
    @patch("handlers.budget.get_budget_by_month")
    async def test_check_budget_handler_no_budgets(
        self, mock_get_budget, mock_get_spend, mock_get_currency
    ):
        mock_get_budget.return_value = []
        mock_get_spend.return_value = []
        mock_get_currency.return_value = "$"
        update = create_mock_callback_update(chat_id=123)
        context = create_mock_context()

        await check_budget_handler(update, context)

        update.callback_query.edit_message_text.assert_called_once_with(
            text="You have not set any budgets for this month."
        )

    @patch("handlers.budget.get_category_name_by_id")
    @patch("handlers.budget.get_currency")
    @patch("handlers.budget.get_spend_by_month")
    @patch("handlers.budget.get_budget_by_month")
    async def test_check_budget_handler_with_budgets(
        self, mock_get_budget, mock_get_spend, mock_get_currency, mock_get_cat_name
    ):
        mock_get_budget.return_value = [
            SimpleNamespace(category_id=1, budgeted_amount=500.0),
            SimpleNamespace(category_id=2, budgeted_amount=100.0),
        ]
        mock_get_spend.return_value = [
            SimpleNamespace(category_id=1, total_spent=300.0),
            SimpleNamespace(category_id=2, total_spent=150.0),
        ]
        mock_get_currency.return_value = "$"
        mock_get_cat_name.side_effect = lambda cat_id: "Food" if cat_id == 1 else "Fun"
        update = create_mock_callback_update(chat_id=123)
        context = create_mock_context()

        await check_budget_handler(update, context)

        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Budget Status", kwargs["text"])
        self.assertIn("*Food*:", kwargs["text"])
        self.assertIn("*Fun*:", kwargs["text"])
        self.assertIn("Overall Summary", kwargs["text"])

    async def test_back_budget_handler_start(self):
        update = create_mock_callback_update(data="start_budget")
        # When start_budget is called inside back_budget_handler, update.message might be expected by start_budget
        update.message = update.callback_query.message
        context = create_mock_context()

        state = await back_budget_handler(update, context)

        self.assertEqual(state, CHOICE)

    async def test_back_budget_handler_month_selection(self):
        update = create_mock_callback_update(data="back_to_month_selection")
        context = create_mock_context()

        state = await back_budget_handler(update, context)

        self.assertEqual(state, MONTH_SELECTION)
        update.callback_query.edit_message_text.assert_called_once()

    async def test_cancel_budget(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await cancel_budget(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.message.reply_text.assert_called_once_with("Budget operation cancelled.")


if __name__ == "__main__":
    unittest.main()
