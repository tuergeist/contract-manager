import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { ShieldCheck, Loader2 } from 'lucide-react'

const TENANT_SETTINGS_QUERY = gql`
  query TenantSettings {
    me {
      id
      tenantId
    }
    tenantSettings {
      twoFactorEnforced
    }
  }
`

const SET_ENFORCEMENT = gql`
  mutation SetTenant2faEnforcement($enforced: Boolean!) {
    setTenant2faEnforcement(enforced: $enforced) {
      success
      error
    }
  }
`

export function TenantSecuritySettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(TENANT_SETTINGS_QUERY)
  const [setEnforcement, { loading }] = useMutation(SET_ENFORCEMENT)
  const [enforced, setEnforced] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (data?.tenantSettings?.twoFactorEnforced != null) {
      setEnforced(data.tenantSettings.twoFactorEnforced)
    }
  }, [data])

  const handleToggle = async () => {
    setError(null)
    const newValue = !enforced
    const result = await setEnforcement({ variables: { enforced: newValue } })
    const d = result.data?.setTenant2faEnforcement
    if (d?.success) {
      setEnforced(newValue)
      refetch()
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium flex items-center gap-2">
          <ShieldCheck className="h-5 w-5" />
          {t('settings.security.tenantTitle')}
        </h3>
        <p className="text-sm text-gray-500 mt-1">{t('settings.security.tenantDescription')}</p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="flex items-center justify-between p-4 rounded-lg border">
        <div>
          <p className="font-medium text-sm">{t('settings.security.require2fa')}</p>
          <p className="text-xs text-gray-500 mt-1">{t('settings.security.require2faDesc')}</p>
        </div>
        <button
          onClick={handleToggle}
          disabled={loading}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enforced ? 'bg-blue-600' : 'bg-gray-200'
          }`}
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mx-auto text-white" />
          ) : (
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                enforced ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          )}
        </button>
      </div>
    </div>
  )
}
