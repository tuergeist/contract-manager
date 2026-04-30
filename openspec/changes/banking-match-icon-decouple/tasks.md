## 1. Backend: matchSummary field

- [ ] 1.1 Add `MatchSummaryType` to `apps/banking/schema.py` with `status: str`, `match_count: int`, `total_matched: Decimal`.
- [ ] 1.2 Add `match_summary` resolver on `BankTransactionType` that aggregates from prefetched `invoice_matches`.
- [ ] 1.3 Update list resolver to `prefetch_related("invoice_matches__invoice", "invoice_matches__invoice_record", "invoice_matches__incoming_invoice")`.
- [ ] 1.4 Backend tests: open / partial / fully matched cases each produce expected summary.

## 2. Frontend: Status Pill Component

- [ ] 2.1 Create `frontend/src/features/banking/MatchStatusPill.tsx` (props: `status`, `count`, optional `total`).
- [ ] 2.2 Color/text mapping per design (grey / yellow / green).
- [ ] 2.3 Unit test rendering for each status.

## 3. Frontend: Banking + Counterparty Pages

- [ ] 3.1 Update `BankingPage.tsx` row renderer: replace blue/grey `Link2` color logic with `<MatchStatusPill>`.
- [ ] 3.2 Update `CounterpartyDetailPage.tsx` rows similarly.
- [ ] 3.3 Action icon (`Link2`) always grey; tooltip text via i18n based on `matchCount > 0`.
- [ ] 3.4 `FileText` quick-link only when `matchCount === 1`.

## 4. i18n

- [ ] 4.1 Add keys: `banking.matchStatus.open`, `.partial`, `.paid`, `banking.matchAction.assign`, `banking.matchAction.edit`.

## 5. Tests

- [ ] 5.1 Vitest: `<MatchStatusPill>` snapshot for each variant.
- [ ] 5.2 Playwright E2E: a matched tx shows green pill + FileText link; clicking action icon opens sheet.

## 6. Verification

- [ ] 6.1 Backend test (`make test-back`).
- [ ] 6.2 Frontend type check.
- [ ] 6.3 Manual smoke in dev: tx with 0 / 1 / 2 / 3 matches.
