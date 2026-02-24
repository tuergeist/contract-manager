import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Copy, ChevronDown, ChevronRight } from 'lucide-react'

const FULL_CONFIG = `{
  "mcpServers": {
    "contract-cora": {
      "url": "https://contract-cora.com/mcp/",
      "auth": "oauth"
    }
  }
}`

const READ_ONLY_CONFIG = `{
  "mcpServers": {
    "contract-cora": {
      "url": "https://contract-cora.com/mcp/",
      "auth": "oauth",
      "scope": "read"
    }
  }
}`

function CopyButton({ text }: { text: string }) {
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
          {t('settings.mcp.copied')}
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          {t('settings.mcp.copyConfig')}
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

export function McpSettings() {
  const { t } = useTranslation()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  return (
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
  )
}
