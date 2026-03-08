import { useTranslation } from 'react-i18next'
import { useAuth } from '../../lib/auth'
import { SecuritySettings } from '../settings/SecuritySettings'
import { useQuery, gql } from '@apollo/client'
import { Navigate } from 'react-router-dom'

const ME_2FA_CHECK = gql`
  query Me2faCheck {
    me {
      id
      twoFactorEnabled
    }
  }
`

export function TwoFactorSetup() {
  const { t } = useTranslation()
  const { token, logout } = useAuth()
  const { data, loading } = useQuery(ME_2FA_CHECK, {
    fetchPolicy: 'network-only',
  })

  // No token at all — go to login
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // If 2FA is already enabled, redirect to main app (re-login will happen naturally)
  if (!loading && data?.me?.twoFactorEnabled) {
    // User set up 2FA — they need to re-login with full tokens
    logout()
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            {t('auth.twoFactorSetupTitle')}
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            {t('auth.twoFactorSetupDescription')}
          </p>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <SecuritySettings />
        </div>

        <div className="text-center">
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            {t('auth.signOut')}
          </button>
        </div>
      </div>
    </div>
  )
}
