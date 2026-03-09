import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useLazyQuery, gql } from '@apollo/client'
import { RefreshCw, CheckCircle, XCircle, Loader2, Upload, Plus, X, Info, Copy, Check, Pencil, Trash2, Save } from 'lucide-react'
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
      maintenanceProjectTemplate
      oneoffProjectTemplate
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

const SAVE_PROJECT_TEMPLATES = gql`
  mutation SaveTimeTrackingProjectTemplates($maintenanceTemplate: String!, $oneoffTemplate: String!) {
    saveTimeTrackingProjectTemplates(maintenanceTemplate: $maintenanceTemplate, oneoffTemplate: $oneoffTemplate)
  }
`

const DEPARTMENTS_QUERY = gql`
  query Departments {
    departments { id name sortOrder }
  }
`

const CLOCKODO_SERVICES_QUERY = gql`
  query ClockodoServices {
    clockodoServices { id name }
  }
`

const DEPARTMENT_SERVICE_MAPPINGS_QUERY = gql`
  query DepartmentServiceMappings {
    departmentServiceMappings { id externalServiceId externalServiceName departmentId }
  }
`

const CREATE_DEPARTMENT = gql`
  mutation CreateDepartment($name: String!) {
    createDepartment(name: $name) { success error }
  }
`

const UPDATE_DEPARTMENT = gql`
  mutation UpdateDepartment($id: ID!, $name: String!) {
    updateDepartment(id: $id, name: $name) { success error }
  }
`

const DELETE_DEPARTMENT = gql`
  mutation DeleteDepartment($id: ID!) {
    deleteDepartment(id: $id) { success error }
  }
`

const SAVE_DEPARTMENT_SERVICE_MAPPINGS = gql`
  mutation SaveDepartmentServiceMappings($mappings: [DepartmentServiceMappingInput!]!) {
    saveDepartmentServiceMappings(mappings: $mappings) { success error }
  }
`

const CLOCKODO_USERS_QUERY = gql`
  query ClockodoUsers {
    clockodoUsers { id name }
  }
`

const USER_COST_PROFILES_QUERY = gql`
  query UserCostProfiles {
    userCostProfiles { id externalUserId externalUserName ftePercentage monthlyIncome defaultDepartmentId }
  }
`

