import { useState, useRef, useEffect, useMemo } from 'react'
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
  FileUp,
  History,
  Search,
  Loader2,
  User,
  FileSignature,
  Receipt,
  X,
  MessageSquarePlus,
  Landmark,
  ListTodo,
  Info,
  FolderKanban,
  PieChart,
  ArrowRight,
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
  { to: '/projects', icon: FolderKanban, labelKey: 'nav.projects' },
  { to: '/invoices', icon: FileUp, labelKey: 'nav.invoices', permission: 'invoices.read' },
  { to: '/offers', icon: FileSignature, labelKey: 'nav.offers', permission: 'offers.read' },
  { to: '/banking', icon: Landmark, labelKey: 'nav.banking', permission: 'banking.read' },
  { to: '/forecasts', icon: TrendingUp, labelKey: 'nav.forecasts' },
  { to: '/department-analysis', icon: PieChart, labelKey: 'nav.departmentAnalysis' },
  { to: '/audit-log', icon: History, labelKey: 'nav.auditLog' },
  { to: '/about', icon: Info, labelKey: 'nav.about' },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings', end: true },
]

interface SearchablePage {
  labelKey: string
  keywords: string[]  // extra terms to match against (always lowercase)
  url: string
  permission?: string
}

const searchablePages: SearchablePage[] = [
  // Main pages
  { labelKey: 'nav.dashboard', keywords: ['dashboard', 'home', 'start'], url: '/' },
  { labelKey: 'nav.todos', keywords: ['todos', 'aufgaben', 'tasks', 'board'], url: '/todos' },
  { labelKey: 'nav.customers', keywords: ['customers', 'kunden'], url: '/customers' },
  { labelKey: 'nav.products', keywords: ['products', 'produkte'], url: '/products' },
  { labelKey: 'nav.contracts', keywords: ['contracts', 'verträge'], url: '/contracts' },
  { labelKey: 'nav.projects', keywords: ['projects', 'projekte'], url: '/projects' },
  { labelKey: 'nav.invoices', keywords: ['invoices', 'rechnungen'], url: '/invoices', permission: 'invoices.read' },
  { labelKey: 'nav.offers', keywords: ['offers', 'angebote'], url: '/offers', permission: 'offers.read' },
  { labelKey: 'nav.banking', keywords: ['banking', 'bankkonten', 'bank'], url: '/banking', permission: 'banking.read' },
  { labelKey: 'nav.forecasts', keywords: ['forecasts', 'vorschauen', 'prognose'], url: '/forecasts' },
  { labelKey: 'nav.departmentAnalysis', keywords: ['department', 'abteilung', 'analyse', 'analysis'], url: '/department-analysis' },
  { labelKey: 'nav.auditLog', keywords: ['audit', 'auditlog', 'log', 'history'], url: '/audit-log' },
  // Settings pages
  { labelKey: 'settings.tabs.user', keywords: ['user', 'benutzer', 'profile', 'profil', 'security', 'sicherheit', '2fa'], url: '/settings' },
  { labelKey: 'settings.tabs.general', keywords: ['general', 'allgemein', 'settings', 'einstellungen', 'contracts'], url: '/settings/general', permission: 'settings.read' },
  { labelKey: 'settings.generalTabs.helpVideos', keywords: ['help videos', 'hilfevideos', 'video', 'tutorial'], url: '/settings/general/help-videos', permission: 'settings.read' },
  { labelKey: 'settings.generalTabs.performance', keywords: ['performance', 'leistung', 'cache'], url: '/settings/general/performance', permission: 'settings.read' },
  { labelKey: 'settings.generalTabs.revenueGoals', keywords: ['revenue goals', 'umsatzziele', 'ziele', 'goals'], url: '/settings/general/revenue-goals', permission: 'settings.read' },
  { labelKey: 'settings.generalTabs.security', keywords: ['security', 'sicherheit', '2fa enforce', 'two factor'], url: '/settings/general/security', permission: 'settings.read' },
  { labelKey: 'settings.tabs.integrations', keywords: ['integrations', 'integrationen', 'hubspot'], url: '/settings/integrations', permission: 'settings.read' },
  { labelKey: 'settings.integrationTabs.timeTracking', keywords: ['clockodo', 'time tracking', 'zeiterfassung'], url: '/settings/integrations/time-tracking', permission: 'settings.read' },
  { labelKey: 'settings.integrationTabs.email', keywords: ['email', 'm365', 'smtp', 'e-mail'], url: '/settings/integrations/email', permission: 'settings.read' },
  { labelKey: 'settings.integrationTabs.notifications', keywords: ['notifications', 'benachrichtigungen', 'slack', 'webhook'], url: '/settings/integrations/notifications', permission: 'settings.read' },
  { labelKey: 'settings.integrationTabs.api', keywords: ['api', 'mcp', 'token', 'api key'], url: '/settings/integrations/api', permission: 'settings.read' },
  { labelKey: 'settings.team.users', keywords: ['users', 'benutzer', 'team', 'mitarbeiter', 'invite', 'einladen'], url: '/settings/team', permission: 'users.read' },
  { labelKey: 'settings.team.roles', keywords: ['roles', 'rollen', 'permissions', 'berechtigungen', 'rbac'], url: '/settings/team/roles', permission: 'users.read' },
  { labelKey: 'invoices.companyData.title', keywords: ['company', 'firma', 'firmendaten', 'legal', 'address', 'adresse', 'ust', 'vat', 'steuernummer'], url: '/settings/documents', permission: 'invoices.settings' },
  { labelKey: 'invoices.template.title', keywords: ['invoice template', 'rechnungsvorlage', 'pdf', 'template', 'vorlage', 'logo'], url: '/settings/documents/template', permission: 'invoices.settings' },
  { labelKey: 'invoices.zugferd.title', keywords: ['zugferd', 'xrechnung', 'electronic', 'elektronisch', 'en16931'], url: '/settings/documents/zugferd', permission: 'invoices.settings' },
  { labelKey: 'settings.tabs.numbering', keywords: ['numbering', 'nummerierung', 'nummernkreis', 'invoice number', 'rechnungsnummer'], url: '/settings/numbering', permission: 'invoices.settings' },
  { labelKey: 'settings.numbering.creditNotes', keywords: ['credit note', 'gutschrift', 'storno', 'stornierung'], url: '/settings/numbering/storno', permission: 'invoices.settings' },
  { labelKey: 'settings.numbering.offers', keywords: ['offer number', 'angebotsnummer', 'offer numbering'], url: '/settings/numbering/offers', permission: 'invoices.settings' },
  { labelKey: 'settings.numbering.orderConfirmations', keywords: ['order confirmation number', 'ab nummer', 'auftragsbestätigung nummer'], url: '/settings/numbering/order-confirmations', permission: 'invoices.settings' },
  { labelKey: 'settings.tabs.emailTemplates', keywords: ['email template', 'e-mail vorlage', 'email vorlage', 'mail template', 'invoice email', 'rechnungs-email'], url: '/settings/email-templates', permission: 'invoices.settings' },
  { labelKey: 'settings.emailTemplates.orderConfirmation', keywords: ['order confirmation', 'auftragsbestätigung', 'ab email', 'order email'], url: '/settings/email-templates/order-confirmation', permission: 'invoices.settings' },
  { labelKey: 'settings.tabs.banking', keywords: ['banking settings', 'bankeinstellungen', 'bank account', 'bankkonto', 'iban'], url: '/settings/banking', permission: 'banking.read' },
]

