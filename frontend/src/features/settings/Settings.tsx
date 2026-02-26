import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, gql } from '@apollo/client'
import { RefreshCw, CheckCircle, XCircle, Loader2, Upload, Plus, X, Info, Copy, Check } from 'lucide-react'
import { formatDateTime } from '@/lib/utils'
import { HelpVideoSettings } from './HelpVideoSettings'

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

const ACTIVATION_CHECKLIST_QUERY = gql`
  query ActivationChecklistSettings {
    activationChecklistSettings {
      availableFields
      requiredFields
    }
  }
`

const SET_ACTIVATION_REQUIRED_FIELDS = gql`
  mutation SetActivationRequiredFields($fields: [String!]!) {
    setActivationRequiredFields(fields: $fields) {
      success
      error
    }
  }
`

const TIME_TRACKING_SETTINGS_QUERY = gql`
  query TimeTrackingSettings {
    timeTrackingSettings {
      provider
      isConfigured
      showRevenue
    }
  }
`

const SAVE_TIME_TRACKING_SETTINGS = gql`
  mutation SaveTimeTrackingSettings($provider: String!, $apiEmail: String!, $apiKey: String!, $showRevenue: Boolean!) {
    saveTimeTrackingSettings(provider: $provider, apiEmail: $apiEmail, apiKey: $apiKey, showRevenue: $showRevenue) {
      success
      error
    }
  }
`

const UPDATE_TIME_TRACKING_DISPLAY = gql`
  mutation UpdateTimeTrackingDisplay($showRevenue: Boolean!) {
    updateTimeTrackingDisplay(showRevenue: $showRevenue)
  }
`

const HUBSPOT_SETTINGS_QUERY = gql`
  query HubSpotSettings {
    hubspotSettings {
      isConfigured
      apiKeySet
      lastSync
      lastProductSync
      lastDealSync
      autoSyncEnabled
      lastAutoSyncCustomers
      lastAutoSyncProducts
      lastAutoSyncDeals
      companyFilters {
        propertyName
        values
      }
      billingContactLabel
      portalId
      syncMode
      webhookLastReceived
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
      warnings
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
      warnings
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
      warnings
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

const SET_HUBSPOT_AUTO_SYNC = gql`
  mutation SetHubSpotAutoSync($enabled: Boolean!) {
    setHubspotAutoSync(enabled: $enabled) {
      success
      error
    }
  }
`

const HUBSPOT_CONTACT_LABELS_QUERY = gql`
  query HubSpotContactAssociationLabels {
    hubspotContactAssociationLabels {
      success
      labels {
        typeId
        label
        category
      }
    }
  }
`

const SET_BILLING_CONTACT_LABEL = gql`
  mutation SetHubSpotBillingContactLabel($label: String) {
    setHubspotBillingContactLabel(label: $label) {
      success
      error
    }
  }
`

const SAVE_WEBHOOK_SETTINGS = gql`
  mutation SaveWebhookSettings($portalId: String, $syncMode: String) {
    saveWebhookSettings(portalId: $portalId, syncMode: $syncMode) {
      success
      error
    }
  }
`

const M365_SETTINGS_QUERY = gql`
  query M365Settings {
    m365Settings {
      isConfigured
      senderMailbox
      clientIdMasked
      azureTenantIdMasked
    }
  }
`

const SAVE_M365_SETTINGS = gql`
  mutation SaveM365Settings($azureTenantId: String!, $clientId: String!, $clientSecret: String!) {
    saveM365Settings(azureTenantId: $azureTenantId, clientId: $clientId, clientSecret: $clientSecret) {
      success
      error
    }
  }
`

const TEST_M365_CONNECTION = gql`
  mutation TestM365Connection {
    testM365Connection {
      success
      error
      organization
    }
  }
`

const SELECT_M365_MAILBOX = gql`
  mutation SelectM365Mailbox($mailbox: String!) {
    selectM365Mailbox(mailbox: $mailbox) {
      success
      error
    }
  }
`

const SEND_M365_TEST_EMAIL = gql`
  mutation SendM365TestEmail {
    sendM365TestEmail {
      success
      error
    }
  }
