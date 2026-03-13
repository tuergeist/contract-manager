import { useState, useEffect, useRef } from 'react'
import { usePersistedState } from '@/lib/usePersistedState'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, Filter, ChevronDown, Search } from 'lucide-react'
import { AuditLogTable, AuditLogEntry } from './AuditLogTable'
import { HelpVideoButton } from '@/components/HelpVideoButton'

const AUDIT_LOGS_QUERY = gql`
  query AuditLogs(
    $entityType: String
    $action: String
    $userId: Int
    $dateFrom: DateTime
    $dateTo: DateTime
    $search: String
    $first: Int
    $after: String
  ) {
    auditLogs(
      entityType: $entityType
      action: $action
      userId: $userId
      dateFrom: $dateFrom
      dateTo: $dateTo
      search: $search
      first: $first
      after: $after
    ) {
      edges {
        node {
          id
          action
          entityType
          entityId
          entityRepr
          userId
          userName
          changes {
            field
            oldValue
            newValue
          }
          timestamp
          parentEntityType
          parentEntityId
        }
        cursor
      }
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
    }
  }
`

const USERS_QUERY = gql`
  query UsersForAuditFilter {
    users {
      id
      fullName
      email
    }
  }
`

interface AuditLogsData {
  auditLogs: {
    edges: Array<{
      node: AuditLogEntry
      cursor: string
    }>
    pageInfo: {
      hasNextPage: boolean
      endCursor: string | null
    }
    totalCount: number
  }
}

interface UsersData {
  users: Array<{
    id: string
    fullName: string
    email: string
  }>
}

const ENTITY_TYPES = ['contract', 'contract_item', 'customer', 'product', 'invoice_record', 'todo'] as const
const ACTIONS = ['create', 'update', 'delete'] as const
const PAGE_SIZE = 25

export function AuditLogPage() {
  const { t } = useTranslation()
  const [entityTypeFilter, setEntityTypeFilter] = usePersistedState<string>('cm:auditLog:entityTypeFilter', '')
  const [actionFilter, setActionFilter] = usePersistedState<string>('cm:auditLog:actionFilter', '')
  const [userFilter, setUserFilter] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [searchInput, setSearchInput] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchQuery(searchInput)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [searchInput])

  const { data: usersData } = useQuery<UsersData>(USERS_QUERY)

  const { data, loading, error, fetchMore } = useQuery<AuditLogsData>(AUDIT_LOGS_QUERY, {
    variables: {
      entityType: entityTypeFilter || null,
      action: actionFilter || null,
      userId: userFilter ? parseInt(userFilter, 10) : null,
      dateFrom: dateFrom ? new Date(dateFrom + 'T00:00:00').toISOString() : null,
      dateTo: dateTo ? new Date(dateTo + 'T23:59:59').toISOString() : null,
      search: searchQuery || null,
      first: PAGE_SIZE,
      after: null,
    },
    fetchPolicy: 'cache-and-network',
  })

  const entries = data?.auditLogs.edges.map((edge) => edge.node) || []
  const totalCount = data?.auditLogs.totalCount || 0
  const hasNextPage = data?.auditLogs.pageInfo.hasNextPage || false
  const endCursor = data?.auditLogs.pageInfo.endCursor

  const handleLoadMore = () => {
    if (hasNextPage && endCursor) {
      fetchMore({
        variables: {
          after: endCursor,
        },
        updateQuery: (prev, { fetchMoreResult }) => {
          if (!fetchMoreResult) return prev
          return {
            auditLogs: {
              ...fetchMoreResult.auditLogs,
              edges: [...prev.auditLogs.edges, ...fetchMoreResult.auditLogs.edges],
            },
          }
        },
      })
    }
  }

  return (
    <div data-testid="audit-log-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('audit.title')}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {totalCount} {t('audit.entries')}
          </span>
          <HelpVideoButton />
        </div>
      </div>

      {/* Filters */}
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <div className="relative">
            <select
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
              className="appearance-none rounded-md border border-gray-300 bg-white py-2 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">{t('audit.allEntityTypes')}</option>
              {ENTITY_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`audit.entityTypes.${type}`)}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          </div>
        </div>

        <div className="relative">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="appearance-none rounded-md border border-gray-300 bg-white py-2 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">{t('audit.allActions')}</option>
            {ACTIONS.map((action) => (
              <option key={action} value={action}>
                {t(`audit.actions.${action}`)}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>

        <div className="relative">
          <select
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            className="appearance-none rounded-md border border-gray-300 bg-white py-2 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">{t('audit.allUsers')}</option>
            {usersData?.users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName || u.email}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>

        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          placeholder={t('audit.dateFrom')}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          placeholder={t('audit.dateTo')}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t('audit.searchPlaceholder')}
            className="rounded-md border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Content */}
      <div className="mt-4">
        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-600">{error.message}</p>
          </div>
        ) : (
          <>
            <AuditLogTable entries={entries} loading={loading && entries.length === 0} />

            {/* Load More */}
            {hasNextPage && (
              <div className="mt-4 flex justify-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loading}
                  className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t('audit.loadMore')}
                </button>
              </div>
            )}

            {/* Showing count */}
            {entries.length > 0 && (
              <div className="mt-4 text-center text-sm text-gray-500">
                {t('audit.showing', { count: entries.length, total: totalCount })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
