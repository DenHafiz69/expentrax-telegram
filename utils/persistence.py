import asyncio
import json
import logging
import pickle
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from telegram.ext import BasePersistence, PersistenceInput

from utils.database import (
    BotCallbackData,
    BotChatData,
    BotConversationState,
    BotData,
    BotUserData,
    engine,
)

logger = logging.getLogger(__name__)


def _serialize_key(key: tuple[Any, ...]) -> str:
    """Serialize conversation key tuple into a JSON string."""
    return json.dumps(list(key))


def _deserialize_key(key_str: str) -> tuple[Any, ...]:
    """Deserialize conversation key string back to a tuple."""
    return tuple(json.loads(key_str))


class SQLAlchemyPersistence(BasePersistence):
    """
    SQLAlchemy-backed persistence for python-telegram-bot to enable
    completely stateless operation on serverless platforms like AWS Lambda.
    """

    def __init__(
        self,
        db_engine=None,
        store_data: PersistenceInput | None = None,
        update_interval: float = 60,
    ):
        if store_data is None:
            store_data = PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=False,
            )
        super().__init__(store_data=store_data, update_interval=update_interval)
        self.engine = db_engine or engine

    # --- User Data ---

    def _load_user_data_sync(self) -> dict[int, dict[str, Any]]:
        with Session(self.engine) as session:
            rows = session.execute(select(BotUserData)).scalars().all()
            result = {}
            for row in rows:
                try:
                    result[row.user_id] = pickle.loads(row.data)
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize user_data for user %s: %s",
                        row.user_id,
                        e,
                    )
            return result

    def _load_single_user_data_sync(self, user_id: int) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.execute(
                select(BotUserData).where(BotUserData.user_id == user_id)
            ).scalar_one_or_none()
            if row:
                try:
                    return pickle.loads(row.data)
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize user_data for user %s: %s", user_id, e
                    )
            return None

    def _save_user_data_sync(self, user_id: int, data: dict[str, Any]) -> None:
        raw_data = pickle.dumps(data)
        with Session(self.engine) as session:
            row = session.execute(
                select(BotUserData).where(BotUserData.user_id == user_id)
            ).scalar_one_or_none()
            if row:
                row.data = raw_data
            else:
                session.add(BotUserData(user_id=user_id, data=raw_data))
            session.commit()

    def _delete_user_data_sync(self, user_id: int) -> None:
        with Session(self.engine) as session:
            session.execute(delete(BotUserData).where(BotUserData.user_id == user_id))
            session.commit()

    async def get_user_data(self) -> dict[int, dict[str, Any]]:
        return await asyncio.to_thread(self._load_user_data_sync)

    async def update_user_data(self, user_id: int, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_user_data_sync, user_id, data)

    async def refresh_user_data(self, user_id: int, user_data: dict[str, Any]) -> None:
        db_data = await asyncio.to_thread(self._load_single_user_data_sync, user_id)
        user_data.clear()
        if db_data:
            user_data.update(db_data)

    async def drop_user_data(self, user_id: int) -> None:
        await asyncio.to_thread(self._delete_user_data_sync, user_id)

    # --- Chat Data ---

    def _load_chat_data_sync(self) -> dict[int, dict[str, Any]]:
        with Session(self.engine) as session:
            rows = session.execute(select(BotChatData)).scalars().all()
            result = {}
            for row in rows:
                try:
                    result[row.chat_id] = pickle.loads(row.data)
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize chat_data for chat %s: %s",
                        row.chat_id,
                        e,
                    )
            return result

    def _load_single_chat_data_sync(self, chat_id: int) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            row = session.execute(
                select(BotChatData).where(BotChatData.chat_id == chat_id)
            ).scalar_one_or_none()
            if row:
                try:
                    return pickle.loads(row.data)
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize chat_data for chat %s: %s", chat_id, e
                    )
            return None

    def _save_chat_data_sync(self, chat_id: int, data: dict[str, Any]) -> None:
        raw_data = pickle.dumps(data)
        with Session(self.engine) as session:
            row = session.execute(
                select(BotChatData).where(BotChatData.chat_id == chat_id)
            ).scalar_one_or_none()
            if row:
                row.data = raw_data
            else:
                session.add(BotChatData(chat_id=chat_id, data=raw_data))
            session.commit()

    def _delete_chat_data_sync(self, chat_id: int) -> None:
        with Session(self.engine) as session:
            session.execute(delete(BotChatData).where(BotChatData.chat_id == chat_id))
            session.commit()

    async def get_chat_data(self) -> dict[int, dict[str, Any]]:
        return await asyncio.to_thread(self._load_chat_data_sync)

    async def update_chat_data(self, chat_id: int, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_chat_data_sync, chat_id, data)

    async def refresh_chat_data(self, chat_id: int, chat_data: dict[str, Any]) -> None:
        db_data = await asyncio.to_thread(self._load_single_chat_data_sync, chat_id)
        chat_data.clear()
        if db_data:
            chat_data.update(db_data)

    async def drop_chat_data(self, chat_id: int) -> None:
        await asyncio.to_thread(self._delete_chat_data_sync, chat_id)

    # --- Bot Data ---

    def _load_bot_data_sync(self) -> dict[str, Any]:
        with Session(self.engine) as session:
            row = session.execute(
                select(BotData).where(BotData.key == "bot_data")
            ).scalar_one_or_none()
            if row:
                try:
                    return pickle.loads(row.data)
                except Exception as e:
                    logger.warning("Failed to deserialize bot_data: %s", e)
            return {}

    def _save_bot_data_sync(self, data: dict[str, Any]) -> None:
        raw_data = pickle.dumps(data)
        with Session(self.engine) as session:
            row = session.execute(
                select(BotData).where(BotData.key == "bot_data")
            ).scalar_one_or_none()
            if row:
                row.data = raw_data
            else:
                session.add(BotData(key="bot_data", data=raw_data))
            session.commit()

    async def get_bot_data(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._load_bot_data_sync)

    async def update_bot_data(self, data: dict[str, Any]) -> None:
        await asyncio.to_thread(self._save_bot_data_sync, data)

    async def refresh_bot_data(self, bot_data: dict[str, Any]) -> None:
        db_data = await asyncio.to_thread(self._load_bot_data_sync)
        bot_data.clear()
        if db_data:
            bot_data.update(db_data)

    # --- Callback Data ---

    def _load_callback_data_sync(self) -> Any | None:
        with Session(self.engine) as session:
            row = session.execute(
                select(BotCallbackData).where(BotCallbackData.key == "callback_data")
            ).scalar_one_or_none()
            if row:
                try:
                    return pickle.loads(row.data)
                except Exception as e:
                    logger.warning("Failed to deserialize callback_data: %s", e)
            return None

    def _save_callback_data_sync(self, data: Any) -> None:
        raw_data = pickle.dumps(data)
        with Session(self.engine) as session:
            row = session.execute(
                select(BotCallbackData).where(BotCallbackData.key == "callback_data")
            ).scalar_one_or_none()
            if row:
                row.data = raw_data
            else:
                session.add(BotCallbackData(key="callback_data", data=raw_data))
            session.commit()

    async def get_callback_data(self) -> Any | None:
        return await asyncio.to_thread(self._load_callback_data_sync)

    async def update_callback_data(self, data: Any) -> None:
        await asyncio.to_thread(self._save_callback_data_sync, data)

    # --- Conversation State ---

    def _load_conversations_sync(self, name: str) -> dict[tuple[Any, ...], Any]:
        with Session(self.engine) as session:
            rows = (
                session.execute(
                    select(BotConversationState).where(
                        BotConversationState.handler_name == name
                    )
                )
                .scalars()
                .all()
            )
            result = {}
            for row in rows:
                try:
                    k = _deserialize_key(row.key)
                    s = pickle.loads(row.state)
                    result[k] = s
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize conversation state for %s (%s): %s",
                        name,
                        row.key,
                        e,
                    )
            return result

    def _save_conversation_sync(
        self, name: str, key: tuple[Any, ...], new_state: Any | None
    ) -> None:
        key_str = _serialize_key(key)
        with Session(self.engine) as session:
            if new_state is None:
                session.execute(
                    delete(BotConversationState).where(
                        BotConversationState.handler_name == name,
                        BotConversationState.key == key_str,
                    )
                )
            else:
                raw_state = pickle.dumps(new_state)
                row = session.execute(
                    select(BotConversationState).where(
                        BotConversationState.handler_name == name,
                        BotConversationState.key == key_str,
                    )
                ).scalar_one_or_none()
                if row:
                    row.state = raw_state
                else:
                    session.add(
                        BotConversationState(
                            handler_name=name, key=key_str, state=raw_state
                        )
                    )
            session.commit()

    async def get_conversations(self, name: str) -> dict[tuple[Any, ...], Any]:
        return await asyncio.to_thread(self._load_conversations_sync, name)

    async def update_conversation(
        self, name: str, key: tuple[Any, ...], new_state: Any | None
    ) -> None:
        await asyncio.to_thread(self._save_conversation_sync, name, key, new_state)

    async def flush(self) -> None:
        pass
