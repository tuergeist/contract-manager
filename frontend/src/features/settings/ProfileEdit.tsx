import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Loader2, User } from 'lucide-react'
import { useAuth } from '@/lib/auth'

const UPDATE_PROFILE = gql`
  mutation UpdateProfile($firstName: String, $lastName: String, $email: String) {
    updateProfile(firstName: $firstName, lastName: $lastName, email: $email) {
      success
      error
      user {
        id
        email
        firstName
        lastName
      }
    }
  }
`

export function ProfileEdit() {
  const { t } = useTranslation()
  const { user, refetchUser } = useAuth()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const [updateProfile, { loading }] = useMutation(UPDATE_PROFILE)

  // Initialize form with current user data
  useEffect(() => {
    if (user) {
      setFirstName(user.firstName || '')
      setLastName(user.lastName || '')
      setEmail(user.email || '')
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    // Basic email validation
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailPattern.test(email)) {
      setError(t('settings.profile.invalidEmail'))
      return
    }

    try {
      const result = await updateProfile({
        variables: { firstName, lastName, email },
      })

      if (result.data?.updateProfile?.success) {
        setSuccess(true)
        // Refresh user data in auth context
        await refetchUser()
      } else {
        setError(result.data?.updateProfile?.error || t('settings.profile.updateFailed'))
      }
    } catch {
      setError(t('settings.profile.updateFailed'))
    }
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center gap-2">
        <User className="h-5 w-5 text-gray-500" />
        <h2 className="text-lg font-medium">{t('settings.profile.title')}</h2>
      </div>

      <form onSubmit={handleSubmit} className="mt-4 max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.profile.firstName')}
          </label>
          <input
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.profile.lastName')}
          </label>
          <input
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.profile.email')}
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {success && (
          <p className="text-sm text-green-600">{t('settings.profile.updateSuccess')}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {t('common.save')}
        </button>
      </form>
    </div>
  )
}
