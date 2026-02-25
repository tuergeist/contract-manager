#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Migrate local files to object storage (no-op if S3 not configured or no files pending)
echo "Checking file storage migration..."
python manage.py migrate_to_object_storage --auto

# Send deploy ping to Todoist
echo "Sending deploy ping..."
python manage.py deploy_ping || true

# Start the application
echo "Starting application..."
exec "$@"