export function Sidebar() {
  const { t } = useTranslation()
  const { user, logout, hasPermission } = useAuth()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [showResults, setShowResults] = useState(false)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
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

  // Client-side page search
  const filteredPages = useMemo(() => {
    if (searchQuery.length < 2) return []
    const q = searchQuery.toLowerCase()
    return searchablePages.filter((page) => {
      // Permission check
      if (page.permission) {
        const [resource, action] = page.permission.split('.')
        if (!hasPermission(resource, action)) return false
      }
      // Match against translated label or keywords
      const label = t(page.labelKey).toLowerCase()
      if (label.includes(q)) return true
      return page.keywords.some((kw) => kw.includes(q))
    }).slice(0, 5)
  }, [searchQuery, t, hasPermission])

  // Flat list of all visible result URLs for keyboard navigation
  const allResultUrls = useMemo(() => {
    const urls: string[] = []
    filteredPages.forEach((page) => urls.push(page.url))
    data?.globalSearch?.groups?.forEach((group: { items: { url: string }[] }) => {
      group.items.forEach((item) => urls.push(item.url))
    })
    return urls
  }, [filteredPages, data])

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(-1)
  }, [allResultUrls])

  const handleResultClick = (url: string) => {
    navigate(url)
    setSearchQuery('')
    setShowResults(false)
    setSelectedIndex(-1)
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || allResultUrls.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev < allResultUrls.length - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : allResultUrls.length - 1))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleResultClick(allResultUrls[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowResults(false)
      setSelectedIndex(-1)
      inputRef.current?.blur()
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'customer':
        return User
      case 'contract':
        return FileSignature
      case 'invoice':
        return Receipt
      default:
        return FileText
    }
  }

  return (
    <aside className="flex w-64 flex-col border-r bg-white">
      <div className="flex h-16 items-center border-b px-6">
        <img src="/vsx-logo.jpg" alt="VSX Vogel Software" className="h-10" />
      </div>
      {/* Search Bar - outside nav to avoid overflow clipping */}
      <div className="relative px-4 pt-4 pb-1">
        <div ref={searchRef} className="relative">
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
              onKeyDown={handleSearchKeyDown}
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
          {showResults && searchQuery.length >= 2 && (() => {
            let flatIndex = 0
            return (
            <div className="absolute left-0 top-full z-50 mt-1 w-[480px] max-h-80 overflow-y-auto rounded-lg border bg-white shadow-lg">
              {/* Pages (client-side) */}
              {filteredPages.length > 0 && (
                <div>
                  <div className="sticky top-0 bg-gray-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {t('search.pages', 'Pages')}
                  </div>
                  {filteredPages.map((page) => {
                    const idx = flatIndex++
                    return (
                      <button
                        key={page.url}
                        onClick={() => handleResultClick(page.url)}
                        className={cn(
                          'flex w-full items-start gap-3 px-3 py-2 text-left',
                          idx === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
                        )}
                      >
                        <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
                        <div className="truncate text-sm font-medium text-gray-900">
                          {t(page.labelKey)}
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
              {/* Data results (API) */}
              {data?.globalSearch?.groups?.map((group: { type: string; label: string; hasMore: boolean; items: { id: number; title: string; subtitle?: string; url: string }[] }) => (
                <div key={group.type}>
                  <div className="sticky top-0 bg-gray-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    {t(`search.${group.type}`, group.label)}
                  </div>
                  {group.items.map((item) => {
                    const Icon = getTypeIcon(group.type)
                    const idx = flatIndex++
                    return (
                      <button
                        key={`${group.type}-${item.id}`}
                        onClick={() => handleResultClick(item.url)}
                        className={cn(
                          'flex w-full items-start gap-3 px-3 py-2 text-left',
                          idx === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
                        )}
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
              ))}
              {/* No results */}
              {filteredPages.length === 0 && !data?.globalSearch?.groups?.length && !loading && (
                <div className="px-3 py-4 text-center text-sm text-gray-500">
                  {t('search.noResults')}
                </div>
              )}
            </div>
            )
          })()}
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto space-y-1 px-4 pb-4">
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
          <p className="text-xs text-gray-400">{user?.companyName || user?.tenantName}</p>
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
