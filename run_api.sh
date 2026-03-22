#!/usr/bin/env bash
set -e

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Loading environment variables..."
set -a
source .env
set +a

echo "Initializing database schema..."
python init_db.py

echo "Seeding local API key..."
python seed_api_key.py

echo "Starting API server..."
uvicorn main:app --reload
