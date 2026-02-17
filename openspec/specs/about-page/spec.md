## Requirements

### Requirement: About page accessible from navigation
The system SHALL provide an About page at route `/about` accessible from the sidebar or settings area.

#### Scenario: User navigates to About page
- **WHEN** user clicks the About link in the navigation
- **THEN** the About page is displayed with version info and attributions sections

### Requirement: Display frontend and backend version info
The About page SHALL display the application version number and build date for both frontend and backend.

#### Scenario: Version info shown with build metadata
- **WHEN** the About page loads
- **THEN** the page displays the frontend version, frontend build date, backend version, and backend build date

#### Scenario: Version info unavailable in development
- **WHEN** the About page loads in a development environment where build metadata is not injected
- **THEN** the page displays "dev" as the version and omits the build date

### Requirement: Display OSS dependency attributions
The About page SHALL display a list of all open-source dependencies for both frontend and backend, including package name, version, and license type.

#### Scenario: Frontend dependencies listed
- **WHEN** the About page loads
- **THEN** a "Frontend Dependencies" section lists all npm production packages with name, version, and license

#### Scenario: Backend dependencies listed
- **WHEN** the About page loads
- **THEN** a "Backend Dependencies" section lists all Python production packages with name, version, and license

#### Scenario: User can search attributions
- **WHEN** the user types in a search field above the attributions list
- **THEN** the list filters to show only packages whose name contains the search term

### Requirement: Backend version endpoint
The backend SHALL expose a public REST endpoint `GET /api/version/` that returns version and build date as JSON.

#### Scenario: Version endpoint returns build info
- **WHEN** a GET request is made to `/api/version/`
- **THEN** the response is JSON with fields `version` (string) and `buildDate` (string, ISO format or empty)

#### Scenario: Version endpoint requires no authentication
- **WHEN** an unauthenticated GET request is made to `/api/version/`
- **THEN** the response is 200 OK with the version info (no auth required)
