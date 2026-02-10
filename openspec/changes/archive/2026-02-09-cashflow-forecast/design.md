## Context

The banking app already imports MT940 bank statements with transactions containing:
- `counterparty_name`, `counterparty_iban` - who was paid
- `amount` - how much (negative for debits/costs)
- `entry_date` - when it occurred
- `booking_text` - payment description

We need to detect patterns in these transactions and project them forward.

## Goals / Non-Goals

**Goals:**
- Detect recurring payments automatically (2+ similarity matches)
- Project detected patterns into future months
- Show liquidity forecast visualization
- Allow users to confirm/adjust detected patterns
- Support both costs (outgoing) and income (incoming)

**Non-Goals:**
- Budget planning or expense categorization
- Bank account synchronization (we already have MT940 import)
- Integration with external forecasting tools
- Multi-currency forecasting (EUR only for now)

## Decisions

### 1. Similarity Detection Algorithm

**Decision:** Score-based matching with threshold

Compare transactions pairwise using:
- **Counterparty match** (name or IBAN): +1 point
- **Amount match** (exact or within 5%): +1 point
- **Timing pattern** (same day-of-month ±3 days, or same interval): +1 point

Require **2+ points** to consider transactions as potentially recurring.

**Why:** Flexible enough to catch "same vendor, varying amounts" (subscriptions with usage) or "same amount, different timing" (quarterly payments). Strict exact-match would miss too many valid patterns.

### 2. Pattern Storage Model

**Decision:** New `RecurringPattern` model linked to source transactions

```
RecurringPattern:
  - tenant (FK)
  - counterparty_name (extracted from transactions)
  - counterparty_iban (optional)
  - average_amount (calculated)
  - frequency (monthly/quarterly/annual/irregular)
  - day_of_month (typical payment day)
  - confidence_score (0.0-1.0)
  - is_confirmed (user verified)
  - is_ignored (user dismissed)
  - last_occurrence (date)
  - source_transactions (M2M to BankTransaction)
```

**Why:** Separating patterns from transactions allows users to confirm/dismiss without affecting source data. M2M link preserves audit trail.

### 3. Forecast Projection

**Decision:** Project confirmed + high-confidence patterns for next 12 months

- Confirmed patterns: always project
- Auto-detected (confidence > 0.7): project with visual indicator
- Low confidence: show in "review" list, don't project

**Why:** Balances automation with accuracy. Users see forecast immediately but can refine.

### 4. UI Structure

**Decision:** Single page with three sections

1. **Forecast Chart** - Line/bar chart showing projected balance over time
2. **Recurring Patterns** - List of detected patterns with confirm/ignore actions
3. **Projection Table** - Month-by-month breakdown of expected transactions

**Why:** Everything on one page reduces navigation. Chart provides quick overview, table provides detail.

## Risks / Trade-offs

**[Risk] False positives in pattern detection** → Require user confirmation before high-impact decisions; show confidence scores; allow easy dismissal

**[Risk] Stale patterns after payment changes** → Re-run detection periodically; show "last seen" date; flag patterns not seen in 2+ expected cycles

**[Risk] Performance with large transaction history** → Limit detection to last 12-18 months; use database aggregation; cache pattern results

**[Trade-off] Simplicity vs accuracy** → Starting with score-based matching is simpler but may need ML later for better pattern recognition
