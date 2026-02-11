#!/bin/bash
# Import script for contract-manager data on Kubernetes
# Restores database and media files from backup

set -e

BACKUP_DIR="${1:?Usage: $0 <backup-directory> [namespace]}"
NAMESPACE="${2:-default}"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "=== Contract Manager Data Import (Kubernetes) ==="
echo "Backup directory: $BACKUP_DIR"
echo "Namespace: $NAMESPACE"
echo ""

# Get pod names
DB_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
BACKEND_POD=$(kubectl get pods -n "$NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$DB_POD" ]; then
    echo "Error: Cannot find postgres pod. Make sure labels are set correctly (app=postgres)"
    echo "Or set DB_POD environment variable manually"
    exit 1
fi

if [ -z "$BACKEND_POD" ]; then
    echo "Error: Cannot find backend pod. Make sure labels are set correctly (app=backend)"
    echo "Or set BACKEND_POD environment variable manually"
    exit 1
fi

echo "Database pod: $DB_POD"
echo "Backend pod: $BACKEND_POD"
echo ""

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
    gunzip -c "$BACKUP_DIR/database.sql.gz" | kubectl exec -i -n "$NAMESPACE" "$DB_POD" -- psql -U contract_manager -d contract_manager
elif [ -f "$BACKUP_DIR/database.sql" ]; then
    echo "   Importing database.sql..."
    kubectl exec -i -n "$NAMESPACE" "$DB_POD" -- psql -U contract_manager -d contract_manager < "$BACKUP_DIR/database.sql"
fi
echo "   Database imported successfully."

# 2. Import media files
echo ""
echo "2. Importing media files..."
if [ -f "$BACKUP_DIR/media.tar.gz" ]; then
    # Clear existing media
    kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- rm -rf /app/media/*
    # Copy and extract
    kubectl cp "$BACKUP_DIR/media.tar.gz" "$NAMESPACE/$BACKEND_POD:/tmp/media.tar.gz"
    kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- tar xzf /tmp/media.tar.gz -C /app
    kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- rm /tmp/media.tar.gz
    echo "   Media files restored."
else
    echo "   No media backup found, skipping."
fi

# 3. Run migrations
echo ""
echo "3. Running database migrations..."
kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- python manage.py migrate --noinput

echo ""
echo "=== Import Complete ==="
echo "You may need to restart deployments:"
echo "  kubectl rollout restart deployment/backend -n $NAMESPACE"
