import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

const ZUGFERD_ENABLED = gql`
  query ZugferdEnabled {
    zugferdEnabled
  }
`

const SET_ZUGFERD_DEFAULT = gql`
  mutation SetZugferdDefault($enabled: Boolean!) {
    setZugferdDefault(enabled: $enabled) {
      success
      error
    }
  }
`

interface ZugferdSettingsProps {
  showHeader?: boolean
}

export function ZugferdSettings({ showHeader = true }: ZugferdSettingsProps) {
  const { t } = useTranslation()

  const { data, loading } = useQuery<{ zugferdEnabled: boolean }>(ZUGFERD_ENABLED)
  const [setZugferdDefault] = useMutation(SET_ZUGFERD_DEFAULT, {
    refetchQueries: [{ query: ZUGFERD_ENABLED }],
  })

  const enabled = data?.zugferdEnabled ?? false

  const handleToggle = async (checked: boolean) => {
    await setZugferdDefault({ variables: { enabled: checked } })
  }

  return (
    <div className="space-y-6">
      {showHeader && (
        <div>
          <h2 className="text-xl font-semibold">{t('invoices.zugferd.title')}</h2>
          <p className="text-sm text-muted-foreground">{t('invoices.zugferd.description')}</p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t('invoices.zugferd.formatTitle')}</CardTitle>
          <CardDescription>{t('invoices.zugferd.formatDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="zugferd-default">{t('invoices.zugferd.defaultLabel')}</Label>
              <p className="text-sm text-muted-foreground">
                {t('invoices.zugferd.defaultDescription')}
              </p>
            </div>
            <Switch
              id="zugferd-default"
              checked={enabled}
              onCheckedChange={handleToggle}
              disabled={loading}
              data-testid="zugferd-default-toggle"
            />
          </div>

          <div className="rounded-lg border bg-muted/50 p-4">
            <h4 className="mb-2 text-sm font-medium">{t('invoices.zugferd.infoTitle')}</h4>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li>- {t('invoices.zugferd.infoPoint1')}</li>
              <li>- {t('invoices.zugferd.infoPoint2')}</li>
              <li>- {t('invoices.zugferd.infoPoint3')}</li>
              <li>- {t('invoices.zugferd.infoPoint4')}</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
