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
import { ForecastsPage } from './features/forecasts/ForecastsPage'
import { SettingsLayout } from './features/settings/SettingsLayout'
import { ContractImport } from './features/contracts/import/ContractImport'
import { InvoiceExportPage } from './features/invoices/InvoiceExportPage'
import { InvoiceDetail } from './features/invoices/InvoiceDetail'
import { InvoiceList } from './features/invoices/InvoiceList'
import { AuditLogPage } from './features/audit/AuditLogPage'
import { BankingPage } from './features/banking/BankingPage'
import { CounterpartyDetailPage } from './features/banking/CounterpartyDetailPage'
import { TodoBoard } from './features/todos/TodoBoard'
import { AboutPage } from './features/about/AboutPage'
import { ProjectList } from './features/projects/ProjectList'

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
        <Route path="projects" element={<ProjectList />} />
        <Route path="forecasts" element={<ForecastsPage />} />
        <Route path="settings/*" element={<SettingsLayout />} />
        <Route path="contracts/import" element={<ContractImport />} />
        <Route path="invoices/export" element={<InvoiceExportPage />} />
        <Route path="invoices/:id" element={<InvoiceDetail />} />
        <Route path="invoices" element={<InvoiceList />} />
        <Route path="banking" element={<BankingPage />} />
        <Route path="banking/counterparty/:id" element={<CounterpartyDetailPage />} />
        <Route path="audit-log" element={<AuditLogPage />} />
        <Route path="todos" element={<TodoBoard />} />
        <Route path="about" element={<AboutPage />} />
      </Route>
    </Routes>
  )
}

export default App
