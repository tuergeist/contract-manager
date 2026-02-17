## Why

There is no way for users or administrators to see which version of the application is deployed, when it was built, or what open-source software it depends on. An About page provides transparency on build info and fulfills OSS license attribution requirements.

## What Changes

- Add an **About page** (`/about`) in the frontend accessible from the sidebar/settings
- Display **frontend and backend version numbers** (git tag) and **build dates** injected at image build time
- Display **OSS dependency attributions** listing all frontend (npm) and backend (pip) packages with their licenses
- Add a **backend `/api/version/` endpoint** exposing the backend's version and build date
- Pass **`BUILD_VERSION` and `BUILD_DATE` as build args** in both Dockerfiles
- Update the **GitHub Actions CI workflow** to pass git tag + build timestamp as build args to Docker builds
- Generate license files at build time: `npm run licenses` and `pip-licenses` output bundled into the images

## Capabilities

### New Capabilities
- `about-page`: Frontend About page showing version info (FE + BE) and OSS attributions
- `build-version-injection`: CI workflow and Dockerfile changes to inject version/date at build time, plus backend version endpoint

### Modified Capabilities
_(none)_

## Impact

- **Frontend**: New `/about` route, new `AboutPage` component, Vite env vars for version/date, license list generated at build time
- **Backend**: New `/api/version/` REST endpoint (public, no auth), build info written to a file during Docker build
- **CI**: `build.yml` updated to pass `BUILD_VERSION` (from git tag) and `BUILD_DATE` (ISO timestamp) as Docker build args
- **Dockerfiles**: Both `Dockerfile.prod` files updated with `ARG`/`ENV` for version and date; license generation steps added
- **Dependencies**: `pip-licenses` added as build-time dev dependency for backend
