import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Trash2 } from 'lucide-react'

const COST_CENTERS_QUERY = gql`
  query CostCentersForSplit { costCenters(isActive: true) { id code name } }
`

const TRANSACTION_SPLITS_QUERY = gql`
  query TransactionSplits($transactionId: Int!) {
    transactionCostCenterSplits(transactionId: $transactionId) {
      id costCenter { id code name } amount isManual
    }
  }
`

const SPLIT_TRANSACTION = gql`
  mutation SplitTransaction($transactionId: Int!, $splits: [ManualSplitInput!]!) {
    splitTransactionCostCenters(transactionId: $transactionId, splits: $splits) {
      success error
      splits { id costCenter { id code name } amount isManual }
    }
  }
`

interface Props {
  transactionId: number
  transactionAmount: number
  onClose?: () => void
}

interface SplitRow {
  costCenterId: string
  amount: string
}

export function TransactionSplitEditor({ transactionId, transactionAmount, onClose: _onClose }: Props) {
  const { t } = useTranslation()
  const absAmount = Math.abs(transactionAmount)
  const { data: ccData } = useQuery(COST_CENTERS_QUERY)
  const { data: splitsData, refetch } = useQuery(TRANSACTION_SPLITS_QUERY, {
    variables: { transactionId },
  })
  const [splitTransaction, { loading }] = useMutation(SPLIT_TRANSACTION)
  const [rows, setRows] = useState<SplitRow[]>([{ costCenterId: '', amount: '' }])
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)

  const costCenters = ccData?.costCenters || []
  const existingSplits = splitsData?.transactionCostCenterSplits || []

  const totalEntered = rows.reduce((s, r) => s + (parseFloat(r.amount) || 0), 0)
  const remaining = absAmount - totalEntered

  const handleSave = async () => {
    setError('')
    if (rows.some(r => !r.costCenterId || !r.amount)) {
      setError(t('splitRules.errorIncompleteAllocation'))
      return
    }
    if (Math.abs(remaining) > 0.01) {
      setError(t('splitEditor.errorMustMatchTotal', { amount: absAmount.toFixed(2) }))
      return
    }

    const { data: res } = await splitTransaction({
      variables: {
        transactionId,
        splits: rows.map(r => ({ costCenterId: r.costCenterId, amount: parseFloat(r.amount) })),
      },
    })
    if (!res.splitTransactionCostCenters.success) {
      setError(res.splitTransactionCostCenters.error)
      return
    }
    setEditing(false)
    refetch()
  }

  const startEdit = () => {
    if (existingSplits.length > 0) {
      setRows(existingSplits.map((s: any) => ({
        costCenterId: s.costCenter.id,
        amount: String(s.amount),
      })))
    } else {
      setRows([{ costCenterId: '', amount: String(absAmount) }])
    }
    setEditing(true)
    setError('')
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium">{t('splitEditor.title')}</h4>

      {existingSplits.length > 0 && !editing && (
        <div className="space-y-1">
          {existingSplits.map((s: any) => (
            <div key={s.id} className="flex justify-between text-sm">
              <span>{s.costCenter.code} – {s.costCenter.name}</span>
              <span>{parseFloat(s.amount).toFixed(2)} €{s.isManual ? ' (manual)' : ''}</span>
            </div>
          ))}
        </div>
      )}

      {!editing ? (
        <button onClick={startEdit} className="text-sm text-primary hover:underline">
          {existingSplits.length > 0 ? t('splitEditor.editSplits') : t('splitEditor.addSplit')}
        </button>
      ) : (
        <div className="space-y-2">
          {rows.map((row, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <select
                className="flex-1 rounded-md border px-3 py-2 text-sm"
                value={row.costCenterId}
                onChange={e => setRows(r => r.map((rr, i) => i === idx ? { ...rr, costCenterId: e.target.value } : rr))}
              >
                <option value="">{t('splitRules.selectCostCenter')}</option>
                {costCenters.map((cc: any) => (
                  <option key={cc.id} value={cc.id}>{cc.code} – {cc.name}</option>
                ))}
              </select>
              <input
                type="number"
                step="0.01"
                className="w-28 rounded-md border px-3 py-2 text-sm"
                placeholder={t('splitEditor.amount')}
                value={row.amount}
                onChange={e => setRows(r => r.map((rr, i) => i === idx ? { ...rr, amount: e.target.value } : rr))}
              />
              {rows.length > 1 && (
                <button onClick={() => setRows(r => r.filter((_, i) => i !== idx))} className="text-destructive">
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
          <button
            onClick={() => setRows(r => [...r, { costCenterId: '', amount: remaining > 0 ? remaining.toFixed(2) : '' }])}
            className="text-sm text-primary hover:underline"
          >
            + {t('splitRules.addAllocation')}
          </button>
          <p className={`text-sm ${Math.abs(remaining) > 0.01 ? 'text-destructive' : 'text-muted-foreground'}`}>
            {t('splitEditor.remaining')}: {remaining.toFixed(2)} € / {absAmount.toFixed(2)} €
          </p>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('common.save')}
            </button>
            <button onClick={() => setEditing(false)} className="rounded-md border px-3 py-2 text-sm hover:bg-muted">
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
