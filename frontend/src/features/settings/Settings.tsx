import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react'

const HUBSPOT_SETTINGS_QUERY = gql`
  query HubSpotSettings {
    hubspotSettings {
      isConfigured
      apiKeySet
      lastSync
      lastProductSync
      lastDealSync
    }
  }
`

const SAVE_HUBSPOT_SETTINGS = gql`
  mutation SaveHubSpotSettings($apiKey: String!) {
    saveHubspotSettings(apiKey: $apiKey) {
      success
      error
    }
  }
`

const SYNC_HUBSPOT_CUSTOMERS = gql`
  mutation SyncHubSpotCustomers {
    syncHubspotCustomers {
      success
      error
      created
      updated
    }
  }
`

const SYNC_HUBSPOT_PRODUCTS = gql`
  mutation SyncHubSpotProducts {
    syncHubspotProducts {
      success
      error
      created
      updated
    }
  }
`

const SYNC_HUBSPOT_DEALS = gql`
  mutation SyncHubSpotDeals {
    syncHubspotDeals {
      success
      error
      created
      skipped
    }
  }
`

export function Settings() {
  const { t, i18n } = useTranslation()
  const [apiKey, setApiKey] = useState('')
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [customerSyncMessage, setCustomerSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [productSyncMessage, setProductSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [dealSyncMessage, setDealSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data: settingsData, refetch: refetchSettings } = useQuery(HUBSPOT_SETTINGS_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_HUBSPOT_SETTINGS)
  const [syncCustomers, { loading: syncingCustomers }] = useMutation(SYNC_HUBSPOT_CUSTOMERS)
  const [syncProducts, { loading: syncingProducts }] = useMutation(SYNC_HUBSPOT_PRODUCTS)
  const [syncDeals, { loading: syncingDeals }] = useMutation(SYNC_HUBSPOT_DEALS)

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang)
  }

  const handleSaveApiKey = async () => {
    setSaveMessage(null)
    try {
      const result = await saveSettings({ variables: { apiKey } })
      if (result.data?.saveHubspotSettings?.success) {
        setSaveMessage({ type: 'success', text: t('settings.hubspot.connectionSuccess') })
        setApiKey('')
        refetchSettings()
      } else {
        setSaveMessage({
          type: 'error',
          text: result.data?.saveHubspotSettings?.error || t('settings.hubspot.connectionFailed')
        })
      }
    } catch {
      setSaveMessage({ type: 'error', text: t('settings.hubspot.connectionFailed') })
    }
  }

  const handleSyncCustomers = async () => {
    setCustomerSyncMessage(null)
    try {
      const result = await syncCustomers()
      if (result.data?.syncHubspotCustomers?.success) {
        const { created, updated } = result.data.syncHubspotCustomers
        setCustomerSyncMessage({
          type: 'success',
          text: t('settings.hubspot.syncSuccess', { created, updated })
        })
        refetchSettings()
      } else {
        setCustomerSyncMessage({
          type: 'error',
          text: result.data?.syncHubspotCustomers?.error || t('settings.hubspot.syncFailed')
        })
      }
    } catch {
      setCustomerSyncMessage({ type: 'error', text: t('settings.hubspot.syncFailed') })
    }
  }

  const handleSyncProducts = async () => {
    setProductSyncMessage(null)
    try {
      const result = await syncProducts()
      if (result.data?.syncHubspotProducts?.success) {
        const { created, updated } = result.data.syncHubspotProducts
        setProductSyncMessage({
          type: 'success',
          text: t('settings.hubspot.syncSuccess', { created, updated })
        })
        refetchSettings()
      } else {
        setProductSyncMessage({
          type: 'error',
          text: result.data?.syncHubspotProducts?.error || t('settings.hubspot.syncFailed')
        })
      }
    } catch {
      setProductSyncMessage({ type: 'error', text: t('settings.hubspot.syncFailed') })
    }
  }

  const handleSyncDeals = async () => {
    setDealSyncMessage(null)
    try {
      const result = await syncDeals()
      if (result.data?.syncHubspotDeals?.success) {
        const { created, skipped } = result.data.syncHubspotDeals
        setDealSyncMessage({
          type: 'success',
          text: t('settings.hubspot.dealSyncSuccess', { created, skipped })
        })
        refetchSettings()
      } else {
        setDealSyncMessage({
          type: 'error',
          text: result.data?.syncHubspotDeals?.error || t('settings.hubspot.syncFailed')
        })
      }
    } catch {
      setDealSyncMessage({ type: 'error', text: t('settings.hubspot.syncFailed') })
    }
  }

  const hubspotSettings = settingsData?.hubspotSettings
  const lastCustomerSync = hubspotSettings?.lastSync
    ? new Date(hubspotSettings.lastSync).toLocaleString(i18n.language)
    : null
  const lastProductSync = hubspotSettings?.lastProductSync
    ? new Date(hubspotSettings.lastProductSync).toLocaleString(i18n.language)
    : null
  const lastDealSync = hubspotSettings?.lastDealSync
    ? new Date(hubspotSettings.lastDealSync).toLocaleString(i18n.language)
    : null

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('nav.settings')}</h1>

      <div className="mt-6 space-y-6">
        {/* HubSpot Integration */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.hubspot.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.hubspot.description')}</p>

          <div className="mt-4 space-y-4">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">{t('settings.hubspot.status')}:</span>
              {hubspotSettings?.isConfigured ? (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  {t('settings.hubspot.connected')}
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm text-gray-500">
                  <XCircle className="h-4 w-4" />
                  {t('settings.hubspot.notConnected')}
                </span>
              )}
            </div>


            {/* API Key Input */}
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700">
                {t('settings.hubspot.apiKey')}
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  id="apiKey"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={hubspotSettings?.apiKeySet ? '••••••••••••••••' : t('settings.hubspot.apiKeyPlaceholder')}
                  className="block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  onClick={handleSaveApiKey}
                  disabled={saving || !apiKey}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t('common.save')}
                </button>
              </div>
              {saveMessage && (
                <p className={`mt-2 text-sm ${saveMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                  {saveMessage.text}
                </p>
              )}
            </div>

            {/* Sync Sections */}
            {hubspotSettings?.isConfigured && (
              <div className="space-y-4 border-t pt-4">
                {/* Customers Sync */}
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.customers')}</h3>
                      {lastCustomerSync && (
                        <p className="text-xs text-gray-500">{t('settings.hubspot.lastSync')}: {lastCustomerSync}</p>
                      )}
                    </div>
                    <button
                      onClick={handleSyncCustomers}
                      disabled={syncingCustomers}
                      className="inline-flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {syncingCustomers ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      {t('settings.hubspot.syncNow')}
                    </button>
                  </div>
                  {customerSyncMessage && (
                    <p className={`mt-2 text-sm ${customerSyncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                      {customerSyncMessage.text}
                    </p>
                  )}
                </div>

                {/* Products Sync */}
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.products')}</h3>
                      {lastProductSync && (
                        <p className="text-xs text-gray-500">{t('settings.hubspot.lastSync')}: {lastProductSync}</p>
                      )}
                    </div>
                    <button
                      onClick={handleSyncProducts}
                      disabled={syncingProducts}
                      className="inline-flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {syncingProducts ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      {t('settings.hubspot.syncNow')}
                    </button>
                  </div>
                  {productSyncMessage && (
                    <p className={`mt-2 text-sm ${productSyncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                      {productSyncMessage.text}
                    </p>
                  )}
                </div>

                {/* Deals Sync */}
                <div>
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.deals')}</h3>
                      <p className="text-xs text-gray-500">{t('settings.hubspot.dealsDescription')}</p>
                      {lastDealSync && (
                        <p className="text-xs text-gray-500">{t('settings.hubspot.lastSync')}: {lastDealSync}</p>
                      )}
                    </div>
                    <button
                      onClick={handleSyncDeals}
                      disabled={syncingDeals}
                      className="inline-flex items-center gap-2 rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {syncingDeals ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      {t('settings.hubspot.syncNow')}
                    </button>
                  </div>
                  {dealSyncMessage && (
                    <p className={`mt-2 text-sm ${dealSyncMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                      {dealSyncMessage.text}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Language */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.language')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.languageDescription')}</p>

          <div className="mt-4 flex gap-2">
            <button
              onClick={() => changeLanguage('de')}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                i18n.language === 'de'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Deutsch
            </button>
            <button
              onClick={() => changeLanguage('en')}
              className={`rounded-md px-4 py-2 text-sm font-medium ${
                i18n.language === 'en'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              English
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
