import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, Link2, Clock, Search } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const TIME_TRACKING_SUMMARY_QUERY = gql`
  query TimeTrackingSummary($contractId: ID!) {
    timeTrackingSummary(contractId: $contractId) {
      totalHours
      totalRevenue
      byService {
        serviceName
        hours
        revenue
      }
      byMonth {
        month
        hours
        revenue
      }
      mappings {
        id
        externalProjectId
        externalProjectName
        externalCustomerName
        contractItemId
      }
    }
    timeTrackingSettings {
      provider
      isConfigured
      showRevenue
    }
  }
`

const TIME_TRACKING_PROJECTS_QUERY = gql`
  query TimeTrackingProjects($search: String!) {
    timeTrackingProjects(search: $search) {
      id
      name
      customerName
      active
    }
  }
`

const MAP_PROJECT_MUTATION = gql`
  mutation MapTimeTrackingProject(
    $contractId: ID!
    $externalProjectId: String!
    $externalProjectName: String!
    $externalCustomerName: String!
  ) {
    mapTimeTrackingProject(
      contractId: $contractId
      externalProjectId: $externalProjectId
      externalProjectName: $externalProjectName
      externalCustomerName: $externalCustomerName
    ) {
      success
      error
    }
  }
`

const UNMAP_PROJECT_MUTATION = gql`
  mutation UnmapTimeTrackingProject($mappingId: ID!) {
    unmapTimeTrackingProject(mappingId: $mappingId) {
      success
      error
    }
  }
`

interface TimeTrackingTabProps {
  contractId: string
  customerName: string
}

interface Mapping {
  id: number
  externalProjectId: string
  externalProjectName: string
  externalCustomerName: string
  contractItemId: number | null
}

interface ExternalProject {
  id: string
  name: string
  customerName: string
  active: boolean
}

