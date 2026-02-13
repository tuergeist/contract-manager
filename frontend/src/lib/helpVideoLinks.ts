import { useQuery, gql } from '@apollo/client'
import { useLocation } from 'react-router-dom'
import { useMemo } from 'react'

export const ROUTE_KEYS = [
  { key: '/', labelKey: 'nav.dashboard' },
  { key: '/customers', labelKey: 'nav.customers' },
  { key: '/customers/:id', labelKey: 'routes.customerDetail' },
  { key: '/contracts', labelKey: 'nav.contracts' },
  { key: '/contracts/:id', labelKey: 'routes.contractDetail' },
  { key: '/contracts/:id/edit', labelKey: 'routes.contractEdit' },
  { key: '/products', labelKey: 'nav.products' },
  { key: '/banking', labelKey: 'nav.banking' },
  { key: '/invoices/imported', labelKey: 'nav.importedInvoices' },
  { key: '/invoices/export', labelKey: 'nav.invoiceExport' },
  { key: '/forecast', labelKey: 'nav.forecast' },
  { key: '/liquidity-forecast', labelKey: 'nav.liquidityForecast' },
  { key: '/todos', labelKey: 'nav.todos' },
  { key: '/audit-log', labelKey: 'nav.auditLog' },
] as const

export interface HelpVideoLink {
  url: string
  label: string | null
}

export interface HelpVideoLinksEntry {
  routeKey: string
  links: HelpVideoLink[]
}

export const HELP_VIDEO_LINKS_QUERY = gql`
  query HelpVideoLinks {
    helpVideoLinks {
      routeKey
      links {
        url
        label
      }
    }
  }
`

export const UPDATE_HELP_VIDEO_LINKS_MUTATION = gql`
  mutation UpdateHelpVideoLinks($entries: [HelpVideoLinksEntryInput!]!) {
    updateHelpVideoLinks(entries: $entries) {
      routeKey
      links {
        url
        label
      }
    }
  }
`

function matchRoute(pattern: string, pathname: string): boolean {
  if (pattern === pathname) return true
  const patternParts = pattern.split('/')
  const pathParts = pathname.split('/')
  if (patternParts.length !== pathParts.length) return false
  return patternParts.every(
    (part, i) => part.startsWith(':') || part === pathParts[i]
  )
}

export function useHelpVideoLinks(): HelpVideoLink[] {
  const { pathname } = useLocation()
  const { data } = useQuery<{ helpVideoLinks: HelpVideoLinksEntry[] }>(
    HELP_VIDEO_LINKS_QUERY
  )

  return useMemo(() => {
    const entries = data?.helpVideoLinks ?? []
    // Find the most specific matching route (longest pattern first)
    const sorted = [...entries].sort(
      (a, b) => b.routeKey.length - a.routeKey.length
    )
    for (const entry of sorted) {
      if (matchRoute(entry.routeKey, pathname)) {
        return entry.links
      }
    }
    return []
  }, [data, pathname])
}
