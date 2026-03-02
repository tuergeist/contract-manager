## Context

The `TimeTrackingProjectMapping` model links external time tracking projects (from Clockodo) to contracts. Today this is a manual process: users search for projects in the `TimeTrackingTab` dialog and click to map them. A Celery Beat task (`refresh_all_time_tracking_data`) runs every 12 hours to sync cached hours/revenue for existing mappings.

The time tracking provider abstraction (`TimeTrackingProvider`) already fetches all projects via `get_projects()`, and the `ClockodoProvider` implements this with pagination. The `time_tracking_config` JSONField on the Tenant model stores provider credentials.

## Goals / Non-Goals

**Goals:**
- Allow per-contract pattern rules that auto-link matching time tracking projects
- Run auto-link evaluation as a daily background task alongside existing data refresh
- Track whether each mapping was created manually or by auto-link
- Provide pattern preview so users can verify rules before saving

**Non-Goals:**
- Regex support (substring and prefix matching cover the use cases; regex can be added later)
- Auto-unlinking when a rule is deleted (existing mappings are retained)
- Customer-level rules (rules are per-contract, optionally targeting a specific contract item)

## Decisions

### 1. New `AutoLinkRule` model

Add a new model in `contracts/models.py`:

```python
class AutoLinkRule(TenantModel):
    contract = ForeignKey(Contract, on_delete=CASCADE, related_name="auto_link_rules")
    contract_item = ForeignKey(ContractItem, on_delete=SET_NULL, null=True, blank=True)
    pattern = CharField(max_length=255)  # the text to match against
    match_type = CharField(choices=[("contains", "Contains"), ("starts_with", "Starts with")])
    is_active = BooleanField(default=True)
```

**Why a separate model rather than a field on TimeTrackingProjectMapping?** Rules are about _intent_ (what to match in the future), while mappings are about _state_ (what is currently linked). A rule can produce zero or many mappings. Keeping them separate avoids conflating the two concepts.

**Why not regex?** Substring ("contains") and prefix ("starts_with") cover the stated use cases (e.g. `[KSB DL-Vertrag]`). Regex adds complexity and security concerns (ReDoS). It can be added as a third match_type later without schema changes.

### 2. `link_source` field on TimeTrackingProjectMapping

Add a `link_source` CharField to `TimeTrackingProjectMapping`:
- `"manual"` (default) — created via the existing UI flow
- `"auto"` — created by the auto-link task

Also add an optional `auto_link_rule` ForeignKey to trace which rule created the mapping. This is nullable (manual mappings have no rule) and SET_NULL on rule deletion so mappings survive rule cleanup.

**Why not a boolean `is_auto_linked`?** The `link_source` char field is more extensible (could add "import" or other sources later), and the FK to the rule provides full traceability.

### 3. Auto-link task: extend existing Celery Beat schedule

Add a new task `auto_link_time_tracking_projects` that runs daily. Rather than bundling it into the existing `refresh_all_time_tracking_data` task (which runs every 12h for data refresh), keep it separate:

1. For each active tenant with a time tracking provider configured:
   - Fetch all projects via `provider.get_projects()`
   - Load all `AutoLinkRule` objects (active, with contract not cancelled)
   - For each rule, find projects matching the pattern
   - For each match, check if `external_project_id` already has a mapping for this tenant
   - If not, create the mapping with `link_source="auto"` and `auto_link_rule=rule`
   - Trigger `sync_time_tracking_mapping_task` for each new mapping to populate cached data
2. Pace API calls per tenant (one `get_projects` call per tenant, not per rule)

Schedule: once daily (86400 seconds), added to `CELERY_BEAT_SCHEDULE`.

**Why not run inside `refresh_all_time_tracking_data`?** Different cadences — data refresh every 12h, auto-link once daily. Separate tasks are easier to monitor, retry, and disable independently.

### 4. Pattern matching logic in Python

Matching is straightforward string operations:
- `contains`: `pattern.lower() in project_name.lower()`
- `starts_with`: `project_name.lower().startswith(pattern.lower())`

Case-insensitive matching is the default — project names from Clockodo can have varied casing. The candidate set is small (all projects for one tenant, typically <200), so Python matching is fine.

### 5. Preview query on BankingQuery → ContractQuery

Add a `previewAutoLinkMatches` query that takes `pattern`, `matchType`, and `contractId`. It fetches projects from the provider, applies the pattern, and returns a list of matching projects that are not yet linked to any contract. This reuses the existing `get_projects()` provider method.

### 6. Frontend: extend TimeTrackingTab

Add an "Auto-link Rules" section to the existing `TimeTrackingTab` component, below the current mappings list. This section shows:
- Existing rules with pattern, match type, and a delete button
- An "Add rule" button that opens a dialog with pattern input, match type select, optional contract item select, and a preview panel
- Mappings display a small badge ("auto" / "manual") to show their source

No new route needed — this fits naturally into the existing tab.

## Risks / Trade-offs

- **[Provider API rate limits]** → The auto-link task calls `get_projects()` once per tenant per day. Clockodo's rate limits are generous for read endpoints. The existing 5-second pacing in `refresh_all_time_tracking_data` is not needed here since we make a single call per tenant.
- **[First-match-wins for multi-contract matches]** → A project can only be mapped to one contract (unique on `tenant + external_project_id`). If the same project name matches rules on two contracts, only the first rule (by creation order) wins. This is acceptable — ambiguous patterns should be avoided. The preview feature helps users verify before saving.
- **[Stale project list]** → The preview fetches live data from the provider. If the provider is slow or unavailable, the preview will fail. Mitigation: show a loading state and error message.
- **[Migration: existing mappings]** → The `link_source` field defaults to `"manual"`, so existing mappings are automatically classified correctly. No data backfill needed.
