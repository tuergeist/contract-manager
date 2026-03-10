import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { Building2, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const CURRENT_TENANT_QUERY = gql`
  query CurrentTenant {
    currentTenant {
      id
      name
    }
  }
`

const UPDATE_TENANT_NAME = gql`
  mutation UpdateTenantName($name: String!) {
    updateTenantName(name: $name) {
      success
      error
    }
  }
`

export function TenantNameSettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(CURRENT_TENANT_QUERY)
  const [updateName, { loading }] = useMutation(UPDATE_TENANT_NAME)
  const [name, setName] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (data?.currentTenant?.name) {
      setName(data.currentTenant.name)
    }
  }, [data])

  const isDirty = data?.currentTenant?.name !== name

  const handleSave = async () => {
    setMessage(null)
    const result = await updateName({ variables: { name } })
    const d = result.data?.updateTenantName
    if (d?.success) {
      setMessage({ type: 'success', text: t('settings.tenantName.saved') })
      refetch()
      setTimeout(() => setMessage(null), 3000)
    } else {
      setMessage({ type: 'error', text: d?.error || t('common.error') })
    }
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium flex items-center gap-2">
        <Building2 className="h-5 w-5" />
        {t('settings.tenantName.title')}
      </h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.tenantName.description')}</p>

      <div className="mt-4 flex items-center gap-3">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="max-w-sm"
          placeholder={t('settings.tenantName.placeholder')}
        />
        <Button
          onClick={handleSave}
          disabled={loading || !isDirty || !name.trim()}
          size="sm"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('common.save')}
        </Button>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}
    </div>
  )
}
