## Context

The system imports HubSpot "closedwon" deals as draft contracts, using `closedate` as the contract's `start_date`. There is no dedicated field to track when a deal was won, and no way to distinguish new business from existing/renewal contracts. The existing revenue goals system (RevenueGoal model) only supports per-stream targets keyed by `revenue_type`.

Currently, contracts with `hubspot_deal_id` set were imported from HubSpot (won deals). Contracts without it were created manually and represent existing/renewal business.

## Goals / Non-Goals

**Goals:**
- Store `deal_won_date` on contracts, populated automatically from HubSpot and settable manually
- Derive new vs existing business classification from `hubspot_deal_id` presence
- Add new goal types for tracking won business metrics (new ARR, new development revenue, etc.)
- Show new business metrics on the Goals dashboard
- Backfill `deal_won_date` for existing HubSpot-imported contracts via data migration

**Non-Goals:**
- Syncing deal stage changes back to HubSpot
- Tracking deal pipeline stages (only closedwon matters)
- Allowing users to manually toggle new/existing classification (derived automatically)
- Modifying the existing per-stream revenue goals — new business goals are additive

## Decisions

### 1. `deal_won_date` as a nullable DateField on Contract

Add `deal_won_date = DateField(null=True, blank=True)` to the Contract model. This is populated from HubSpot `closedate` on deal import. For manually created contracts, it stays null (existing business).

**Why not reuse `start_date`?** The won date and contract start date can differ — a deal might be won in December but the contract starts in January. Keeping them separate preserves accuracy.

**Why not a separate Deal model?** The 1:1 relationship between deals and contracts doesn't justify a new model. A field on Contract is simpler and avoids joins.

### 2. New business = has `hubspot_deal_id`

A contract is "new business" if it has a `hubspot_deal_id`. This is a simple, existing convention that requires no migration. Expose this as a computed `is_new_business` property on the model and a GraphQL field.

**Alternative considered:** A separate `is_new_business` boolean field. Rejected because it duplicates information already derivable from `hubspot_deal_id` and could get out of sync.

### 3. Separate goal model for new business goals: `NewBusinessGoal`

Create a new `NewBusinessGoal` model rather than extending `RevenueGoal`. The new goals have different semantics — they track won deal metrics rather than recognized revenue targets. Fields:

- `tenant`, `year` (same as RevenueGoal)
- `goal_type`: TextChoices — `new_arr` (won new ARR), `new_development` (won development/training revenue), `new_deal_count` (number of won deals)
- `target_amount`: Decimal target

Unique together: `tenant + year + goal_type`.

**Why not extend RevenueGoal?** The existing model is keyed by `revenue_type` (recurring/dev/training). New business goals cut across streams (new ARR spans all streams) or track counts, not revenue types. Mixing them would require schema changes and break the existing settings UI.

### 4. Calculate new business metrics from contracts with `deal_won_date` in the year

Query contracts where `deal_won_date` falls in the selected year and `hubspot_deal_id` is not null. From their items, calculate:

- **Won new ARR**: Sum of annualized recurring item prices from new contracts won that year
- **Won development revenue**: Sum of one-off + development items from new contracts won that year
- **Won deal count**: Count of distinct contracts won that year

This reuses the existing item-level revenue type classification and price calculations.

### 5. Backfill via data migration (not API call)

For existing contracts with `hubspot_deal_id` and no `deal_won_date`, set `deal_won_date = start_date` in a data migration. This is safe because the current HubSpot sync already uses `closedate` as `start_date`.

**Why not call HubSpot API during migration?** API calls in migrations are fragile (rate limits, auth tokens, network). Since `closedate` is already stored as `start_date`, copying it is reliable and instant.

### 6. Dashboard layout: new "New Business" card below the existing goals table

Add a collapsible section below the per-stream goals table showing:
- Summary cards: Won ARR, Won Development, Won Deal Count (each with target if set, actual, progress)
- Expandable list of won deals for the year (contract name, customer, won date, ARR)

## Risks / Trade-offs

- **[`deal_won_date = start_date` assumption]** → Acceptable because HubSpot sync currently sets `start_date` from `closedate`. For any edge cases where they differ, users can manually update `deal_won_date` later via the contract edit form.
- **[New business = has hubspot_deal_id]** → Manually created contracts are always "existing". If a user creates a contract manually for a genuinely new deal (without HubSpot), it won't count as new business. This is acceptable for now — HubSpot is the canonical source for won deals.
- **[Separate NewBusinessGoal model]** → Adds a new table and settings UI section. The alternative (overloading RevenueGoal) would be more complex and harder to maintain.

## Migration Plan

1. Add `deal_won_date` field to Contract (nullable, no default)
2. Data migration: `UPDATE contract SET deal_won_date = start_date WHERE hubspot_deal_id IS NOT NULL`
3. Update HubSpot sync to populate `deal_won_date` from `closedate`
4. Add `NewBusinessGoal` model + migration
5. Add GraphQL queries/mutations
6. Update frontend Goals dashboard and settings

Rollback: All changes are additive (new field, new model). Rollback = revert migrations.
