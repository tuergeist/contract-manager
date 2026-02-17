## Context

The application currently has no version indicator or OSS attribution page. Version/build info is not injected during Docker builds. The frontend uses Vite (env vars via `import.meta.env`), the backend uses Django, and images are built via GitHub Actions with `docker/build-push-action`.

## Goals / Non-Goals

**Goals:**
- Show version + build date for both FE and BE on a single About page
- List all OSS dependencies with license info for both stacks
- Inject version metadata at CI build time without changing the dev workflow
- Keep it simple — one page, no database, no auth required for the version endpoint

**Non-Goals:**
- Full license text display (just name + type is sufficient)
- Auto-update checks or release notes
- Version info in API response headers

## Decisions

### 1. About page as a standalone route, not a settings tab

**Decision**: Add `/about` as a top-level route with its own nav item (Info icon at bottom of sidebar), rather than embedding it as a settings sub-tab.

**Rationale**: About/version info is read-only and relevant to all users regardless of permissions. Settings tabs are permission-gated and focused on configuration. An Info icon near the bottom of the sidebar (before Settings) is a common pattern.

**Alternative**: Settings sub-tab — rejected because it would require settings.read permission and buries the info.

### 2. Vite env vars for frontend build metadata

**Decision**: Use `VITE_BUILD_VERSION` and `VITE_BUILD_DATE` as Docker build args → Vite env vars. Access via `import.meta.env.VITE_BUILD_VERSION` at runtime.

**Rationale**: This is the standard Vite mechanism for compile-time constants. No runtime config injection needed. Falls back to `undefined` in dev, which the About page handles gracefully.

### 3. `build-info.json` file for backend metadata

**Decision**: Write a static `build-info.json` file during Docker build via a `RUN echo` command using the build args. The `/api/version/` endpoint reads this file.

**Rationale**: Simpler than environment variables for the backend — a file is read once at startup and doesn't require config changes. If the file is missing (local dev), the endpoint returns `{"version": "dev", "buildDate": ""}`.

**Alternative**: Env vars read by Django settings — works but adds more settings boilerplate for a static read-only value.

### 4. License generation at Docker build time

**Decision**:
- **Frontend**: Run `npx license-checker-rsync2 --json --production --out /app/licenses-frontend.json` during the builder stage, then copy to nginx static dir.
- **Backend**: Run `pip-licenses --format=json --output-file=/app/licenses-backend.json` during the builder stage.

Both files are JSON arrays with `name`, `version`, `license`/`licenseType` fields.

**Rationale**: Generating at build time captures the exact dependency tree of the built image. `license-checker-rsync2` is the maintained fork of the popular `license-checker` npm package. `pip-licenses` is the standard tool for Python. Both are dev/build-only dependencies — `license-checker-rsync2` is only in the builder stage, and `pip-licenses` runs in the builder stage before it's discarded.

### 5. Backend serves its own license file via the version endpoint

**Decision**: The `/api/version/` endpoint returns `{ version, buildDate }`. A separate `/api/version/licenses/` endpoint returns the backend license JSON. The frontend fetches both the backend version and backend licenses from these endpoints. Frontend licenses are served as a static file by nginx at `/licenses-frontend.json`.

**Rationale**: Keeps the frontend from needing a backend roundtrip for its own license data (it's a static file co-located with the built assets). Backend licenses must come through the API since the backend is a separate service.

### 6. CI: use git ref as version

**Decision**: In the build step, set `BUILD_VERSION` to the git tag if present (`github.ref_name` for tag triggers), or the short SHA for branch builds. `BUILD_DATE` is set to the current UTC ISO 8601 timestamp.

**Rationale**: Tags like `1.2.3` are the semantic version. For non-tag builds (which only happen during tests, since builds are gated by `startsWith(github.ref, 'refs/tags/')`), the SHA serves as a unique identifier.

## Risks / Trade-offs

- **License data size**: The JSON files could be large (~50-100KB each). Acceptable for an About page loaded on-demand. The frontend file is cached by nginx, the backend one by the browser.
- **Stale license data**: License info is frozen at build time. This is correct — it reflects the actual deployed dependencies, not the current repo state.
- **`license-checker-rsync2` adds build time**: Only runs during Docker image builds, not in dev or tests. Adds ~5s to the frontend build stage.
- **`pip-licenses` must be installed in builder**: Added to the builder stage only; not present in the final runtime image.
