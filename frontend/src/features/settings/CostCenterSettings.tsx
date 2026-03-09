import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Plus, Pencil, Trash2, Check, X, Loader2 } from 'lucide-react'

const COST_CENTERS_QUERY = gql`
  query CostCenters { costCenters { id code name isActive } }
`
const CREATE_COST_CENTER = gql`
  mutation CreateCostCenter($input: CreateCostCenterInput!) {
    createCostCenter(input: $input) { success error costCenter { id code name isActive } }
  }
`
const UPDATE_COST_CENTER = gql`
  mutation UpdateCostCenter($input: UpdateCostCenterInput!) {
    updateCostCenter(input: $input) { success error costCenter { id code name isActive } }
  }
`
const DELETE_COST_CENTER = gql`
  mutation DeleteCostCenter($id: ID!, $force: Boolean!) {
    deleteCostCenter(id: $id, force: $force) { success error inUse usageCount }
  }
`

interface CostCenter { id: string; code: string; name: string; isActive: boolean }

export function CostCenterSettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(COST_CENTERS_QUERY)
  const [createCostCenter, { loading: creating }] = useMutation(CREATE_COST_CENTER)
  const [updateCostCenter] = useMutation(UPDATE_COST_CENTER)
  const [deleteCostCenter] = useMutation(DELETE_COST_CENTER)

  const [showCreate, setShowCreate] = useState(false)
  const [newCode, setNewCode] = useState('')
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editCode, setEditCode] = useState('')
  const [editName, setEditName] = useState('')
  const [editActive, setEditActive] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const costCenters: CostCenter[] = data?.costCenters || []

  const flash = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const handleCreate = async () => {
    if (!newCode.trim() || !newName.trim()) return
    const r = await createCostCenter({ variables: { input: { code: newCode.trim(), name: newName.trim() } } })
    if (r.data?.createCostCenter?.success) {
      setNewCode(''); setNewName(''); setShowCreate(false)
      flash('success', t('costCenters.saved')); refetch()
    } else flash('error', r.data?.createCostCenter?.error || 'Error')
  }

  const handleUpdate = async (id: string) => {
    const r = await updateCostCenter({ variables: { input: { id, code: editCode.trim(), name: editName.trim(), isActive: editActive } } })
    if (r.data?.updateCostCenter?.success) {
      setEditingId(null); flash('success', t('costCenters.saved')); refetch()
    } else flash('error', r.data?.updateCostCenter?.error || 'Error')
  }

  const handleDelete = async (id: string) => {
    const r = await deleteCostCenter({ variables: { id, force: false } })
    const d = r.data?.deleteCostCenter
    if (d?.success) { flash('success', t('costCenters.deleted')); refetch() }
    else if (d?.inUse) {
      if (confirm(t('costCenters.deleteInUse', { count: d.usageCount }))) {
        const r2 = await deleteCostCenter({ variables: { id, force: true } })
        if (r2.data?.deleteCostCenter?.success) { flash('success', t('costCenters.deleted')); refetch() }
      }
    } else flash('error', d?.error || 'Error')
  }

  const startEdit = (cc: CostCenter) => { setEditingId(cc.id); setEditCode(cc.code); setEditName(cc.name); setEditActive(cc.isActive) }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{t('costCenters.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('costCenters.settingsDescription')}</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> {t('costCenters.create')}
        </button>
      </div>

      {message && <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>{message.text}</p>}

      {showCreate && (
        <div className="mt-4 flex items-end gap-2 rounded-md border border-blue-200 bg-blue-50 p-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">{t('costCenters.code')}</label>
            <input type="text" value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder={t('costCenters.codePlaceholder')} className="mt-1 block w-32 rounded-md border border-gray-300 px-2 py-1.5 text-sm" autoFocus />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-700">{t('costCenters.name')}</label>
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleCreate()} placeholder={t('costCenters.namePlaceholder')} className="mt-1 block w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm" />
          </div>
          <button onClick={handleCreate} disabled={creating || !newCode.trim() || !newName.trim()} className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {creating && <Loader2 className="h-3 w-3 animate-spin" />} <Check className="h-4 w-4" />
          </button>
          <button onClick={() => { setShowCreate(false); setNewCode(''); setNewName('') }} className="rounded p-1.5 text-gray-400 hover:bg-gray-100"><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="mt-4">
        {costCenters.length === 0 ? (
          <p className="text-sm text-gray-500">{t('costCenters.noCostCenters')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-2 font-medium text-gray-700">{t('costCenters.code')}</th>
                <th className="pb-2 font-medium text-gray-700">{t('costCenters.name')}</th>
                <th className="pb-2 font-medium text-gray-700">{t('costCenters.status')}</th>
                <th className="pb-2 w-24"></th>
              </tr>
            </thead>
            <tbody>
              {costCenters.map((cc) => (
                <tr key={cc.id} className="border-b last:border-0">
                  {editingId === cc.id ? (
                    <>
                      <td className="py-2 pr-2"><input type="text" value={editCode} onChange={(e) => setEditCode(e.target.value)} className="w-full rounded border border-gray-300 px-2 py-1 text-sm" /></td>
                      <td className="py-2 pr-2"><input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleUpdate(cc.id)} className="w-full rounded border border-gray-300 px-2 py-1 text-sm" /></td>
                      <td className="py-2 pr-2">
                        <label className="flex items-center gap-2">
                          <input type="checkbox" checked={editActive} onChange={(e) => setEditActive(e.target.checked)} className="h-4 w-4 rounded border-gray-300 text-blue-600" />
                          <span className="text-sm">{editActive ? t('costCenters.active') : t('costCenters.inactive')}</span>
                        </label>
                      </td>
                      <td className="py-2 text-right">
                        <button onClick={() => handleUpdate(cc.id)} className="rounded p-1 text-green-600 hover:bg-green-50"><Check className="h-4 w-4" /></button>
                        <button onClick={() => setEditingId(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100"><X className="h-4 w-4" /></button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="py-2 pr-2 font-mono text-gray-900">{cc.code}</td>
                      <td className="py-2 pr-2 text-gray-900">{cc.name}</td>
                      <td className="py-2 pr-2">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cc.isActive ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {cc.isActive ? t('costCenters.active') : t('costCenters.inactive')}
                        </span>
                      </td>
                      <td className="py-2 text-right">
                        <button onClick={() => startEdit(cc)} className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"><Pencil className="h-3.5 w-3.5" /></button>
                        <button onClick={() => handleDelete(cc.id)} className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
