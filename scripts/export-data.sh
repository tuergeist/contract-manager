#!/bin/bash
# Export script for contract-manager data
# Creates a backup of database and media files for migration

set -e

BACKUP_DIR="${1:-./backup-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$BACKUP_DIR"

echo "=== Contract Manager Data Export ==="
echo "Backup directory: $BACKUP_DIR"
echo ""

# 1. Export PostgreSQL database
echo "1. Exporting PostgreSQL database..."
docker compose exec -T db pg_dump -U contract_manager -d contract_manager --clean --if-exists > "$BACKUP_DIR/database.sql"
echo "   Database exported to: $BACKUP_DIR/database.sql"

# Also create a compressed version
gzip -c "$BACKUP_DIR/database.sql" > "$BACKUP_DIR/database.sql.gz"
echo "   Compressed: $BACKUP_DIR/database.sql.gz"

# 2. Export media files
echo ""
echo "2. Exporting media files..."
docker compose exec -T backend tar czf - -C /app media 2>/dev/null > "$BACKUP_DIR/media.tar.gz" || true
if [ -s "$BACKUP_DIR/media.tar.gz" ]; then
    echo "   Media files exported to: $BACKUP_DIR/media.tar.gz"
else
    echo "   No media files to export (or directory empty)"
    rm -f "$BACKUP_DIR/media.tar.gz"
fi

# 3. Create manifest
echo ""
echo "3. Creating manifest..."
cat > "$BACKUP_DIR/manifest.json" << EOF
{
    "export_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "source": "docker-compose",
    "database": "database.sql.gz",
    "media": "media.tar.gz",
    "notes": "Export for K8s migration"
}
EOF
echo "   Manifest created: $BACKUP_DIR/manifest.json"

# 4. Summary
echo ""
echo "=== Export Complete ==="
ls -lh "$BACKUP_DIR"
echo ""
echo "To import on K8s, copy this folder and run import-data.sh"