const SAVE_USER_COST_PROFILES = gql`
  mutation SaveUserCostProfiles($profiles: [UserCostProfileInput!]!) {
    saveUserCostProfiles(profiles: $profiles) { success error }
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

const WEBHOOK_EVENT_LOGS_QUERY = gql`
  query WebhookEventLogs($limit: Int) {
    webhookEventLogs(limit: $limit) {
      id
      subscriptionType
      objectId
      objectKind
      status
      result
      errorMessage
      receivedAt
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
  const [saveProjectTemplates, { loading: savingTemplates }] = useMutation(SAVE_PROJECT_TEMPLATES)
  const [maintenanceTemplate, setMaintenanceTemplate] = useState('')
  const [oneoffTemplate, setOneoffTemplate] = useState('')
  const [templateMessage, setTemplateMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Time tracking sub-tab state
  const [ttSubTab, setTtSubTab] = useState<'connection' | 'departments' | 'costs' | 'projects'>('connection')

  // Department state
  const [newDeptName, setNewDeptName] = useState('')
  const [editingDeptId, setEditingDeptId] = useState<string | null>(null)
  const [editingDeptName, setEditingDeptName] = useState('')
  const [deptMessage, setDeptMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [serviceAssignments, setServiceAssignments] = useState<Record<string, string>>({}) // serviceId -> deptId
  const [assignmentMessage, setAssignmentMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const isTimeTrackingConfigured = !!ttSettingsData?.timeTrackingSettings?.isConfigured
  const { data: deptsData, refetch: refetchDepts } = useQuery(DEPARTMENTS_QUERY, { skip: !isTimeTrackingConfigured })
  const [fetchServices, { data: servicesData, loading: loadingServices }] = useLazyQuery(CLOCKODO_SERVICES_QUERY)
  const { data: mappingsData, refetch: refetchMappings } = useQuery(DEPARTMENT_SERVICE_MAPPINGS_QUERY, { skip: !isTimeTrackingConfigured })
  const [createDepartment] = useMutation(CREATE_DEPARTMENT)
  const [updateDepartment] = useMutation(UPDATE_DEPARTMENT)
  const [deleteDepartment] = useMutation(DELETE_DEPARTMENT)
  const [saveDeptMappings, { loading: savingMappings }] = useMutation(SAVE_DEPARTMENT_SERVICE_MAPPINGS)

  // User cost profile state
  const [fetchClockodoUsers, { data: clockodoUsersData, loading: loadingClockodoUsers }] = useLazyQuery(CLOCKODO_USERS_QUERY)
  const { data: costProfilesData, refetch: refetchCostProfiles } = useQuery(USER_COST_PROFILES_QUERY, { skip: !isTimeTrackingConfigured })
  const [saveCostProfiles, { loading: savingCostProfiles }] = useMutation(SAVE_USER_COST_PROFILES)
  const [costProfiles, setCostProfiles] = useState<Record<string, { ftePercentage: number; monthlyIncome: string; defaultDepartmentId: string }>>({})
  const [costProfileMessage, setCostProfileMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

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

  const { data: webhookLogsData } = useQuery(WEBHOOK_EVENT_LOGS_QUERY, { variables: { limit: 20 } })

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

  useEffect(() => {
    if (ttSettingsData?.timeTrackingSettings) {
      setMaintenanceTemplate(ttSettingsData.timeTrackingSettings.maintenanceProjectTemplate || '')
      setOneoffTemplate(ttSettingsData.timeTrackingSettings.oneoffProjectTemplate || '')
    }
  }, [ttSettingsData?.timeTrackingSettings])

  // Initialize service assignments from existing mappings
  useEffect(() => {
    if (mappingsData?.departmentServiceMappings) {
      const assignments: Record<string, string> = {}
      for (const m of mappingsData.departmentServiceMappings) {
        assignments[m.externalServiceId] = m.departmentId
      }
      setServiceAssignments(assignments)
    }
  }, [mappingsData?.departmentServiceMappings])

  // Fetch services when time tracking section is visible and configured
  const loadServices = useCallback(() => {
    if (isTimeTrackingConfigured) {
      fetchServices()
    }
  }, [isTimeTrackingConfigured, fetchServices])

  useEffect(() => {
    if ((!section || section === 'timeTracking') && isTimeTrackingConfigured) {
      loadServices()
      fetchClockodoUsers()
    }
  }, [section, isTimeTrackingConfigured, loadServices, fetchClockodoUsers])

  // Initialize cost profiles from existing data
  useEffect(() => {
    if (costProfilesData?.userCostProfiles) {
      const profiles: Record<string, { ftePercentage: number; monthlyIncome: string; defaultDepartmentId: string }> = {}
      for (const p of costProfilesData.userCostProfiles) {
        profiles[p.externalUserId] = {
          ftePercentage: p.ftePercentage,
          monthlyIncome: String(p.monthlyIncome),
          defaultDepartmentId: p.defaultDepartmentId || '',
        }
      }
      setCostProfiles(profiles)
    }
  }, [costProfilesData?.userCostProfiles])

  const handleSaveCostProfiles = async () => {
    const clockodoUsers = clockodoUsersData?.clockodoUsers || []
    const profiles = clockodoUsers
      .filter((u: { id: string }) => {
        const p = costProfiles[u.id]
        return p && (p.ftePercentage !== 100 || p.monthlyIncome !== '0' || p.defaultDepartmentId)
      })
      .map((u: { id: string; name: string }) => {
        const p = costProfiles[u.id] || { ftePercentage: 100, monthlyIncome: '0', defaultDepartmentId: '' }
        return {
          externalUserId: u.id,
          externalUserName: u.name,
          ftePercentage: p.ftePercentage,
          monthlyIncome: parseFloat(p.monthlyIncome) || 0,
          defaultDepartmentId: p.defaultDepartmentId || null,
        }
      })
    const result = await saveCostProfiles({ variables: { profiles } })
    if (result.data?.saveUserCostProfiles?.success) {
      setCostProfileMessage({ type: 'success', text: t('settings.departments.costProfilesSaved') })
      refetchCostProfiles()
    } else {
      setCostProfileMessage({ type: 'error', text: result.data?.saveUserCostProfiles?.error || t('settings.departments.costProfilesFailed') })
    }
    setTimeout(() => setCostProfileMessage(null), 3000)
  }

  const handleCreateDept = async () => {
    const name = newDeptName.trim()
    if (!name) return
    const result = await createDepartment({ variables: { name } })
    if (result.data?.createDepartment?.success) {
      setNewDeptName('')
      setDeptMessage(null)
      refetchDepts()
    } else {
      setDeptMessage({ type: 'error', text: result.data?.createDepartment?.error || 'Failed' })
    }
  }

  const handleRenameDept = async (id: string) => {
    const name = editingDeptName.trim()
    if (!name) return
    const result = await updateDepartment({ variables: { id, name } })
    if (result.data?.updateDepartment?.success) {
      setEditingDeptId(null)
      setDeptMessage(null)
      refetchDepts()
    } else {
      setDeptMessage({ type: 'error', text: result.data?.updateDepartment?.error || 'Failed' })
    }
  }

  const handleDeleteDept = async (id: string) => {
    if (!confirm(t('settings.departments.confirmDelete'))) return
    const result = await deleteDepartment({ variables: { id } })
    if (result.data?.deleteDepartment?.success) {
      refetchDepts()
      refetchMappings()
    }
  }

  const handleSaveAssignments = async () => {
    const services = servicesData?.clockodoServices || []
    const mappings = services
      .filter((s: { id: string }) => serviceAssignments[s.id])
      .map((s: { id: string; name: string }) => ({
        externalServiceId: s.id,
        externalServiceName: s.name,
        departmentId: serviceAssignments[s.id],
      }))
    const result = await saveDeptMappings({ variables: { mappings } })
    if (result.data?.saveDepartmentServiceMappings?.success) {
      setAssignmentMessage({ type: 'success', text: t('settings.departments.assignmentsSaved') })
      refetchMappings()
    } else {
      setAssignmentMessage({ type: 'error', text: result.data?.saveDepartmentServiceMappings?.error || t('settings.departments.assignmentsFailed') })
    }
    setTimeout(() => setAssignmentMessage(null), 3000)
  }

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

                    {/* Webhook Event Log */}
                    {webhookLogsData?.webhookEventLogs && webhookLogsData.webhookEventLogs.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-xs font-medium text-gray-700 mb-2">{t('settings.hubspot.webhookEventLog')}</h4>
                        <div className="overflow-x-auto rounded border border-gray-200">
                          <table className="min-w-full text-xs">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-3 py-1.5 text-left font-medium text-gray-500">{t('settings.hubspot.webhookEventTime')}</th>
                                <th className="px-3 py-1.5 text-left font-medium text-gray-500">{t('settings.hubspot.webhookEventType')}</th>
                                <th className="px-3 py-1.5 text-left font-medium text-gray-500">{t('settings.hubspot.webhookEventObject')}</th>
                                <th className="px-3 py-1.5 text-left font-medium text-gray-500">{t('settings.hubspot.webhookEventStatus')}</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {webhookLogsData.webhookEventLogs.map((event: { id: number; subscriptionType: string; objectId: string; objectKind: string; status: string; result: string; errorMessage: string; receivedAt: string }) => (
                                <tr key={event.id} className="hover:bg-gray-50">
                                  <td className="px-3 py-1.5 text-gray-500 whitespace-nowrap">{formatDateTime(event.receivedAt)}</td>
                                  <td className="px-3 py-1.5 text-gray-700">{event.subscriptionType}</td>
                                  <td className="px-3 py-1.5 text-gray-500">
                                    {event.objectKind}{event.objectId ? ` #${event.objectId}` : ''}
                                  </td>
                                  <td className="px-3 py-1.5">
                                    <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${
                                      event.status === 'processed' ? 'bg-green-50 text-green-700' :
                                      event.status === 'failed' ? 'bg-red-50 text-red-700' :
                                      'bg-gray-100 text-gray-600'
                                    }`}>
                                      {event.status}
                                    </span>
                                    {event.errorMessage && (
                                      <span className="ml-1 text-red-500" title={event.errorMessage}>!</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
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

          {/* Sub-tab menu */}
          <div className="mt-4 flex border-b">
            {(['connection', 'departments', 'costs', 'projects'] as const).map((tab) => {
              const labelKey = tab === 'connection' ? 'tabConnection' : tab === 'departments' ? 'tabDepartments' : tab === 'projects' ? 'tabProjects' : 'tabUserCosts'
              const disabled = tab !== 'connection' && !isTimeTrackingConfigured
              return (
                <button
                  key={tab}
                  onClick={() => !disabled && setTtSubTab(tab)}
                  disabled={disabled}
                  className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                    ttSubTab === tab
                      ? 'border-blue-500 text-blue-600'
                      : disabled
                        ? 'border-transparent text-gray-300 cursor-not-allowed'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {t(`settings.timeTracking.${labelKey}`)}
                </button>
              )
            })}
          </div>

          {/* Connection tab */}
          {ttSubTab === 'connection' && (
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
          )}

          {/* Departments tab */}
          {ttSubTab === 'departments' && isTimeTrackingConfigured && (
            <div className="mt-4 space-y-4">
              {/* Department list */}
              <div className="space-y-2">
                {(deptsData?.departments || []).map((dept: { id: string; name: string }) => (
                  <div key={dept.id} className="flex items-center gap-2">
                    {editingDeptId === dept.id ? (
                      <>
                        <input
                          type="text"
                          value={editingDeptName}
                          onChange={(e) => setEditingDeptName(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleRenameDept(dept.id)}
                          className="block w-full max-w-xs rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                          autoFocus
                        />
                        <button
                          onClick={() => handleRenameDept(dept.id)}
                          className="rounded p-1 text-green-600 hover:bg-green-50"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setEditingDeptId(null)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="text-sm text-gray-900">{dept.name}</span>
                        <button
                          onClick={() => { setEditingDeptId(dept.id); setEditingDeptName(dept.name) }}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteDept(dept.id)}
                          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                ))}

                {/* Add department inline */}
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={newDeptName}
                    onChange={(e) => setNewDeptName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateDept()}
                    placeholder={t('settings.departments.namePlaceholder')}
                    className="block w-full max-w-xs rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleCreateDept}
                    disabled={!newDeptName.trim()}
                    className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    {t('settings.departments.addDepartment')}
                  </button>
                </div>
                {deptMessage && (
                  <p className={`text-sm ${deptMessage.type === 'error' ? 'text-red-600' : 'text-green-600'}`}>
                    {deptMessage.text}
                  </p>
                )}
              </div>

              {/* Service assignment table */}
              {(deptsData?.departments?.length ?? 0) > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-gray-900">{t('settings.departments.serviceAssignment')}</h3>
                  <p className="mt-1 text-sm text-gray-500">{t('settings.departments.serviceAssignmentDescription')}</p>

                  {loadingServices ? (
                    <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {t('common.loading')}
                    </div>
                  ) : (servicesData?.clockodoServices?.length ?? 0) === 0 ? (
                    <p className="mt-4 text-sm text-gray-500">{t('settings.departments.noServices')}</p>
                  ) : (
                    <div className="mt-3">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left">
                            <th className="pb-2 font-medium text-gray-700">{t('settings.departments.service')}</th>
                            <th className="pb-2 font-medium text-gray-700">{t('settings.departments.department')}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {servicesData.clockodoServices.map((service: { id: string; name: string }) => (
                            <tr key={service.id} className="border-b last:border-0">
                              <td className="py-2 text-gray-900">{service.name}</td>
                              <td className="py-2">
                                <select
                                  value={serviceAssignments[service.id] || ''}
                                  onChange={(e) => setServiceAssignments(prev => ({ ...prev, [service.id]: e.target.value }))}
                                  className="block w-full max-w-xs rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                >
                                  <option value="">{t('settings.departments.unassigned')}</option>
                                  {deptsData.departments.map((dept: { id: string; name: string }) => (
                                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                                  ))}
                                </select>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="mt-3 flex items-center gap-3">
                        <button
                          onClick={handleSaveAssignments}
                          disabled={savingMappings}
                          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {savingMappings ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                          {t('settings.departments.saveAssignments')}
                        </button>
                        {assignmentMessage && (
                          <span className={`text-sm ${assignmentMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                            {assignmentMessage.text}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* User Costs tab */}
          {ttSubTab === 'costs' && isTimeTrackingConfigured && (
            <div className="mt-4">
              <p className="text-sm text-gray-500">{t('settings.departments.userCostDescription')}</p>
              {loadingClockodoUsers ? (
                <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading users...
                </div>
              ) : (clockodoUsersData?.clockodoUsers?.length ?? 0) === 0 ? (
                <p className="mt-4 text-sm text-gray-500">{t('settings.departments.noServices')}</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs font-medium text-gray-500">
                        <th className="pb-2">{t('settings.departments.userName')}</th>
                        <th className="pb-2 px-2">{t('settings.departments.ftePercentage')}</th>
                        <th className="pb-2 px-2">{t('settings.departments.monthlyIncome')}</th>
                        <th className="pb-2">{t('settings.departments.defaultDepartment')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clockodoUsersData.clockodoUsers.map((u: { id: string; name: string }) => {
                        const profile = costProfiles[u.id] || { ftePercentage: 100, monthlyIncome: '0', defaultDepartmentId: '' }
                        return (
                          <tr key={u.id} className="border-b last:border-0">
                            <td className="py-2 text-gray-900">{u.name}</td>
                            <td className="py-2 px-2">
                              <input
                                type="number"
                                min={0}
                                max={100}
                                value={profile.ftePercentage}
                                onChange={(e) => setCostProfiles(prev => ({
                                  ...prev,
                                  [u.id]: { ...profile, ftePercentage: parseInt(e.target.value) || 0 },
                                }))}
                                className="w-20 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                            </td>
                            <td className="py-2 px-2">
                              <input
                                type="number"
                                min={0}
                                step="100"
                                value={profile.monthlyIncome}
                                onChange={(e) => setCostProfiles(prev => ({
                                  ...prev,
                                  [u.id]: { ...profile, monthlyIncome: e.target.value },
                                }))}
                                className="w-28 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                            </td>
                            <td className="py-2">
                              <select
                                value={profile.defaultDepartmentId}
                                onChange={(e) => setCostProfiles(prev => ({
                                  ...prev,
                                  [u.id]: { ...profile, defaultDepartmentId: e.target.value },
                                }))}
                                className="block w-full max-w-xs rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              >
                                <option value="">{t('settings.departments.none')}</option>
                                {deptsData?.departments?.map((dept: { id: string; name: string }) => (
                                  <option key={dept.id} value={dept.id}>{dept.name}</option>
                                ))}
                              </select>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  <div className="mt-3 flex items-center gap-3">
                    <button
                      onClick={handleSaveCostProfiles}
                      disabled={savingCostProfiles}
                      className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {savingCostProfiles ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      {t('settings.departments.saveCostProfiles')}
                    </button>
                    {costProfileMessage && (
                      <span className={`text-sm ${costProfileMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                        {costProfileMessage.text}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Projects tab */}
          {ttSubTab === 'projects' && isTimeTrackingConfigured && (
            <div className="mt-4 space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-900">{t('settings.timeTracking.projectTemplates')}</h3>
                <p className="mt-1 text-xs text-gray-500">{t('settings.timeTracking.projectTemplatesDescription')}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('settings.timeTracking.maintenanceTemplate')}
                </label>
                <input
                  type="text"
                  value={maintenanceTemplate}
                  onChange={(e) => setMaintenanceTemplate(e.target.value)}
                  placeholder={t('settings.timeTracking.maintenanceTemplateDefault')}
                  className="mt-1 block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t('settings.timeTracking.oneoffTemplate')}
                </label>
                <input
                  type="text"
                  value={oneoffTemplate}
                  onChange={(e) => setOneoffTemplate(e.target.value)}
                  placeholder={t('settings.timeTracking.oneoffTemplateDefault')}
                  className="mt-1 block w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">{t('settings.timeTracking.templatePlaceholders')}</p>
                <div className="flex flex-wrap gap-1.5">
                  {['{customer_name}', '{contract_name}', '{item_name}', '{year}', '{ab_number}'].map((ph) => (
                    <span key={ph} className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-mono text-gray-600">
                      {ph}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={async () => {
                    try {
                      await saveProjectTemplates({
                        variables: {
                          maintenanceTemplate,
                          oneoffTemplate,
                        },
                      })
                      setTemplateMessage({ type: 'success', text: t('settings.timeTracking.templateSaved') })
                    } catch {
                      setTemplateMessage({ type: 'error', text: t('settings.timeTracking.templateSaveFailed') })
                    }
                  }}
                  disabled={savingTemplates}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {savingTemplates ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {t('settings.timeTracking.templateSave')}
                </button>
                {templateMessage && (
                  <span className={`text-sm ${templateMessage.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                    {templateMessage.text}
                  </span>
                )}
              </div>
            </div>
          )}
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
