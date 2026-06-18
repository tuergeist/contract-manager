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

## Releasing

Releases are tagged on the `main` branch. CI (`.github/workflows/build.yml`) builds and pushes Docker images to `ghcr.io` on every tag that matches `[0-9]*`. Tags have **no `v` prefix** — use `2.34.1`, not `v2.34.1`.

### 1. Make sure `main` is ready

```bash
git checkout main
git pull
git status                       # working tree must be clean
make test-back && make test-front
```

Stop here if anything is red or uncommitted — releases never bundle untested or in-progress changes.

### 2. Pick the next version

Run `git tag --list --sort=-v:refname | head -1` to see the latest tag.

Apply semver based on what landed since:

- **patch** (e.g. `2.34.0` → `2.34.1`): bug fixes only, no behaviour change
- **minor** (e.g. `2.34.1` → `2.35.0`): new features, additive only
- **major** (e.g. `2.34.1` → `3.0.0`): breaking changes for the user or for API consumers

If unsure, default to patch.

### 3. Write the changelog entry

The user-visible changelog lives at `frontend/public/changelogs.json` and is rendered inside the app's "What's new" view. **Prepend** a new object to the JSON array:

```json
{
  "version": "2.34.2",
  "date": "2026-06-18",
  "title": "Short user-facing title (under 60 chars)",
  "description": "One or two sentences on what changed and why.",
  "type": "bugfix",
  "details": [
    "Concrete change 1 (past tense, user-visible)",
    "Concrete change 2"
  ]
}
```

Rules:

- `type` is one of `feature` / `bugfix` / `breaking`. Use `feature` whenever the release adds anything new.
- One bullet per logical change, **not** per commit. Squash related commits into a single bullet.
- Past tense in the bullets ("Added…", "Fixed…", "Behoben…").
- Bullets should be readable by a non-developer customer. Internal-only details belong in the diary, not the changelog.

### 4. Commit, tag, push

```bash
# 1. Commit the changelog
git add frontend/public/changelogs.json
git commit -m "Add changelog for 2.34.2"

# 2. Tag the commit (no v prefix)
git tag 2.34.2

# 3. Push commit AND tag
git push
git push --tags
```

### 5. Watch CI

```bash
gh run list --limit 2
```

The tag push triggers a five-job pipeline: `preflight`, `test-backend`, `test-frontend`, `build-backend`, `build-frontend`. All five must finish green before the new images land on `ghcr.io`. If any job fails:

- Do **not** force-push or delete the tag.
- Land the fix on `main` first, then cut a new patch tag (e.g. `2.34.3`) that supersedes the broken one. The previous tag stays in history as evidence.

### Hotfix

Same flow as a normal release, just on top of `main` directly. There is no separate release branch.

### AI helper

Inside Claude Code there is a `/release` slash command that automates steps 2–4 (version bump, changelog scaffold, commit, tag, push). Useful for routine releases. It will refuse to release if the working tree is dirty or tests are red.

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

## License

This project is dual-licensed:

- **Open Source**: [GNU General Public License v3.0](LICENSE) — free to use, modify, and distribute under GPLv3 terms.
- **Commercial**: A commercial license is available for use without copyleft obligations. See [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) for details or contact [Christoph Becker](https://ch-becker.de).

## Development Guidelines

- Use TDD - write tests first
- All development happens inside Docker containers
- Multi-tenant: All models use TenantModel base class
- i18n: German (de) and English (en) supported
- Commit only when all tests are green
