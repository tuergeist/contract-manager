## Context

Contracts contain recurring and one-off items. Today these items are independent — each has its own billing dates and no relationship to other items. In practice, recurring items often depend on one-off deliverables (custom development, workshops, onboarding) that must be completed first. Users currently track this manually and update billing dates by hand after delivery.

The `ContractItem` model already supports `start_date`, `billing_start_date`, `billing_end_date`, and `is_one_off`. The billing schedule logic in `Contract.get_billing_schedule()` iterates over all items and generates billing events based on these dates. Invoice generation in `InvoiceService` calls the billing schedule to determine what to bill.

## Goals / Non-Goals

**Goals:**
- Model item-to-item dependencies within a contract (one-off blocks recurring)
- Track delivery status of one-off items so billing can be gated on completion
- Automatically unblock dependent items when a dependency is marked as delivered
- Provide a cross-contract "Projects" overview of all deliverable items
- Keep billing logic correct: blocked items produce no billing events

**Non-Goals:**
- Cross-contract dependencies (item in contract A depends on item in contract B)
- Multi-level dependency chains (A → B → C) — only direct single-parent dependencies
- Project management features (timelines, Gantt charts, resource allocation)
- External project tool integrations (Jira, Asana, etc.)
- Automatic delivery detection — delivery is always a manual user action

## Decisions

### D1: Delivery status on ContractItem (not a separate model)

Add `delivery_status` field directly to `ContractItem` rather than creating a separate `Deliverable` or `Project` model.

**Rationale:** The item itself IS the deliverable. A separate model would add unnecessary indirection and complicate queries. The field is nullable — items without delivery tracking simply have `delivery_status = NULL` (current behavior preserved).

**Values:** `NULL` (no tracking / not applicable), `pending`, `delivered`

**Alternative considered:** Separate `Project` model linking to items — rejected because it duplicates item metadata and complicates the billing path.

### D2: Self-referencing FK for dependencies

Add `depends_on` FK on `ContractItem` pointing to another `ContractItem` in the same contract (self-referential, nullable).

**Rationale:** Simple, fits the existing pattern (`added_by_amendment` is already an FK on `ContractItem`). Single FK means one parent dependency per item, which matches the business case (recurring item depends on one development effort).

**Constraint:** `depends_on` must reference an item in the same contract. Enforced at the mutation level, not at DB level (same pattern as other cross-field validations).

### D3: Billing blocking via existing date mechanism

A dependent item whose dependency is not yet delivered has `billing_start_date = NULL`. When the dependency is marked as delivered, the system sets `billing_start_date` on the dependent item (user can choose the date, defaulting to the delivery date).

**Rationale:** The billing schedule already skips items with no `billing_start_date` that falls within the forecast window — no changes needed to the core billing loop. This is simpler and more reliable than adding a separate "blocked" boolean that billing must check.

**Alternative considered:** Adding an `is_blocked` boolean — rejected because it creates two sources of truth (blocked flag vs. missing billing date) and requires changes throughout the billing pipeline.

### D4: `delivered_at` timestamp for audit trail

When marking an item as delivered, store `delivered_at` (DateField). This serves as both an audit trail and the default `billing_start_date` for dependent items.

### D5: Projects overview as a flat query, not a new model

The "Projects" page queries `ContractItem` objects filtered by `delivery_status IS NOT NULL` (i.e., items that have delivery tracking enabled). No separate `Project` model needed.

**Rationale:** Avoids model proliferation. The query is simple: `ContractItem.objects.filter(delivery_status__isnull=False).select_related('contract', 'contract__customer', 'product')`.

### D6: Route placement

New route at `/projects` in the main navigation, between Contracts and Invoices. This gives it first-class visibility since it's a daily workflow for tracking outstanding work.

## Risks / Trade-offs

**[Risk] Orphaned dependencies when items are deleted** → When a `depends_on` target is deleted, use `SET_NULL` on the FK. The dependent item becomes unblocked (no dependency). The mutation for deleting items should warn if the item has dependents.

**[Risk] Delivery status on all item types, not just one-offs** → The `delivery_status` field is available on all items but only meaningful when explicitly set. Recurring items could theoretically have delivery tracking too (e.g., "setup phase complete"), keeping the model flexible.

**[Trade-off] Single dependency only** → An item can depend on exactly one other item. If multi-dependency is needed later, this could evolve to a M2M through table — but for now YAGNI applies.

**[Trade-off] No automatic billing_start_date propagation** → When a dependency is delivered, the user is prompted to set the billing start date for dependent items rather than auto-setting it. This gives users control over the exact billing date (which may not always be the delivery date).
