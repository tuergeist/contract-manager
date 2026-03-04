import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Switch } from '@/components/ui/switch'
import { Loader2 } from 'lucide-react'

const DASHBOARD_PREFERENCES = gql`
  query DashboardPreferences {
    dashboardPreferences {
      showContracts
      showRevenueGoals
      showNewBusiness
      showPriceIncreaseImpact
    }
  }
`

const UPDATE_DASHBOARD_PREFERENCES = gql`
  mutation UpdateDashboardPreferences($showContracts: Boolean, $showRevenueGoals: Boolean, $showNewBusiness: Boolean, $showPriceIncreaseImpact: Boolean) {
    updateDashboardPreferences(showContracts: $showContracts, showRevenueGoals: $showRevenueGoals, showNewBusiness: $showNewBusiness, showPriceIncreaseImpact: $showPriceIncreaseImpact) {
      success
      error
    }
  }
`

export function DashboardPreferences() {
  const { t } = useTranslation()
  const { data, loading } = useQuery(DASHBOARD_PREFERENCES)
  const [updatePreferences] = useMutation(UPDATE_DASHBOARD_PREFERENCES, {
    refetchQueries: [{ query: DASHBOARD_PREFERENCES }],
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

  const prefs = data?.dashboardPreferences

  const togglePreference = (key: string, currentValue: boolean) => {
    updatePreferences({
      variables: { [key]: !currentValue },
    })
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.dashboardPreferences.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">
        {t('settings.dashboardPreferences.description')}
      </p>

      <div className="mt-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.dashboardPreferences.showContracts')}</p>
            <p className="text-sm text-gray-500">{t('settings.dashboardPreferences.showContractsDescription')}</p>
          </div>
          <Switch
            checked={prefs?.showContracts ?? true}
            onCheckedChange={() => togglePreference('showContracts', prefs?.showContracts ?? true)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.dashboardPreferences.showNewBusiness')}</p>
            <p className="text-sm text-gray-500">{t('settings.dashboardPreferences.showNewBusinessDescription')}</p>
          </div>
          <Switch
            checked={prefs?.showNewBusiness ?? true}
            onCheckedChange={() => togglePreference('showNewBusiness', prefs?.showNewBusiness ?? true)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.dashboardPreferences.showPriceIncreaseImpact')}</p>
            <p className="text-sm text-gray-500">{t('settings.dashboardPreferences.showPriceIncreaseImpactDescription')}</p>
          </div>
          <Switch
            checked={prefs?.showPriceIncreaseImpact ?? true}
            onCheckedChange={() => togglePreference('showPriceIncreaseImpact', prefs?.showPriceIncreaseImpact ?? true)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">{t('settings.dashboardPreferences.showRevenueGoals')}</p>
            <p className="text-sm text-gray-500">{t('settings.dashboardPreferences.showRevenueGoalsDescription')}</p>
          </div>
          <Switch
            checked={prefs?.showRevenueGoals ?? true}
            onCheckedChange={() => togglePreference('showRevenueGoals', prefs?.showRevenueGoals ?? true)}
          />
        </div>
      </div>
    </div>
  )
}
