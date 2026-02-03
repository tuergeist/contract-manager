#!/bin/bash
# Import script for contract-manager data
# Restores database and media files from backup

set -e

BACKUP_DIR="${1:?Usage: $0 <backup-directory>}"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "=== Contract Manager Data Import ==="
echo "Backup directory: $BACKUP_DIR"
echo ""

# Check for required files
if [ ! -f "$BACKUP_DIR/database.sql.gz" ] && [ ! -f "$BACKUP_DIR/database.sql" ]; then
    echo "Error: No database backup found (database.sql or database.sql.gz)"
    exit 1
fi

# 1. Import PostgreSQL database
echo "1. Importing PostgreSQL database..."
echo "   WARNING: This will overwrite existing data!"
read -p "   Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

if [ -f "$BACKUP_DIR/database.sql.gz" ]; then
    echo "   Decompressing and importing database.sql.gz..."
    gunzip -c "$BACKUP_DIR/database.sql.gz" | docker compose exec -T db psql -U contract_manager -d contract_manager
elif [ -f "$BACKUP_DIR/database.sql" ]; then
    echo "   Importing database.sql..."
    docker compose exec -T db psql -U contract_manager -d contract_manager < "$BACKUP_DIR/database.sql"
fi
echo "   Database imported successfully."

# 2. Import media files
echo ""
echo "2. Importing media files..."
if [ -f "$BACKUP_DIR/media.tar.gz" ]; then
    docker compose exec -T backend rm -rf /app/media/*
    cat "$BACKUP_DIR/media.tar.gz" | docker compose exec -T backend tar xzf - -C /app
    echo "   Media files restored."
else
    echo "   No media backup found, skipping."
fi

# 3. Run migrations (in case schema changed)
echo ""
echo "3. Running database migrations..."
docker compose exec -T backend python manage.py migrate --noinput

echo ""
echo "=== Import Complete ==="
echo "You may need to restart services: docker compose restart"
