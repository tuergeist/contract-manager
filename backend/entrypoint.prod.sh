#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Start the application
echo "Starting application..."
exec "$@"
