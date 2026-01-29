import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, gql } from '@apollo/client'
import { RefreshCw, CheckCircle, XCircle, Loader2, Upload, Plus, X } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'

interface CompanyFilter {
  propertyName: string
  values: string[]
}

interface HubSpotProperty {
  name: string
  label: string
  propertyType: string
  options: string[] | null
}

const HUBSPOT_SETTINGS_QUERY = gql`
  query HubSpotSettings {
    hubspotSettings {
      isConfigured
      apiKeySet
      lastSync
      lastProductSync
      lastDealSync
      companyFilters {
        propertyName
        values
      }
    }
    hubspotCompanyProperties {
      success
      properties {
        name
        label
        propertyType
        options
      }
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

const SAVE_COMPANY_FILTERS = gql`
  mutation SaveHubSpotCompanyFilters($filters: [HubSpotCompanyFilterInput!]!) {
    saveHubspotCompanyFilters(filters: $filters) {
      success
      error
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
  const [companyFilters, setCompanyFilters] = useState<CompanyFilter[]>([])
  const [filterMessage, setFilterMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [propertySearch, setPropertySearch] = useState('')
  const [openPropertyDropdown, setOpenPropertyDropdown] = useState<number | null>(null)

  const { data: settingsData, refetch: refetchSettings } = useQuery(HUBSPOT_SETTINGS_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_HUBSPOT_SETTINGS)
  const [syncCustomers, { loading: syncingCustomers }] = useMutation(SYNC_HUBSPOT_CUSTOMERS)
  const [syncProducts, { loading: syncingProducts }] = useMutation(SYNC_HUBSPOT_PRODUCTS)
  const [syncDeals, { loading: syncingDeals }] = useMutation(SYNC_HUBSPOT_DEALS)
  const [saveFilters, { loading: savingFilters }] = useMutation(SAVE_COMPANY_FILTERS)

  // Initialize filters from settings
  useEffect(() => {
    if (settingsData?.hubspotSettings?.companyFilters) {
      setCompanyFilters(
        settingsData.hubspotSettings.companyFilters.map((f: CompanyFilter) => ({
          propertyName: f.propertyName,
          values: [...f.values],
        }))
      )
    }
  }, [settingsData?.hubspotSettings?.companyFilters])

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang)
  }

  const addFilter = () => {
    setCompanyFilters([...companyFilters, { propertyName: '', values: [] }])
  }

  const removeFilter = (index: number) => {
    setCompanyFilters(companyFilters.filter((_, i) => i !== index))
  }

  const updateFilterProperty = (index: number, propertyName: string) => {
    const updated = [...companyFilters]
    updated[index] = { ...updated[index], propertyName }
    setCompanyFilters(updated)
  }

  const updateFilterValues = (index: number, valuesString: string) => {
    const updated = [...companyFilters]
    const values = valuesString.split(',').map(v => v.trim()).filter(v => v)
    updated[index] = { ...updated[index], values }
    setCompanyFilters(updated)
  }

  const toggleFilterValue = (index: number, value: string) => {
    const updated = [...companyFilters]
    const currentValues = updated[index].values
    if (currentValues.includes(value)) {
      updated[index] = { ...updated[index], values: currentValues.filter(v => v !== value) }
    } else {
      updated[index] = { ...updated[index], values: [...currentValues, value] }
    }
    setCompanyFilters(updated)
  }

  const selectProperty = (index: number, propertyName: string) => {
    updateFilterProperty(index, propertyName)
    setOpenPropertyDropdown(null)
    setPropertySearch('')
  }

  const handleSaveFilters = async () => {
    setFilterMessage(null)
    try {
      // Filter out empty entries
      const validFilters = companyFilters.filter(f => f.propertyName && f.values.length > 0)
      const result = await saveFilters({
        variables: {
          filters: validFilters.map(f => ({
            propertyName: f.propertyName,
            values: f.values,
          })),
        },
      })
      if (result.data?.saveHubspotCompanyFilters?.success) {
        setFilterMessage({ type: 'success', text: t('settings.hubspot.filtersSaved') })
        refetchSettings()
      } else {
        setFilterMessage({
          type: 'error',
          text: result.data?.saveHubspotCompanyFilters?.error || t('settings.hubspot.filtersSaveFailed')
        })
      }
    } catch {
      setFilterMessage({ type: 'error', text: t('settings.hubspot.filtersSaveFailed') })
    }
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
  const hubspotProperties: HubSpotProperty[] = settingsData?.hubspotCompanyProperties?.properties || []

  // Filter properties for dropdown search
  const filteredProperties = hubspotProperties.filter(p =>
    p.label.toLowerCase().includes(propertySearch.toLowerCase()) ||
    p.name.toLowerCase().includes(propertySearch.toLowerCase())
  )

  // Get property details by name
  const getPropertyByName = (name: string) => hubspotProperties.find(p => p.name === name)

  const lastCustomerSync = hubspotSettings?.lastSync
    ? formatDateTime(hubspotSettings.lastSync)
    : null
  const lastProductSync = hubspotSettings?.lastProductSync
    ? formatDateTime(hubspotSettings.lastProductSync)
    : null
  const lastDealSync = hubspotSettings?.lastDealSync
    ? formatDateTime(hubspotSettings.lastDealSync)
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

                  {/* Company Filters */}
                  <div className="mt-4 rounded-md border border-gray-200 bg-gray-50 p-4">
                    <h4 className="text-sm font-medium text-gray-700">{t('settings.hubspot.activeFilter')}</h4>
                    <p className="mt-1 text-xs text-gray-500">{t('settings.hubspot.activeFilterDescription')}</p>

                    <div className="mt-3 space-y-4">
                      {companyFilters.map((filter, index) => {
                        const selectedProperty = getPropertyByName(filter.propertyName)
                        const hasOptions = selectedProperty?.options && selectedProperty.options.length > 0

                        return (
                          <div key={index} className="rounded-md border border-gray-200 bg-white p-3">
                            <div className="flex items-center gap-2">
                              {/* Property Dropdown */}
                              <div className="relative flex-1">
                                <button
                                  type="button"
                                  onClick={() => setOpenPropertyDropdown(openPropertyDropdown === index ? null : index)}
                                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-left text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                >
                                  {selectedProperty ? (
                                    <span>{selectedProperty.label} <span className="text-gray-400">({selectedProperty.name})</span></span>
                                  ) : filter.propertyName ? (
                                    <span className="text-gray-600">{filter.propertyName}</span>
                                  ) : (
                                    <span className="text-gray-400">{t('settings.hubspot.selectProperty')}</span>
                                  )}
                                </button>

                                {openPropertyDropdown === index && (
                                  <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 bg-white shadow-lg">
                                    <div className="sticky top-0 bg-white p-2">
                                      <input
                                        type="text"
                                        value={propertySearch}
                                        onChange={(e) => setPropertySearch(e.target.value)}
                                        placeholder={t('common.search')}
                                        className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                                        autoFocus
                                      />
                                    </div>
                                    <div className="max-h-48 overflow-y-auto">
                                      {filteredProperties.map(prop => (
                                        <button
                                          key={prop.name}
                                          type="button"
                                          onClick={() => selectProperty(index, prop.name)}
                                          className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                                        >
                                          <span className="font-medium">{prop.label}</span>
                                          <span className="ml-2 text-gray-400">({prop.name})</span>
                                          {prop.propertyType === 'enumeration' && (
                                            <span className="ml-2 text-xs text-blue-500">{prop.options?.length} options</span>
                                          )}
                                        </button>
                                      ))}
                                      {filteredProperties.length === 0 && (
                                        <p className="px-3 py-2 text-sm text-gray-500">{t('settings.hubspot.noPropertiesFound')}</p>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>

                              <button
                                onClick={() => removeFilter(index)}
                                className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>

                            {/* Values Selection */}
                            {filter.propertyName && (
                              <div className="mt-2">
                                {hasOptions ? (
                                  <div className="flex flex-wrap gap-2">
                                    {selectedProperty.options!.map(option => (
                                      <label
                                        key={option}
                                        className={`inline-flex cursor-pointer items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                                          filter.values.includes(option)
                                            ? 'bg-blue-100 text-blue-800'
                                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                        }`}
                                      >
                                        <input
                                          type="checkbox"
                                          checked={filter.values.includes(option)}
                                          onChange={() => toggleFilterValue(index, option)}
                                          className="sr-only"
                                        />
                                        {option}
                                      </label>
                                    ))}
                                  </div>
                                ) : (
                                  <input
                                    type="text"
                                    value={filter.values.join(', ')}
                                    onChange={(e) => updateFilterValues(index, e.target.value)}
                                    placeholder={t('settings.hubspot.filterValuesPlaceholder')}
                                    className="w-full rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>

                    <div className="mt-3 flex items-center justify-between">
                      <button
                        onClick={addFilter}
                        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
                      >
                        <Plus className="h-4 w-4" />
                        {t('settings.hubspot.addFilter')}
                      </button>
                      <button
                        onClick={handleSaveFilters}
                        disabled={savingFilters}
                        className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {savingFilters && <Loader2 className="h-3 w-3 animate-spin" />}
                        {t('common.save')}
                      </button>
                    </div>

                    {filterMessage && (
                      <p className={`mt-2 text-sm ${filterMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {filterMessage.text}
                      </p>
                    )}
                  </div>
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

        {/* Contract Import */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('import.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('import.description')}</p>

          <div className="mt-4">
            <Link
              to="/contracts/import"
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Upload className="h-4 w-4" />
              {t('import.title')}
            </Link>
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
