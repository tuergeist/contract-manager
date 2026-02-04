# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Contract-Manager is an internal contract management tool for small companies. It handles complex contract relationships including:
- Customers synced from Hubspot (one-way, read-only)
- Products from CRM or manually created
- Contracts with amendments, flexible pricing, and various billing cycles
- Multi-tenant architecture

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Shadcn/ui
- **Backend**: Django 5, Strawberry-GraphQL, PostgreSQL
- **Caching**: Redis (when needed)
- **Containerization**: Docker Compose for local development, ghcr.io images for production

## Development Commands

All development happens inside Docker containers. Use `make help` to see all commands.

```bash
# Docker
make up              # Start all services
make down            # Stop all services
make build           # Build/rebuild images
make logs            # Follow all logs
make clean           # Full reset (removes volumes)

# Testing
make test            # Run all tests
make test-back       # Run backend tests only
make test-front      # Run frontend tests only

# Linting
make lint            # Run all linters
make lint-back-fix   # Auto-fix backend lint issues

# Django
make shell           # Django shell
make migrate         # Run migrations
make makemigrations  # Create new migrations
make superuser       # Create superuser

# Health checks
make health          # Check backend health endpoint
make graphql-health  # Test GraphQL endpoint
```

## Test Credentials

```
Email: admin@test.local
Password: admin123
```

Set up test data with: `docker compose exec backend python manage.py setup_test_data`

## Project Structure

```
contract-manager/
├── backend/                 # Django + Strawberry-GraphQL
│   ├── config/             # Django settings and URLs
│   │   └── settings/       # Split settings (base, local, production, test)
│   ├── apps/               # Django apps
│   │   ├── core/          # Base models and utilities
│   │   ├── tenants/       # Multi-tenant, users, roles
│   │   ├── customers/     # Customer management
│   │   ├── products/      # Product catalog
│   │   └── contracts/     # Contract management
│   └── tests/              # Pytest tests
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/    # Shared UI components (Shadcn/ui)
│   │   ├── features/      # Feature modules
│   │   │   ├── auth/      # Login
│   │   │   ├── customers/ # CustomerList, CustomerDetail
│   │   │   ├── contracts/ # ContractList, ContractDetail, ContractForm
│   │   │   ├── products/  # ProductList
│   │   │   ├── dashboard/ # Dashboard
│   │   │   └── settings/  # Settings
│   │   ├── lib/           # Apollo client, i18n, utilities
│   │   └── locales/       # Translation files (de, en)
│   ├── e2e/               # Playwright E2E tests
│   └── playwright.config.ts
└── docker-compose.yml      # Local development setup
```

## Frontend Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Dashboard | Home page |
| `/customers` | CustomerList | Customer list with search/sort |
| `/customers/:id` | CustomerDetail | Customer details + contracts |
| `/contracts` | ContractList | Contract list with filters |
| `/contracts/new` | ContractForm | Create new contract |
| `/contracts/:id` | ContractDetail | Contract overview (items, amendments) |
| `/contracts/:id/edit` | ContractForm | View/Edit contract details |
| `/products` | ProductList | Product catalog |
| `/settings` | Settings | App settings, HubSpot integration |

## Contract Views Terminology

- **Detail View 1** (`/contracts/:id`): Overview with items/amendments tabs
- **Detail View 2** (`/contracts/:id/edit` read-only): Contract details before clicking "Edit"
- **Edit View** (`/contracts/:id/edit` editing): Form after clicking "Edit" button

Status transition buttons (Activate, Pause, Cancel, etc.) appear only in Detail View 2.

## Docker Files

- `backend/Dockerfile` - Local development (includes dev dependencies, hot-reload)
- `backend/Dockerfile.prod` - **Production image built by CI** (multi-stage, slim, no dev deps)
- `frontend/Dockerfile.prod` - Production frontend image built by CI
- `docker-compose.yml` - Local development
- `docker-compose.prod.yml` - Production deployment with ghcr.io images

When modifying Docker build for production, edit `Dockerfile.prod` files. CI (`.github/workflows/build.yml`) uses these to build and push images to ghcr.io.

## Key Conventions

- All development happens inside Docker containers
- Use TDD: write tests first
- Multi-tenant: All models use TenantModel base class
- i18n: German (de) and English (en) supported
- GraphQL API via Strawberry-Django

## Testing

### E2E Tests (Playwright)

```bash
cd frontend
npm run test:e2e        # Run all E2E tests
npm run test:e2e:ui     # Run with Playwright UI
```

### Test ID Convention

Always use `data-testid` attributes for E2E test selectors, never text-based selectors.

Pattern: `{entity}-{element}-{id?}`

Examples:
- `data-testid="customer-detail-page"`
- `data-testid="customer-name"`
- `data-testid="customer-link-{id}"`
- `data-testid="customers-table-body"`
- `data-testid="contract-row-{id}"`
- `data-testid="contract-customer-link-{id}"`

## Strawberry GraphQL

### Circular Imports with Lazy Types

When types reference each other (e.g., Customer ↔ Contract), use `strawberry.lazy`:

```python
from typing import TYPE_CHECKING, Annotated, List
import strawberry

if TYPE_CHECKING:
    from apps.contracts.schema import ContractType

@strawberry_django.type(Customer)
class CustomerType:
    @strawberry.field
    def contracts(self) -> List[Annotated["ContractType", strawberry.lazy("apps.contracts.schema")]]:
        from apps.contracts.models import Contract
        return list(Contract.objects.filter(customer=self))
```

## Contract Status Transitions

```
draft → active
active → paused, cancelled
paused → active, cancelled
cancelled → ended
```

## Firefox Debugging Agent

Use the `firefox-debugger` agent for interactive frontend debugging:

```
/task firefox-debugger "Debug why the customer table shows no data"
```

The agent will:
1. Open Firefox and navigate to the page
2. Check console for errors
3. Inspect network requests
4. Take snapshots to understand page structure
5. Iteratively fix issues until resolved

**Note**: Firefox MCP is for debugging only. Use Playwright for automated testing.
