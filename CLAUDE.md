# CLAUDE.md - AI Assistant Guide for Contract-Manager

## Project Overview

Contract-Manager is an internal multi-tenant contract management tool designed for small companies (20-30 employees) managing 70-150 customers. The application handles complex contract relationships, pricing structures, customer agreements, and integrates with HubSpot for customer/product sync.

### Business Domain

**Core Concepts:**
- **Customers**: Synced from HubSpot (read-only), can have multiple contracts (independent or linked)
- **Products**: Imported from HubSpot or manually created, with variants and dependencies
- **Contracts**: Full lifecycle (Draft → Active → Paused → Cancelled → Ended), with amendments
- **Pricing**: Hierarchical (contract-fixed > customer-specific > list price), with automatic adjustments
- **Discounts**: Percentage, absolute, tiered, free units - applicable to items, contracts, or categories
- **Multi-tenant**: Shared schema with tenant isolation

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite |
| UI Components | shadcn/ui + Tailwind CSS |
| Backend | Django 5 + Strawberry-GraphQL |
| API | GraphQL (via strawberry-django) |
| Database | PostgreSQL 16 |
| Caching | Redis (when needed) |
| E2E Testing | Playwright |
| Linting | Ruff (backend), ESLint (frontend) |
| Containerization | Docker Compose (dev), Kubernetes (prod) |

## Project Structure

```
contract-manager/
├── backend/                  # Django application
│   ├── apps/
│   │   ├── contracts/        # Contract management (models, schema, tests)
│   │   ├── customers/        # Customer management + HubSpot sync
│   │   ├── products/         # Products, pricing, price lists
│   │   ├── tenants/          # Multi-tenant support, users, roles
│   │   └── core/             # Shared utilities, base models
│   ├── config/               # Django settings, URLs, ASGI/WSGI
│   ├── tests/                # Integration tests
│   ├── Dockerfile            # Development image
│   ├── Dockerfile.prod       # Production image
│   └── pyproject.toml        # Python dependencies (uv)
├── frontend/                 # React TypeScript application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── features/         # Feature-based modules
│   │   ├── lib/              # Utilities, GraphQL client
│   │   └── locales/          # i18n translations (de, en)
│   ├── e2e/                  # Playwright E2E tests
│   ├── Dockerfile            # Development image
│   └── Dockerfile.prod       # Production image (nginx)
├── k8s/                      # Kubernetes manifests
├── .github/workflows/        # CI/CD pipelines
├── docker-compose.yml        # Local development
├── Makefile                  # Development commands
└── README.md                 # Full specification (German)
```

## OpenSpec

The project specification is documented in `README.md` using a structured format covering:

- **Kunden (Customers)**: HubSpot sync, data model, notes
- **Produkte (Products)**: Structure, variants, dependencies, pricing models
- **Verträge (Contracts)**: Lifecycle, billing, amendments, documents
- **Preise & Abrechnung (Pricing & Billing)**: Intervals, pro-rata, history
- **Rabatte & Konditionen (Discounts)**: Types, scopes, validity
- **Preisanpassungen (Price Adjustments)**: Inflation, manual, hierarchies
- **Auditing**: Full change tracking
- **Benutzer & Berechtigungen (Users & Permissions)**: Roles, tenants

When implementing features, always reference the README.md specification for business rules.

## Development Commands

Use `make help` to see all available commands. Key commands:

```bash
# Docker lifecycle
make up              # Start all services
make down            # Stop all services
make build           # Build/rebuild images
make logs            # Follow all logs
make clean           # Full reset (removes volumes)

# Testing
make test            # Run all tests
make test-back       # Backend tests (pytest)
make test-front      # Frontend tests

# Linting
make lint            # Run all linters
make lint-back-fix   # Auto-fix backend issues

# Django
make migrate         # Run migrations
make makemigrations  # Create migrations
make shell           # Django shell_plus
make superuser       # Create superuser

# Database
make db-shell        # PostgreSQL shell
make db-dump         # Dump database

# Health checks
make health          # Check backend health
make graphql-health  # Test GraphQL endpoint
```

## Development Guidelines

### Test-Driven Development (TDD)

1. **Write tests first** before implementing features
2. **Unit tests required** for both frontend and backend
3. **Only commit when all tests are green**
4. **E2E tests** for critical user flows

### Code Quality

**Backend (Python/Django):**
- Ruff for linting and formatting
- Type hints required
- Follow Django conventions
- Use Strawberry for GraphQL types

**Frontend (React/TypeScript):**
- Strict TypeScript
- Functional components with hooks
- Feature-based organization
- i18n for all user-facing strings

### Commit and Versioning

- Semantic versioning (MAJOR.MINOR.PATCH)
- Atomic commits with clear messages
- Tag releases with git tags

## CI/CD Workflow

| Trigger | Action |
|---------|--------|
| Push to branch | Run all tests + linting |
| Pull request | Build images, run tests |
| Merge to main | Build and push images, create release |

## GraphQL API

The API uses Strawberry-GraphQL with Django integration:

- Types defined in each app's `schema.py`
- Root schema in `config/schema.py`
- Authentication via JWT or session
- Pagination using Relay-style connections

**Endpoints:**
- GraphQL: `http://localhost:8001/graphql`
- GraphiQL: `http://localhost:8001/graphql` (browser)
- Health: `http://localhost:8001/api/health`

## Key Conventions for AI Assistants

### When Working on This Codebase

1. **Read README.md** for business requirements (in German)
2. **Run tests** after making changes: `make test`
3. **Run linters** before committing: `make lint`
4. **Use Docker Compose** for all development
5. **Follow existing patterns** in each app

### Common Tasks

**Adding a new feature:**
1. Check README.md for specification
2. Write tests first (TDD)
3. Implement backend model + GraphQL schema
4. Implement frontend components
5. Add E2E test for critical paths
6. Run `make test && make lint`

**Bug fixes:**
1. Write failing test reproducing the bug
2. Fix the bug
3. Verify test passes
4. Check for edge cases

### Important Files

| File | Purpose |
|------|---------|
| `README.md` | Full project specification |
| `Makefile` | Development commands |
| `docker-compose.yml` | Local environment |
| `backend/config/settings.py` | Django configuration |
| `backend/apps/*/schema.py` | GraphQL type definitions |
| `frontend/src/lib/graphql.ts` | GraphQL client setup |

## Production Environment

- **Platform**: Kubernetes (k8s/ manifests provided)
- **Database**: PostgreSQL (managed or containerized)
- **Caching**: Redis (when needed)
- **Static files**: Served via nginx in frontend container

## Language Note

- **README.md**: German (project specification)
- **Code & comments**: English
- **UI**: i18n (German + English)
