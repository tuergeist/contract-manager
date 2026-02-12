import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import {
  Loader2,
  UserPlus,
  Copy,
  Check,
  X,
  UserX,
  UserCheck,
  Key,
} from 'lucide-react'
import { formatDateTime } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  fullName: string
  isActive: boolean
  isAdmin: boolean
  lastLogin: string | null
  roleNames: string[]
}

interface Invitation {
  id: string
  email: string
  status: string
  expiresAt: string
  createdAt: string
  createdByName: string | null
  inviteUrl: string
  isExpired: boolean
}

const USERS_QUERY = gql`
  query Users {
    users {
      id
      email
      firstName
      lastName
      fullName
      isActive
      isAdmin
      lastLogin
      roleNames
    }
    pendingInvitations {
      id
      email
      status
      expiresAt
      createdAt
      createdByName
      inviteUrl
      isExpired
    }
  }
`

const CREATE_INVITATION = gql`
  mutation CreateInvitation($email: String!, $baseUrl: String, $roleIds: [ID!]) {
    createInvitation(email: $email, baseUrl: $baseUrl, roleIds: $roleIds) {
      success
      error
      inviteUrl
    }
  }
`

const REVOKE_INVITATION = gql`
  mutation RevokeInvitation($invitationId: ID!) {
    revokeInvitation(invitationId: $invitationId) {
      success
      error
    }
  }
`

const DEACTIVATE_USER = gql`
  mutation DeactivateUser($userId: ID!) {
    deactivateUser(userId: $userId) {
      success
      error
    }
  }
`

const REACTIVATE_USER = gql`
  mutation ReactivateUser($userId: ID!) {
    reactivateUser(userId: $userId) {
      success
      error
    }
  }
`

const CREATE_PASSWORD_RESET = gql`
  mutation CreatePasswordReset($userId: ID!, $baseUrl: String) {
    createPasswordReset(userId: $userId, baseUrl: $baseUrl) {
      success
      error
      resetUrl
    }
  }
`

const ROLES_QUERY = gql`
  query RolesForAssignment {
    roles {
      id
      name
    }
  }
`

const ASSIGN_USER_ROLES = gql`
  mutation AssignUserRoles($userId: ID!, $roleIds: [ID!]!) {
    assignUserRoles(userId: $userId, roleIds: $roleIds) {
      success
      error
    }
  }
`

interface RoleOption {
  id: string
  name: string
}

