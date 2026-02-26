import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, Pencil, Trash2, Sparkles } from 'lucide-react'

const REVENUE_ACCOUNTS_QUERY = gql`
  query RevenueAccounts {
    revenueAccounts {
      id
      accountNumber
      name
      description
      taxRate
      vatClassification
      isActive
      sortOrder
      mappingCount
    }
  }
`

const CREATE_REVENUE_ACCOUNT = gql`
  mutation CreateRevenueAccount($input: RevenueAccountInput!) {
    createRevenueAccount(input: $input) {
      id
      accountNumber
      name
    }
  }
`

const UPDATE_REVENUE_ACCOUNT = gql`
  mutation UpdateRevenueAccount($id: ID!, $input: RevenueAccountInput!) {
    updateRevenueAccount(id: $id, input: $input) {
      id
      accountNumber
      name
    }
  }
`

const DELETE_REVENUE_ACCOUNT = gql`
  mutation DeleteRevenueAccount($id: ID!) {
    deleteRevenueAccount(id: $id) {
      success
      error
    }
  }
`

const SEED_DEFAULTS = gql`
  mutation SeedDefaultRevenueAccounts {
    seedDefaultRevenueAccounts {
      id
      accountNumber
      name
    }
  }
`

interface RevenueAccount {
  id: number
  accountNumber: string
  name: string
  description: string
  taxRate: string | null
  vatClassification: string
  isActive: boolean
  sortOrder: number
  mappingCount: number
}

interface FormData {
  accountNumber: string
  name: string
  description: string
  taxRate: string
  vatClassification: string
  isActive: boolean
  sortOrder: string
}

const emptyForm: FormData = {
  accountNumber: '',
  name: '',
  description: '',
  taxRate: '',
  vatClassification: 'any',
  isActive: true,
  sortOrder: '0',
}

const VAT_CLASSIFICATIONS = ['any', 'domestic', 'eu', 'non_eu']

