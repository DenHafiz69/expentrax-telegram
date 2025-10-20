from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import add_custom_category, get_categories_name, get_custom_categories_name_and_id, get_category_id, delete_category
from utils.misc import list_chunker

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pass


async def 
