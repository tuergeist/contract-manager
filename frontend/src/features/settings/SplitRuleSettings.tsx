import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-react'

const SPLIT_RULES_QUERY = gql`
  query SplitRules {
    costCenterSplitRules {
      id bookingTextPattern priority isActive
      counterparty { id name }
      allocations { id costCenter { id code name } percentage fixedAmount }
    }
    costCenters { id code name isActive }
    counterparties(pageSize: 1000) { items { id name } }
  }
`

const CREATE_SPLIT_RULE = gql`
  mutation CreateSplitRule($input: CreateSplitRuleInput!) {
    createCostCenterSplitRule(input: $input) {
      success error
      rule { id counterparty { id name } bookingTextPattern priority isActive allocations { id costCenter { id code name } percentage fixedAmount } }
    }
  }
`

const UPDATE_SPLIT_RULE = gql`
  mutation UpdateSplitRule($input: UpdateSplitRuleInput!) {
    updateCostCenterSplitRule(input: $input) {
      success error
      rule { id counterparty { id name } bookingTextPattern priority isActive allocations { id costCenter { id code name } percentage fixedAmount } }
    }
  }
`

const DELETE_SPLIT_RULE = gql`
  mutation DeleteSplitRule($id: ID!) {
    deleteCostCenterSplitRule(id: $id) { success error }
  }
`

interface Allocation {
  costCenterId: string
  percentage: string
}

interface RuleForm {
  counterpartyId: string
  bookingTextPattern: string
  priority: string
  allocations: Allocation[]
}

const emptyForm: RuleForm = {
  counterpartyId: '',
  bookingTextPattern: '',
  priority: '0',
  allocations: [{ costCenterId: '', percentage: '' }],
}

