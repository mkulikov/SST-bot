#!/bin/sh
set -e

if [ ! -f "${DB_PATH}" ]; then
  echo "Initializing database..."
  sqlite3 "${DB_PATH}" < /app/init.sql
else
  echo "Database already exists"
fi

exec "$@"