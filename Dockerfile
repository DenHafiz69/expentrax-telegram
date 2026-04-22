FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g. for psycopg2 if Postgres is used)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY . .

# Ensure data directory exists and has correct permissions
RUN mkdir -p data

# Run the bot
CMD ["python", "main.py"]
