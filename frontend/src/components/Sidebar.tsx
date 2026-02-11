import { useState, useRef, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useLazyQuery, useQuery, gql } from '@apollo/client'
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
  Search,
  Loader2,
  User,
  FileSignature,
  X,
  MessageSquarePlus,
  Landmark,
  Wallet,
  ListTodo,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { FeedbackModal } from './FeedbackModal'

const GLOBAL_SEARCH = gql`
  query GlobalSearch($query: String!, $limit: Int) {
    globalSearch(query: $query, limit: $limit) {
      totalCount
      groups {
        type
        label
        hasMore
        items {
          id
          title
          subtitle
          url
        }
      }
    }
  }
`

const FEEDBACK_ENABLED = gql`
  query FeedbackEnabled {
    feedbackEnabled
  }
`

interface NavItem {
  to: string
  icon: typeof LayoutDashboard
  labelKey: string
  permission?: string  // "resource.action" format
  end?: boolean
}

const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboard, labelKey: 'nav.dashboard', end: true },
  { to: '/todos', icon: ListTodo, labelKey: 'nav.todos' },
  { to: '/customers', icon: Users, labelKey: 'nav.customers' },
  { to: '/products', icon: Package, labelKey: 'nav.products' },
  { to: '/contracts', icon: FileText, labelKey: 'nav.contracts' },
  { to: '/invoices/export', icon: FileDown, labelKey: 'nav.invoiceExport', permission: 'invoices.export' },
  { to: '/banking', icon: Landmark, labelKey: 'nav.banking', permission: 'banking.read' },
  { to: '/liquidity-forecast', icon: Wallet, labelKey: 'nav.liquidityForecast', permission: 'banking.read' },
  { to: '/forecast', icon: TrendingUp, labelKey: 'nav.forecast' },
  { to: '/audit-log', icon: History, labelKey: 'nav.auditLog' },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings', end: true },
]

export function Sidebar() {
  const { t } = useTranslation()
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [showResults, setShowResults] = useState(false)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const [search, { data, loading }] = useLazyQuery(GLOBAL_SEARCH, {
    fetchPolicy: 'cache-and-network',
  })

  const { data: feedbackData } = useQuery(FEEDBACK_ENABLED)
  const feedbackEnabled = feedbackData?.feedbackEnabled ?? false

  // Debounced search
  useEffect(() => {
    if (searchQuery.length < 2) {
      return
    }
    const timer = setTimeout(() => {
      search({ variables: { query: searchQuery, limit: 10 } })
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, search])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // "/" keyboard shortcut to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input/textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }
      if (e.key === '/') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleResultClick = (url: string) => {
    navigate(url)
    setSearchQuery('')
    setShowResults(false)
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'customer':
        return User
      case 'contract':
        return FileSignature
      default:
        return FileText
    }
  }

  return (
    <aside className="flex w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center border-b px-6">
        <img src="/vsx-logo.jpg" alt="VSX Vogel Software" className="h-10" />
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {/* Search Bar */}
        <div ref={searchRef} className="relative mb-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setShowResults(true)
              }}
              onFocus={() => setShowResults(true)}
              placeholder={t('common.search')}
              className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2 pl-9 pr-8 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {loading ? (
              <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
            ) : searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('')
                  setShowResults(false)
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showResults && searchQuery.length >= 2 && (
            <div className="absolute left-0 top-full z-50 mt-1 w-[340px] max-h-80 overflow-y-auto rounded-lg border bg-white shadow-lg">
              {data?.globalSearch?.groups?.length > 0 ? (
                data.globalSearch.groups.map((group: { type: string; label: string; hasMore: boolean; items: { id: number; title: string; subtitle?: string; url: string }[] }) => (
                  <div key={group.type}>
                    <div className="sticky top-0 bg-gray-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                      {t(`search.${group.type}`, group.label)}
                    </div>
                    {group.items.map((item) => {
                      const Icon = getTypeIcon(group.type)
                      return (
                        <button
                          key={`${group.type}-${item.id}`}
                          onClick={() => handleResultClick(item.url)}
                          className="flex w-full items-start gap-3 px-3 py-2 text-left hover:bg-gray-50"
                        >
                          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium text-gray-900">
                              {item.title}
                            </div>
                            {item.subtitle && (
                              <div className="truncate text-xs text-gray-500">
                                {item.subtitle}
                              </div>
                            )}
                          </div>
                        </button>
                      )
                    })}
                    {group.hasMore && (
                      <div className="px-3 py-2 text-xs text-gray-400 italic">
                        {t('search.moreResults', '+ more results...')}
                      </div>
                    )}
                  </div>
                ))
              ) : !loading ? (
                <div className="px-3 py-4 text-center text-sm text-gray-500">
                  {t('search.noResults')}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {navItems
          .filter((item) => {
            if (!item.permission) return true
            const [resource, action] = item.permission.split('.')
            return hasPermission(resource, action)
          })
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
        {feedbackEnabled && (
          <button
            onClick={() => setFeedbackOpen(true)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            <MessageSquarePlus className="h-5 w-5" />
            {t('feedback.menuItem')}
          </button>
        )}
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
        >
          <LogOut className="h-5 w-5" />
          {t('auth.signOut')}
        </button>
      </div>

      <FeedbackModal open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </aside>
  )
}
