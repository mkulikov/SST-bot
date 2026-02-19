#!/bin/sh
set -e

DB_PATH="/app/data/bot.db"

if [ ! -f "$DB_PATH" ]; then
  echo "Initializing database..."
  sqlite3 "$DB_PATH" < /app/init.sql
else
  echo "Database already exists"
fi

exec "$@"