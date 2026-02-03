import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Loader2, Key } from 'lucide-react'

const CHANGE_PASSWORD = gql`
  mutation ChangePassword($currentPassword: String!, $newPassword: String!) {
    changePassword(currentPassword: $currentPassword, newPassword: $newPassword) {
      success
      error
    }
  }
`

export function PasswordChange() {
  const { t } = useTranslation()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const [changePassword, { loading }] = useMutation(CHANGE_PASSWORD)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    if (newPassword !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    if (newPassword.length < 8) {
      setError(t('auth.passwordTooShort'))
      return
    }

    try {
      const result = await changePassword({
        variables: { currentPassword, newPassword },
      })

      if (result.data?.changePassword?.success) {
        setSuccess(true)
        setCurrentPassword('')
        setNewPassword('')
        setConfirmPassword('')
      } else {
        setError(result.data?.changePassword?.error || t('settings.passwordChangeFailed'))
      }
    } catch {
      setError(t('settings.passwordChangeFailed'))
    }
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center gap-2">
        <Key className="h-5 w-5 text-gray-500" />
        <h2 className="text-lg font-medium">{t('settings.changePassword')}</h2>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.currentPassword')}
          </label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.newPassword')}
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">{t('auth.passwordHint')}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.confirmNewPassword')}
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

        {success && (
          <p className="text-sm text-green-600">{t('settings.passwordChanged')}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {t('settings.changePassword')}
        </button>
      </form>
    </div>
  )
}
