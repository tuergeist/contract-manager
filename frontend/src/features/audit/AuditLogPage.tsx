import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, Filter, ChevronDown } from 'lucide-react'
import { AuditLogTable, AuditLogEntry } from './AuditLogTable'

const AUDIT_LOGS_QUERY = gql`
  query AuditLogs(
    $entityType: String
    $action: String
    $first: Int
    $after: String
  ) {
    auditLogs(
      entityType: $entityType
      action: $action
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

const ENTITY_TYPES = ['contract', 'contract_item', 'customer', 'product'] as const
const ACTIONS = ['create', 'update', 'delete'] as const
const PAGE_SIZE = 25

export function AuditLogPage() {
  const { t } = useTranslation()
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<string>('')

  const { data, loading, error, fetchMore } = useQuery<AuditLogsData>(AUDIT_LOGS_QUERY, {
    variables: {
      entityType: entityTypeFilter || null,
      action: actionFilter || null,
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
        <span className="text-sm text-gray-500">
          {totalCount} {t('audit.entries')}
        </span>
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