export function UserManagement() {
  const { t } = useTranslation()
  const { user: currentUser, hasPermission } = useAuth()
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRoleIds, setInviteRoleIds] = useState<string[]>([])
  const [inviteUrl, setInviteUrl] = useState<string | null>(null)
  const [resetUrl, setResetUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showInviteModal, setShowInviteModal] = useState(false)

  const { data, loading, refetch } = useQuery(USERS_QUERY)
  const { data: rolesData } = useQuery(ROLES_QUERY)
  const [createInvitation, { loading: creating }] = useMutation(CREATE_INVITATION)
  const [revokeInvitation] = useMutation(REVOKE_INVITATION)
  const [deactivateUser] = useMutation(DEACTIVATE_USER)
  const [reactivateUser] = useMutation(REACTIVATE_USER)
  const [createPasswordReset] = useMutation(CREATE_PASSWORD_RESET)
  const [assignUserRoles] = useMutation(ASSIGN_USER_ROLES)

  const users: User[] = data?.users || []
  const invitations: Invitation[] = data?.pendingInvitations || []
  const availableRoles: RoleOption[] = rolesData?.roles || []

  const handleToggleRole = async (userId: string, currentRoleNames: string[], roleName: string) => {
    const role = availableRoles.find((r) => r.name === roleName)
    if (!role) return
    const isAssigned = currentRoleNames.includes(roleName)
    let newRoleIds: string[]
    if (isAssigned) {
      // Remove role
      newRoleIds = availableRoles
        .filter((r) => currentRoleNames.includes(r.name) && r.name !== roleName)
        .map((r) => r.id)
    } else {
      // Add role
      newRoleIds = availableRoles
        .filter((r) => currentRoleNames.includes(r.name) || r.name === roleName)
        .map((r) => r.id)
    }
    try {
      const result = await assignUserRoles({ variables: { userId, roleIds: newRoleIds } })
      if (result.data?.assignUserRoles?.success) {
        refetch()
      } else {
        setError(result.data?.assignUserRoles?.error || t('settings.roles.rolesUpdateFailed'))
      }
    } catch {
      setError(t('settings.roles.rolesUpdateFailed'))
    }
  }

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleCreateInvitation = async () => {
    setError(null)
    setInviteUrl(null)
    try {
      const result = await createInvitation({
        variables: {
          email: inviteEmail,
          baseUrl: window.location.origin,
          roleIds: inviteRoleIds.length > 0 ? inviteRoleIds : undefined,
        }
      })
      if (result.data?.createInvitation?.success) {
        setInviteUrl(result.data.createInvitation.inviteUrl)
        refetch()
      } else {
        setError(result.data?.createInvitation?.error || t('users.inviteFailed'))
      }
    } catch {
      setError(t('users.inviteFailed'))
    }
  }

  const handleRevokeInvitation = async (invitationId: string) => {
    if (!confirm(t('users.confirmRevoke'))) return
    try {
      await revokeInvitation({ variables: { invitationId } })
      refetch()
    } catch {
      // ignore
    }
  }

  const handleDeactivateUser = async (userId: string) => {
    if (!confirm(t('users.confirmDeactivate'))) return
    try {
      const result = await deactivateUser({ variables: { userId } })
      if (result.data?.deactivateUser?.success) {
        refetch()
      } else {
        setError(result.data?.deactivateUser?.error)
      }
    } catch {
      // ignore
    }
  }

  const handleReactivateUser = async (userId: string) => {
    try {
      await reactivateUser({ variables: { userId } })
      refetch()
    } catch {
      // ignore
    }
  }

  const handleCreatePasswordReset = async (userId: string) => {
    setResetUrl(null)
    try {
      const result = await createPasswordReset({
        variables: { userId, baseUrl: window.location.origin }
      })
      if (result.data?.createPasswordReset?.success) {
        setResetUrl(result.data.createPasswordReset.resetUrl)
      }
    } catch {
      // ignore
    }
  }

  const closeInviteModal = () => {
    setShowInviteModal(false)
    setInviteEmail('')
    setInviteRoleIds([])
    setInviteUrl(null)
    setError(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  // Check if current user has user management permission
  if (!hasPermission('users', 'read')) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{t('users.accessDenied')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Users Section */}
      <div className="rounded-lg border bg-white">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-medium">{t('users.title')}</h2>
          <button
            onClick={() => {
              const managerRole = availableRoles.find((r) => r.name === 'Manager')
              setInviteRoleIds(managerRole ? [managerRole.id] : [])
              setShowInviteModal(true)
            }}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <UserPlus className="h-4 w-4" />
            {t('users.inviteUser')}
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {resetUrl && (
          <div className="mx-6 mt-4 rounded-md bg-blue-50 p-3">
            <p className="text-sm font-medium text-blue-800">{t('users.resetLinkCreated')}</p>
            <div className="mt-2 flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={resetUrl}
                className="flex-1 rounded border bg-white px-2 py-1 text-sm"
              />
              <button
                onClick={() => handleCopy(resetUrl, 'reset')}
                className="inline-flex items-center gap-1 rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
              >
                {copied === 'reset' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied === 'reset' ? t('users.copied') : t('users.copyLink')}
              </button>
              <button
                onClick={() => setResetUrl(null)}
                className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('users.name')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('users.email')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('settings.roles.permissions')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('users.status')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('users.lastLogin')}
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('users.actions')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {users.map((user) => (
              <tr key={user.id}>
                <td className="whitespace-nowrap px-6 py-4">
                  <span className="font-medium text-gray-900">
                    {user.fullName || user.email}
                  </span>
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                  {user.email}
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {availableRoles.map((role) => {
                      const isAssigned = user.roleNames?.includes(role.name)
                      return (
                        <button
                          key={role.id}
                          onClick={() => hasPermission('users', 'write') ? handleToggleRole(user.id, user.roleNames || [], role.name) : undefined}
                          disabled={!hasPermission('users', 'write')}
                          className={`rounded-full px-2 py-0.5 text-xs font-medium transition-colors ${
                            isAssigned
                              ? role.name === 'Admin'
                                ? 'bg-purple-100 text-purple-800'
                                : role.name === 'Manager'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-green-100 text-green-800'
                              : 'bg-gray-50 text-gray-400 hover:bg-gray-100'
                          } ${hasPermission('users', 'write') ? 'cursor-pointer' : 'cursor-default'}`}
                          title={isAssigned ? `Remove ${role.name}` : `Add ${role.name}`}
                        >
                          {role.name}
                        </button>
                      )
                    })}
                  </div>
                </td>
                <td className="whitespace-nowrap px-6 py-4">
                  {user.isActive ? (
                    <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                      {t('users.active')}
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800">
                      {t('users.inactive')}
                    </span>
                  )}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                  {user.lastLogin ? formatDateTime(user.lastLogin) : '-'}
                </td>
                <td className="whitespace-nowrap px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleCreatePasswordReset(user.id)}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-blue-600"
                      title={t('users.resetPassword')}
                    >
                      <Key className="h-4 w-4" />
                    </button>
                    {String(user.id) !== String(currentUser?.id) && (
                      user.isActive ? (
                        <button
                          onClick={() => handleDeactivateUser(user.id)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                          title={t('users.deactivate')}
                        >
                          <UserX className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleReactivateUser(user.id)}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-green-600"
                          title={t('users.reactivate')}
                        >
                          <UserCheck className="h-4 w-4" />
                        </button>
                      )
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pending Invitations */}
      {invitations.length > 0 && (
        <div className="rounded-lg border bg-white">
          <div className="border-b px-6 py-4">
            <h2 className="text-lg font-medium">{t('users.pendingInvitations')}</h2>
          </div>

          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('users.email')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('users.invitedBy')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('users.expiresAt')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('users.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {invitations.map((invitation) => (
                <tr key={invitation.id} className={invitation.isExpired ? 'bg-gray-50' : ''}>
                  <td className="whitespace-nowrap px-6 py-4 font-medium text-gray-900">
                    {invitation.email}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {invitation.createdByName || '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {formatDateTime(invitation.expiresAt)}
                    {invitation.isExpired && (
                      <span className="ml-2 text-xs text-red-500">({t('users.expired')})</span>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {!invitation.isExpired && (
                        <button
                          onClick={() => handleCopy(invitation.inviteUrl, invitation.id)}
                          className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-1 text-sm text-gray-700 hover:bg-gray-200"
                        >
                          {copied === invitation.id ? (
                            <Check className="h-3 w-3" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                          {copied === invitation.id ? t('users.copied') : t('users.copyLink')}
                        </button>
                      )}
                      <button
                        onClick={() => handleRevokeInvitation(invitation.id)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
                        title={t('users.revoke')}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-lg font-medium">{t('users.inviteUser')}</h3>

            {!inviteUrl ? (
              <>
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('users.email')}
                  </label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="user@example.com"
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('settings.roles.assignRoles')}
                  </label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {availableRoles.map((role) => {
                      const isSelected = inviteRoleIds.includes(role.id)
                      return (
                        <button
                          key={role.id}
                          type="button"
                          onClick={() => {
                            setInviteRoleIds((prev) =>
                              isSelected
                                ? prev.filter((id) => id !== role.id)
                                : [...prev, role.id]
                            )
                          }}
                          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                            isSelected
                              ? 'bg-blue-100 text-blue-800 ring-1 ring-blue-300'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                          }`}
                        >
                          {role.name}
                        </button>
                      )
                    })}
                  </div>
                </div>

                {error && (
                  <p className="mt-2 text-sm text-red-600">{error}</p>
                )}

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={closeInviteModal}
                    className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
                  >
                    {t('common.cancel')}
                  </button>
                  <button
                    onClick={handleCreateInvitation}
                    disabled={creating || !inviteEmail}
                    className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {creating && <Loader2 className="h-4 w-4 animate-spin" />}
                    {t('users.sendInvite')}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="mt-4 text-sm text-gray-600">{t('users.inviteCreated')}</p>

                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700">
                    {t('users.inviteLink')}
                  </label>
                  <div className="mt-1 flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={inviteUrl}
                      className="flex-1 rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm"
                    />
                    <button
                      onClick={() => handleCopy(inviteUrl, 'invite-modal')}
                      className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      {copied === 'invite-modal' ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                      {copied === 'invite-modal' ? t('users.copied') : t('users.copyLink')}
                    </button>
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={closeInviteModal}
                    className="rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200"
                  >
                    {t('common.cancel')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
