#!/bin/bash
# Quick setup script for production deployment
# Run this on your server to download all needed files

set -e

BASE_URL="https://raw.githubusercontent.com/tuergeist/contract-manager/main"

echo "=== Contract Manager Production Setup ==="
echo ""

# Download files
echo "Downloading configuration files..."
curl -fsSL "$BASE_URL/docker-compose.prod.yml" -o docker-compose.yml
curl -fsSL "$BASE_URL/nginx.prod.conf" -o nginx.prod.conf
curl -fsSL "$BASE_URL/scripts/export-data.sh" -o export-data.sh
curl -fsSL "$BASE_URL/scripts/import-data.sh" -o import-data.sh
chmod +x export-data.sh import-data.sh

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Required - Generate with: openssl rand -hex 32
DJANGO_SECRET_KEY=change-me-to-a-random-string

# Database (defaults work for single-server setup)
POSTGRES_USER=contract_manager
POSTGRES_PASSWORD=contract_manager
POSTGRES_DB=contract_manager

# Allowed hosts (comma-separated)
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# CSRF trusted origins (include protocol)
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,https://your-domain.com

# Port to expose (default: 80)
PORT=80
EOF
    echo "   Created .env - PLEASE EDIT IT before starting!"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Files downloaded:"
ls -la docker-compose.yml nginx.prod.conf export-data.sh import-data.sh .env 2>/dev/null
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your settings (especially DJANGO_SECRET_KEY)"
echo "  2. Start services: docker compose up -d"
echo "  3. (Optional) Import data: ./import-data.sh ./backup"
echo ""