`

interface SettingsProps {
  showHeader?: boolean
  section?: 'hubspot' | 'timeTracking' | 'email' | 'contracts' | 'helpVideos'
}

export function Settings({ showHeader = true, section }: SettingsProps) {
  const { t } = useTranslation()
  const [ttProvider, setTtProvider] = useState('clockodo')
  const [ttApiEmail, setTtApiEmail] = useState('')
  const [ttApiKey, setTtApiKey] = useState('')
  const [ttShowRevenue, setTtShowRevenue] = useState(true)
  const [ttMessage, setTtMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const [apiKey, setApiKey] = useState('')
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [customerSyncMessage, setCustomerSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [productSyncMessage, setProductSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [dealSyncMessage, setDealSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [companyFilters, setCompanyFilters] = useState<CompanyFilter[]>([])
  const [filterMessage, setFilterMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [propertySearch, setPropertySearch] = useState('')
  const [openPropertyDropdown, setOpenPropertyDropdown] = useState<number | null>(null)

  const [checklistMessage, setChecklistMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data: checklistData, refetch: refetchChecklist } = useQuery(ACTIVATION_CHECKLIST_QUERY)
  const [setActivationFields, { loading: savingChecklist }] = useMutation(SET_ACTIVATION_REQUIRED_FIELDS)

  const { data: ttSettingsData, refetch: refetchTtSettings } = useQuery(TIME_TRACKING_SETTINGS_QUERY)
  const [saveTtSettings, { loading: savingTt }] = useMutation(SAVE_TIME_TRACKING_SETTINGS)
  const [updateTtDisplay] = useMutation(UPDATE_TIME_TRACKING_DISPLAY)

  const { data: settingsData, refetch: refetchSettings } = useQuery(HUBSPOT_SETTINGS_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_HUBSPOT_SETTINGS)
  const [syncCustomers, { loading: syncingCustomers }] = useMutation(SYNC_HUBSPOT_CUSTOMERS)
  const [syncProducts, { loading: syncingProducts }] = useMutation(SYNC_HUBSPOT_PRODUCTS)
  const [syncDeals, { loading: syncingDeals }] = useMutation(SYNC_HUBSPOT_DEALS)
  const [saveFilters, { loading: savingFilters }] = useMutation(SAVE_COMPANY_FILTERS)
  const [setAutoSync] = useMutation(SET_HUBSPOT_AUTO_SYNC)
  const { data: contactLabelsData } = useQuery(HUBSPOT_CONTACT_LABELS_QUERY)
  const [setBillingContactLabel] = useMutation(SET_BILLING_CONTACT_LABEL)
  const [saveWebhookSettings, { loading: savingWebhook }] = useMutation(SAVE_WEBHOOK_SETTINGS)

  const [webhookPortalId, setWebhookPortalId] = useState('')
  const [webhookMessage, setWebhookMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [webhookCopied, setWebhookCopied] = useState(false)

  // M365 state
  const [m365AzureTenantId, setM365AzureTenantId] = useState('')
  const [m365ClientId, setM365ClientId] = useState('')
  const [m365ClientSecret, setM365ClientSecret] = useState('')
  const [m365Message, setM365Message] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [m365SenderMailbox, setM365SenderMailbox] = useState('')

  const { data: m365Data, refetch: refetchM365 } = useQuery(M365_SETTINGS_QUERY)
  const [saveM365, { loading: savingM365 }] = useMutation(SAVE_M365_SETTINGS)
  const [testM365, { loading: testingM365 }] = useMutation(TEST_M365_CONNECTION)
  const [selectMailbox] = useMutation(SELECT_M365_MAILBOX)
  const [sendTestEmail, { loading: sendingTestEmail }] = useMutation(SEND_M365_TEST_EMAIL)

  // Initialize time tracking show revenue from settings
  useEffect(() => {
    if (ttSettingsData?.timeTrackingSettings?.showRevenue !== undefined) {
      setTtShowRevenue(ttSettingsData.timeTrackingSettings.showRevenue)
    }
  }, [ttSettingsData?.timeTrackingSettings?.showRevenue])

  // Initialize webhook portal ID from settings
  useEffect(() => {
    if (settingsData?.hubspotSettings?.portalId) {
      setWebhookPortalId(settingsData.hubspotSettings.portalId)
    }
  }, [settingsData?.hubspotSettings?.portalId])

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

  const handleSaveTtSettings = async () => {
    setTtMessage(null)
    try {
      const result = await saveTtSettings({
        variables: {
          provider: ttProvider,
          apiEmail: ttApiEmail,
          apiKey: ttApiKey,
          showRevenue: ttShowRevenue,
        },
      })
      if (result.data?.saveTimeTrackingSettings?.success) {
        setTtMessage({ type: 'success', text: t('settings.timeTracking.connectionSuccess') })
        setTtApiKey('')
        refetchTtSettings()
      } else {
        setTtMessage({
          type: 'error',
          text: result.data?.saveTimeTrackingSettings?.error || t('settings.timeTracking.connectionFailed'),
        })
      }
    } catch {
      setTtMessage({ type: 'error', text: t('settings.timeTracking.connectionFailed') })
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
        const { created, updated, warnings } = result.data.syncHubspotCustomers
        let text = t('settings.hubspot.syncSuccess', { created, updated })
        if (warnings?.length) {
          text += `\n${t('settings.hubspot.syncWarnings')}: ${warnings[0]}`
          if (warnings.length > 1) text += ` (+${warnings.length - 1} more)`
        }
        setCustomerSyncMessage({
          type: warnings?.length ? 'error' : 'success',
          text,
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
        const { created, updated, warnings } = result.data.syncHubspotProducts
        let text = t('settings.hubspot.syncSuccess', { created, updated })
        if (warnings?.length) {
          text += `\n${t('settings.hubspot.syncWarnings')}: ${warnings[0]}`
          if (warnings.length > 1) text += ` (+${warnings.length - 1} more)`
        }
        setProductSyncMessage({
          type: warnings?.length ? 'error' : 'success',
          text,
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
        const { created, skipped, warnings } = result.data.syncHubspotDeals
        let text = t('settings.hubspot.dealSyncSuccess', { created, skipped })
        if (warnings?.length) {
          text += `\n${t('settings.hubspot.syncWarnings')}: ${warnings[0]}`
          if (warnings.length > 1) text += ` (+${warnings.length - 1} more)`
        }
        setDealSyncMessage({
          type: warnings?.length ? 'error' : 'success',
          text,
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
  const lastAutoSyncCustomers = hubspotSettings?.lastAutoSyncCustomers
    ? formatDateTime(hubspotSettings.lastAutoSyncCustomers)
    : null
  const lastAutoSyncProducts = hubspotSettings?.lastAutoSyncProducts
    ? formatDateTime(hubspotSettings.lastAutoSyncProducts)
    : null
  const lastAutoSyncDeals = hubspotSettings?.lastAutoSyncDeals
    ? formatDateTime(hubspotSettings.lastAutoSyncDeals)
    : null

  const handleToggleChecklistField = async (fieldName: string, enabled: boolean) => {
    setChecklistMessage(null)
    const currentFields: string[] = checklistData?.activationChecklistSettings?.requiredFields || []
    const newFields = enabled
      ? [...currentFields, fieldName]
      : currentFields.filter((f: string) => f !== fieldName)

    try {
      const result = await setActivationFields({ variables: { fields: newFields } })
      if (result.data?.setActivationRequiredFields?.success) {
        setChecklistMessage({ type: 'success', text: t('settings.activationChecklist.saved') })
        refetchChecklist()
      } else {
        setChecklistMessage({
          type: 'error',
          text: result.data?.setActivationRequiredFields?.error || t('settings.activationChecklist.saveFailed'),
        })
      }
    } catch {
      setChecklistMessage({ type: 'error', text: t('settings.activationChecklist.saveFailed') })
    }
  }

  const handleToggleAutoSync = async (enabled: boolean) => {
    await setAutoSync({ variables: { enabled } })
    refetchSettings()
  }

  const handleSetBillingContactLabel = async (label: string | null) => {
    await setBillingContactLabel({ variables: { label } })
    refetchSettings()
  }

  const handleSaveWebhookSettings = async () => {
    setWebhookMessage(null)
    try {
      const result = await saveWebhookSettings({ variables: { portalId: webhookPortalId } })
      if (result.data?.saveWebhookSettings?.success) {
        setWebhookMessage({ type: 'success', text: t('settings.hubspot.webhookSaved') })
        refetchSettings()
      } else {
        setWebhookMessage({
          type: 'error',
          text: result.data?.saveWebhookSettings?.error || t('settings.hubspot.webhookSaveFailed'),
        })
      }
    } catch {
      setWebhookMessage({ type: 'error', text: t('settings.hubspot.webhookSaveFailed') })
    }
  }

  const handleToggleSyncMode = async (mode: string) => {
    setWebhookMessage(null)
    try {
      const result = await saveWebhookSettings({ variables: { syncMode: mode } })
      if (result.data?.saveWebhookSettings?.success) {
        refetchSettings()
      } else {
        setWebhookMessage({
          type: 'error',
          text: result.data?.saveWebhookSettings?.error || t('settings.hubspot.webhookSaveFailed'),
        })
      }
    } catch {
      setWebhookMessage({ type: 'error', text: t('settings.hubspot.webhookSaveFailed') })
    }
  }

  const handleCopyWebhookUrl = () => {
    const url = `${window.location.origin}/api/hubspot/webhook/`
    navigator.clipboard.writeText(url)
    setWebhookCopied(true)
    setTimeout(() => setWebhookCopied(false), 2000)
  }

  const contactLabels: { typeId: number; label: string; category: string }[] =
    contactLabelsData?.hubspotContactAssociationLabels?.labels || []

  const handleSaveM365 = async () => {
    setM365Message(null)
    try {
      const result = await saveM365({
        variables: {
          azureTenantId: m365AzureTenantId,
          clientId: m365ClientId,
          clientSecret: m365ClientSecret,
        },
      })
      if (result.data?.saveM365Settings?.success) {
        setM365Message({ type: 'success', text: t('settings.m365.saved') })
        setM365ClientSecret('')
        refetchM365()
      } else {
        setM365Message({ type: 'error', text: result.data?.saveM365Settings?.error || t('settings.m365.saveFailed') })
      }
    } catch {
      setM365Message({ type: 'error', text: t('settings.m365.saveFailed') })
    }
  }

  const handleTestM365 = async () => {
    setM365Message(null)
    try {
      const result = await testM365()
      if (result.data?.testM365Connection?.success) {
        setM365Message({
          type: 'success',
          text: t('settings.m365.connectionSuccess', { org: result.data.testM365Connection.organization || '' }),
        })
      } else {
        setM365Message({ type: 'error', text: result.data?.testM365Connection?.error || t('settings.m365.connectionFailed') })
      }
    } catch {
      setM365Message({ type: 'error', text: t('settings.m365.connectionFailed') })
    }
  }

  const handleSelectMailbox = async (mailbox: string) => {
    setM365Message(null)
    try {
      const result = await selectMailbox({ variables: { mailbox } })
      if (result.data?.selectM365Mailbox?.success) {
        setM365Message({ type: 'success', text: t('settings.m365.mailboxSelected') })
        refetchM365()
      } else {
        setM365Message({ type: 'error', text: result.data?.selectM365Mailbox?.error || t('settings.m365.selectFailed') })
      }
    } catch {
      setM365Message({ type: 'error', text: t('settings.m365.selectFailed') })
    }
  }

  const handleSendTestEmail = async () => {
    setM365Message(null)
    try {
      const result = await sendTestEmail()
      if (result.data?.sendM365TestEmail?.success) {
        setM365Message({ type: 'success', text: t('settings.m365.testEmailSent') })
      } else {
        setM365Message({ type: 'error', text: result.data?.sendM365TestEmail?.error || t('settings.m365.testEmailFailed') })
      }
    } catch {
      setM365Message({ type: 'error', text: t('settings.m365.testEmailFailed') })
    }
  }

  return (
    <div>
      {showHeader && <h1 className="text-2xl font-bold">{t('nav.settings')}</h1>}

      <div className={showHeader ? "mt-6 space-y-6" : "space-y-6"}>
        {/* HubSpot Integration */}
        {(!section || section === 'hubspot') && <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.hubspot.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.hubspot.description')}</p>

          <details className="mt-3 rounded-md border border-blue-100 bg-blue-50">
            <summary className="flex cursor-pointer items-center gap-2 px-4 py-2 text-sm font-medium text-blue-700">
              <Info className="h-4 w-4" />
              {t('settings.hubspot.setupGuide')}
            </summary>
            <div className="px-4 pb-3 text-sm text-blue-900 space-y-2">
              <p>{t('settings.hubspot.setup.intro')}</p>
              <ul className="list-disc ml-4 space-y-0.5">
                <li><code className="text-xs bg-blue-100 px-1 rounded">crm.objects.companies.read</code></li>
                <li><code className="text-xs bg-blue-100 px-1 rounded">crm.schemas.companies.read</code></li>
                <li><code className="text-xs bg-blue-100 px-1 rounded">crm.objects.products.read</code></li>
                <li><code className="text-xs bg-blue-100 px-1 rounded">crm.objects.deals.read</code></li>
                <li><code className="text-xs bg-blue-100 px-1 rounded">crm.objects.contacts.read</code></li>
              </ul>
              <p className="text-xs text-blue-700 mt-2">
                {t('settings.hubspot.setup.createKeyLink')}
              </p>
            </div>
          </details>

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
              <p className="text-xs text-gray-500 mt-0.5">{t('settings.hubspot.apiKeyDescription')}</p>
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

                {/* Auto-sync toggle */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.autoSync')}</h3>
                      <p className="text-xs text-gray-500">{t('settings.hubspot.autoSyncDescription')}</p>
                      {(lastAutoSyncCustomers || lastAutoSyncProducts || lastAutoSyncDeals) && (
                        <div className="mt-1 space-y-0.5">
                          {lastAutoSyncCustomers && (
                            <p className="text-xs text-gray-400">{t('settings.hubspot.lastAutoSync')}: {t('settings.hubspot.customers')} {lastAutoSyncCustomers}</p>
                          )}
                          {lastAutoSyncProducts && (
                            <p className="text-xs text-gray-400">{t('settings.hubspot.lastAutoSync')}: {t('settings.hubspot.products')} {lastAutoSyncProducts}</p>
                          )}
                          {lastAutoSyncDeals && (
                            <p className="text-xs text-gray-400">{t('settings.hubspot.lastAutoSync')}: {t('settings.hubspot.deals')} {lastAutoSyncDeals}</p>
                          )}
                        </div>
                      )}
                    </div>
                    <label className="relative inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={hubspotSettings?.autoSyncEnabled || false}
                        onChange={(e) => handleToggleAutoSync(e.target.checked)}
                        className="peer sr-only"
                      />
                      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300" />
                    </label>
                  </div>
                </div>

                {/* Billing Contact Label */}
                <div className="border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.billingContactLabel')}</h3>
                  <p className="text-xs text-gray-500 mt-1">{t('settings.hubspot.billingContactLabelDescription')}</p>
                  <select
                    className="mt-2 block w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={hubspotSettings?.billingContactLabel || ''}
                    onChange={(e) => handleSetBillingContactLabel(e.target.value || null)}
                  >
                    <option value="">{t('settings.hubspot.billingContactLabelNone')}</option>
                    {contactLabels.map((cl) => (
                      <option key={cl.typeId} value={cl.label}>
                        {cl.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Webhook Settings */}
                <div className="border-t pt-4">
                  <h3 className="text-sm font-medium text-gray-900">{t('settings.hubspot.webhookTitle')}</h3>
                  <p className="text-xs text-gray-500 mt-1">{t('settings.hubspot.webhookDescription')}</p>

                  <div className="mt-3 space-y-3">
                    {/* Sync Mode */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">{t('settings.hubspot.syncMode')}</label>
                      <div className="flex gap-4">
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            type="radio"
                            name="syncMode"
                            value="polling"
                            checked={hubspotSettings?.syncMode !== 'webhooks'}
                            onChange={() => handleToggleSyncMode('polling')}
                            className="text-blue-600"
                          />
                          {t('settings.hubspot.syncModePolling')}
                        </label>
                        <label className={`flex items-center gap-2 text-sm ${!hubspotSettings?.portalId ? 'text-gray-400' : ''}`}>
                          <input
                            type="radio"
                            name="syncMode"
                            value="webhooks"
                            checked={hubspotSettings?.syncMode === 'webhooks'}
                            onChange={() => handleToggleSyncMode('webhooks')}
                            disabled={!hubspotSettings?.portalId}
                            className="text-blue-600"
                          />
                          {t('settings.hubspot.syncModeWebhooks')}
                        </label>
                      </div>
                    </div>

                    {/* Portal ID */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700">{t('settings.hubspot.portalId')}</label>
                      <input
                        type="text"
                        value={webhookPortalId}
                        onChange={(e) => setWebhookPortalId(e.target.value)}
                        placeholder={t('settings.hubspot.portalIdPlaceholder')}
                        className="mt-1 block w-full max-w-xs rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      />
                    </div>

                    {/* Save button */}
                    <button
                      onClick={handleSaveWebhookSettings}
                      disabled={savingWebhook || !webhookPortalId}
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingWebhook ? <Loader2 className="h-4 w-4 animate-spin inline mr-1" /> : null}
                      {t('settings.hubspot.webhookSave')}
                    </button>

                    {webhookMessage && (
                      <p className={`text-sm ${webhookMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {webhookMessage.text}
                      </p>
                    )}

                    {/* Webhook URL */}
                    <div className="mt-2 rounded-md bg-gray-50 p-3">
                      <label className="block text-xs font-medium text-gray-700 mb-1">{t('settings.hubspot.webhookUrl')}</label>
                      <div className="flex items-center gap-2">
                        <code className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded flex-1 overflow-x-auto">
                          {window.location.origin}/api/hubspot/webhook/
                        </code>
                        <button
                          onClick={handleCopyWebhookUrl}
                          className="text-gray-500 hover:text-gray-700 p-1"
                          title={t('settings.hubspot.copyUrl')}
                        >
                          {webhookCopied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Last webhook received */}
                    {hubspotSettings?.webhookLastReceived && (
                      <p className="text-xs text-gray-400">
                        {t('settings.hubspot.webhookLastReceived')}: {formatDateTime(hubspotSettings.webhookLastReceived)}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>}

        {/* Time Tracking */}
        {(!section || section === 'timeTracking') && <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.timeTracking.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.timeTracking.description')}</p>

          <div className="mt-4 space-y-4">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">{t('settings.timeTracking.status')}:</span>
              {ttSettingsData?.timeTrackingSettings?.isConfigured ? (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  {t('settings.timeTracking.connected')}
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm text-gray-500">
                  <XCircle className="h-4 w-4" />
                  {t('settings.timeTracking.notConnected')}
                </span>
              )}
            </div>

            {/* Provider Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.timeTracking.provider')}
              </label>
              <select
                value={ttProvider}
                onChange={(e) => setTtProvider(e.target.value)}
                className="mt-1 block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="clockodo">{t('settings.timeTracking.clockodo')}</option>
              </select>
            </div>

            {/* API Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.timeTracking.apiEmail')}
              </label>
              <input
                type="email"
                value={ttApiEmail}
                onChange={(e) => setTtApiEmail(e.target.value)}
                placeholder={t('settings.timeTracking.apiEmailPlaceholder')}
                className="mt-1 block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.timeTracking.apiKey')}
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  type="password"
                  value={ttApiKey}
                  onChange={(e) => setTtApiKey(e.target.value)}
                  placeholder={ttSettingsData?.timeTrackingSettings?.isConfigured ? '••••••••••••••••' : t('settings.timeTracking.apiKeyPlaceholder')}
                  className="block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  onClick={handleSaveTtSettings}
                  disabled={savingTt || !ttApiKey || !ttApiEmail}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {savingTt && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t('settings.timeTracking.saveAndTest')}
                </button>
              </div>
              {ttMessage && (
                <p className={`mt-2 text-sm ${ttMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                  {ttMessage.text}
                </p>
              )}
            </div>

            {/* Show Revenue Toggle */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="ttShowRevenue"
                checked={ttShowRevenue}
                onChange={async (e) => {
                  const newValue = e.target.checked
                  setTtShowRevenue(newValue)
                  await updateTtDisplay({ variables: { showRevenue: newValue } })
                }}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="ttShowRevenue" className="text-sm text-gray-700">
                {t('settings.timeTracking.showRevenue')}
              </label>
            </div>
          </div>
        </div>}

        {/* Contract Import */}
        {(!section || section === 'contracts') && <>
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

        {/* Activation Checklist */}
        <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.activationChecklist.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.activationChecklist.description')}</p>

          <div className="mt-4 space-y-3">
            {(checklistData?.activationChecklistSettings?.availableFields || []).map((field: string) => {
              const isRequired = (checklistData?.activationChecklistSettings?.requiredFields || []).includes(field)
              return (
                <div key={field} className="flex items-center justify-between">
                  <label htmlFor={`checklist-${field}`} className="text-sm text-gray-700">
                    {t(`settings.activationChecklist.fields.${field}`)}
                  </label>
                  <label className="relative inline-flex cursor-pointer items-center">
                    <input
                      id={`checklist-${field}`}
                      type="checkbox"
                      checked={isRequired}
                      onChange={(e) => handleToggleChecklistField(field, e.target.checked)}
                      disabled={savingChecklist}
                      className="peer sr-only"
                    />
                    <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300" />
                  </label>
                </div>
              )
            })}
          </div>

          {checklistMessage && (
            <p className={`mt-3 text-sm ${checklistMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
              {checklistMessage.text}
            </p>
          )}
        </div>

        </>}

        {/* Help Video Links */}
        {(!section || section === 'helpVideos') && <HelpVideoSettings />}

        {/* Microsoft 365 Email */}
        {(!section || section === 'email') && <div className="rounded-lg border bg-white p-6">
          <h2 className="text-lg font-medium">{t('settings.m365.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.m365.description')}</p>

          <details className="mt-3 rounded-md border border-blue-100 bg-blue-50">
            <summary className="flex cursor-pointer items-center gap-2 px-4 py-2 text-sm font-medium text-blue-700">
              <Info className="h-4 w-4" />
              {t('settings.m365.setupGuide')}
            </summary>
            <div className="px-4 pb-3 text-sm text-blue-900 space-y-2">
              <ol className="list-decimal ml-4 space-y-1">
                <li>{t('settings.m365.setup.step1')}</li>
                <li>{t('settings.m365.setup.step2')}</li>
                <li>{t('settings.m365.setup.step3')}</li>
                <li>{t('settings.m365.setup.step4')}</li>
                <li>{t('settings.m365.setup.step5')}</li>
              </ol>
              <p className="text-xs text-blue-700 mt-2">{t('settings.m365.setup.restrictNote')}</p>
            </div>
          </details>

          <div className="mt-4 space-y-4">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">{t('settings.m365.status')}:</span>
              {m365Data?.m365Settings?.isConfigured ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm text-green-600">{t('settings.m365.connected')}</span>
                  {m365Data.m365Settings.senderMailbox && (
                    <span className="text-sm text-gray-500">
                      ({t('settings.m365.sender')}: {m365Data.m365Settings.senderMailbox})
                    </span>
                  )}
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-500">{t('settings.m365.notConfigured')}</span>
                </>
              )}
            </div>

            {/* Credential Fields */}
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.m365.azureTenantId')}
              </label>
              <input
                type="text"
                value={m365AzureTenantId}
                onChange={(e) => setM365AzureTenantId(e.target.value)}
                placeholder={m365Data?.m365Settings?.azureTenantIdMasked || ''}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.m365.clientId')}
              </label>
              <input
                type="text"
                value={m365ClientId}
                onChange={(e) => setM365ClientId(e.target.value)}
                placeholder={m365Data?.m365Settings?.clientIdMasked || ''}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.m365.clientSecret')}
              </label>
              <input
                type="password"
                value={m365ClientSecret}
                onChange={(e) => setM365ClientSecret(e.target.value)}
                placeholder="••••••••"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleSaveM365}
                disabled={savingM365 || (!m365AzureTenantId && !m365ClientId && !m365ClientSecret)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {savingM365 && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('settings.m365.save')}
              </button>

              {m365Data?.m365Settings?.isConfigured && (
                <>
                  <button
                    onClick={handleTestM365}
                    disabled={testingM365}
                    className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {testingM365 && <Loader2 className="h-4 w-4 animate-spin" />}
                    {t('settings.m365.testConnection')}
                  </button>
                  {m365Data.m365Settings.senderMailbox && (
                    <button
                      onClick={handleSendTestEmail}
                      disabled={sendingTestEmail}
                      className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {sendingTestEmail && <Loader2 className="h-4 w-4 animate-spin" />}
                      {t('settings.m365.sendTestEmail')}
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Sender Mailbox */}
            {m365Data?.m365Settings?.isConfigured && (
              <div className="border-t pt-4 space-y-3">
                <h3 className="text-sm font-medium text-gray-700">{t('settings.m365.senderMailbox')}</h3>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={m365SenderMailbox}
                    onChange={(e) => setM365SenderMailbox(e.target.value)}
                    placeholder={m365Data?.m365Settings?.senderMailbox || t('settings.m365.senderMailboxPlaceholder')}
                    className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => handleSelectMailbox(m365SenderMailbox)}
                    disabled={!m365SenderMailbox}
                    className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {t('settings.m365.saveMailbox')}
                  </button>
                </div>
              </div>
            )}

            {m365Message && (
              <p className={`text-sm ${m365Message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {m365Message.text}
              </p>
            )}
          </div>
        </div>}
      </div>
    </div>
  )
}
