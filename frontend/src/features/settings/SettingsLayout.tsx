import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { User, Settings, Puzzle, Users, FileUp, Landmark } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { UserSettings } from './UserSettings'
import { TeamSettingsTabs } from './TeamSettingsTabs'
import { InvoiceSettingsTabs } from './InvoiceSettingsTabs'
import { GeneralSettingsTabs } from './GeneralSettingsTabs'
import { IntegrationSettingsTabs } from './IntegrationSettingsTabs'
import { BankingSettings } from './BankingSettings'

export function SettingsLayout() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()

  // Determine active tab from URL
  const getActiveTab = () => {
    if (location.pathname.startsWith('/settings/team')) return 'team'
    if (location.pathname.startsWith('/settings/invoices')) return 'invoices'
    if (location.pathname.startsWith('/settings/banking')) return 'banking'
    if (location.pathname.startsWith('/settings/integrations')) return 'integrations'
    if (location.pathname.startsWith('/settings/general')) return 'general'
    return 'user'
  }

  const activeTab = getActiveTab()

  const handleTabChange = (value: string) => {
    switch (value) {
      case 'general':
        navigate('/settings/general')
        break
      case 'integrations':
        navigate('/settings/integrations')
        break
      case 'team':
        navigate('/settings/team')
        break
      case 'invoices':
        navigate('/settings/invoices')
        break
      case 'banking':
        navigate('/settings/banking')
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
          <TabsTrigger value="user"><User className="mr-1.5 h-4 w-4" />{t('settings.tabs.user')}</TabsTrigger>
          <TabsTrigger value="general"><Settings className="mr-1.5 h-4 w-4" />{t('settings.tabs.general')}</TabsTrigger>
          <TabsTrigger value="integrations"><Puzzle className="mr-1.5 h-4 w-4" />{t('settings.tabs.integrations')}</TabsTrigger>
          {canViewUsers && (
            <TabsTrigger value="team"><Users className="mr-1.5 h-4 w-4" />{t('settings.tabs.team')}</TabsTrigger>
          )}
          {canViewInvoiceSettings && (
            <TabsTrigger value="invoices"><FileUp className="mr-1.5 h-4 w-4" />{t('settings.tabs.invoices')}</TabsTrigger>
          )}
          <TabsTrigger value="banking"><Landmark className="mr-1.5 h-4 w-4" />{t('settings.tabs.banking')}</TabsTrigger>
        </TabsList>

        <TabsContent value="user">
          <UserSettings />
        </TabsContent>

        <TabsContent value="general">
          <GeneralSettingsTabs />
        </TabsContent>

        <TabsContent value="integrations">
          <IntegrationSettingsTabs />
        </TabsContent>

        {canViewUsers && (
          <TabsContent value="team">
            <TeamSettingsTabs />
          </TabsContent>
        )}

        {canViewInvoiceSettings && (
          <TabsContent value="invoices">
            <InvoiceSettingsTabs />
          </TabsContent>
        )}

        <TabsContent value="banking">
          <BankingSettings />
        </TabsContent>
      </Tabs>
    </div>
  )
}
