## 1. Backend: Models & Migrations

- [x] 1.1 Add `AutoLinkRule` model to `contracts/models.py` — `contract` FK, optional `contract_item` FK (SET_NULL), `pattern` CharField(255), `match_type` CharField with choices `contains`/`starts_with`, `is_active` BooleanField(default=True)
- [x] 1.2 Add `link_source` CharField to `TimeTrackingProjectMapping` — choices `manual`/`auto`, default `"manual"`
- [x] 1.3 Add `auto_link_rule` FK on `TimeTrackingProjectMapping` — nullable, SET_NULL, related_name `"created_mappings"`
- [x] 1.4 Create migration for all three changes
- [x] 1.5 Register `AutoLinkRule` in `contracts/admin.py`

## 2. Backend: Pattern Matching & Auto-Link Task

- [x] 2.1 Add `matches_project_name(pattern, match_type, project_name) -> bool` helper in `services/time_tracking.py` — case-insensitive contains/starts_with
- [x] 2.2 Add `auto_link_time_tracking_projects` Celery task in `contracts/tasks.py` — iterate active tenants, fetch projects once per tenant, match against active rules (contract not cancelled), create mappings, trigger data sync for new mappings
- [x] 2.3 Add `auto-link-time-tracking` entry to `CELERY_BEAT_SCHEDULE` in `settings/base.py` — schedule 86400 seconds (daily)

## 3. Backend: GraphQL Schema

- [x] 3.1 Add `AutoLinkRuleType` Strawberry type — `id`, `pattern`, `matchType`, `isActive`, `contractItemId`, `contractItemName`, `createdMappingsCount`
- [x] 3.2 Add `autoLinkRules` field to `TimeTrackingSummaryType` — list of rules for the contract
- [x] 3.3 Add `linkSource` field to `TimeTrackingMappingType`
- [x] 3.4 Add `createAutoLinkRule` mutation — accepts `contractId`, `pattern`, `matchType`, optional `contractItemId`, validates contract exists and item belongs to contract
- [x] 3.5 Add `deleteAutoLinkRule` mutation — accepts `ruleId`, deletes rule, existing mappings remain
- [x] 3.6 Add `previewAutoLinkMatches` query — accepts `pattern`, `matchType`, fetches projects from provider, returns list of matching unlinked projects

## 4. Backend: Tests

- [x] 4.1 Test `matches_project_name` helper — contains match, starts_with match, case insensitivity, no match
- [x] 4.2 Test `auto_link_time_tracking_projects` task — creates mapping for matching project, skips already-linked, skips cancelled contracts, skips tenants without provider, first-match-wins for multi-rule conflicts
- [x] 4.3 Test `createAutoLinkRule` mutation — success, validates contract item belongs to contract
- [x] 4.4 Test `deleteAutoLinkRule` mutation — rule deleted, existing mappings retained
- [x] 4.5 Test `previewAutoLinkMatches` query — returns matching unlinked projects, excludes already-linked
- [x] 4.6 Test `linkSource` field on mapping type — manual mapping shows "manual", auto mapping shows "auto"

## 5. Frontend: Auto-Link Rules UI

- [x] 5.1 Add `AUTO_LINK_RULES` fields to `TIME_TRACKING_SUMMARY_QUERY` in `TimeTrackingTab.tsx` — include `autoLinkRules` list and `linkSource` on mappings
- [x] 5.2 Add `CREATE_AUTO_LINK_RULE` and `DELETE_AUTO_LINK_RULE` mutations
- [x] 5.3 Add `PREVIEW_AUTO_LINK_MATCHES` query
- [x] 5.4 Show "Auto-link Rules" section below mappings list — display existing rules with pattern, match type badge, linked item name, created mappings count, and delete button
- [x] 5.5 Add "Add auto-link rule" dialog — pattern input, match type select (Contains/Starts with), optional contract item select, preview panel showing matching projects
- [x] 5.6 Show `linkSource` badge ("auto"/"manual") on each mapping row in the existing mappings list

## 6. i18n

- [x] 6.1 Add translation keys to `en.json` and `de.json` — auto-link rules header, add rule button, pattern label, match type labels, preview button, empty states, link source badges, delete confirmation
