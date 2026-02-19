import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'

const SMTP_SETTINGS_QUERY = gql`
  query SmtpSettings {
    smtpSettings {
      host
      port
      username
      fromName
      fromAddress
      useTls
      isConfigured
      passwordSet
    }
  }
`

const SAVE_SMTP_SETTINGS = gql`
  mutation SaveSmtpSettings(
    $host: String!
    $port: Int!
    $username: String!
    $password: String!
    $fromName: String!
    $fromAddress: String!
    $useTls: Boolean!
  ) {
    saveSmtpSettings(
      host: $host
      port: $port
      username: $username
      password: $password
      fromName: $fromName
      fromAddress: $fromAddress
      useTls: $useTls
    ) {
      success
      error
    }
  }
`

const TEST_SMTP_CONNECTION = gql`
  mutation TestSmtpConnection {
    testSmtpConnection {
      success
      error
    }
  }
`

const SEND_SMTP_TEST_EMAIL = gql`
  mutation SendSmtpTestEmail {
    sendSmtpTestEmail {
      success
      error
    }
  }
`

export function SmtpSettings() {
  const { t } = useTranslation()
  const [host, setHost] = useState('')
  const [port, setPort] = useState('587')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fromName, setFromName] = useState('')
  const [fromAddress, setFromAddress] = useState('')
  const [useTls, setUseTls] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [testResult, setTestResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [sendResult, setSendResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, refetch } = useQuery(SMTP_SETTINGS_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_SMTP_SETTINGS)
  const [testConnection, { loading: testing }] = useMutation(TEST_SMTP_CONNECTION)
  const [sendTestEmail, { loading: sending }] = useMutation(SEND_SMTP_TEST_EMAIL)

  useEffect(() => {
    const settings = data?.smtpSettings
    if (settings) {
      setHost(settings.host || '')
      setPort(String(settings.port || 587))
      setUsername(settings.username || '')
      setFromName(settings.fromName || '')
      setFromAddress(settings.fromAddress || '')
      setUseTls(settings.useTls ?? true)
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    try {
      const { data: result } = await saveSettings({
        variables: {
          host,
          port: parseInt(port, 10) || 587,
          username,
          password,
          fromName,
          fromAddress,
          useTls,
        },
      })
      if (result?.saveSmtpSettings?.success) {
        setMessage({ type: 'success', text: t('settings.smtp.saved') })
        setPassword('')
        refetch()
      } else {
        setMessage({ type: 'error', text: result?.saveSmtpSettings?.error || t('settings.smtp.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.smtp.saveFailed') })
    }
  }

  const handleTestConnection = async () => {
    setTestResult(null)
    try {
      const { data: result } = await testConnection()
      if (result?.testSmtpConnection?.success) {
        setTestResult({ type: 'success', text: t('settings.smtp.connectionSuccess') })
      } else {
        setTestResult({ type: 'error', text: result?.testSmtpConnection?.error || t('settings.smtp.connectionFailed') })
      }
    } catch {
      setTestResult({ type: 'error', text: t('settings.smtp.connectionFailed') })
    }
  }

  const handleSendTestEmail = async () => {
    setSendResult(null)
    try {
      const { data: result } = await sendTestEmail()
      if (result?.sendSmtpTestEmail?.success) {
        setSendResult({ type: 'success', text: t('settings.smtp.testEmailSent') })
      } else {
        setSendResult({ type: 'error', text: result?.sendSmtpTestEmail?.error || t('settings.smtp.testEmailFailed') })
      }
    } catch {
      setSendResult({ type: 'error', text: t('settings.smtp.testEmailFailed') })
    }
  }

  const isConfigured = data?.smtpSettings?.isConfigured

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.smtp.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.smtp.description')}</p>

      <div className="mt-4 space-y-4">
        {/* Connection Status */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">{t('settings.smtp.status')}:</span>
          {isConfigured ? (
            <>
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm text-green-600">{t('settings.smtp.configured')}</span>
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-500">{t('settings.smtp.notConfigured')}</span>
            </>
          )}
        </div>

        {/* Form Fields */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.host')}</label>
            <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="smtp-relay.brevo.com" className={inputClass} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.port')}</label>
            <input type="number" value={port} onChange={(e) => setPort(e.target.value)} placeholder="587" className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.username')}</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className={inputClass} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.password')}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={data?.smtpSettings?.passwordSet ? '••••••••' : ''} className={inputClass} />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.fromName')}</label>
            <input type="text" value={fromName} onChange={(e) => setFromName(e.target.value)} placeholder="Contract Cora" className={inputClass} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.smtp.fromAddress')}</label>
            <input type="email" value={fromAddress} onChange={(e) => setFromAddress(e.target.value)} placeholder="noreply@company.com" className={inputClass} />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input type="checkbox" id="smtp-tls" checked={useTls} onChange={(e) => setUseTls(e.target.checked)} className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
          <label htmlFor="smtp-tls" className="text-sm font-medium text-gray-700">{t('settings.smtp.useTls')}</label>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving || !host}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('settings.smtp.save')}
          </button>

          {isConfigured && (
            <>
              <button
                onClick={handleTestConnection}
                disabled={testing}
                className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {testing && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('settings.smtp.testConnection')}
              </button>

              <button
                onClick={handleSendTestEmail}
                disabled={sending}
                className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {sending && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('settings.smtp.sendTestEmail')}
              </button>
            </>
          )}
        </div>

        {/* Status Messages */}
        {message && (
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}
        {testResult && (
          <p className={`text-sm ${testResult.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {testResult.text}
          </p>
        )}
        {sendResult && (
          <p className={`text-sm ${sendResult.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {sendResult.text}
          </p>
        )}
      </div>
    </div>
  )
}
