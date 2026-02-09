import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useAuth } from '@/lib/auth'
import { Settings } from './Settings'
import { UserManagement } from './UserManagement'
import { InvoiceSettingsTabs } from './InvoiceSettingsTabs'

export function SettingsLayout() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()

  // Determine active tab from URL
  const getActiveTab = () => {
    if (location.pathname.startsWith('/settings/users')) return 'users'
    if (location.pathname.startsWith('/settings/invoices')) return 'invoices'
    return 'general'
  }

  const activeTab = getActiveTab()

  const handleTabChange = (value: string) => {
    switch (value) {
      case 'users':
        navigate('/settings/users')
        break
      case 'invoices':
        navigate('/settings/invoices')
        break
      default:
        navigate('/settings')
    }
  }

  const canViewUsers = hasPermission('users', 'read')
  const canViewInvoiceSettings = hasPermission('invoices', 'settings')

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('nav.settings')}</h1>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-6">
        <TabsList className="mb-6">
          <TabsTrigger value="general">{t('settings.tabs.general')}</TabsTrigger>
          {canViewUsers && (
            <TabsTrigger value="users">{t('settings.tabs.users')}</TabsTrigger>
          )}
          {canViewInvoiceSettings && (
            <TabsTrigger value="invoices">{t('settings.tabs.invoices')}</TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="general">
          <Settings showHeader={false} />
        </TabsContent>

        {canViewUsers && (
          <TabsContent value="users">
            <UserManagement />
          </TabsContent>
        )}

        {canViewInvoiceSettings && (
          <TabsContent value="invoices">
            <InvoiceSettingsTabs />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
