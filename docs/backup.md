# Backup & Restore

This document describes how to backup and restore Contract Manager data.

## What Gets Backed Up

- **Database** (`database.sql.gz`): All application data including contracts, customers, users, invoices, audit logs, etc.
- **Media files** (`media.tar.gz`): Uploaded attachments (contract documents, customer files)

## Quick Reference

```bash
# Create backup
./scripts/export-data.sh ./backup

# Restore backup (Docker Compose)
./scripts/import-data.sh ./backup

# Restore backup (Kubernetes)
./scripts/import-data-k8s.sh ./backup [namespace]
```

## Creating a Backup

Run the export script with an optional backup directory:

```bash
./scripts/export-data.sh ./backup
```

This creates:

```
./backup/
├── database.sql.gz   # Compressed PostgreSQL dump
├── database.sql      # Uncompressed dump (for debugging)
├── media.tar.gz      # Uploaded files
└── manifest.json     # Export metadata
```

### Automated Backups

For scheduled backups, add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/contract-manager && ./scripts/export-data.sh ./backups/backup-$(date +\%Y\%m\%d)
```

## Restoring a Backup

### Docker Compose

1. Ensure services are running:
   ```bash
   docker compose up -d
   ```

2. Wait for database to be ready (~10 seconds)

3. Run the import script:
   ```bash
   ./scripts/import-data.sh ./backup
   ```

4. Confirm when prompted (this overwrites existing data)

### Kubernetes

1. Ensure pods are running with correct labels:
   - Database pod: `app=postgres`
   - Backend pod: `app=backend`

2. Run the K8s import script:
   ```bash
   ./scripts/import-data-k8s.sh ./backup my-namespace
   ```

3. Restart deployments if needed:
   ```bash
   kubectl rollout restart deployment/backend -n my-namespace
   ```

## Migration to New Server

1. On the source server, create a backup:
   ```bash
   ./scripts/export-data.sh ./backup
   ```

2. Copy the project and backup to the new server:
   ```bash
   rsync -av ./contract-manager/ user@newserver:/path/to/contract-manager/
   ```

3. On the new server, start services and import:
   ```bash
   cd /path/to/contract-manager
   docker compose up -d
   sleep 10  # Wait for DB
   ./scripts/import-data.sh ./backup
   ```

## Troubleshooting

### Database connection errors

Ensure the database container is healthy:
```bash
docker compose ps
docker compose logs db
```

### Media files not restoring

Check if the media directory exists in the container:
```bash
docker compose exec backend ls -la /app/media/
```

### Permission issues

The backend container runs as a non-root user. Ensure media files have correct ownership:
```bash
docker compose exec backend chown -R app:app /app/media/
```
