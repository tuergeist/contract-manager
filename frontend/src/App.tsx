import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './features/auth/Login'
import { Dashboard } from './features/dashboard/Dashboard'
import { CustomerList } from './features/customers/CustomerList'
import { CustomerDetail } from './features/customers/CustomerDetail'
import { ProductList } from './features/products/ProductList'
import { ContractList } from './features/contracts/ContractList'
import { ContractForm } from './features/contracts/ContractForm'
import { ContractDetail } from './features/contracts/ContractDetail'
import { RevenueForecast } from './features/forecast/RevenueForecast'
import { Settings } from './features/settings/Settings'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
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
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