export function RevenueAccountsSettings() {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading, refetch } = useQuery(REVENUE_ACCOUNTS_QUERY)
  const [createAccount, { loading: creating }] = useMutation(CREATE_REVENUE_ACCOUNT)
  const [updateAccount, { loading: updating }] = useMutation(UPDATE_REVENUE_ACCOUNT)
  const [deleteAccount] = useMutation(DELETE_REVENUE_ACCOUNT)
  const [seedDefaults, { loading: seeding }] = useMutation(SEED_DEFAULTS)

  const accounts: RevenueAccount[] = data?.revenueAccounts || []

  const handleEdit = (account: RevenueAccount) => {
    setEditingId(account.id)
    setForm({
      accountNumber: account.accountNumber,
      name: account.name,
      description: account.description,
      taxRate: account.taxRate || '',
      vatClassification: account.vatClassification,
      isActive: account.isActive,
      sortOrder: String(account.sortOrder),
    })
    setShowForm(true)
  }

  const handleCreate = () => {
    setEditingId(null)
    setForm(emptyForm)
    setShowForm(true)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setForm(emptyForm)
  }

  const handleSave = async () => {
    setMessage(null)
    const input = {
      accountNumber: form.accountNumber,
      name: form.name,
      description: form.description,
      taxRate: form.taxRate || null,
      vatClassification: form.vatClassification,
      isActive: form.isActive,
      sortOrder: parseInt(form.sortOrder) || 0,
    }
    try {
      if (editingId) {
        await updateAccount({ variables: { id: String(editingId), input } })
      } else {
        await createAccount({ variables: { input } })
      }
      await refetch()
      setShowForm(false)
      setEditingId(null)
      setForm(emptyForm)
      setMessage({ type: 'success', text: t('accounting.revenueAccounts.saved') })
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : t('accounting.revenueAccounts.saveFailed')
      setMessage({ type: 'error', text: errorMessage })
    }
  }

  const handleDelete = async (id: number) => {
    setMessage(null)
    try {
      const { data: result } = await deleteAccount({ variables: { id: String(id) } })
      if (result?.deleteRevenueAccount?.success) {
        await refetch()
        setMessage({ type: 'success', text: t('accounting.revenueAccounts.deleted') })
      } else {
        setMessage({ type: 'error', text: result?.deleteRevenueAccount?.error || t('accounting.revenueAccounts.deleteFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('accounting.revenueAccounts.deleteFailed') })
    }
  }

  const handleSeedDefaults = async () => {
    setMessage(null)
    try {
      await seedDefaults()
      await refetch()
      setMessage({ type: 'success', text: t('accounting.revenueAccounts.seeded') })
    } catch {
      setMessage({ type: 'error', text: t('accounting.revenueAccounts.seedFailed') })
    }
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  if (loading) {
    return <div className="flex items-center gap-2 p-6 text-gray-500"><Loader2 className="h-4 w-4 animate-spin" />{t('common.loading')}</div>
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{t('accounting.revenueAccounts.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('accounting.revenueAccounts.description')}</p>
        </div>
        <div className="flex gap-2">
          {accounts.length === 0 && (
            <button
              onClick={handleSeedDefaults}
              disabled={seeding}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {seeding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {t('accounting.revenueAccounts.seedDefaults')}
            </button>
          )}
          <button
            onClick={handleCreate}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('accounting.revenueAccounts.add')}
          </button>
        </div>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}

      {showForm && (
        <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-4">
          <h3 className="mb-3 text-sm font-medium">
            {editingId ? t('accounting.revenueAccounts.edit') : t('accounting.revenueAccounts.addNew')}
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.accountNumber')}</label>
              <input
                type="text"
                value={form.accountNumber}
                onChange={(e) => setForm({ ...form, accountNumber: e.target.value })}
                className={inputClass}
                placeholder="4400"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.name')}</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.taxRate')}</label>
              <input
                type="number"
                step="0.01"
                value={form.taxRate}
                onChange={(e) => setForm({ ...form, taxRate: e.target.value })}
                className={inputClass}
                placeholder="19.00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.vatClassification')}</label>
              <select
                value={form.vatClassification}
                onChange={(e) => setForm({ ...form, vatClassification: e.target.value })}
                className={inputClass}
              >
                {VAT_CLASSIFICATIONS.map((vc) => (
                  <option key={vc} value={vc}>{t(`accounting.vatClassification.${vc}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.sortOrder')}</label>
              <input
                type="number"
                value={form.sortOrder}
                onChange={(e) => setForm({ ...form, sortOrder: e.target.value })}
                className={inputClass}
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.isActive}
                  onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
                  className="rounded border-gray-300"
                />
                {t('accounting.revenueAccounts.active')}
              </label>
            </div>
          </div>
          <div className="mt-2">
            <label className="block text-sm font-medium text-gray-700">{t('accounting.revenueAccounts.descriptionLabel')}</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className={inputClass}
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleSave}
              disabled={creating || updating}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {(creating || updating) && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('common.save')}
            </button>
            <button
              onClick={handleCancel}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      <div className="mt-4">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.revenueAccounts.accountNumber')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.revenueAccounts.name')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.revenueAccounts.taxRate')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.revenueAccounts.vatClassification')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.revenueAccounts.status')}</th>
              <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {accounts.map((account) => (
              <tr key={account.id} className={!account.isActive ? 'opacity-50' : ''}>
                <td className="whitespace-nowrap px-3 py-2 text-sm font-mono">{account.accountNumber}</td>
                <td className="px-3 py-2 text-sm">{account.name}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">{account.taxRate ? `${account.taxRate}%` : '–'}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">{t(`accounting.vatClassification.${account.vatClassification}`)}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${account.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {account.isActive ? t('accounting.revenueAccounts.active') : t('accounting.revenueAccounts.inactive')}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                  <button
                    onClick={() => handleEdit(account)}
                    className="mr-2 text-gray-400 hover:text-blue-600"
                    title={t('common.edit')}
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  {account.mappingCount === 0 && (
                    <button
                      onClick={() => handleDelete(account.id)}
                      className="text-gray-400 hover:text-red-600"
                      title={t('common.delete')}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-sm text-gray-500">
                  {t('accounting.revenueAccounts.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