export function SplitRuleSettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(SPLIT_RULES_QUERY)
  const [createRule, { loading: creating }] = useMutation(CREATE_SPLIT_RULE)
  const [updateRule, { loading: updating }] = useMutation(UPDATE_SPLIT_RULE)
  const [deleteRule] = useMutation(DELETE_SPLIT_RULE)
  const [form, setForm] = useState<RuleForm>(emptyForm)
  const [editId, setEditId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')

  const rules = data?.costCenterSplitRules || []
  const costCenters = (data?.costCenters || []).filter((cc: any) => cc.isActive)
  const counterparties = data?.counterparties?.items || []

  const totalPct = form.allocations.reduce((sum, a) => sum + (parseFloat(a.percentage) || 0), 0)

  const handleSubmit = async () => {
    setError('')
    if (!form.counterpartyId && !form.bookingTextPattern) {
      setError(t('splitRules.errorNeedMatcher'))
      return
    }
    if (form.allocations.some(a => !a.costCenterId || !a.percentage)) {
      setError(t('splitRules.errorIncompleteAllocation'))
      return
    }
    if (Math.abs(totalPct - 100) > 0.01) {
      setError(t('splitRules.errorMustTotal100'))
      return
    }

    const input: any = {
      counterpartyId: form.counterpartyId || null,
      bookingTextPattern: form.bookingTextPattern || null,
      priority: parseInt(form.priority) || 0,
      isActive: true,
      allocations: form.allocations.map(a => ({
        costCenterId: a.costCenterId,
        percentage: parseFloat(a.percentage),
      })),
    }

    if (editId) {
      input.id = editId
      const { data: res } = await updateRule({ variables: { input } })
      if (!res.updateCostCenterSplitRule.success) {
        setError(res.updateCostCenterSplitRule.error)
        return
      }
    } else {
      const { data: res } = await createRule({ variables: { input } })
      if (!res.createCostCenterSplitRule.success) {
        setError(res.createCostCenterSplitRule.error)
        return
      }
    }
    setShowForm(false)
    setEditId(null)
    setForm(emptyForm)
    refetch()
  }

  const handleEdit = (rule: any) => {
    setForm({
      counterpartyId: rule.counterparty?.id || '',
      bookingTextPattern: rule.bookingTextPattern || '',
      priority: String(rule.priority),
      allocations: rule.allocations.map((a: any) => ({
        costCenterId: a.costCenter.id,
        percentage: a.percentage != null ? String(a.percentage) : '',
      })),
    })
    setEditId(rule.id)
    setShowForm(true)
    setError('')
  }

  const handleDelete = async (id: string) => {
    if (!confirm(t('splitRules.deleteConfirm'))) return
    await deleteRule({ variables: { id } })
    refetch()
  }

  const addAllocation = () => {
    setForm(f => ({ ...f, allocations: [...f.allocations, { costCenterId: '', percentage: '' }] }))
  }

  const removeAllocation = (idx: number) => {
    setForm(f => ({ ...f, allocations: f.allocations.filter((_, i) => i !== idx) }))
  }

  const updateAllocation = (idx: number, field: keyof Allocation, value: string) => {
    setForm(f => ({
      ...f,
      allocations: f.allocations.map((a, i) => i === idx ? { ...a, [field]: value } : a),
    }))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">{t('splitRules.title')}</h3>
          <p className="text-sm text-muted-foreground">{t('splitRules.description')}</p>
        </div>
        <button
          onClick={() => { setForm(emptyForm); setEditId(null); setShowForm(true); setError('') }}
          className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> {t('splitRules.create')}
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg border p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">{t('splitRules.counterparty')}</label>
              <select
                className="w-full mt-1 rounded-md border px-3 py-2 text-sm"
                value={form.counterpartyId}
                onChange={e => setForm(f => ({ ...f, counterpartyId: e.target.value }))}
              >
                <option value="">{t('splitRules.noCounterparty')}</option>
                {counterparties.map((cp: any) => (
                  <option key={cp.id} value={cp.id}>{cp.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">{t('splitRules.bookingPattern')}</label>
              <input
                className="w-full mt-1 rounded-md border px-3 py-2 text-sm"
                placeholder={t('splitRules.bookingPatternPlaceholder')}
                value={form.bookingTextPattern}
                onChange={e => setForm(f => ({ ...f, bookingTextPattern: e.target.value }))}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">{t('splitRules.priority')}</label>
            <input
              type="number"
              className="w-24 mt-1 rounded-md border px-3 py-2 text-sm"
              value={form.priority}
              onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
            />
          </div>

          <div>
            <label className="text-sm font-medium">{t('splitRules.allocations')}</label>
            <div className="space-y-2 mt-1">
              {form.allocations.map((alloc, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <select
                    className="flex-1 rounded-md border px-3 py-2 text-sm"
                    value={alloc.costCenterId}
                    onChange={e => updateAllocation(idx, 'costCenterId', e.target.value)}
                  >
                    <option value="">{t('splitRules.selectCostCenter')}</option>
                    {costCenters.map((cc: any) => (
                      <option key={cc.id} value={cc.id}>{cc.code} – {cc.name}</option>
                    ))}
                  </select>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      className="w-20 rounded-md border px-3 py-2 text-sm"
                      placeholder="%"
                      value={alloc.percentage}
                      onChange={e => updateAllocation(idx, 'percentage', e.target.value)}
                    />
                    <span className="text-sm">%</span>
                  </div>
                  {form.allocations.length > 1 && (
                    <button onClick={() => removeAllocation(idx)} className="text-destructive hover:text-destructive/80">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={addAllocation} className="text-sm text-primary hover:underline">
                + {t('splitRules.addAllocation')}
              </button>
            </div>
            <p className={`text-sm mt-1 ${Math.abs(totalPct - 100) > 0.01 ? 'text-destructive' : 'text-muted-foreground'}`}>
              {t('splitRules.totalPercentage')}: {totalPct.toFixed(1)}%
            </p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-2">
            <button
              onClick={handleSubmit}
              disabled={creating || updating}
              className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {(creating || updating) && <Loader2 className="h-4 w-4 animate-spin" />}
              {editId ? t('common.save') : t('common.create')}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditId(null) }}
              className="rounded-md border px-3 py-2 text-sm hover:bg-muted"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Rules list */}
      <div className="space-y-2">
        {rules.length === 0 && !showForm && (
          <p className="text-sm text-muted-foreground">{t('splitRules.noRules')}</p>
        )}
        {rules.map((rule: any) => (
          <div key={rule.id} className="rounded-lg border p-3 flex items-start justify-between">
            <div>
              <div className="font-medium text-sm">
                {rule.counterparty ? rule.counterparty.name : `"${rule.bookingTextPattern}"`}
                <span className="ml-2 text-xs text-muted-foreground">
                  {t('splitRules.priority')}: {rule.priority}
                </span>
                {!rule.isActive && (
                  <span className="ml-2 text-xs text-yellow-600">{t('common.inactive')}</span>
                )}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {rule.allocations.map((a: any) => (
                  <span key={a.id} className="mr-3">
                    {a.costCenter.code}: {a.percentage != null ? `${a.percentage}%` : `${a.fixedAmount} fixed`}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex gap-1">
              <button onClick={() => handleEdit(rule)} className="p-1 hover:bg-muted rounded">
                <Pencil className="h-4 w-4" />
              </button>
              <button onClick={() => handleDelete(rule.id)} className="p-1 hover:bg-muted rounded text-destructive">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
