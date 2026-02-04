## 1. Backend GraphQL Schema

- [x] 1.1 Add `DashboardKPIsType` strawberry type with fields: totalActiveContracts, totalContractValue, annualRecurringRevenue, yearToDateRevenue, currentYearForecast, nextYearForecast
- [x] 1.2 Implement `dashboardKpis` query in contracts schema with KPI calculation logic
- [x] 1.3 Add helper function for calculating TCV (total contract value) using get_duration_months()
- [x] 1.4 Add helper function for calculating ARR (annualized recurring revenue) excluding one-off items
- [x] 1.5 Add helper function for YTD and forecast calculations using get_recognition_schedule()

## 2. Frontend KPI Card Component

- [x] 2.1 Create `KPICard.tsx` component with title, value, and info icon
- [x] 2.2 Add Tooltip integration for calculation explanation on info icon hover
- [x] 2.3 Format currency values with € symbol and thousands separators

## 3. Dashboard Integration

- [x] 3.1 Add GraphQL query for dashboardKpis in Dashboard.tsx
- [x] 3.2 Replace placeholder content with responsive KPI card grid (3 columns on desktop, 2 on tablet, 1 on mobile)
- [x] 3.3 Add loading state while KPIs are being fetched
- [x] 3.4 Add error handling for failed KPI queries

## 4. Translations

- [x] 4.1 Add English translations for KPI labels and explanations in en.json
- [x] 4.2 Add German translations for KPI labels and explanations in de.json

## 5. Testing

- [x] 5.1 Create test_dashboard_kpis.py with tests for total active contracts count
- [x] 5.2 Add tests for TCV calculation (fixed-term and open-ended contracts)
- [x] 5.3 Add tests for ARR calculation (recurring items only, excludes one-off)
- [x] 5.4 Add tests for YTD and forecast calculations
- [x] 5.5 Add test for tenant isolation (user only sees own tenant's KPIs)
