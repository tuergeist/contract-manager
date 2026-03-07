import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { ShieldCheck, ShieldOff, Key, Mail, Loader2, Copy, Check } from 'lucide-react'

const ME_2FA_QUERY = gql`
  query Me2fa {
    me {
      id
      twoFactorEnabled
      twoFactorMethod
    }
  }
`

const SETUP_TOTP = gql`
  mutation SetupTotp {
    setupTotp {
      success
      error
      secret
      provisioningUri
    }
  }
`

const CONFIRM_TOTP = gql`
  mutation ConfirmTotp($code: String!) {
    confirmTotp(code: $code) {
      success
      error
      recoveryCodes
    }
  }
`

const ENABLE_EMAIL_2FA = gql`
  mutation EnableEmail2fa {
    enableEmail2fa {
      success
      error
      recoveryCodes
    }
  }
`

const DISABLE_2FA = gql`
  mutation Disable2fa($password: String!) {
    disable2fa(password: $password) {
      success
      error
    }
  }
`

const REGENERATE_CODES = gql`
  mutation RegenerateRecoveryCodes($password: String!) {
    regenerateRecoveryCodes(password: $password) {
      success
      error
      recoveryCodes
    }
  }
`

type Step = 'idle' | 'totp-setup' | 'totp-confirm' | 'email-setup' | 'recovery-codes' | 'disable' | 'regenerate'

