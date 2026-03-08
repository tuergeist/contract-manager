## Context

Clockodo integration exists (read-only):
- `ClockodoProvider` — fetches projects, services, users, time entries via API v2
- `TimeTrackingProjectMapping` model — links external project IDs to contracts
- Manual project linking via UI (user picks from fetched project list)
- Config stored in `tenant.time_tracking_config` (provider, api_email, api_key)

No write operations exist yet. No customer-level linking (projects are linked directly to contracts). Contract activation is a status transition in `update_contract_status` mutation (draft → active).

## Goals / Non-Goals

**Goals:**
- Bidirectional CM customer ↔ Clockodo customer mapping
- Automatic Clockodo project creation on contract activation
- Configurable naming templates for maintenance and one-off projects
- User control over one-off project granularity (per contract vs. per item)
- Automatic TimeTrackingProjectMapping creation

**Non-Goals:**
- Syncing project changes back (rename, delete) after creation
- Automatic project archival on contract cancellation (future consideration)
- Supporting providers other than Clockodo for write operations
- Time entry creation or management

## Decisions

### 1. Customer linking via `clockodo_customer_id` on Customer model
Add nullable `clockodo_customer_id` CharField to `apps.customers.Customer`. Simple, direct, no extra join table needed. If we need multi-provider support later, we can add a generic external_ids JSONField.

### 2. Naming templates in tenant settings
Store in `tenant.time_tracking_config`:
```json
{
  "maintenance_project_template": "Wartung {customer_name}",
  "oneoff_project_template": "{customer_name} - {contract_name}"
}
```
Placeholders: `{customer_name}`, `{contract_name}`, `{item_name}`, `{year}`.

**Rationale:** Keeps config close to other time tracking settings. No new model needed.

### 3. Activation hook with confirmation dialog
The `update_contract_status` mutation stays unchanged. Instead:
1. Frontend calls a new `previewContractActivation(contractId)` query before activating
2. Query returns: customer linked? maintenance project exists? one-off items needing projects?
3. Frontend shows a dialog with options (create/skip, combined/per-item)
4. User confirms → frontend calls `provisionClockodoProjects(contractId, options)` mutation
5. Then calls `updateContractStatus` to activate

**Alternative considered:** Hook inside `updateContractStatus` — rejected because it would make the mutation too complex and the user needs to make choices (one-off strategy).

### 4. Write operations on ClockodoProvider
Add `_post` helper + `create_customer(name)` and `create_project(customer_id, name)` methods. Same retry/rate-limit pattern as reads.

### 5. Maintenance project lookup: by name pattern on Clockodo customer
To check if a maintenance project already exists, query Clockodo projects for the linked customer and match against the naming template pattern. Cache the lookup result.

### 6. Celery task for project creation
`provision_clockodo_projects` task handles the actual API calls. Non-blocking — if it fails, contract is still activated and user is notified of the failure via the response.

## Risks / Trade-offs

- [Risk] Clockodo API rate limits on project creation → Mitigation: 0.3s sleep between calls, retry on 429 (existing pattern)
- [Risk] Clockodo customer name doesn't match CM exactly → Mitigation: fuzzy matching option + manual override in bulk linking
- [Risk] Naming template collisions (two contracts with same name) → Mitigation: Clockodo allows duplicate project names per customer; the mapping prevents confusion on CM side
- [Risk] User skips project creation, forgets to do it later → Mitigation: show warning on contract detail if no time tracking mapping exists
