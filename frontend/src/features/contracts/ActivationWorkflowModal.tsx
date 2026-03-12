import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { ClockodoActivationDialog } from './ClockodoActivationDialog'

const ACTIVATION_CHECKLIST_QUERY = gql`
  query ActivationChecklistSettings {
    activationChecklistSettings {
      availableFields
      requiredFields
    }
  }
`

const M365_CHECK_QUERY = gql`
  query M365Check {
    m365Settings {
      isConfigured
    }
  }
`

const CUSTOMER_BILLING_EMAILS_QUERY = gql`
  query CustomerBillingEmails($customerId: ID!) {
    customer(id: $customerId) {
      id
      billingEmails
    }
  }
`

const TRANSITION_CONTRACT_STATUS_MUTATION = gql`
  mutation TransitionContractStatus(
    $contractId: ID!
    $newStatus: String!
    $activationOptions: ActivationOptionsInput
  ) {
    transitionContractStatus(
      contractId: $contractId
      newStatus: $newStatus
      activationOptions: $activationOptions
    ) {
      success
      error
      contract {
        id
        status
      }
    }
  }
`

// Map backend field names to contract object keys
const FIELD_KEY_MAP: Record<string, keyof ActivationContract> = {
  po_number: 'poNumber',
  order_confirmation_number: 'orderConfirmationNumber',
  netsuite_sales_order_number: 'netsuiteSalesOrderNumber',
  netsuite_contract_number: 'netsuiteContractNumber',
  netsuite_url: 'netsuiteUrl',
}

interface ActivationContract {
  status: string
  customer: { id: string; name: string }
  poNumber?: string | null
  orderConfirmationNumber?: string | null
  netsuiteSalesOrderNumber?: string | null
  netsuiteContractNumber?: string | null
  netsuiteUrl?: string | null
}

interface ActivationWorkflowModalProps {
  contractId: string
  contract: ActivationContract
  onClose: () => void
  onSuccess: () => void
}

type ModalState = 'options' | 'clockodo' | 'activating' | 'success'

export function ActivationWorkflowModal({
  contractId,
  contract,
  onClose,
  onSuccess,
}: ActivationWorkflowModalProps) {
  const { t } = useTranslation()
  const [state, setState] = useState<ModalState>('options')
  const [sendAB, setSendAB] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [abSent, setAbSent] = useState(false)

  const { data: checklistData } = useQuery(ACTIVATION_CHECKLIST_QUERY)
  const { data: m365Data } = useQuery(M365_CHECK_QUERY)
  const { data: billingData } = useQuery(CUSTOMER_BILLING_EMAILS_QUERY, {
    variables: { customerId: contract.customer.id },
  })

  const [transitionStatus, { loading }] = useMutation(TRANSITION_CONTRACT_STATUS_MUTATION)

  const m365Configured = m365Data?.m365Settings?.isConfigured === true
  const hasBillingEmails = (billingData?.customer?.billingEmails?.length ?? 0) > 0

  // AB can only be sent if M365 is configured AND customer has billing emails
  const canSendAB = m365Configured && hasBillingEmails
  const abDisabledReason = !m365Configured
    ? t('activation.abDisabledNoM365')
    : !hasBillingEmails
      ? t('activation.abDisabledNoEmails')
      : null

  // Determine missing required fields
  const missingFields: string[] = []
  if (checklistData?.activationChecklistSettings) {
    const requiredFields: string[] = checklistData.activationChecklistSettings.requiredFields || []
    for (const field of requiredFields) {
      const key = FIELD_KEY_MAP[field]
      if (key && !contract[key]) {
        missingFields.push(field)
      }
    }
  }

  const canActivate = missingFields.length === 0

  const doActivation = async () => {
    setError(null)
    setState('activating')
    try {
      const result = await transitionStatus({
        variables: {
          contractId,
          newStatus: 'active',
          activationOptions: {
            sendOrderConfirmation: sendAB && canSendAB,
          },
        },
      })
      if (!result.data?.transitionContractStatus.success) {
        setError(result.data?.transitionContractStatus.error || 'Activation failed')
        setState('options')
        return
      }
      setAbSent(sendAB && canSendAB)
      setState('success')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setState('options')
    }
  }

  const handleConfirm = () => {
    // Show Clockodo dialog first if applicable
    setState('clockodo')
  }

  const proceedAfterClockodo = () => {
    doActivation()
  }

  if (state === 'clockodo') {
    return (
      <ClockodoActivationDialog
        contractId={contractId}
        open={true}
        onClose={() => setState('options')}
        onComplete={proceedAfterClockodo}
      />
    )
  }

  return (
    <Dialog open={true} onOpenChange={(open) => !open && (state === 'success' ? onSuccess() : onClose())}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{t('activation.title')}</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {state === 'options' && (
          <div className="space-y-4 py-2">
            {/* Activation checklist warnings */}
            {missingFields.length > 0 && (
              <div className="rounded border border-amber-200 bg-amber-50 p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      {t('settings.activationChecklist.missingFieldsTitle')}
                    </p>
                    <p className="mt-1 text-sm text-amber-700">
                      {t('settings.activationChecklist.missingFieldsDescription')}
                    </p>
                    <ul className="mt-2 list-inside list-disc text-sm text-amber-700">
                      {missingFields.map((field) => (
                        <li key={field}>{t(`settings.activationChecklist.fields.${field}`)}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Confirmation text */}
            <p className="text-sm text-muted-foreground">
              {t('activation.confirmMessage')}
            </p>

            {/* Post-activation options */}
            <div className="rounded border p-3 space-y-3">
              <p className="text-sm font-medium">{t('activation.optionsTitle')}</p>
              <div className="flex items-start gap-2">
                <Checkbox
                  id="send-ab"
                  checked={canSendAB ? sendAB : false}
                  onCheckedChange={(c) => setSendAB(!!c)}
                  disabled={!canSendAB}
                />
                <div className="space-y-1">
                  <Label htmlFor="send-ab" className={!canSendAB ? 'text-muted-foreground' : ''}>
                    {t('activation.sendOrderConfirmation')}
                  </Label>
                  {abDisabledReason && (
                    <p className="text-xs text-muted-foreground">{abDisabledReason}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {state === 'activating' && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-3 text-muted-foreground">{t('activation.activating')}</span>
          </div>
        )}

        {state === 'success' && (
          <div className="space-y-3 py-4">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle2 className="h-5 w-5" />
              <p className="font-medium">{t('activation.success')}</p>
            </div>
            {abSent && (
              <p className="text-sm text-muted-foreground">
                {t('activation.abBeingSent')}
              </p>
            )}
          </div>
        )}

        <DialogFooter>
          {state === 'options' && (
            <>
              <Button variant="outline" onClick={onClose}>
                {t('contracts.actions.cancel')}
              </Button>
              <Button onClick={handleConfirm} disabled={!canActivate || loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('contracts.statusTransition.activate')}
              </Button>
            </>
          )}
          {state === 'success' && (
            <Button onClick={onSuccess}>
              {t('common.close')}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
