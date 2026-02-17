## 1. CI & Dockerfiles — Build Version Injection

- [ ] 1.1 Update `.github/workflows/build.yml` to compute `BUILD_VERSION` (tag name or short SHA) and `BUILD_DATE` (ISO 8601 UTC) and pass them as build-args to both backend and frontend Docker builds
- [ ] 1.2 Update `frontend/Dockerfile.prod` to accept `BUILD_VERSION` and `BUILD_DATE` args, set them as `VITE_BUILD_VERSION` and `VITE_BUILD_DATE` env vars before `npm run build`
- [ ] 1.3 Update `backend/Dockerfile.prod` to accept `BUILD_VERSION` and `BUILD_DATE` args and write `build-info.json` to `/app/build-info.json`

## 2. License Generation at Build Time

- [ ] 2.1 Add `license-checker-rsync2` as a dev dependency in `frontend/package.json` and add a script `"licenses": "license-checker-rsync2 --json --production --customPath name,version,licenses --out licenses-frontend.json"`
- [ ] 2.2 Update `frontend/Dockerfile.prod` builder stage to run license generation and copy `licenses-frontend.json` to the nginx static dir
- [ ] 2.3 Install `pip-licenses` in the `backend/Dockerfile.prod` builder stage and run `pip-licenses --format=json --output-file=licenses-backend.json`, then copy the file into the final image

## 3. Backend Version Endpoint

- [ ] 3.1 Create `/api/version/` REST view that reads `build-info.json` and returns `{ "version": "...", "buildDate": "..." }` (no auth required, fallback to `"dev"` if file missing)
- [ ] 3.2 Create `/api/version/licenses/` REST view that reads `licenses-backend.json` and returns it as JSON (no auth, fallback to empty array)
- [ ] 3.3 Register both views in `config/urls.py`
- [ ] 3.4 Add tests for version and licenses endpoints

## 4. Frontend About Page

- [ ] 4.1 Create `frontend/src/features/about/AboutPage.tsx` with version info section (reads `import.meta.env.VITE_BUILD_VERSION` and `VITE_BUILD_DATE` for FE, fetches `/api/version/` for BE)
- [ ] 4.2 Add OSS attributions section: fetch `/licenses-frontend.json` (static) and `/api/version/licenses/` (backend), display both in searchable tables
- [ ] 4.3 Add `/about` route in `App.tsx`
- [ ] 4.4 Add Info nav item in `Sidebar.tsx` (Info icon, before Settings)
- [ ] 4.5 Add i18n keys for About page labels in `de.json` and `en.json`
- [ ] 4.6 Run `npx tsc --noEmit` to verify no type errors
