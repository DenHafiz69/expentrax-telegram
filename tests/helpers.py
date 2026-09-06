from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from telegram import CallbackQuery, Chat, Message, Update, User


def create_mock_context(user_data=None):
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    return context


def create_mock_message_update(
    user_id=123, chat_id=123, text="", first_name="TestUser", username="testuser"
):
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = user_id
    user.first_name = first_name
    user.username = username

    chat = MagicMock(spec=Chat)
    chat.id = chat_id

    message = MagicMock(spec=Message)
    message.text = text
    message.from_user = user
    message.chat = chat
    message.reply_text = AsyncMock()
    message.date = datetime.now(tz=UTC)

    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    update.callback_query = None
    return update


def create_mock_callback_update(
    user_id=123, chat_id=123, data="", first_name="TestUser", username="testuser"
):
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = user_id
    user.first_name = first_name
    user.username = username

    chat = MagicMock(spec=Chat)
    chat.id = chat_id

    query = MagicMock(spec=CallbackQuery)
    query.data = data
    query.from_user = user
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    message = MagicMock(spec=Message)
    message.chat = chat
    message.from_user = user
    message.reply_text = AsyncMock()
    message.date = datetime.now(tz=UTC)
    query.message = message

    update.effective_user = user
    update.effective_chat = chat
    update.message = None
    update.callback_query = query
    return update
