## Requirements

### Requirement: CI passes version and date as Docker build args
The GitHub Actions workflow SHALL pass `BUILD_VERSION` and `BUILD_DATE` as build arguments when building both frontend and backend Docker images.

#### Scenario: Tagged release build
- **WHEN** CI builds images from a git tag (e.g., `1.2.3`)
- **THEN** `BUILD_VERSION` is set to the tag name and `BUILD_DATE` is set to the current ISO 8601 timestamp

#### Scenario: Non-tagged build
- **WHEN** CI builds images from a branch push (no tag)
- **THEN** `BUILD_VERSION` is set to the short commit SHA and `BUILD_DATE` is set to the current ISO 8601 timestamp

### Requirement: Frontend Dockerfile accepts and embeds build args
The frontend `Dockerfile.prod` SHALL accept `BUILD_VERSION` and `BUILD_DATE` as build arguments and pass them as `VITE_BUILD_VERSION` and `VITE_BUILD_DATE` environment variables during the Vite build step.

#### Scenario: Vite build receives version env vars
- **WHEN** the frontend image is built with `BUILD_VERSION=1.2.3` and `BUILD_DATE=2026-02-16T10:00:00Z`
- **THEN** `import.meta.env.VITE_BUILD_VERSION` resolves to `"1.2.3"` and `import.meta.env.VITE_BUILD_DATE` resolves to `"2026-02-16T10:00:00Z"` in the built JavaScript

### Requirement: Backend Dockerfile accepts and writes build info
The backend `Dockerfile.prod` SHALL accept `BUILD_VERSION` and `BUILD_DATE` as build arguments and write them to a `build-info.json` file in the application directory.

#### Scenario: Build info file created during image build
- **WHEN** the backend image is built with `BUILD_VERSION=1.2.3` and `BUILD_DATE=2026-02-16T10:00:00Z`
- **THEN** a `build-info.json` file exists at `/app/build-info.json` containing `{"version": "1.2.3", "buildDate": "2026-02-16T10:00:00Z"}`

### Requirement: Frontend generates license list at build time
The frontend `Dockerfile.prod` SHALL generate a JSON file listing all production npm dependency licenses during the build stage, bundled into the final image as a static asset.

#### Scenario: License file generated and served
- **WHEN** the frontend image is built
- **THEN** a file at `/usr/share/nginx/html/licenses-frontend.json` exists containing an array of objects with `name`, `version`, and `license` fields

### Requirement: Backend generates license list at build time
The backend `Dockerfile.prod` SHALL generate a JSON file listing all production Python dependency licenses during the build stage.

#### Scenario: License file available to backend
- **WHEN** the backend image is built
- **THEN** a file at `/app/licenses-backend.json` exists containing an array of objects with `name`, `version`, and `license` fields
