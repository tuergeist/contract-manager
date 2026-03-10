import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { User, Settings, Puzzle, Users, FileText, Landmark, Hash, Mail, Inbox } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { UserSettings } from './UserSettings'
import { TeamSettingsTabs } from './TeamSettingsTabs'
import { DocumentSettingsTabs } from './DocumentSettingsTabs'
import { NumberingSettingsTabs } from './NumberingSettingsTabs'
import { EmailTemplateSettingsTabs } from './EmailTemplateSettingsTabs'
import { GeneralSettingsTabs } from './GeneralSettingsTabs'
import { IntegrationSettingsTabs } from './IntegrationSettingsTabs'
import { BankingSettings } from './BankingSettings'
import { InvoiceInboxSettings } from './InvoiceInboxSettings'
import { CostCenterSettings } from './CostCenterSettings'
import { SplitRuleSettings } from './SplitRuleSettings'

export function SettingsLayout() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()

  // Determine active tab from URL
  const getActiveTab = () => {
    if (location.pathname.startsWith('/settings/team')) return 'team'
    if (location.pathname.startsWith('/settings/documents')) return 'documents'
    if (location.pathname.startsWith('/settings/invoices')) return 'documents' // backward compat
    if (location.pathname.startsWith('/settings/numbering')) return 'numbering'
    if (location.pathname.startsWith('/settings/email-templates')) return 'email-templates'
    if (location.pathname.startsWith('/settings/invoice-inboxes')) return 'invoice-inboxes'
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
      case 'documents':
        navigate('/settings/documents')
        break
      case 'numbering':
        navigate('/settings/numbering')
        break
      case 'email-templates':
        navigate('/settings/email-templates')
        break
      case 'invoice-inboxes':
        navigate('/settings/invoice-inboxes')
        break
      case 'banking':
        navigate('/settings/banking')
        break
      default:
        navigate('/settings')
    }
  }

  const canViewSettings = hasPermission('settings', 'read')
  const canViewUsers = hasPermission('users', 'read')
  const canViewInvoiceSettings = hasPermission('invoices', 'settings')
  const canViewBanking = hasPermission('banking', 'read')
  const canConfigInboxes = hasPermission('incoming_invoices', 'config')

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('nav.settings')}</h1>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-6">
        <TabsList className="mb-6">
          <TabsTrigger value="user"><User className="mr-1.5 h-4 w-4" />{t('settings.tabs.user')}</TabsTrigger>
          {canViewSettings && (
            <TabsTrigger value="general"><Settings className="mr-1.5 h-4 w-4" />{t('settings.tabs.general')}</TabsTrigger>
          )}
          {canViewSettings && (
            <TabsTrigger value="integrations"><Puzzle className="mr-1.5 h-4 w-4" />{t('settings.tabs.integrations')}</TabsTrigger>
          )}
          {canViewUsers && (
            <TabsTrigger value="team"><Users className="mr-1.5 h-4 w-4" />{t('settings.tabs.team')}</TabsTrigger>
          )}
          {canViewInvoiceSettings && (
            <TabsTrigger value="documents"><FileText className="mr-1.5 h-4 w-4" />{t('settings.tabs.documents')}</TabsTrigger>
          )}
          {canViewInvoiceSettings && (
            <TabsTrigger value="numbering"><Hash className="mr-1.5 h-4 w-4" />{t('settings.tabs.numbering')}</TabsTrigger>
          )}
          {canViewInvoiceSettings && (
            <TabsTrigger value="email-templates"><Mail className="mr-1.5 h-4 w-4" />{t('settings.tabs.emailTemplates')}</TabsTrigger>
          )}
          {canViewBanking && (
            <TabsTrigger value="banking"><Landmark className="mr-1.5 h-4 w-4" />{t('settings.tabs.banking')}</TabsTrigger>
          )}
          {canConfigInboxes && (
            <TabsTrigger value="invoice-inboxes"><Inbox className="mr-1.5 h-4 w-4" />{t('settings.tabs.invoiceInboxes')}</TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="user">
          <UserSettings />
        </TabsContent>

        {canViewSettings && (
          <TabsContent value="general">
            <GeneralSettingsTabs />
          </TabsContent>
        )}

        {canViewSettings && (
          <TabsContent value="integrations">
            <IntegrationSettingsTabs />
          </TabsContent>
        )}

        {canViewUsers && (
          <TabsContent value="team">
            <TeamSettingsTabs />
          </TabsContent>
        )}

        {canViewInvoiceSettings && (
          <TabsContent value="documents">
            <DocumentSettingsTabs />
          </TabsContent>
        )}

        {canViewInvoiceSettings && (
          <TabsContent value="numbering">
            <NumberingSettingsTabs />
          </TabsContent>
        )}

        {canViewInvoiceSettings && (
          <TabsContent value="email-templates">
            <EmailTemplateSettingsTabs />
          </TabsContent>
        )}

        {canViewBanking && (
          <TabsContent value="invoice-inboxes">
            <InvoiceInboxSettings />
          </TabsContent>
        )}

        {canViewBanking && (
          <TabsContent value="banking">
            <div className="space-y-6">
              <BankingSettings />
              <CostCenterSettings />
              <SplitRuleSettings />
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
