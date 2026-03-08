import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { useAuth } from '../../lib/auth'
import { TwoFactorVerify } from './TwoFactorVerify'

const SIGNUP_ENABLED = gql`
  query SignupEnabled {
    signupEnabled
  }
`

export function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { login, loginWithTokens, isLoading: authLoading } = useAuth()
  const { data: signupData } = useQuery(SIGNUP_ENABLED)
  const signupEnabled = signupData?.signupEnabled ?? false

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [twoFactor, setTwoFactor] = useState<{ challengeToken: string; method: string } | null>(null)

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const result = await login(email, password)

    if (result.success) {
      navigate(from, { replace: true })
    } else if (result.setupRequired) {
      navigate('/setup-2fa', { replace: true })
    } else if (result.twoFactor) {
      setTwoFactor(result.twoFactor)
    } else {
      setError(result.error || t('auth.loginFailed'))
    }

    setIsSubmitting(false)
  }

  const handleDevLogin = async () => {
    setError(null)
    setIsSubmitting(true)
    const result = await login('admin@test.local', 'admin123')
    if (result.success) {
      navigate(from, { replace: true })
    } else if (result.setupRequired) {
      navigate('/setup-2fa', { replace: true })
    } else if (result.twoFactor) {
      setTwoFactor(result.twoFactor)
    } else {
      setError(result.error || t('auth.loginFailed'))
    }
    setIsSubmitting(false)
  }

  const handle2faSuccess = async (accessToken: string, refreshToken: string) => {
    await loginWithTokens(accessToken, refreshToken)
    navigate(from, { replace: true })
  }

  if (twoFactor) {
    return (
      <TwoFactorVerify
        challengeToken={twoFactor.challengeToken}
        method={twoFactor.method}
        onSuccess={handle2faSuccess}
        onCancel={() => setTwoFactor(null)}
      />
    )
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">{t('common.loading')}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h1 className="text-center text-3xl font-bold text-gray-900">
            Contract Manager
          </h1>
          <h2 className="mt-6 text-center text-xl text-gray-600">
            {t('auth.signIn')}
          </h2>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                {t('auth.email')}
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="admin@test.local"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                {t('auth.password')}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Link
              to="/forgot-password"
              className="text-sm font-medium text-blue-600 hover:text-blue-500"
            >
              {t('auth.forgotPassword')}
            </Link>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? t('common.loading') : t('auth.signInButton')}
            </button>
          </div>

          {isLocalhost && (
            <div>
              <button
                type="button"
                onClick={handleDevLogin}
                disabled={isSubmitting}
                className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Dev Login (admin@test.local)
              </button>
            </div>
          )}
        </form>

        {signupEnabled && (
          <p className="text-center text-sm text-gray-600">
            {t('auth.noAccount')}{' '}
            <Link to="/signup" className="font-medium text-blue-600 hover:text-blue-500">
              {t('auth.signUp')}
            </Link>
          </p>
        )}
      </div>
    </div>
  )
}
