import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, Pencil, Trash2 } from 'lucide-react'

const TAX_ACCOUNTS_QUERY = gql`
  query TaxAccounts {
    taxAccounts {
      id
      accountNumber
      name
      taxRate
      isActive
    }
  }
`

const CREATE_TAX_ACCOUNT = gql`
  mutation CreateTaxAccount($input: TaxAccountInput!) {
    createTaxAccount(input: $input) {
      id
      accountNumber
      name
    }
  }
`

const UPDATE_TAX_ACCOUNT = gql`
  mutation UpdateTaxAccount($id: ID!, $input: TaxAccountInput!) {
    updateTaxAccount(id: $id, input: $input) {
      id
      accountNumber
      name
    }
  }
`

const DELETE_TAX_ACCOUNT = gql`
  mutation DeleteTaxAccount($id: ID!) {
    deleteTaxAccount(id: $id) {
      success
      error
    }
  }
`

interface TaxAccount {
  id: number
  accountNumber: string
  name: string
  taxRate: string
  isActive: boolean
}

interface FormData {
  accountNumber: string
  name: string
  taxRate: string
  isActive: boolean
}

const emptyForm: FormData = {
  accountNumber: '',
  name: '',
  taxRate: '',
  isActive: true,
}

export function TaxAccountsSettings() {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading, refetch } = useQuery(TAX_ACCOUNTS_QUERY)
  const [createAccount, { loading: creating }] = useMutation(CREATE_TAX_ACCOUNT)
  const [updateAccount, { loading: updating }] = useMutation(UPDATE_TAX_ACCOUNT)
  const [deleteAccount] = useMutation(DELETE_TAX_ACCOUNT)

  const accounts: TaxAccount[] = data?.taxAccounts || []

  const handleEdit = (account: TaxAccount) => {
    setEditingId(account.id)
    setForm({
      accountNumber: account.accountNumber,
      name: account.name,
      taxRate: account.taxRate,
      isActive: account.isActive,
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
      taxRate: form.taxRate,
      isActive: form.isActive,
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
      setMessage({ type: 'success', text: t('accounting.taxAccounts.saved') })
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : t('accounting.taxAccounts.saveFailed')
      setMessage({ type: 'error', text: errorMessage })
    }
  }

  const handleDelete = async (id: number) => {
    setMessage(null)
    try {
      const { data: result } = await deleteAccount({ variables: { id: String(id) } })
      if (result?.deleteTaxAccount?.success) {
        await refetch()
        setMessage({ type: 'success', text: t('accounting.taxAccounts.deleted') })
      } else {
        setMessage({ type: 'error', text: result?.deleteTaxAccount?.error || t('accounting.taxAccounts.deleteFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('accounting.taxAccounts.deleteFailed') })
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
          <h2 className="text-lg font-medium">{t('accounting.taxAccounts.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('accounting.taxAccounts.description')}</p>
        </div>
        <button
          onClick={handleCreate}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          {t('accounting.taxAccounts.add')}
        </button>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}

      {showForm && (
        <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-4">
          <h3 className="mb-3 text-sm font-medium">
            {editingId ? t('accounting.taxAccounts.edit') : t('accounting.taxAccounts.addNew')}
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.taxAccounts.accountNumber')}</label>
              <input
                type="text"
                value={form.accountNumber}
                onChange={(e) => setForm({ ...form, accountNumber: e.target.value })}
                className={inputClass}
                placeholder="3806"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.taxAccounts.name')}</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.taxAccounts.taxRate')}</label>
              <input
                type="number"
                step="0.01"
                value={form.taxRate}
                onChange={(e) => setForm({ ...form, taxRate: e.target.value })}
                className={inputClass}
                placeholder="19.00"
              />
            </div>
          </div>
          <div className="mt-2">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.isActive}
                onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
                className="rounded border-gray-300"
              />
              {t('accounting.taxAccounts.active')}
            </label>
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
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.taxAccounts.accountNumber')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.taxAccounts.name')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.taxAccounts.taxRate')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.taxAccounts.status')}</th>
              <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {accounts.map((account) => (
              <tr key={account.id} className={!account.isActive ? 'opacity-50' : ''}>
                <td className="whitespace-nowrap px-3 py-2 text-sm font-mono">{account.accountNumber}</td>
                <td className="px-3 py-2 text-sm">{account.name}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">{account.taxRate}%</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${account.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {account.isActive ? t('accounting.taxAccounts.active') : t('accounting.taxAccounts.inactive')}
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
                  <button
                    onClick={() => handleDelete(account.id)}
                    className="text-gray-400 hover:text-red-600"
                    title={t('common.delete')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
            {accounts.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-sm text-gray-500">
                  {t('accounting.taxAccounts.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
