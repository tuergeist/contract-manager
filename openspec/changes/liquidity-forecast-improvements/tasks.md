## 1. Calendar Year Date Range

- [x] 1.1 Update `LiquidityForecast.tsx` to calculate forecast period as Jan 1 current year to Jan 1 next year
- [x] 1.2 Calculate months parameter dynamically based on current date to Jan 1 next year
- [x] 1.3 Update ForecastChart x-axis labels to show calendar year range

## 2. Patterns Table Sorting

- [x] 2.1 Add `sortColumn` and `sortDirection` state to LiquidityForecast component
- [x] 2.2 Create sortable column headers for: counterparty, amount, frequency, confidence
- [x] 2.3 Implement sorting logic with `useMemo` for each column type (string, number, custom frequency order)
- [x] 2.4 Add visual indicator (arrow) for current sort column and direction

## 3. Patterns Table Search

- [x] 3.1 Add `searchQuery` state to LiquidityForecast component
- [x] 3.2 Add search input field above patterns table
- [x] 3.3 Implement debounced filtering (300ms) by counterparty name (case-insensitive)

## 4. Independent Income/Costs Toggles

- [x] 4.1 Replace single type filter with `showIncome` and `showCosts` boolean states (both default true)
- [x] 4.2 Update filter UI to show two toggle buttons instead of radio/select
- [x] 4.3 Filter patterns list based on toggle states (amount > 0 for income, amount < 0 for costs)
- [x] 4.4 Pass filtered patterns to ForecastChart component
- [x] 4.5 Pass filtered patterns to ProjectionTable component
- [x] 4.6 Show hint message when both toggles are off

## 5. Translations

- [x] 5.1 Add German and English translations for new UI elements (search placeholder, toggle labels, sort tooltips, empty state hint)
