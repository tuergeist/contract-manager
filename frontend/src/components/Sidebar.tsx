import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Users,
  Package,
  FileText,
  TrendingUp,
  Settings,
  LogOut,
  FileDown,
  History,
  UserCog,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

interface NavItem {
  to: string
  icon: typeof LayoutDashboard
  labelKey: string
  adminOnly?: boolean
  end?: boolean
}

const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboard, labelKey: 'nav.dashboard', end: true },
  { to: '/customers', icon: Users, labelKey: 'nav.customers' },
  { to: '/products', icon: Package, labelKey: 'nav.products' },
  { to: '/contracts', icon: FileText, labelKey: 'nav.contracts' },
  { to: '/invoices/export', icon: FileDown, labelKey: 'nav.invoiceExport' },
  { to: '/forecast', icon: TrendingUp, labelKey: 'nav.forecast' },
  { to: '/audit-log', icon: History, labelKey: 'nav.auditLog' },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings', end: true },
  { to: '/settings/users', icon: UserCog, labelKey: 'users.title', adminOnly: true },
]

export function Sidebar() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()

  return (
    <aside className="flex w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-xl font-semibold">Contract Manager</h1>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navItems
          .filter((item) => !item.adminOnly || user?.isAdmin)
          .map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
            >
              <item.icon className="h-5 w-5" />
              {t(item.labelKey)}
            </NavLink>
          ))}
      </nav>
      <div className="border-t p-4">
        <div className="mb-2 px-3">
          <p className="text-sm font-medium text-gray-900">{user?.firstName} {user?.lastName}</p>
          <p className="text-xs text-gray-500">{user?.email}</p>
          <p className="text-xs text-gray-400">{user?.tenantName}</p>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <LogOut className="h-5 w-5" />
          {t('auth.signOut')}
        </button>
      </div>
    </aside>
  )
}
