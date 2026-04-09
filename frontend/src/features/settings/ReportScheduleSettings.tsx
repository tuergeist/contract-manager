import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Send } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

const REPORT_SCHEDULES_QUERY = gql`
  query ReportSchedules {
    reportSchedules {
      id
      reportType
      enabled
      recipients
      sendDayOfMonth
      autoFinalize
    }
  }
`

const SEND_REPORT_NOW = gql`
  mutation SendReportNow($reportType: String!, $year: Int!, $month: Int!) {
    sendReportNow(reportType: $reportType, year: $year, month: $month) {
      success
      error
    }
  }
`

const SAVE_REPORT_SCHEDULE = gql`
  mutation SaveReportSchedule($input: SaveReportScheduleInput!) {
    saveReportSchedule(input: $input) {
      id
      reportType
      enabled
      recipients
      sendDayOfMonth
      autoFinalize
    }
  }
`

interface ScheduleState {
  enabled: boolean
  recipients: string
  sendDayOfMonth: number
  autoFinalize: boolean
}

const defaultSchedule: ScheduleState = {
  enabled: false,
  recipients: '',
  sendDayOfMonth: 5,
  autoFinalize: false,
}

function ScheduleCard({
  title,
  schedule,
  reportType,
  showAutoFinalize,
  onChange,
  onSave,
  onSendNow,
  saving,
  sending,
  message,
  t,
}: {
  title: string
  schedule: ScheduleState
  reportType: string
  showAutoFinalize: boolean
  onChange: (field: keyof ScheduleState, value: string | number | boolean) => void
  onSave: () => void
  onSendNow: () => void
  saving: boolean
  sending: boolean
  message: { type: 'success' | 'error'; text: string } | null
  t: (key: string) => string
}) {
  const inputClass =
    'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium">{title}</h3>
        <div className="flex items-center gap-2">
          <Label htmlFor={`${reportType}-enabled`} className="text-sm">
            {t('settings.reports.enabled')}
          </Label>
          <Switch
            id={`${reportType}-enabled`}
            checked={schedule.enabled}
            onCheckedChange={(checked) => onChange('enabled', checked)}
          />
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.reports.recipients')}
          </label>
          <input
            type="text"
            value={schedule.recipients}
            onChange={(e) => onChange('recipients', e.target.value)}
            placeholder="hr@example.com, finance@example.com"
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">{t('settings.reports.recipientsHint')}</p>
        </div>

        <div className="max-w-[200px]">
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.reports.sendDay')}
          </label>
          <input
            type="number"
            min={1}
            max={28}
            value={schedule.sendDayOfMonth}
            onChange={(e) => onChange('sendDayOfMonth', parseInt(e.target.value) || 1)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">{t('settings.reports.sendDayHint')}</p>
        </div>

        {showAutoFinalize && (
          <div className="flex items-center gap-3">
            <Switch
              id={`${reportType}-autoFinalize`}
              checked={schedule.autoFinalize}
              onCheckedChange={(checked) => onChange('autoFinalize', checked)}
            />
            <div>
              <Label htmlFor={`${reportType}-autoFinalize`} className="text-sm font-medium">
                {t('settings.reports.autoFinalize')}
              </Label>
              <p className="text-xs text-gray-500">{t('settings.reports.autoFinalizeHint')}</p>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            onClick={onSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('common.save')}
          </button>
          <button
            onClick={onSendNow}
            disabled={sending || !schedule.recipients.trim()}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            title={t('settings.reports.sendNowHint')}
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {t('settings.reports.sendNow')}
          </button>
          {message && (
            <span className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
              {message.text}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export function ReportScheduleSettings() {
  const { t } = useTranslation()

  const [absence, setAbsence] = useState<ScheduleState>(defaultSchedule)
  const [department, setDepartment] = useState<ScheduleState>(defaultSchedule)
  const [absenceMessage, setAbsenceMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [departmentMessage, setDepartmentMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data } = useQuery(REPORT_SCHEDULES_QUERY)
  const [saveSchedule, { loading: saving }] = useMutation(SAVE_REPORT_SCHEDULE)
  const [sendNow] = useMutation(SEND_REPORT_NOW)
  const [savingType, setSavingType] = useState<string | null>(null)
  const [sendingType, setSendingType] = useState<string | null>(null)

  useEffect(() => {
    if (data?.reportSchedules) {
      for (const schedule of data.reportSchedules) {
        const state: ScheduleState = {
          enabled: schedule.enabled,
          recipients: (schedule.recipients || []).join(', '),
          sendDayOfMonth: schedule.sendDayOfMonth,
          autoFinalize: schedule.autoFinalize,
        }
        if (schedule.reportType === 'absence') {
          setAbsence(state)
        } else if (schedule.reportType === 'department_time') {
          setDepartment(state)
        }
      }
    }
  }, [data])

  const handleSave = async (reportType: string) => {
    const schedule = reportType === 'absence' ? absence : department
    const setMessage = reportType === 'absence' ? setAbsenceMessage : setDepartmentMessage
    setMessage(null)
    setSavingType(reportType)

    try {
      const recipients = schedule.recipients
        .split(',')
        .map((e) => e.trim())
        .filter(Boolean)

      await saveSchedule({
        variables: {
          input: {
            reportType,
            enabled: schedule.enabled,
            recipients,
            sendDayOfMonth: Math.min(28, Math.max(1, schedule.sendDayOfMonth)),
            autoFinalize: schedule.autoFinalize,
          },
        },
        refetchQueries: ['ReportSchedules'],
      })
      setMessage({ type: 'success', text: t('settings.reports.saved') })
      setTimeout(() => setMessage(null), 3000)
    } catch {
      setMessage({ type: 'error', text: t('common.error') })
    } finally {
      setSavingType(null)
    }
  }

  const handleAbsenceChange = (field: keyof ScheduleState, value: string | number | boolean) => {
    setAbsence((prev) => ({ ...prev, [field]: value }))
  }

  const handleDepartmentChange = (field: keyof ScheduleState, value: string | number | boolean) => {
    setDepartment((prev) => ({ ...prev, [field]: value }))
  }

  const handleSendNow = async (reportType: string) => {
    const setMessage = reportType === 'absence' ? setAbsenceMessage : setDepartmentMessage
    setMessage(null)
    setSendingType(reportType)
    try {
      // Send for previous month
      const now = new Date()
      const prevMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const result = await sendNow({
        variables: {
          reportType,
          year: prevMonth.getFullYear(),
          month: prevMonth.getMonth() + 1,
        },
      })
      if (result.data?.sendReportNow?.success) {
        setMessage({ type: 'success', text: t('settings.reports.sent') })
      } else {
        setMessage({ type: 'error', text: result.data?.sendReportNow?.error || t('common.error') })
      }
      setTimeout(() => setMessage(null), 5000)
    } catch {
      setMessage({ type: 'error', text: t('common.error') })
    } finally {
      setSendingType(null)
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <ScheduleCard
        title={t('settings.reports.absence')}
        schedule={absence}
        reportType="absence"
        showAutoFinalize={true}
        onChange={handleAbsenceChange}
        onSave={() => handleSave('absence')}
        onSendNow={() => handleSendNow('absence')}
        saving={saving && savingType === 'absence'}
        sending={sendingType === 'absence'}
        message={absenceMessage}
        t={t}
      />
      <ScheduleCard
        title={t('settings.reports.departmentTime')}
        schedule={department}
        reportType="department_time"
        showAutoFinalize={false}
        onChange={handleDepartmentChange}
        onSave={() => handleSave('department_time')}
        onSendNow={() => handleSendNow('department_time')}
        saving={saving && savingType === 'department_time'}
        sending={sendingType === 'department_time'}
        message={departmentMessage}
        t={t}
      />
    </div>
  )
}