export function TimeTrackingTab({ contractId, customerName }: TimeTrackingTabProps) {
  const { t } = useTranslation()
  const [showLinkDialog, setShowLinkDialog] = useState(false)

  const { data, loading, refetch } = useQuery(TIME_TRACKING_SUMMARY_QUERY, {
    variables: { contractId },
  })

  const [unmapProject] = useMutation(UNMAP_PROJECT_MUTATION)

  const summary = data?.timeTrackingSummary
  const isConfigured = data?.timeTrackingSettings?.isConfigured
  const showRevenue = data?.timeTrackingSettings?.showRevenue ?? true

  const handleUnlink = async (mappingId: number) => {
    if (!confirm(t('timeTracking.unlinkConfirm'))) return
    await unmapProject({ variables: { mappingId: String(mappingId) } })
    refetch()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!isConfigured) {
    return (
      <div className="rounded-lg border bg-white p-8 text-center">
        <Clock className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-gray-600">{t('timeTracking.noProvider')}</p>
      </div>
    )
  }

  const mappings: Mapping[] = summary?.mappings || []

  return (
    <div className="space-y-6">
      {/* Mapped Projects */}
      <div className="rounded-lg border bg-white p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-900">
            {t('timeTracking.mappedProjects')}
          </h3>
          <button
            onClick={() => setShowLinkDialog(true)}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('timeTracking.linkProject')}
          </button>
        </div>

        {mappings.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">{t('timeTracking.noMappings')}</p>
        ) : (
          <div className="mt-4">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-2 font-medium">{t('timeTracking.projectName')}</th>
                  <th className="pb-2 font-medium">{t('timeTracking.customerName')}</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {mappings.map((m) => (
                  <tr key={m.id} className="border-b last:border-0">
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <Link2 className="h-4 w-4 text-gray-400" />
                        <a
                          href={`https://my.clockodo.com/de/projects/${m.externalProjectId}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {m.externalProjectName}
                        </a>
                      </div>
                    </td>
                    <td className="py-2 text-gray-600">{m.externalCustomerName}</td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => handleUnlink(m.id)}
                        className="text-sm text-red-600 hover:text-red-800"
                      >
                        {t('timeTracking.unlinkProject')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Time Summary */}
      {mappings.length > 0 && summary && (
        <>
          {/* KPI Cards */}
          <div className={`grid gap-4 ${showRevenue ? 'grid-cols-2' : 'grid-cols-1'}`}>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-sm text-gray-500">{t('timeTracking.totalHours')}</p>
              <p className="mt-1 text-2xl font-semibold">{summary.totalHours.toFixed(1)}h</p>
            </div>
            {showRevenue && (
              <div className="rounded-lg border bg-white p-4">
                <p className="text-sm text-gray-500">{t('timeTracking.totalRevenue')}</p>
                <p className="mt-1 text-2xl font-semibold">
                  {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(summary.totalRevenue)}
                </p>
              </div>
            )}
          </div>

          {/* By Service */}
          {summary.byService.length > 0 && (
            <div className="rounded-lg border bg-white p-6">
              <h3 className="text-sm font-medium text-gray-900">{t('timeTracking.byService')}</h3>
              <table className="mt-3 min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-2 font-medium">{t('timeTracking.serviceName')}</th>
                    <th className="pb-2 text-right font-medium">{t('timeTracking.hours')}</th>
                    {showRevenue && <th className="pb-2 text-right font-medium">{t('timeTracking.revenue')}</th>}
                  </tr>
                </thead>
                <tbody>
                  {summary.byService.map((s: { serviceName: string; hours: number; revenue: number }) => (
                    <tr key={s.serviceName} className="border-b last:border-0">
                      <td className="py-2">{s.serviceName}</td>
                      <td className="py-2 text-right">{s.hours.toFixed(1)}h</td>
                      {showRevenue && (
                        <td className="py-2 text-right">
                          {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(s.revenue)}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* By Month */}
          {summary.byMonth.length > 0 && (
            <div className="rounded-lg border bg-white p-6">
              <h3 className="text-sm font-medium text-gray-900">{t('timeTracking.byMonth')}</h3>
              <table className="mt-3 min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-2 font-medium">{t('timeTracking.month')}</th>
                    <th className="pb-2 text-right font-medium">{t('timeTracking.hours')}</th>
                    {showRevenue && <th className="pb-2 text-right font-medium">{t('timeTracking.revenue')}</th>}
                  </tr>
                </thead>
                <tbody>
                  {summary.byMonth.map((m: { month: string; hours: number; revenue: number }) => (
                    <tr key={m.month} className="border-b last:border-0">
                      <td className="py-2">{m.month}</td>
                      <td className="py-2 text-right">{m.hours.toFixed(1)}h</td>
                      {showRevenue && (
                        <td className="py-2 text-right">
                          {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(m.revenue)}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {summary.totalHours === 0 && (
            <div className="rounded-lg border bg-white p-8 text-center">
              <Clock className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-gray-600">{t('timeTracking.noData')}</p>
            </div>
          )}
        </>
      )}

      {/* Link Project Dialog */}
      {showLinkDialog && (
        <LinkProjectDialog
          contractId={contractId}
          customerName={customerName}
          linkedProjectIds={mappings.map((m) => m.externalProjectId)}
          onClose={() => setShowLinkDialog(false)}
          onLinked={() => {
            setShowLinkDialog(false)
            refetch()
          }}
        />
      )}
    </div>
  )
}

interface LinkProjectDialogProps {
  contractId: string
  customerName: string
  linkedProjectIds: string[]
  onClose: () => void
  onLinked: () => void
}

function LinkProjectDialog({
  contractId,
  customerName,
  linkedProjectIds,
  onClose,
  onLinked,
}: LinkProjectDialogProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState(customerName)

  const { data, loading } = useQuery(TIME_TRACKING_PROJECTS_QUERY, {
    variables: { search },
    skip: !search,
  })

  const [mapProject, { loading: mapping }] = useMutation(MAP_PROJECT_MUTATION)

  const projects: ExternalProject[] = data?.timeTrackingProjects || []

  const handleLink = async (project: ExternalProject) => {
    const result = await mapProject({
      variables: {
        contractId,
        externalProjectId: project.id,
        externalProjectName: project.name,
        externalCustomerName: project.customerName,
      },
    })
    if (result.data?.mapTimeTrackingProject?.success) {
      onLinked()
    }
  }

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('timeTracking.linkProject')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('timeTracking.searchProjects')}
              className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              autoFocus
            />
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : projects.length === 0 && search ? (
            <p className="py-8 text-center text-sm text-gray-500">
              {t('search.noResults')}
            </p>
          ) : (
            <div className="max-h-96 overflow-y-auto">
              <table className="min-w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="border-b text-left text-gray-500">
                    <th className="pb-2 font-medium">{t('timeTracking.projectName')}</th>
                    <th className="pb-2 font-medium">{t('timeTracking.customerName')}</th>
                    <th className="pb-2 font-medium">{t('timeTracking.status')}</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => {
                    const isLinked = linkedProjectIds.includes(project.id)
                    return (
                      <tr key={project.id} className="border-b last:border-0">
                        <td className="py-2">{project.name}</td>
                        <td className="py-2 text-gray-600">{project.customerName}</td>
                        <td className="py-2">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                              project.active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {project.active ? t('timeTracking.active') : t('timeTracking.inactive')}
                          </span>
                        </td>
                        <td className="py-2 text-right">
                          {isLinked ? (
                            <span className="text-xs text-gray-400">{t('timeTracking.alreadyLinked')}</span>
                          ) : (
                            <button
                              onClick={() => handleLink(project)}
                              disabled={mapping}
                              className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                              {mapping && <Loader2 className="h-3 w-3 animate-spin" />}
                              {t('timeTracking.link')}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
