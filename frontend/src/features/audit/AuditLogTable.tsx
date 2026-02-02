import { useState, Fragment } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight, Plus, Pencil, Trash2 } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'

export interface AuditLogChange {
  field: string
  oldValue: unknown
  newValue: unknown
}

export interface AuditLogEntry {
  id: number
  action: string
  entityType: string
  entityId: number
  entityRepr: string
  userId: number | null
  userName: string | null
  changes: AuditLogChange[]
  timestamp: string
  parentEntityType: string | null
  parentEntityId: number | null
}

interface AuditLogTableProps {
  entries: AuditLogEntry[]
  showEntity?: boolean
  loading?: boolean
}

function getActionBadgeClass(action: string): string {
  switch (action) {
    case 'create':
      return 'bg-green-100 text-green-800'
    case 'update':
      return 'bg-blue-100 text-blue-800'
    case 'delete':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function getActionIcon(action: string) {
  switch (action) {
    case 'create':
      return <Plus className="h-3 w-3" />
    case 'update':
      return <Pencil className="h-3 w-3" />
    case 'delete':
      return <Trash2 className="h-3 w-3" />
    default:
      return null
  }
}

function getEntityLink(entityType: string, entityId: number): string | null {
  switch (entityType) {
    case 'contract':
      return `/contracts/${entityId}`
    case 'customer':
      return `/customers/${entityId}`
    case 'product':
      return `/products/${entityId}`
    case 'contract_item':
      return null // Contract items don't have their own page
    default:
      return null
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatFieldName(field: string, t: any): string {
  // Try to get translation, fall back to formatted field name
  const key = `audit.fields.${field}`
  const translated = t(key)
  if (translated !== key) {
    return translated
  }
  // Fallback: convert snake_case to Title Case
  return field
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function AuditLogChanges({ changes, t }: { changes: AuditLogChange[]; t: any }) {
  if (changes.length === 0) {
    return <span className="text-gray-400">-</span>
  }

  return (
    <div className="space-y-1">
      {changes.map((change, index) => (
        <div key={index} className="text-sm">
          <span className="font-medium text-gray-700">{formatFieldName(change.field, t)}:</span>{' '}
          <span className="text-gray-500">{formatValue(change.oldValue)}</span>
          <span className="mx-1 text-gray-400">&rarr;</span>
          <span className="text-gray-900">{formatValue(change.newValue)}</span>
        </div>
      ))}
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getChangesSummary(changes: AuditLogChange[], t: any): string {
  if (changes.length === 0) {
    return '-'
  }
  if (changes.length === 1) {
    return formatFieldName(changes[0].field, t)
  }
  return t('audit.changesCount', { count: changes.length })
}

export function AuditLogTable({ entries, showEntity = true, loading = false }: AuditLogTableProps) {
  const { t } = useTranslation()
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  const toggleRow = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600" />
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <div className="py-8 text-center text-gray-500">
        {t('audit.noEntries')}
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="w-10 px-3 py-3"></th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('audit.timestamp')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('audit.user')}
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('audit.action')}
            </th>
            {showEntity && (
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('audit.entity')}
              </th>
            )}
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('audit.changes')}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white" data-testid="audit-log-table-body">
          {entries.map((entry) => {
            const isExpanded = expandedRows.has(entry.id)
            const entityLink = getEntityLink(entry.entityType, entry.entityId)
            const hasChanges = entry.changes.length > 0

            return (
              <Fragment key={entry.id}>
                <tr
                  className={`hover:bg-gray-50 ${hasChanges ? 'cursor-pointer' : ''}`}
                  onClick={() => hasChanges && toggleRow(entry.id)}
                  data-testid={`audit-log-row-${entry.id}`}
                >
                  <td className="px-3 py-4">
                    {hasChanges && (
                      <button
                        type="button"
                        className="text-gray-400 hover:text-gray-600"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleRow(entry.id)
                        }}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-500">
                    {formatDateTime(entry.timestamp)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-4 text-sm text-gray-900">
                    {entry.userName || t('audit.systemUser')}
                  </td>
                  <td className="whitespace-nowrap px-4 py-4">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${getActionBadgeClass(entry.action)}`}
                    >
                      {getActionIcon(entry.action)}
                      {t(`audit.actions.${entry.action}`)}
                    </span>
                  </td>
                  {showEntity && (
                    <td className="whitespace-nowrap px-4 py-4 text-sm">
                      <div className="flex flex-col">
                        <span className="text-xs text-gray-500">
                          {t(`audit.entityTypes.${entry.entityType}`)}
                        </span>
                        {entityLink ? (
                          <Link
                            to={entityLink}
                            className="text-blue-600 hover:text-blue-800"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {entry.entityRepr}
                          </Link>
                        ) : (
                          <span className="text-gray-900">{entry.entityRepr}</span>
                        )}
                        {entry.parentEntityType && entry.parentEntityId && (
                          <span className="text-xs text-gray-400">
                            {t(`audit.entityTypes.${entry.parentEntityType}`)}:{' '}
                            <Link
                              to={getEntityLink(entry.parentEntityType, entry.parentEntityId) || '#'}
                              className="text-blue-600 hover:text-blue-800"
                              onClick={(e) => e.stopPropagation()}
                            >
                              #{entry.parentEntityId}
                            </Link>
                          </span>
                        )}
                      </div>
                    </td>
                  )}
                  <td className="px-4 py-4 text-sm text-gray-500">
                    {getChangesSummary(entry.changes, t)}
                  </td>
                </tr>
                {isExpanded && hasChanges && (
                  <tr className="bg-gray-50">
                    <td></td>
                    <td colSpan={showEntity ? 5 : 4} className="px-4 py-4">
                      <AuditLogChanges changes={entry.changes} t={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
