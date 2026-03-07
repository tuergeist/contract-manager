import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Loader2, ShieldCheck } from 'lucide-react'

const VERIFY_2FA = gql`
  mutation Verify2fa($challengeToken: String!, $code: String!) {
    verify2fa(challengeToken: $challengeToken, code: $code) {
      ... on AuthPayload {
        accessToken
        refreshToken
        userId
        email
        tenantId
      }
      ... on AuthError {
        message
      }
    }
  }
`

interface TwoFactorVerifyProps {
  challengeToken: string
  method: string
  onSuccess: (accessToken: string, refreshToken: string) => void
  onCancel: () => void
}

export function TwoFactorVerify({ challengeToken, method, onSuccess, onCancel }: TwoFactorVerifyProps) {
  const { t } = useTranslation()
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [useRecovery, setUseRecovery] = useState(false)

  const [verify, { loading }] = useMutation(VERIFY_2FA)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      const result = await verify({
        variables: { challengeToken, code: code.trim() },
      })

      const data = result.data?.verify2fa
      if (data?.accessToken) {
        onSuccess(data.accessToken, data.refreshToken)
      } else if (data?.message) {
        setError(data.message)
      }
    } catch {
      setError(t('auth.verificationFailed'))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <ShieldCheck className="mx-auto h-12 w-12 text-blue-500" />
          <h2 className="mt-4 text-xl font-semibold text-gray-900">
            {t('auth.twoFactorTitle')}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {method === 'email'
              ? t('auth.twoFactorEmailDesc')
              : useRecovery
                ? t('auth.twoFactorRecoveryDesc')
                : t('auth.twoFactorTotpDesc')
            }
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700">
              {useRecovery ? t('auth.recoveryCode') : t('auth.verificationCode')}
            </label>
            <input
              id="code"
              type="text"
              inputMode={useRecovery ? 'text' : 'numeric'}
              autoComplete="one-time-code"
              autoFocus
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={useRecovery ? 'abcd1234' : '000000'}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-center text-lg tracking-widest placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              maxLength={useRecovery ? 8 : 6}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : t('auth.verify')}
          </button>

          <div className="flex justify-between text-sm">
            {method === 'totp' && (
              <button
                type="button"
                onClick={() => { setUseRecovery(!useRecovery); setCode(''); setError(null) }}
                className="text-blue-600 hover:text-blue-500"
              >
                {useRecovery ? t('auth.useAuthenticator') : t('auth.useRecoveryCode')}
              </button>
            )}
            <button
              type="button"
              onClick={onCancel}
              className="text-gray-500 hover:text-gray-700"
            >
              {t('auth.backToLogin')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
