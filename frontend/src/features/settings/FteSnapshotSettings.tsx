import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { ChevronDown, ChevronRight, Camera, Loader2 } from 'lucide-react'

const FTE_SNAPSHOTS_QUERY = gql`
  query FteSnapshots($year: Int) {
    fteDistributionSnapshots(year: $year) {
      id yearMonth capturedAt capturedByName
      entries { id departmentName costCenterCode ftePercentage monthlyIncomeTotal hoursTotal }
    }
  }
`

const CAPTURE_SNAPSHOT = gql`
  mutation CaptureSnapshot($yearMonth: String!) {
    captureFteDistributionSnapshot(yearMonth: $yearMonth) {
      success error
      snapshot {
        id yearMonth capturedAt capturedByName
        entries { id departmentName costCenterCode ftePercentage monthlyIncomeTotal hoursTotal }
      }
    }
  }
`

const TENANT_SETTINGS_QUERY = gql`
  query TenantSettingsForSnapshot {
    tenantSettings { fteSnapshotCaptureDay fteSnapshotNotificationEmail }
  }
`

const UPDATE_SNAPSHOT_SETTINGS = gql`
  mutation UpdateSnapshotSettings($captureDay: Int, $notificationEmail: String) {
    updateFteSnapshotSettings(captureDay: $captureDay, notificationEmail: $notificationEmail) { success error }
  }
`

export function FteSnapshotSettings() {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [captureMonth, setCaptureMonth] = useState('')
  const [captureError, setCaptureError] = useState('')

  const { data, refetch } = useQuery(FTE_SNAPSHOTS_QUERY, { variables: { year: selectedYear } })
  const { data: settingsData } = useQuery(TENANT_SETTINGS_QUERY)
  const [captureSnapshot, { loading: capturing }] = useMutation(CAPTURE_SNAPSHOT)
  const [updateSettings] = useMutation(UPDATE_SNAPSHOT_SETTINGS)

  const snapshots = data?.fteDistributionSnapshots || []
  const settings = settingsData?.tenantSettings

  const handleCapture = async () => {
    setCaptureError('')
    if (!captureMonth) return
    const { data: res } = await captureSnapshot({ variables: { yearMonth: captureMonth } })
    if (res?.captureFteDistributionSnapshot?.success) {
      setCaptureMonth('')
      refetch()
    } else {
      setCaptureError(res?.captureFteDistributionSnapshot?.error || 'Failed')
    }
  }

  const handleSaveSettings = async (field: string, value: any) => {
    const vars: any = {}
    if (field === 'captureDay') vars.captureDay = value
    if (field === 'notificationEmail') vars.notificationEmail = value
    await updateSettings({ variables: vars })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium">{t('fteSnapshots.title')}</h3>
        <p className="text-sm text-muted-foreground">{t('fteSnapshots.description')}</p>
      </div>

      {/* Settings */}
      <div className="grid grid-cols-2 gap-4 rounded-lg border p-4">
        <div>
          <label className="text-sm font-medium">{t('fteSnapshots.captureDay')}</label>
          <input
            type="number"
            min={1}
            max={28}
            className="w-24 mt-1 block rounded-md border px-3 py-2 text-sm"
            defaultValue={settings?.fteSnapshotCaptureDay || 7}
            onBlur={(e) => handleSaveSettings('captureDay', parseInt(e.target.value) || 7)}
          />
          <p className="text-xs text-muted-foreground mt-1">{t('fteSnapshots.captureDayHint')}</p>
        </div>
        <div>
          <label className="text-sm font-medium">{t('fteSnapshots.notificationEmail')}</label>
          <input
            type="email"
            className="w-full mt-1 block rounded-md border px-3 py-2 text-sm"
            defaultValue={settings?.fteSnapshotNotificationEmail || ''}
            placeholder={t('fteSnapshots.notificationEmailPlaceholder')}
            onBlur={(e) => handleSaveSettings('notificationEmail', e.target.value || null)}
          />
        </div>
      </div>

      {/* Manual capture */}
      <div className="flex items-end gap-2">
        <div>
          <label className="text-sm font-medium">{t('fteSnapshots.manualCapture')}</label>
          <input
            type="month"
            className="mt-1 block rounded-md border px-3 py-2 text-sm"
            value={captureMonth}
            onChange={(e) => setCaptureMonth(e.target.value)}
          />
        </div>
        <button
          onClick={handleCapture}
          disabled={!captureMonth || capturing}
          className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {capturing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
          {t('fteSnapshots.capture')}
        </button>
        {captureError && <span className="text-sm text-destructive">{captureError}</span>}
      </div>

      {/* Year selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">{t('fteSnapshots.year')}:</label>
        <select
          className="rounded-md border px-2 py-1 text-sm"
          value={selectedYear}
          onChange={(e) => setSelectedYear(parseInt(e.target.value))}
        >
          {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Snapshot list */}
      <div className="space-y-2">
        {snapshots.length === 0 && (
          <p className="text-sm text-muted-foreground">{t('fteSnapshots.noSnapshots')}</p>
        )}
        {snapshots.map((snap: any) => (
          <div key={snap.id} className="rounded-lg border">
            <button
              onClick={() => setExpandedId(expandedId === snap.id ? null : snap.id)}
              className="w-full flex items-center justify-between p-3 hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                {expandedId === snap.id ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                <span className="font-medium text-sm">{snap.yearMonth}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(snap.capturedAt).toLocaleDateString()}
                  {snap.capturedByName && ` · ${snap.capturedByName}`}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {snap.entries.length} {t('fteSnapshots.departments')}
              </span>
            </button>
            {expandedId === snap.id && (
              <div className="border-t px-3 pb-3">
                <table className="w-full text-sm mt-2">
                  <thead>
                    <tr className="text-left text-xs text-muted-foreground">
                      <th className="pb-1">{t('fteSnapshots.department')}</th>
                      <th className="pb-1">{t('fteSnapshots.costCenter')}</th>
                      <th className="pb-1 text-right">{t('fteSnapshots.ftePercent')}</th>
                      <th className="pb-1 text-right">{t('fteSnapshots.costShare')}</th>
                      <th className="pb-1 text-right">{t('fteSnapshots.hours')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const totalFte = snap.entries.reduce((sum: number, e: any) => sum + Number(e.ftePercentage), 0)
                      return snap.entries.map((e: any) => (
                        <tr key={e.id} className="border-t">
                          <td className="py-1">{e.departmentName}</td>
                          <td className="py-1">{e.costCenterCode}</td>
                          <td className="py-1 text-right">{Number(e.ftePercentage).toFixed(1)}%</td>
                          <td className="py-1 text-right">{totalFte > 0 ? (Number(e.ftePercentage) / totalFte * 100).toFixed(1) : '0.0'}%</td>
                          <td className="py-1 text-right">{Number(e.hoursTotal).toFixed(1)}</td>
                        </tr>
                      ))
                    })()}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
