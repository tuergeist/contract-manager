#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Migrate files to object storage if S3 is configured
if [ -n "$AWS_S3_ENDPOINT_URL" ]; then
    echo "S3 configured, checking for files to migrate..."
    python manage.py migrate_to_object_storage --auto
fi

# Start the application
echo "Starting application..."
exec "$@"
