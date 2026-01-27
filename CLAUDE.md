# CLAUDE.md - AI Assistant Guide for Contract-Manager

## Project Overview

Contract-Manager is an internal contract management tool designed for a small company (20-30 employees) managing 70-150 customers. The application handles complex contract relationships, pricing structures, and customer agreements.

### Business Domain

**Core Concepts:**
- **Customers** can have multiple contracts (independent or linked)
- **Linked Contracts**: One primary contract determines duration and payment intervals for others
- **Contract Products**: Contracts contain n products in quantity m
- **Pricing Models**: Either a total price or individual product prices
- **Discounts**: With or without time limits
- **Automatic Adjustments**: e.g., inflation adjustments (x% from a specific date)
- **Price Lists**: Products can be freely defined or selected from a price list
- **Customer Agreements**: Special arrangements like "10% off price list" or "20% discount for >2 year duration"

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React with TypeScript |
| Backend | Django with Strawberry-GraphQL |
| API | GraphQL (via strawberry-django) |
| Database | PostgreSQL |
| Caching | Redis (when needed) |
| E2E Testing | Playwright |
| Containerization | Docker Compose (dev), Kubernetes/Swarm (prod) |

## Project Structure (Planned)

```
contract-manager/
├── frontend/                 # React TypeScript application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page-level components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── graphql/          # GraphQL queries, mutations, fragments
│   │   ├── types/            # TypeScript type definitions
│   │   └── utils/            # Utility functions
│   ├── tests/                # Frontend unit tests
│   └── package.json
├── backend/                  # Django application
│   ├── config/               # Django settings and configuration
│   ├── apps/
│   │   ├── contracts/        # Contract management app
│   │   ├── customers/        # Customer management app
│   │   ├── products/         # Product and price list app
│   │   └── users/            # User authentication app
│   ├── schema/               # Strawberry GraphQL schema
│   └── tests/                # Backend unit tests
├── e2e/                      # Playwright E2E tests
├── docker-compose.yml        # Local development setup
├── docker-compose.prod.yml   # Production configuration
└── .github/workflows/        # CI/CD pipelines
```

## Development Guidelines

### Test-Driven Development (TDD)

1. **Write tests first** before implementing features
2. **Unit tests required** for both frontend and backend code
3. **Only commit when all tests are green**
4. **E2E tests** with Playwright for critical user flows (login, complete features)

### Commit and Versioning

- Use **semantic versioning** (MAJOR.MINOR.PATCH)
- Tag releases with git tags
- Write clear, descriptive commit messages
- Commits should represent logical units of work

### Code Quality

- **Backend (Python/Django)**:
  - Follow PEP 8 style guidelines
  - Use type hints where appropriate
  - Document complex business logic

- **Frontend (React/TypeScript)**:
  - Use functional components with hooks
  - Maintain strict TypeScript typing
  - Follow React best practices

### Local Development

The development environment uses Docker Compose. Developers should not need to install anything beyond Docker.

```bash
# Start all services
docker-compose up

# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm test

# Run E2E tests
docker-compose exec e2e npx playwright test
```

## CI/CD Workflow

| Trigger | Action |
|---------|--------|
| Push to branch | Run all tests |
| Merge request | Build images, run tests |
| Merge to main | Build and push final images, create release |

## Authentication

- **Current**: Username/password authentication
- **Future**: Magic email link or email code authentication
- Internal use only (no public registration)

## GraphQL API

The API uses Strawberry-GraphQL with Django integration. Key considerations:

- Define schemas in the `schema/` directory
- Use Strawberry's Django integration for model types
- Implement proper authentication/authorization on resolvers
- Follow GraphQL best practices for pagination and error handling

**Documentation**: https://github.com/strawberry-graphql/strawberry-django

## Key Conventions for AI Assistants

### When Working on This Codebase

1. **Always run tests** after making changes
2. **Respect the TDD approach** - consider writing tests first
3. **Use Docker Compose** for all development tasks
4. **Follow the existing code style** and patterns
5. **Keep commits atomic** and well-described

### Common Tasks

**Adding a new feature:**
1. Create/update tests for the new functionality
2. Implement the backend model and GraphQL schema
3. Implement the frontend components and queries
4. Add E2E test for critical paths
5. Ensure all tests pass before committing

**Bug fixes:**
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Add any additional edge case tests

### Important Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development environment |
| `backend/config/settings.py` | Django configuration |
| `backend/schema/` | GraphQL schema definitions |
| `frontend/src/graphql/` | Frontend GraphQL operations |
| `.github/workflows/` | CI/CD pipeline definitions |

## Production Environment

- Target: Kubernetes or Docker Swarm on Linux
- Database: PostgreSQL (managed or containerized)
- Caching: Redis (when needed for performance)

## Language Note

The README and some documentation may be in German (the target company's language). Code, comments, and technical documentation should be in English.
