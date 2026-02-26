import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, Pencil, Trash2 } from 'lucide-react'

const MAPPINGS_QUERY = gql`
  query RevenueAccountMappings {
    revenueAccountMappings {
      id
      productId
      productName
      productCategoryName
      taxRate
      vatClassification
      revenueAccount {
        id
        accountNumber
        name
      }
    }
  }
`

const REVENUE_ACCOUNTS_QUERY = gql`
  query RevenueAccountsForMapping {
    revenueAccounts(isActive: true) {
      id
      accountNumber
      name
    }
  }
`

const PRODUCTS_QUERY = gql`
  query ProductsForMapping {
    products(isActive: true, pageSize: 200) {
      items {
        id
        name
        category {
          id
          name
        }
      }
    }
  }
`

const CREATE_MAPPING = gql`
  mutation CreateMapping($input: RevenueAccountMappingInput!) {
    createRevenueAccountMapping(input: $input) {
      id
    }
  }
`

const UPDATE_MAPPING = gql`
  mutation UpdateMapping($id: ID!, $input: RevenueAccountMappingInput!) {
    updateRevenueAccountMapping(id: $id, input: $input) {
      id
    }
  }
`

const DELETE_MAPPING = gql`
  mutation DeleteMapping($id: ID!) {
    deleteRevenueAccountMapping(id: $id) {
      success
      error
    }
  }
`

interface Mapping {
  id: number
  productId: number | null
  productName: string | null
  productCategoryName: string | null
  taxRate: string | null
  vatClassification: string
  revenueAccount: {
    id: number
    accountNumber: string
    name: string
  }
}

interface FormData {
  productId: string
  taxRate: string
  vatClassification: string
  revenueAccountId: string
}

const emptyForm: FormData = {
  productId: '',
  taxRate: '',
  vatClassification: 'any',
  revenueAccountId: '',
}

const VAT_CLASSIFICATIONS = ['any', 'domestic', 'eu', 'non_eu']

export function MappingRulesSettings() {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormData>(emptyForm)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading, refetch } = useQuery(MAPPINGS_QUERY)
  const { data: accountsData } = useQuery(REVENUE_ACCOUNTS_QUERY)
  const { data: productsData } = useQuery(PRODUCTS_QUERY)
  const [createMapping, { loading: creating }] = useMutation(CREATE_MAPPING)
  const [updateMapping, { loading: updating }] = useMutation(UPDATE_MAPPING)
  const [deleteMapping] = useMutation(DELETE_MAPPING)

  const mappings: Mapping[] = data?.revenueAccountMappings || []
  const accounts = accountsData?.revenueAccounts || []
  const products = productsData?.products?.items || []

  const handleEdit = (mapping: Mapping) => {
    setEditingId(mapping.id)
    setForm({
      productId: mapping.productId ? String(mapping.productId) : '',
      taxRate: mapping.taxRate || '',
      vatClassification: mapping.vatClassification,
      revenueAccountId: String(mapping.revenueAccount.id),
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
      productId: form.productId ? parseInt(form.productId) : null,
      taxRate: form.taxRate || null,
      vatClassification: form.vatClassification,
      revenueAccountId: parseInt(form.revenueAccountId),
    }
    try {
      if (editingId) {
        await updateMapping({ variables: { id: String(editingId), input } })
      } else {
        await createMapping({ variables: { input } })
      }
      await refetch()
      setShowForm(false)
      setEditingId(null)
      setForm(emptyForm)
      setMessage({ type: 'success', text: t('accounting.mappings.saved') })
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : t('accounting.mappings.saveFailed')
      setMessage({ type: 'error', text: errorMessage })
    }
  }

  const handleDelete = async (id: number) => {
    setMessage(null)
    try {
      const { data: result } = await deleteMapping({ variables: { id: String(id) } })
      if (result?.deleteRevenueAccountMapping?.success) {
        await refetch()
        setMessage({ type: 'success', text: t('accounting.mappings.deleted') })
      } else {
        setMessage({ type: 'error', text: result?.deleteRevenueAccountMapping?.error || t('accounting.mappings.deleteFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('accounting.mappings.deleteFailed') })
    }
  }

  const getMappingLabel = (mapping: Mapping) => {
    if (mapping.productName) {
      return mapping.productName
    }
    if (mapping.taxRate) {
      return `${mapping.taxRate}% ${t('accounting.mappings.defaultRule')}`
    }
    return t('accounting.mappings.globalFallback')
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  if (loading) {
    return <div className="flex items-center gap-2 p-6 text-gray-500"><Loader2 className="h-4 w-4 animate-spin" />{t('common.loading')}</div>
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{t('accounting.mappings.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('accounting.mappings.description')}</p>
        </div>
        <button
          onClick={handleCreate}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          {t('accounting.mappings.add')}
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
            {editingId ? t('accounting.mappings.edit') : t('accounting.mappings.addNew')}
          </h3>
          <p className="mb-3 text-xs text-gray-500">{t('accounting.mappings.formHint')}</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.mappings.product')}</label>
              <select
                value={form.productId}
                onChange={(e) => setForm({ ...form, productId: e.target.value })}
                className={inputClass}
              >
                <option value="">{t('accounting.mappings.anyProduct')}</option>
                {products.map((p: { id: number; name: string }) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.mappings.taxRate')}</label>
              <input
                type="number"
                step="0.01"
                value={form.taxRate}
                onChange={(e) => setForm({ ...form, taxRate: e.target.value })}
                className={inputClass}
                placeholder={t('accounting.mappings.anyTaxRate')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{t('accounting.mappings.vatClassification')}</label>
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
              <label className="block text-sm font-medium text-gray-700">{t('accounting.mappings.revenueAccount')}</label>
              <select
                value={form.revenueAccountId}
                onChange={(e) => setForm({ ...form, revenueAccountId: e.target.value })}
                className={inputClass}
              >
                <option value="">{t('accounting.mappings.selectAccount')}</option>
                {accounts.map((a: { id: number; accountNumber: string; name: string }) => (
                  <option key={a.id} value={a.id}>{a.accountNumber} – {a.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleSave}
              disabled={creating || updating || !form.revenueAccountId}
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
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.mappings.rule')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.mappings.taxRate')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.mappings.vatClassification')}</th>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('accounting.mappings.revenueAccount')}</th>
              <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {mappings.map((mapping) => (
              <tr key={mapping.id}>
                <td className="px-3 py-2 text-sm">
                  <div className="font-medium">{getMappingLabel(mapping)}</div>
                  {mapping.productCategoryName && (
                    <div className="text-xs text-gray-500">{mapping.productCategoryName}</div>
                  )}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">{mapping.taxRate ? `${mapping.taxRate}%` : '–'}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm">{t(`accounting.vatClassification.${mapping.vatClassification}`)}</td>
                <td className="whitespace-nowrap px-3 py-2 text-sm font-mono">
                  {mapping.revenueAccount.accountNumber} – {mapping.revenueAccount.name}
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                  <button
                    onClick={() => handleEdit(mapping)}
                    className="mr-2 text-gray-400 hover:text-blue-600"
                    title={t('common.edit')}
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(mapping.id)}
                    className="text-gray-400 hover:text-red-600"
                    title={t('common.delete')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
            {mappings.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-8 text-center text-sm text-gray-500">
                  {t('accounting.mappings.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
