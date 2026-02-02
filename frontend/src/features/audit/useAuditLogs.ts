import { useQuery, gql } from '@apollo/client'
import { AuditLogEntry } from './AuditLogTable'

const AUDIT_LOGS_QUERY = gql`
  query AuditLogs(
    $entityType: String
    $entityId: Int
    $includeRelated: Boolean
    $first: Int
    $after: String
  ) {
    auditLogs(
      entityType: $entityType
      entityId: $entityId
      includeRelated: $includeRelated
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

interface UseAuditLogsOptions {
  entityType: string
  entityId: number
  includeRelated?: boolean
  pageSize?: number
}

export function useAuditLogs({
  entityType,
  entityId,
  includeRelated = true,
  pageSize = 25,
}: UseAuditLogsOptions) {
  const { data, loading, error, fetchMore } = useQuery<AuditLogsData>(AUDIT_LOGS_QUERY, {
    variables: {
      entityType,
      entityId,
      includeRelated,
      first: pageSize,
      after: null,
    },
    fetchPolicy: 'cache-and-network',
  })

  const entries = data?.auditLogs.edges.map((edge) => edge.node) || []
  const totalCount = data?.auditLogs.totalCount || 0
  const hasNextPage = data?.auditLogs.pageInfo.hasNextPage || false
  const endCursor = data?.auditLogs.pageInfo.endCursor

  const loadMore = () => {
    if (hasNextPage && endCursor) {
      return fetchMore({
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

  return {
    entries,
    totalCount,
    hasNextPage,
    loading,
    error,
    loadMore,
  }
}
