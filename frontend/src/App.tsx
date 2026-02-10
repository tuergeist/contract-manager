import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './features/auth/Login'
import { AcceptInvitation } from './features/auth/AcceptInvitation'
import { ResetPassword } from './features/auth/ResetPassword'
import { Dashboard } from './features/dashboard/Dashboard'
import { CustomerList } from './features/customers/CustomerList'
import { CustomerDetail } from './features/customers/CustomerDetail'
import { ProductList } from './features/products/ProductList'
import { ContractList } from './features/contracts/ContractList'
import { ContractForm } from './features/contracts/ContractForm'
import { ContractDetail } from './features/contracts/ContractDetail'
import { RevenueForecast } from './features/forecast/RevenueForecast'
import { SettingsLayout } from './features/settings/SettingsLayout'
import { ContractImport } from './features/contracts/import/ContractImport'
import { InvoiceExportPage } from './features/invoices/InvoiceExportPage'
import { AuditLogPage } from './features/audit/AuditLogPage'
import { BankingPage } from './features/banking/BankingPage'
import { CounterpartyDetailPage } from './features/banking/CounterpartyDetailPage'
import { LiquidityForecast } from './features/liquidity'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/invite/:token" element={<AcceptInvitation />} />
      <Route path="/reset-password/:token" element={<ResetPassword />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<CustomerList />} />
        <Route path="customers/:id" element={<CustomerDetail />} />
        <Route path="products" element={<ProductList />} />
        <Route path="contracts" element={<ContractList />} />
        <Route path="contracts/new" element={<ContractForm />} />
        <Route path="contracts/:id" element={<ContractDetail />} />
        <Route path="contracts/:id/edit" element={<ContractForm />} />
        <Route path="forecast" element={<RevenueForecast />} />
        <Route path="settings" element={<SettingsLayout />} />
        <Route path="settings/general" element={<SettingsLayout />} />
        <Route path="settings/team" element={<SettingsLayout />} />
        <Route path="settings/team/roles" element={<SettingsLayout />} />
        <Route path="settings/invoices" element={<SettingsLayout />} />
        <Route path="settings/invoices/numbering" element={<SettingsLayout />} />
        <Route path="settings/invoices/template" element={<SettingsLayout />} />
        <Route path="contracts/import" element={<ContractImport />} />
        <Route path="invoices/export" element={<InvoiceExportPage />} />
        <Route path="banking" element={<BankingPage />} />
        <Route path="banking/counterparty/:name" element={<CounterpartyDetailPage />} />
        <Route path="liquidity-forecast" element={<LiquidityForecast />} />
        <Route path="audit-log" element={<AuditLogPage />} />
      </Route>
    </Routes>
  )
}

export default App
