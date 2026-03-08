import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { useAuth } from '../../lib/auth'

const VERIFY_SIGNUP = gql`
  mutation VerifySignup($token: String!) {
    verifySignup(token: $token) {
      success
      error
      accessToken
      refreshToken
    }
  }
`

export function VerifySignup() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const { loginWithTokens } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [verified, setVerified] = useState(false)

  const [verifySignup] = useMutation(VERIFY_SIGNUP)
  const token = searchParams.get('token')

  useEffect(() => {
    if (!token) {
      setError(t('auth.verifyFailedDesc'))
      return
    }

    const verify = async () => {
      try {
        const result = await verifySignup({ variables: { token } })
        const data = result.data?.verifySignup

        if (data?.success && data.accessToken && data.refreshToken) {
          setVerified(true)
          await loginWithTokens(data.accessToken, data.refreshToken)
          setTimeout(() => {
            window.location.href = '/'
          }, 1500)
        } else {
          setError(data?.error || t('auth.verifyFailedDesc'))
        }
      } catch {
        setError(t('auth.verifyFailedDesc'))
      }
    }

    verify()
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  if (verified) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-6 text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
          <h2 className="text-xl font-semibold text-gray-900">
            {t('auth.verifySuccess')}
          </h2>
          <p className="text-sm text-gray-600">
            {t('auth.verifySuccessDesc')}
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-6 text-center">
          <XCircle className="mx-auto h-12 w-12 text-red-500" />
          <h2 className="text-xl font-semibold text-gray-900">
            {t('auth.verifyFailed')}
          </h2>
          <p className="text-sm text-gray-600">{error}</p>
          <Link
            to="/login"
            className="inline-block text-sm font-medium text-blue-600 hover:text-blue-500"
          >
            {t('auth.backToLogin')}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6 text-center">
        <Loader2 className="mx-auto h-12 w-12 text-blue-500 animate-spin" />
        <h2 className="text-xl font-semibold text-gray-900">
          {t('auth.verifyingAccount')}
        </h2>
      </div>
    </div>
  )
}
