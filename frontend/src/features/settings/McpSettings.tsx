import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Check, Copy, ChevronDown, ChevronRight, Plus, Key, Trash2, AlertTriangle, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// -- GraphQL --

const API_KEYS_QUERY = gql`
  query APIKeys {
    apiKeys {
      id
      name
      prefix
      permissions
      createdAt
      expiresAt
      lastUsedAt
      isActive
    }
    permissionRegistry {
      resource
      actions
    }
  }
`

const GENERATE_API_KEY = gql`
  mutation GenerateAPIKey($input: GenerateAPIKeyInput!) {
    generateApiKey(input: $input) {
      success
      error
      rawKey
      apiKey {
        id
        name
        prefix
        permissions
        createdAt
        expiresAt
        isActive
      }
    }
  }
`

const REVOKE_API_KEY = gql`
  mutation RevokeAPIKey($keyId: ID!) {
    revokeApiKey(keyId: $keyId) {
      success
      error
    }
  }
`

// -- Types --

interface APIKeyData {
  id: number
  name: string
  prefix: string
  permissions: Record<string, boolean>
  createdAt: string
  expiresAt: string | null
  lastUsedAt: string | null
  isActive: boolean
}

interface PermissionResource {
  resource: string
  actions: string[]
}

// -- MCP Config Blocks (existing) --

const FULL_CONFIG = `{
  "mcpServers": {
    "contract-cora": {
      "url": "https://contract-cora.com/mcp",
      "auth": "oauth"
    }
  }
}`

const READ_ONLY_CONFIG = `{
  "mcpServers": {
    "contract-cora": {
      "url": "https://contract-cora.com/mcp",
      "auth": "oauth",
      "scope": "read"
    }
  }
}`

function CopyButton({ text, label }: { text: string; label?: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-green-500" />
          {label || t('settings.mcp.copied')}
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          {label || t('settings.mcp.copyConfig')}
        </>
      )}
    </button>
  )
}

function ConfigBlock({ label, config }: { label: string; config: string }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-gray-700">{label}</p>
      <div className="relative">
        <pre className="rounded-md border bg-gray-50 p-4 text-sm text-gray-800 overflow-x-auto">
          <code>{config}</code>
        </pre>
        <div className="mt-2">
          <CopyButton text={config} />
        </div>
      </div>
    </div>
  )
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  const d = new Date(dateStr)
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getKeyStatus(key: APIKeyData): 'active' | 'revoked' | 'expired' {
  if (!key.isActive) return 'revoked'
  if (key.expiresAt && new Date(key.expiresAt) < new Date()) return 'expired'
  return 'active'
}

// -- Generate Dialog --

