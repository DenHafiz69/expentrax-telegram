import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from telegram.ext import ConversationHandler

from handlers.history import (
    CHOICE,
    MONTHLY,
    SUMMARY,
    WEEKLY,
    YEARLY,
    back_history_handler,
    cancel_history,
    history_choice,
    monthly_handler,
    recent_handler,
    start_history,
    summary_handler,
    weekly_handler,
    yearly_handler,
)
from tests.helpers import (
    create_mock_callback_update,
    create_mock_context,
    create_mock_message_update,
)


class TestHistoryHandler(unittest.IsolatedAsyncioTestCase):
    async def test_start_history(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await start_history(update, context)

        self.assertEqual(state, CHOICE)
        update.message.reply_text.assert_called_once()
        args, kwargs = update.message.reply_text.call_args
        self.assertIn("Welcome to the transaction history!", args[0])
        self.assertIn("reply_markup", kwargs)

    @patch("handlers.history.recent_handler")
    async def test_history_choice_recent(self, mock_recent):
        mock_recent.return_value = ConversationHandler.END
        update = create_mock_callback_update(data="recent")
        context = create_mock_context()

        state = await history_choice(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_recent.assert_called_once_with(update, context)

    async def test_history_choice_summary(self):
        update = create_mock_callback_update(data="summary")
        context = create_mock_context()

        state = await history_choice(update, context)

        self.assertEqual(state, SUMMARY)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Please specify a summary period:", kwargs["text"])

    async def test_history_choice_invalid(self):
        update = create_mock_callback_update(data="invalid_choice")
        context = create_mock_context()

        state = await history_choice(update, context)

        self.assertEqual(state, CHOICE)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Oops! Please select 'Recent' or 'Summary'", kwargs["text"])

    @patch("handlers.history.get_recent_transactions")
    @patch("handlers.history.get_currency")
    async def test_recent_handler_empty(self, mock_currency, mock_recent):
        mock_currency.return_value = "$"
        mock_recent.return_value = []
        update = create_mock_callback_update(chat_id=123)
        context = create_mock_context()

        state = await recent_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("No recent transactions found", kwargs["text"])

    @patch("handlers.history.get_category_name_by_id")
    @patch("handlers.history.get_recent_transactions")
    @patch("handlers.history.get_currency")
    async def test_recent_handler_with_transactions(
        self, mock_currency, mock_recent, mock_cat_name
    ):
        mock_currency.return_value = "$"
        mock_recent.return_value = [
            SimpleNamespace(
                type_of_transaction="income",
                category_id=1,
                timestamp=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
                amount=2000.0,
                description="Salary",
            ),
            SimpleNamespace(
                type_of_transaction="expense",
                category_id=2,
                timestamp=datetime(2026, 1, 16, 14, 0, tzinfo=UTC),
                amount=50.0,
                description="Dinner",
            ),
        ]
        mock_cat_name.side_effect = lambda cid: "Paycheck" if cid == 1 else "Food"
        update = create_mock_callback_update(chat_id=123)
        context = create_mock_context()

        state = await recent_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Here are your recent transactions:", kwargs["text"])
        self.assertIn("💰 Income", kwargs["text"])
        self.assertIn("💸 Expense", kwargs["text"])
        self.assertIn("Paycheck", kwargs["text"])
        self.assertIn("Food", kwargs["text"])

    @patch("handlers.history.get_summary_periods")
    async def test_summary_handler_empty(self, mock_periods):
        mock_periods.return_value = []
        update = create_mock_callback_update(chat_id=123, data="weekly")
        context = create_mock_context()

        state = await summary_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("No weekly summary found", kwargs["text"])

    @patch("handlers.history.get_summary_periods")
    async def test_summary_handler_weekly(self, mock_periods):
        mock_periods.return_value = ["Week 10 2026", "Week 11 2026"]
        update = create_mock_callback_update(chat_id=123, data="weekly")
        context = create_mock_context()

        state = await summary_handler(update, context)

        self.assertEqual(state, WEEKLY)
        update.callback_query.edit_message_text.assert_called_once()

    @patch("handlers.history.get_summary_periods")
    async def test_summary_handler_monthly(self, mock_periods):
        mock_periods.return_value = ["Jan 2026", "Feb 2026"]
        update = create_mock_callback_update(chat_id=123, data="monthly")
        context = create_mock_context()

        state = await summary_handler(update, context)

        self.assertEqual(state, MONTHLY)
        update.callback_query.edit_message_text.assert_called_once()

    @patch("handlers.history.get_summary_periods")
    async def test_summary_handler_yearly(self, mock_periods):
        mock_periods.return_value = ["2025", "2026"]
        update = create_mock_callback_update(chat_id=123, data="yearly")
        context = create_mock_context()

        state = await summary_handler(update, context)

        self.assertEqual(state, YEARLY)
        update.callback_query.edit_message_text.assert_called_once()

    @patch("handlers.history.get_currency")
    @patch("handlers.history.get_period_total")
    async def test_weekly_handler(self, mock_period_total, mock_currency):
        mock_currency.return_value = "$"
        mock_period_total.return_value = SimpleNamespace(
            total_income=1000.0, total_expense=400.0
        )
        update = create_mock_callback_update(chat_id=123, data="Week 10 2026")
        context = create_mock_context()

        state = await weekly_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_period_total.assert_called_once_with(
            123, period_type="week", target_year=2026, target_week=10
        )
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Weekly Summary (2026 Week 10)", kwargs["text"])
        self.assertIn("1000.00", kwargs["text"])
        self.assertIn("400.00", kwargs["text"])

    @patch("handlers.history.get_currency")
    @patch("handlers.history.get_period_total")
    async def test_monthly_handler(self, mock_period_total, mock_currency):
        mock_currency.return_value = "$"
        mock_period_total.return_value = SimpleNamespace(
            total_income=3000.0, total_expense=1200.0
        )
        update = create_mock_callback_update(chat_id=123, data="Jan 2026")
        context = create_mock_context()

        state = await monthly_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_period_total.assert_called_once_with(
            123, period_type="month", target_year=2026, target_month=1
        )
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Monthly Summary (Jan 2026)", kwargs["text"])

    @patch("handlers.history.get_currency")
    @patch("handlers.history.get_period_total")
    async def test_yearly_handler(self, mock_period_total, mock_currency):
        mock_currency.return_value = "$"
        mock_period_total.return_value = SimpleNamespace(
            total_income=30000.0, total_expense=20000.0
        )
        update = create_mock_callback_update(chat_id=123, data="2026")
        context = create_mock_context()

        state = await yearly_handler(update, context)

        self.assertEqual(state, ConversationHandler.END)
        mock_period_total.assert_called_once_with(
            123, period_type="year", target_year=2026
        )
        update.callback_query.edit_message_text.assert_called_once()
        _, kwargs = update.callback_query.edit_message_text.call_args
        self.assertIn("Yearly Summary (2026)", kwargs["text"])

    async def test_back_history_handler_start(self):
        update = create_mock_callback_update(data="start_history")
        update.message = update.callback_query.message
        context = create_mock_context()

        state = await back_history_handler(update, context)

        self.assertEqual(state, CHOICE)

    async def test_back_history_handler_summary(self):
        update = create_mock_callback_update(data="back_to_summary")
        context = create_mock_context()

        state = await back_history_handler(update, context)

        self.assertEqual(state, SUMMARY)
        update.callback_query.edit_message_text.assert_called_once()

    async def test_cancel_history(self):
        update = create_mock_message_update()
        context = create_mock_context()

        state = await cancel_history(update, context)

        self.assertEqual(state, ConversationHandler.END)
        update.message.reply_text.assert_called_once_with("❌ History operation cancelled.")


if __name__ == "__main__":
    unittest.main()