export function SecuritySettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery(ME_2FA_QUERY)
  const [step, setStep] = useState<Step>('idle')
  const [totpSecret, setTotpSecret] = useState('')
  const [totpUri, setTotpUri] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const [setupTotp, { loading: settingUp }] = useMutation(SETUP_TOTP)
  const [confirmTotp, { loading: confirming }] = useMutation(CONFIRM_TOTP)
  const [enableEmail, { loading: enablingEmail }] = useMutation(ENABLE_EMAIL_2FA)
  const [disable2fa, { loading: disabling }] = useMutation(DISABLE_2FA)
  const [regenerate, { loading: regenerating }] = useMutation(REGENERATE_CODES)

  const is2faEnabled = data?.me?.twoFactorEnabled
  const method = data?.me?.twoFactorMethod

  const handleSetupTotp = async () => {
    setError(null)
    const result = await setupTotp()
    const d = result.data?.setupTotp
    if (d?.success) {
      setTotpSecret(d.secret)
      setTotpUri(d.provisioningUri)
      setStep('totp-confirm')
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  const handleConfirmTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const result = await confirmTotp({ variables: { code: code.trim() } })
    const d = result.data?.confirmTotp
    if (d?.success) {
      setRecoveryCodes(d.recoveryCodes)
      setStep('recovery-codes')
      refetch()
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  const handleEnableEmail = async () => {
    setError(null)
    const result = await enableEmail()
    const d = result.data?.enableEmail2fa
    if (d?.success) {
      setRecoveryCodes(d.recoveryCodes)
      setStep('recovery-codes')
      refetch()
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const result = await disable2fa({ variables: { password } })
    const d = result.data?.disable2fa
    if (d?.success) {
      setStep('idle')
      setPassword('')
      refetch()
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  const handleRegenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const result = await regenerate({ variables: { password } })
    const d = result.data?.regenerateRecoveryCodes
    if (d?.success) {
      setRecoveryCodes(d.recoveryCodes)
      setStep('recovery-codes')
      setPassword('')
    } else {
      setError(d?.error || t('common.error'))
    }
  }

  const copyRecoveryCodes = () => {
    navigator.clipboard.writeText(recoveryCodes.join('\n'))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const resetState = () => {
    setStep('idle')
    setCode('')
    setPassword('')
    setError(null)
    setTotpSecret('')
    setTotpUri('')
    setCopied(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">{t('settings.security.title')}</h3>
        <p className="text-sm text-gray-500">{t('settings.security.description')}</p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Current status */}
      {step === 'idle' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 rounded-lg bg-gray-50">
            {is2faEnabled ? (
              <>
                <ShieldCheck className="h-6 w-6 text-green-500" />
                <div>
                  <p className="font-medium text-green-700">{t('settings.security.enabled')}</p>
                  <p className="text-sm text-gray-500">
                    {method === 'totp' ? t('settings.security.methodTotp') : t('settings.security.methodEmail')}
                  </p>
                </div>
              </>
            ) : (
              <>
                <ShieldOff className="h-6 w-6 text-gray-400" />
                <div>
                  <p className="font-medium text-gray-700">{t('settings.security.disabled')}</p>
                  <p className="text-sm text-gray-500">{t('settings.security.disabledDesc')}</p>
                </div>
              </>
            )}
          </div>

          {!is2faEnabled ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                onClick={handleSetupTotp}
                disabled={settingUp}
                className="flex items-center gap-2 px-4 py-3 border rounded-lg hover:bg-gray-50 text-left"
              >
                <Key className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="font-medium text-sm">{t('settings.security.setupTotp')}</p>
                  <p className="text-xs text-gray-500">{t('settings.security.setupTotpDesc')}</p>
                </div>
              </button>
              <button
                onClick={handleEnableEmail}
                disabled={enablingEmail}
                className="flex items-center gap-2 px-4 py-3 border rounded-lg hover:bg-gray-50 text-left"
              >
                <Mail className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="font-medium text-sm">{t('settings.security.setupEmail')}</p>
                  <p className="text-xs text-gray-500">{t('settings.security.setupEmailDesc')}</p>
                </div>
              </button>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={() => setStep('regenerate')}
                className="px-4 py-2 text-sm border rounded-md hover:bg-gray-50"
              >
                {t('settings.security.regenerateCodes')}
              </button>
              <button
                onClick={() => setStep('disable')}
                className="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50"
              >
                {t('settings.security.disable2fa')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* TOTP confirmation */}
      {step === 'totp-confirm' && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{t('settings.security.scanQr')}</p>

          {/* QR code placeholder — rendered as text URI for now */}
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`}
              alt="QR Code"
              className="mx-auto"
              width={200}
              height={200}
            />
            <p className="mt-2 text-xs text-gray-500 font-mono break-all">{totpSecret}</p>
          </div>

          <form onSubmit={handleConfirmTotp} className="space-y-3">
            <input
              type="text"
              inputMode="numeric"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="000000"
              maxLength={6}
              className="block w-full px-3 py-2 border rounded-md text-center text-lg tracking-widest"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={confirming}
                className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {confirming ? <Loader2 className="h-4 w-4 animate-spin mx-auto" /> : t('auth.verify')}
              </button>
              <button type="button" onClick={resetState} className="px-4 py-2 border rounded-md text-sm">
                {t('common.cancel')}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Recovery codes display */}
      {step === 'recovery-codes' && (
        <div className="space-y-4">
          <div className="rounded-md bg-yellow-50 p-4">
            <p className="text-sm font-medium text-yellow-800">{t('settings.security.saveRecoveryCodes')}</p>
            <p className="text-xs text-yellow-700 mt-1">{t('settings.security.recoveryCodesWarning')}</p>
          </div>

          <div className="grid grid-cols-2 gap-2 p-4 bg-gray-50 rounded-lg font-mono text-sm">
            {recoveryCodes.map((c, i) => (
              <span key={i} className="px-2 py-1 bg-white rounded border">{c}</span>
            ))}
          </div>

          <div className="flex gap-2">
            <button onClick={copyRecoveryCodes} className="flex items-center gap-1 px-4 py-2 border rounded-md text-sm">
              {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
              {copied ? t('common.copied') : t('common.copy')}
            </button>
            <button onClick={resetState} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
              {t('common.done')}
            </button>
          </div>
        </div>
      )}

      {/* Disable 2FA */}
      {step === 'disable' && (
        <form onSubmit={handleDisable} className="space-y-3">
          <p className="text-sm text-gray-600">{t('settings.security.confirmDisable')}</p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('auth.password')}
            required
            className="block w-full px-3 py-2 border rounded-md text-sm"
          />
          <div className="flex gap-2">
            <button type="submit" disabled={disabling} className="px-4 py-2 bg-red-600 text-white rounded-md text-sm">
              {disabling ? <Loader2 className="h-4 w-4 animate-spin" /> : t('settings.security.disable2fa')}
            </button>
            <button type="button" onClick={resetState} className="px-4 py-2 border rounded-md text-sm">
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}

      {/* Regenerate codes */}
      {step === 'regenerate' && (
        <form onSubmit={handleRegenerate} className="space-y-3">
          <p className="text-sm text-gray-600">{t('settings.security.confirmRegenerate')}</p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('auth.password')}
            required
            className="block w-full px-3 py-2 border rounded-md text-sm"
          />
          <div className="flex gap-2">
            <button type="submit" disabled={regenerating} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
              {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : t('settings.security.regenerateCodes')}
            </button>
            <button type="button" onClick={resetState} className="px-4 py-2 border rounded-md text-sm">
              {t('common.cancel')}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
