import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { NumberSchemeSettings } from '@/features/invoices/NumberSchemeSettings'
import { StornoNumberSchemeSettings } from '@/features/invoices/StornoNumberSchemeSettings'
import { OfferNumberSchemeSettings } from '@/features/offers/OfferNumberSchemeSettings'
import { ABNumberSchemeSettings } from '@/features/contracts/ABNumberSchemeSettings'
import { SettingsCrossLink } from './SettingsCrossLink'

export function NumberingSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/storno')) return 'storno'
    if (location.pathname.includes('/offers')) return 'offers'
    if (location.pathname.includes('/order-confirmations')) return 'order-confirmations'
    return 'invoices'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'storno':
        navigate('/settings/numbering/storno')
        break
      case 'offers':
        navigate('/settings/numbering/offers')
        break
      case 'order-confirmations':
        navigate('/settings/numbering/order-confirmations')
        break
      default:
        navigate('/settings/numbering')
    }
  }

  return (
    <div>
      <SettingsCrossLink
        text={t('settings.crossLink.emailTemplatesHint')}
        to="/settings/email-templates"
        linkText={t('settings.crossLink.emailTemplates')}
      />
      <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
        <TabsList className="mb-4">
          <TabsTrigger value="invoices">{t('settings.numbering.invoices')}</TabsTrigger>
          <TabsTrigger value="storno">{t('settings.numbering.creditNotes')}</TabsTrigger>
          <TabsTrigger value="offers">{t('settings.numbering.offers')}</TabsTrigger>
          <TabsTrigger value="order-confirmations">{t('settings.numbering.orderConfirmations')}</TabsTrigger>
        </TabsList>

        <TabsContent value="invoices">
          <NumberSchemeSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="storno">
          <StornoNumberSchemeSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="offers">
          <OfferNumberSchemeSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="order-confirmations">
          <ABNumberSchemeSettings showHeader={false} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
