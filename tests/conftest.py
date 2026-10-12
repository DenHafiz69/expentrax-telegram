import os

# The test suite must never connect to a remote database (e.g. Turso) that may
# be configured in a local .env file. `load_dotenv()` does not override existing
# variables, so assigning empty strings here forces the SQLite fallback.
os.environ["DB_URL"] = ""
os.environ["DB_TOKEN"] = ""
