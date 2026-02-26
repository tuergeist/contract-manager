import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { RevenueAccountsSettings } from './accounting/RevenueAccountsSettings'
import { TaxAccountsSettings } from './accounting/TaxAccountsSettings'
import { MappingRulesSettings } from './accounting/MappingRulesSettings'
import { DebitorSchemeSettings } from './accounting/DebitorSchemeSettings'

export function AccountingSettings() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/accounting/tax-accounts')) return 'taxAccounts'
    if (location.pathname.includes('/accounting/mappings')) return 'mappings'
    if (location.pathname.includes('/accounting/debitors')) return 'debitors'
    return 'revenueAccounts'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'taxAccounts':
        navigate('/settings/accounting/tax-accounts')
        break
      case 'mappings':
        navigate('/settings/accounting/mappings')
        break
      case 'debitors':
        navigate('/settings/accounting/debitors')
        break
      default:
        navigate('/settings/accounting')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="revenueAccounts">{t('accounting.tabs.revenueAccounts')}</TabsTrigger>
        <TabsTrigger value="taxAccounts">{t('accounting.tabs.taxAccounts')}</TabsTrigger>
        <TabsTrigger value="mappings">{t('accounting.tabs.mappings')}</TabsTrigger>
        <TabsTrigger value="debitors">{t('accounting.tabs.debitors')}</TabsTrigger>
      </TabsList>

      <TabsContent value="revenueAccounts">
        <RevenueAccountsSettings />
      </TabsContent>

      <TabsContent value="taxAccounts">
        <TaxAccountsSettings />
      </TabsContent>

      <TabsContent value="mappings">
        <MappingRulesSettings />
      </TabsContent>

      <TabsContent value="debitors">
        <DebitorSchemeSettings />
      </TabsContent>
    </Tabs>
  )
}
