import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Switch } from '@/components/ui/switch'
import { Loader2 } from 'lucide-react'

const NOTIFICATION_PREFERENCES = gql`
  query NotificationPreferences {
    notificationPreferences {
      todoAssigned
      hubspotNewContract
    }
  }
`

const UPDATE_NOTIFICATION_PREFERENCES = gql`
  mutation UpdateNotificationPreferences($todoAssigned: Boolean, $hubspotNewContract: Boolean) {
    updateNotificationPreferences(todoAssigned: $todoAssigned, hubspotNewContract: $hubspotNewContract) {
      success
      error
    }
  }
`

export function NotificationPreferences() {
  const { t } = useTranslation()
  const { data, loading } = useQuery(NOTIFICATION_PREFERENCES)
  const [updatePreferences] = useMutation(UPDATE_NOTIFICATION_PREFERENCES, {
    refetchQueries: [{ query: NOTIFICATION_PREFERENCES }],
  })

  if (loading) {
    return (
      <div className="rounded-lg border bg-white p-6">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-gray-500">{t('common.loading')}</span>
        </div>
      </div>
    )
  }

  const prefs = data?.notificationPreferences

  const togglePreference = (key: string, currentValue: boolean) => {
    updatePreferences({
      variables: { [key]: !currentValue },
    })
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.notificationPreferences.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">
        {t('settings.notificationPreferences.description')}
      </p>

      <div className="mt-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.notificationPreferences.todoAssigned')}</p>
            <p className="text-sm text-gray-500">{t('settings.notificationPreferences.todoAssignedDescription')}</p>
          </div>
          <Switch
            checked={prefs?.todoAssigned ?? true}
            onCheckedChange={() => togglePreference('todoAssigned', prefs?.todoAssigned ?? true)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.notificationPreferences.hubspotNewContract')}</p>
            <p className="text-sm text-gray-500">{t('settings.notificationPreferences.hubspotNewContractDescription')}</p>
          </div>
          <Switch
            checked={prefs?.hubspotNewContract ?? true}
            onCheckedChange={() => togglePreference('hubspotNewContract', prefs?.hubspotNewContract ?? true)}
          />
        </div>
      </div>
    </div>
  )
}
