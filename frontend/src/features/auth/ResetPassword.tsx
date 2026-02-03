import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const VALIDATE_RESET = gql`
  query ValidatePasswordReset($token: String!) {
    validatePasswordReset(token: $token) {
      valid
      email
      error
    }
  }
`

const RESET_PASSWORD = gql`
  mutation ResetPassword($token: String!, $newPassword: String!) {
    resetPassword(token: $token, newPassword: $newPassword) {
      success
      error
    }
  }
`

export function ResetPassword() {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data, loading: validating } = useQuery(VALIDATE_RESET, {
    variables: { token },
    skip: !token,
  })

  const [resetPassword, { loading: resetting }] = useMutation(RESET_PASSWORD)

  const validation = data?.validatePasswordReset

  useEffect(() => {
    if (validation && !validation.valid) {
      setError(validation.error)
    }
  }, [validation])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    if (password.length < 8) {
      setError(t('auth.passwordTooShort'))
      return
    }

    try {
      const result = await resetPassword({
        variables: { token, newPassword: password },
      })

      if (result.data?.resetPassword?.success) {
        navigate('/login', { state: { message: t('auth.passwordReset') } })
      } else {
        setError(result.data?.resetPassword?.error || t('auth.resetFailed'))
      }
    } catch {
      setError(t('auth.resetFailed'))
    }
  }

  if (validating) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!validation?.valid) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-100">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg">
          <h1 className="text-xl font-semibold text-red-600">{t('auth.invalidResetLink')}</h1>
          <p className="mt-2 text-gray-600">{error || t('auth.resetLinkExpired')}</p>
          <button
            onClick={() => navigate('/login')}
            className="mt-6 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            {t('auth.goToLogin')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg">
        <h1 className="text-xl font-semibold">{t('auth.resetPasswordTitle')}</h1>
        <p className="mt-2 text-gray-600">
          {t('auth.resettingFor')} <strong>{validation.email}</strong>
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('auth.newPassword')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">{t('auth.passwordHint')}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('auth.confirmPassword')}
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}

          <button
            type="submit"
            disabled={resetting}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {resetting ? (
              <Loader2 className="mx-auto h-5 w-5 animate-spin" />
            ) : (
              t('auth.setNewPassword')
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