function GenerateKeyDialog({
  open,
  onOpenChange,
  permissionRegistry,
  onGenerate,
  generating,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  permissionRegistry: PermissionResource[]
  onGenerate: (name: string, permissions: Record<string, boolean>, expiresInDays: number | null) => void
  generating: boolean
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [selectedPerms, setSelectedPerms] = useState<Record<string, boolean>>({})
  const [expiry, setExpiry] = useState<string>('never')

  const handleTogglePerm = (perm: string) => {
    setSelectedPerms(prev => ({
      ...prev,
      [perm]: !prev[perm],
    }))
  }

  const handleToggleResource = (resource: string, actions: string[]) => {
    const allSelected = actions.every(a => selectedPerms[`${resource}.${a}`])
    const newPerms = { ...selectedPerms }
    actions.forEach(a => {
      newPerms[`${resource}.${a}`] = !allSelected
    })
    setSelectedPerms(newPerms)
  }

  const handleSubmit = () => {
    const expiresInDays = expiry === 'never' ? null : parseInt(expiry, 10)
    onGenerate(name, selectedPerms, expiresInDays)
  }

  const selectedCount = Object.values(selectedPerms).filter(Boolean).length

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      setName('')
      setSelectedPerms({})
      setExpiry('never')
    }
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            {t('settings.api.generate')}
          </DialogTitle>
          <DialogDescription>
            {t('settings.api.generateDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Name */}
          <div className="space-y-2">
            <Label>{t('settings.api.name')}</Label>
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('settings.api.namePlaceholder')}
              data-testid="api-key-name-input"
            />
          </div>

          {/* Permissions */}
          <div className="space-y-2">
            <Label>{t('settings.api.permissions')}</Label>
            <div className="rounded-md border max-h-60 overflow-y-auto">
              {permissionRegistry.map(({ resource, actions }) => (
                <div key={resource} className="border-b last:border-b-0">
                  <div
                    className="flex items-center gap-2 px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleToggleResource(resource, actions)}
                  >
                    <Checkbox
                      checked={actions.every(a => selectedPerms[`${resource}.${a}`])}
                      onCheckedChange={() => handleToggleResource(resource, actions)}
                    />
                    <span className="text-sm font-medium capitalize">{resource.replace('_', ' ')}</span>
                  </div>
                  <div className="px-3 py-1.5 flex flex-wrap gap-x-4 gap-y-1">
                    {actions.map(action => {
                      const perm = `${resource}.${action}`
                      return (
                        <label key={perm} className="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer">
                          <Checkbox
                            checked={!!selectedPerms[perm]}
                            onCheckedChange={() => handleTogglePerm(perm)}
                          />
                          {action}
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Expiry */}
          <div className="space-y-2">
            <Label>{t('settings.api.expiry')}</Label>
            <Select value={expiry} onValueChange={setExpiry}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="never">{t('settings.api.never')}</SelectItem>
                <SelectItem value="30">30 {t('settings.api.days')}</SelectItem>
                <SelectItem value="90">90 {t('settings.api.days')}</SelectItem>
                <SelectItem value="365">1 {t('settings.api.year')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!name.trim() || selectedCount === 0 || generating}
            data-testid="api-key-generate-submit"
          >
            {generating ? `${t('settings.api.generate')}...` : t('settings.api.generate')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -- Key Created Dialog --

function KeyCreatedDialog({
  open,
  onOpenChange,
  rawKey,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  rawKey: string
}) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(rawKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-green-700">
            <Check className="h-5 w-5" />
            {t('settings.api.keyCreated')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3">
            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-amber-800">{t('settings.api.copyWarning')}</p>
          </div>

          <div className="relative">
            <pre className="rounded-md border bg-gray-50 p-4 text-sm text-gray-800 break-all whitespace-pre-wrap font-mono">
              {rawKey}
            </pre>
            <div className="mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopy}
                className="gap-1.5"
                data-testid="api-key-copy-button"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-green-500" />
                    {t('settings.api.copied')}
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    {t('settings.api.copyKey')}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            {t('common.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// -- API Keys Section --

function APIKeysSection() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(API_KEYS_QUERY)
  const [generateApiKey, { loading: generating }] = useMutation(GENERATE_API_KEY)
  const [revokeApiKey] = useMutation(REVOKE_API_KEY)

  const [generateOpen, setGenerateOpen] = useState(false)
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [revokeId, setRevokeId] = useState<number | null>(null)

  const apiKeys: APIKeyData[] = data?.apiKeys || []
  const permissionRegistry: PermissionResource[] = data?.permissionRegistry || []

  const handleGenerate = async (
    name: string,
    permissions: Record<string, boolean>,
    expiresInDays: number | null,
  ) => {
    const result = await generateApiKey({
      variables: {
        input: { name, permissions, expiresInDays },
      },
    })
    const res = result.data?.generateApiKey
    if (res?.success && res.rawKey) {
      setGenerateOpen(false)
      setCreatedKey(res.rawKey)
      refetch()
    }
  }

  const handleRevoke = async () => {
    if (revokeId == null) return
    await revokeApiKey({ variables: { keyId: String(revokeId) } })
    setRevokeId(null)
    refetch()
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium flex items-center gap-2">
            <Shield className="h-5 w-5 text-gray-500" />
            {t('settings.api.title')}
          </h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.api.description')}</p>
        </div>
        <Button onClick={() => setGenerateOpen(true)} className="gap-1.5" data-testid="api-key-generate-button">
          <Plus className="h-4 w-4" />
          {t('settings.api.generate')}
        </Button>
      </div>

      {apiKeys.length === 0 ? (
        <div className="mt-6 text-center py-8 text-sm text-gray-500">
          <Key className="h-8 w-8 mx-auto mb-2 text-gray-300" />
          {t('settings.api.noKeys')}
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('settings.api.name')}</TableHead>
                <TableHead>{t('settings.api.keyPrefix')}</TableHead>
                <TableHead>{t('settings.api.created')}</TableHead>
                <TableHead>{t('settings.api.lastUsed')}</TableHead>
                <TableHead>{t('settings.api.expiry')}</TableHead>
                <TableHead>{t('settings.api.status')}</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map(key => {
                const status = getKeyStatus(key)
                return (
                  <TableRow key={key.id} data-testid={`api-key-row-${key.id}`}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono">
                        {key.prefix}...
                      </code>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDate(key.createdAt)}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDate(key.lastUsedAt)}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {key.expiresAt ? formatDate(key.expiresAt) : t('settings.api.never')}
                    </TableCell>
                    <TableCell>
                      {status === 'active' && (
                        <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-100">
                          {t('settings.api.active')}
                        </Badge>
                      )}
                      {status === 'revoked' && (
                        <Badge variant="secondary" className="bg-gray-100 text-gray-600">
                          {t('settings.api.revoked')}
                        </Badge>
                      )}
                      {status === 'expired' && (
                        <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                          {t('settings.api.expired')}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {status === 'active' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setRevokeId(key.id)}
                          className="h-8 w-8 text-gray-400 hover:text-red-600"
                          data-testid={`api-key-revoke-${key.id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Generate Dialog */}
      <GenerateKeyDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        permissionRegistry={permissionRegistry}
        onGenerate={handleGenerate}
        generating={generating}
      />

      {/* Key Created Dialog */}
      {createdKey && (
        <KeyCreatedDialog
          open={!!createdKey}
          onOpenChange={() => setCreatedKey(null)}
          rawKey={createdKey}
        />
      )}

      {/* Revoke Confirmation Dialog */}
      <Dialog open={revokeId !== null} onOpenChange={() => setRevokeId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{t('settings.api.revoke')}</DialogTitle>
            <DialogDescription>
              {t('settings.api.revokeConfirm')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevokeId(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleRevoke} data-testid="api-key-revoke-confirm">
              {t('settings.api.revoke')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// -- Main Component --

export function McpSettings() {
  const { t } = useTranslation()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  return (
    <div className="space-y-6">
      {/* API Keys Section */}
      <APIKeysSection />

      {/* MCP Connection Info */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="text-lg font-medium">{t('settings.mcp.title')}</h2>
        <p className="mt-1 text-sm text-gray-500">{t('settings.mcp.description')}</p>

        {/* Section 1: Connection Setup */}
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-900">{t('settings.mcp.connectionTitle')}</h3>
          <p className="mt-1 text-sm text-gray-500">{t('settings.mcp.connectionDescription')}</p>
          <div className="mt-3">
            <ConfigBlock
              label={t('settings.mcp.configSnippet')}
              config={FULL_CONFIG}
            />
          </div>
        </div>

        {/* Section 2: Read-Only Access */}
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-900">{t('settings.mcp.readOnlyTitle')}</h3>
          <p className="mt-1 text-sm text-gray-500">{t('settings.mcp.readOnlyDescription')}</p>
          <div className="mt-3">
            <ConfigBlock
              label={t('settings.mcp.readOnlyConfigSnippet')}
              config={READ_ONLY_CONFIG}
            />
          </div>
        </div>

        {/* Section 3: Available Tools */}
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-900">{t('settings.mcp.toolsTitle')}</h3>
          <p className="mt-1 text-sm text-gray-500">{t('settings.mcp.toolsDescription')}</p>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-md border bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-700">{t('settings.mcp.readTools')}</p>
              <ul className="mt-2 space-y-1 text-sm text-gray-600">
                <li>- list_customers, get_customer</li>
                <li>- list_products, get_product</li>
                <li>- list_contracts, get_contract</li>
                <li>- list_invoices, get_invoice</li>
                <li>- list_transactions, get_transaction</li>
              </ul>
            </div>
            <div className="rounded-md border bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-700">{t('settings.mcp.writeTools')}</p>
              <ul className="mt-2 space-y-1 text-sm text-gray-600">
                <li>- create_contract, update_contract</li>
                <li>- generate_invoices, void_invoice</li>
                <li>- send_invoice_email</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Expandable: Advanced OAuth Endpoints */}
        <div className="mt-8 border-t pt-4">
          <button
            onClick={() => setAdvancedOpen(!advancedOpen)}
            className="flex items-center gap-1.5 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            {advancedOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {t('settings.mcp.advancedTitle')}
          </button>
          {advancedOpen && (
            <div className="mt-3 rounded-md border bg-gray-50 p-4">
              <p className="mb-2 text-sm font-medium text-gray-700">{t('settings.mcp.oauthEndpoints')}</p>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="font-mono text-xs text-gray-500">{t('settings.mcp.metadataUrl')}</dt>
                  <dd className="font-mono text-gray-800">https://contract-cora.com/.well-known/oauth-authorization-server</dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-gray-500">{t('settings.mcp.authorizeUrl')}</dt>
                  <dd className="font-mono text-gray-800">https://contract-cora.com/oauth/authorize/</dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-gray-500">{t('settings.mcp.tokenUrl')}</dt>
                  <dd className="font-mono text-gray-800">https://contract-cora.com/oauth/token/</dd>
                </div>
                <div>
                  <dt className="font-mono text-xs text-gray-500">{t('settings.mcp.registrationUrl')}</dt>
                  <dd className="font-mono text-gray-800">https://contract-cora.com/oauth/register/</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
