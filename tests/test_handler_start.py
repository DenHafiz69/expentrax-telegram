import unittest
from unittest.mock import patch

from handlers.start import start_command
from tests.helpers import create_mock_context, create_mock_message_update


class TestStartHandler(unittest.IsolatedAsyncioTestCase):
    @patch("handlers.start.save_user")
    @patch("handlers.start.read_user")
    async def test_start_command_new_user(self, mock_read_user, mock_save_user):
        mock_read_user.return_value = None
        update = create_mock_message_update(user_id=123, username="johndoe")
        context = create_mock_context()

        await start_command(update, context)

        mock_read_user.assert_called_once_with(123)
        mock_save_user.assert_called_once_with(id=123, username="johndoe")
        context.bot.send_message.assert_called_once()
        kwargs = context.bot.send_message.call_args.kwargs
        self.assertEqual(kwargs["chat_id"], 123)
        self.assertIn("Welcome to Expentrax!", kwargs["text"])
        self.assertEqual(kwargs["parse_mode"], "HTML")

    @patch("handlers.start.save_user")
    @patch("handlers.start.read_user")
    async def test_start_command_existing_user(self, mock_read_user, mock_save_user):
        mock_read_user.return_value = {"id": 123, "username": "johndoe"}
        update = create_mock_message_update(user_id=123, username="johndoe")
        context = create_mock_context()

        await start_command(update, context)

        mock_read_user.assert_called_once_with(123)
        mock_save_user.assert_not_called()
        context.bot.send_message.assert_called_once()
        kwargs = context.bot.send_message.call_args.kwargs
        self.assertEqual(kwargs["chat_id"], 123)
        self.assertIn("Welcome to Expentrax!", kwargs["text"])


if __name__ == "__main__":
    unittest.main()
