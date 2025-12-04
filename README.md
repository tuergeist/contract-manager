# Contract-Manager

Für eine kleine Firma (20-30 MA) mit 70-150 Kunden soll der Contract Manager ein Tool zur Vertragsverwaltung sein.

## Fakten

- Kunden können mehrere Verträge haben die voneinander unabhängig oder miteinander verbunden sein können
- Bei verbundenen Verträgen ist ein Vertrag der primäre und er bestimmt dann die Laufzeit und Zahlungsintervalle
- Verträge enthalten n Produkte in Anzahl m 
- Verträge haben entweder einen Komplettpreis oder bestehen aus den Projekt-Einzelpreisen
- 

## Tech Stack
- React with Typescript
- Django with Strawberry-GraphQL https://github.com/strawberry-graphql/strawberry-django to use GraphQL to interact between front-backend
- PostgreSQL as a database
- if needed, Redis for caching

## Development Guidelines
- use TDD
- commit only when all tests are green
- always create unit tests for front- and backend
- Use some selected E2E Tests with Playwright to check if a complete feature works (or just login)
- make the dev environment use docker compose locally, so the developers has nothing else to install
- github workflows shall run tests on branches, build images on merge requests, pushing building final images when merged to main
- use semantic versioning (together with git tags)

## Target for Production
- k8s or swarm running linux
- 
