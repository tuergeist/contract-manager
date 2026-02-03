# Contract-Manager

Internal contract management tool for small companies (20-30 employees, 70-150 customers).

## Quick Start (Production)

### One-liner Setup

```bash
curl -fsSL https://raw.githubusercontent.com/tuergeist/contract-manager/main/scripts/setup-prod.sh | bash
```

This downloads all required files. Then:

1. Edit `.env` with your settings (especially `DJANGO_SECRET_KEY`)
2. Start: `docker compose up -d`

### Manual Setup

```bash
# Download files
curl -O https://raw.githubusercontent.com/tuergeist/contract-manager/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/tuergeist/contract-manager/main/nginx.prod.conf
mv docker-compose.prod.yml docker-compose.yml

# Create .env file
cat > .env << 'EOF'
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost,your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com
PORT=80
EOF

# Start
docker compose up -d
```

### Data Migration

Export from existing installation:
```bash
./export-data.sh ./backup
```

Import on new server:
```bash
./import-data.sh ./backup
```

## Development Setup

```bash
git clone https://github.com/tuergeist/contract-manager.git
cd contract-manager
make up
```

Open http://localhost:5173 (frontend) or http://localhost:8000/admin (Django admin).

**Test credentials:** `admin@test.local` / `admin123`

Setup test data: `docker compose exec backend python manage.py setup_test_data`

### Common Commands

```bash
make help            # Show all commands
make up              # Start all services
make down            # Stop all services
make test            # Run all tests
make logs            # Follow logs
```

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Shadcn/ui
- **Backend**: Django 5, Strawberry-GraphQL, PostgreSQL
- **Caching**: Redis

## Project Structure

```
contract-manager/
├── backend/              # Django + Strawberry-GraphQL
│   ├── apps/            # Django apps (tenants, customers, products, contracts)
│   └── config/          # Django settings
├── frontend/            # React + Vite + TypeScript
│   ├── src/features/    # Feature modules
│   └── e2e/             # Playwright tests
├── docs/                # Documentation
│   └── SPECIFICATION.md # Detailed requirements & data model
└── docker-compose.yml   # Local development
```

## Documentation

- [Detailed Specification](docs/SPECIFICATION.md) - Requirements, data model, architecture decisions
- [CLAUDE.md](CLAUDE.md) - Development guidelines for AI assistants

## Development Guidelines

- Use TDD - write tests first
- All development happens inside Docker containers
- Multi-tenant: All models use TenantModel base class
- i18n: German (de) and English (en) supported
- Commit only when all tests are green
