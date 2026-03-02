## Why

Time tracking projects are currently linked to contracts manually via the UI. Many customers follow a naming convention for their time tracking projects (e.g. `[KSB DL-Vertrag]` in the project name). When these naming patterns are consistent, the system could auto-link projects to contracts — saving manual work and ensuring new projects are linked promptly without user intervention.

## What Changes

- Add per-contract configurable pattern rules that match against external project names (e.g. substring match, prefix, regex)
- Add a background Celery Beat task that runs daily, fetches projects from the time tracking provider, matches them against pattern rules, and creates mappings automatically
- Auto-linked mappings should be distinguishable from manual ones (flag or source field) so users can see how a link was created
- Pattern rules are managed on the contract detail, alongside existing manual time tracking mappings
- Existing manual linking flow remains unchanged

## Capabilities

### New Capabilities
- `time-tracking-auto-link`: Pattern-based rules for automatically linking time tracking projects to contracts, including background sync

### Modified Capabilities

## Impact

- `backend/apps/contracts/models.py` — new model for auto-link rules, new field on TimeTrackingProjectMapping to track link source
- `backend/apps/contracts/schema.py` — CRUD mutations for auto-link rules, query to preview matches
- `backend/apps/contracts/tasks.py` — new Celery task for auto-link sync, integrate with existing daily refresh
- `backend/apps/contracts/services/time_tracking.py` — pattern matching logic
- Frontend contract detail — UI for managing auto-link rules alongside existing mappings
