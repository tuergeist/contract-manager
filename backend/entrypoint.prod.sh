#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Send deploy ping to Todoist
echo "Sending deploy ping..."
python manage.py deploy_ping || true

# Start the application
echo "Starting application..."
exec "$@"
