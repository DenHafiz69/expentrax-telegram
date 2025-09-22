# Import necessary modules
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

# Access environment variables
TELEGRAM_API = os.getenv('TELEGRAM_API')