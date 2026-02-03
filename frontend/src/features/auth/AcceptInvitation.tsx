import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const VALIDATE_INVITATION = gql`
  query ValidateInvitation($token: String!) {
    validateInvitation(token: $token) {
      valid
      email
      error
    }
  }
`

const ACCEPT_INVITATION = gql`
  mutation AcceptInvitation($token: String!, $password: String!, $firstName: String, $lastName: String) {
    acceptInvitation(token: $token, password: $password, firstName: $firstName, lastName: $lastName) {
      success
      error
    }
  }
`

export function AcceptInvitation() {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data, loading: validating } = useQuery(VALIDATE_INVITATION, {
    variables: { token },
    skip: !token,
  })

  const [acceptInvitation, { loading: accepting }] = useMutation(ACCEPT_INVITATION)

  const validation = data?.validateInvitation

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
      const result = await acceptInvitation({
        variables: { token, password, firstName, lastName },
      })

      if (result.data?.acceptInvitation?.success) {
        // Redirect to login
        navigate('/login', { state: { message: t('auth.accountCreated') } })
      } else {
        setError(result.data?.acceptInvitation?.error || t('auth.acceptFailed'))
      }
    } catch {
      setError(t('auth.acceptFailed'))
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
          <h1 className="text-xl font-semibold text-red-600">{t('auth.invalidInvite')}</h1>
          <p className="mt-2 text-gray-600">{error || t('auth.inviteExpired')}</p>
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
        <h1 className="text-xl font-semibold">{t('auth.setupAccount')}</h1>
        <p className="mt-2 text-gray-600">
          {t('auth.settingUpFor')} <strong>{validation.email}</strong>
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                {t('auth.firstName')}
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
                {t('auth.lastName')}
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('auth.password')}
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
            disabled={accepting}
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {accepting ? (
              <Loader2 className="mx-auto h-5 w-5 animate-spin" />
            ) : (
              t('auth.createAccount')
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
