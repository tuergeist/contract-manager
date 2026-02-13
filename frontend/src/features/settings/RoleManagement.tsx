import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { Shield, Loader2, Plus, Trash2, Pencil, X } from 'lucide-react'
import { useAuth } from '@/lib/auth'

interface Role {
  id: number
  name: string
  isSystem: boolean
  permissions: Record<string, boolean>
  userCount: number
}

interface PermissionResource {
  resource: string
  actions: string[]
}

const ROLES_QUERY = gql`
  query Roles {
    roles {
      id
      name
      isSystem
      permissions
      userCount
    }
    permissionRegistry {
      resource
      actions
    }
  }
`

const CREATE_ROLE = gql`
  mutation CreateRole($name: String!, $permissions: JSON) {
    createRole(name: $name, permissions: $permissions) {
      success
      error
      role {
        id
        name
        isSystem
        permissions
        userCount
      }
    }
  }
`

const UPDATE_ROLE_PERMISSIONS = gql`
  mutation UpdateRolePermissions($roleId: ID!, $permissions: JSON!) {
    updateRolePermissions(roleId: $roleId, permissions: $permissions) {
      success
      error
      role {
        id
        name
        isSystem
        permissions
        userCount
      }
    }
  }
`

const DELETE_ROLE = gql`
  mutation DeleteRole($roleId: ID!) {
    deleteRole(roleId: $roleId) {
      success
      error
    }
  }
`

export function RoleManagement() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const [editingRole, setEditingRole] = useState<Role | null>(null)
  const [editPermissions, setEditPermissions] = useState<Record<string, boolean>>({})
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newRoleName, setNewRoleName] = useState('')
  const [newRolePermissions, setNewRolePermissions] = useState<Record<string, boolean>>({})
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading, error, refetch } = useQuery(ROLES_QUERY)
  const [createRole, { loading: creating }] = useMutation(CREATE_ROLE)
  const [updatePermissions, { loading: updating }] = useMutation(UPDATE_ROLE_PERMISSIONS)
  const [deleteRole, { loading: deleting }] = useMutation(DELETE_ROLE)

  const canWrite = hasPermission('users', 'write')

  const roles: Role[] = data?.roles || []
  const registry: PermissionResource[] = data?.permissionRegistry || []

  const handleEditRole = (role: Role) => {
    // Build set of valid keys from registry to filter out any stale/invalid keys
    const validKeys = new Set(registry.flatMap((r) => r.actions.map((a) => `${r.resource}.${a}`)))
    setEditingRole(role)
    setEditPermissions(
      Object.fromEntries(Object.entries(role.permissions).filter(([key]) => validKeys.has(key)))
    )
    setMessage(null)
  }

  const handleSavePermissions = async () => {
    if (!editingRole) return
    setMessage(null)
    try {
      const result = await updatePermissions({
        variables: { roleId: editingRole.id, permissions: editPermissions },
      })
      if (result.data?.updateRolePermissions?.success) {
        setMessage({ type: 'success', text: t('settings.roles.permissionsSaved') })
        setEditingRole(null)
        refetch()
      } else {
        setMessage({
          type: 'error',
          text: result.data?.updateRolePermissions?.error || t('settings.roles.permissionsSaveFailed'),
        })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.roles.permissionsSaveFailed') })
    }
  }

  const handleCreateRole = async () => {
    if (!newRoleName.trim()) return
    setMessage(null)
    try {
      const result = await createRole({
        variables: { name: newRoleName.trim(), permissions: newRolePermissions },
      })
      if (result.data?.createRole?.success) {
        setShowCreateDialog(false)
        setNewRoleName('')
        setNewRolePermissions({})
        refetch()
      } else {
        setMessage({
          type: 'error',
          text: result.data?.createRole?.error || t('settings.roles.permissionsSaveFailed'),
        })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.roles.permissionsSaveFailed') })
    }
  }

  const handleDeleteRole = async (role: Role) => {
    if (!confirm(t('settings.roles.confirmDelete'))) return
    try {
      const result = await deleteRole({ variables: { roleId: role.id } })
      if (result.data?.deleteRole?.success) {
        refetch()
      } else {
        setMessage({
          type: 'error',
          text: result.data?.deleteRole?.error || t('settings.roles.permissionsSaveFailed'),
        })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.roles.permissionsSaveFailed') })
    }
  }

  const togglePermission = (
    perms: Record<string, boolean>,
    setPerms: (p: Record<string, boolean>) => void,
    key: string
  ) => {
    setPerms({ ...perms, [key]: !perms[key] })
  }

  if (loading) return <div className="flex justify-center p-4"><Loader2 className="h-6 w-6 animate-spin" /></div>
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">Error loading roles: {error.message}</div>

  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{t('settings.roles.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('settings.roles.description')}</p>
        </div>
        {canWrite && (
          <button
            onClick={() => {
              setShowCreateDialog(true)
              setNewRoleName('')
              setNewRolePermissions({})
              setMessage(null)
            }}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('settings.roles.createRole')}
          </button>
        )}
      </div>

      {message && !editingRole && !showCreateDialog && (
        <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}

      {/* Roles List */}
      <div className="mt-4 space-y-2">
        {roles.map((role) => (
          <div
            key={role.id}
            className="flex items-center justify-between rounded-lg border px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <Shield className={`h-5 w-5 ${role.isSystem ? 'text-purple-500' : 'text-gray-400'}`} />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">{role.name}</span>
                  {role.isSystem && (
                    <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                      {t('settings.roles.system')}
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-500">
                  {role.userCount} {t('settings.roles.userCount').toLowerCase()}
                </span>
              </div>
            </div>
            {canWrite && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleEditRole(role)}
                  className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  title={t('settings.roles.editRole')}
                >
                  <Pencil className="h-4 w-4" />
                </button>
                {!role.isSystem && role.userCount === 0 && (
                  <button
                    onClick={() => handleDeleteRole(role)}
                    disabled={deleting}
                    className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    title={t('settings.roles.deleteRole')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Edit Permissions Dialog */}
      {editingRole && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">
                {t('settings.roles.editRole')}: {editingRole.name}
              </h3>
              <button onClick={() => setEditingRole(null)} className="rounded p-1 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>

            <PermissionMatrix
              registry={registry}
              permissions={editPermissions}
              onChange={(key) => togglePermission(editPermissions, setEditPermissions, key)}
              disabledKeys={
                editingRole.name === 'Admin' && editingRole.isSystem
                  ? registry
                      .filter((r) => r.resource === 'users' || r.resource === 'settings')
                      .flatMap((r) => r.actions.map((a) => `${r.resource}.${a}`))
                  : undefined
              }
              t={t}
            />

            <div className="mt-4 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
              <p className="text-xs font-medium text-gray-500">{t('settings.roles.permissionHints.title')}</p>
              <ul className="mt-1 space-y-0.5 text-xs text-gray-500">
                <li>{t('settings.roles.permissionHints.invoicePaymentMatching')}</li>
                <li>{t('settings.roles.permissionHints.contractCreation')}</li>
                <li>{t('settings.roles.permissionHints.contractItems')}</li>
                <li>{t('settings.roles.permissionHints.invoiceGeneration')}</li>
                <li>{t('settings.roles.permissionHints.customerMatching')}</li>
              </ul>
            </div>

            {message && (
              <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {message.text}
              </p>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setEditingRole(null)}
                className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleSavePermissions}
                disabled={updating}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {updating && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('settings.roles.savePermissions')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Role Dialog */}
      {showCreateDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-2xl rounded-lg bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium">{t('settings.roles.createRole')}</h3>
              <button onClick={() => setShowCreateDialog(false)} className="rounded p-1 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700">
                {t('settings.roles.name')}
              </label>
              <input
                type="text"
                value={newRoleName}
                onChange={(e) => setNewRoleName(e.target.value)}
                placeholder={t('settings.roles.namePlaceholder')}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                autoFocus
              />
            </div>

            <PermissionMatrix
              registry={registry}
              permissions={newRolePermissions}
              onChange={(key) => togglePermission(newRolePermissions, setNewRolePermissions, key)}
              t={t}
            />

            {message && (
              <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {message.text}
              </p>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowCreateDialog(false)}
                className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleCreateRole}
                disabled={creating || !newRoleName.trim()}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {creating && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('settings.roles.createRole')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function PermissionMatrix({
  registry,
  permissions,
  onChange,
  disabledKeys,
  t,
}: {
  registry: PermissionResource[]
  permissions: Record<string, boolean>
  onChange: (key: string) => void
  disabledKeys?: string[]
  t: (key: string) => string
}) {
  // Collect all unique actions across resources
  // Common actions first, invoice-specific actions last
  const allActions = Array.from(
    new Set(registry.flatMap((r) => r.actions))
  ).sort((a, b) => {
    const order = ['read', 'write', 'delete', 'export', 'generate', 'settings']
    const aIdx = order.indexOf(a)
    const bIdx = order.indexOf(b)
    // Unknown actions go to the end
    if (aIdx === -1 && bIdx === -1) return a.localeCompare(b)
    if (aIdx === -1) return 1
    if (bIdx === -1) return -1
    return aIdx - bIdx
  })

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="px-3 py-2 text-left font-medium text-gray-700">
              {t('settings.roles.permissions')}
            </th>
            {allActions.map((action) => (
              <th key={action} className="px-3 py-2 text-center font-medium text-gray-700">
                {t(`settings.roles.actions.${action}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {registry.map((resource) => (
            <tr key={resource.resource} className="border-b last:border-0">
              <td className="px-3 py-2 font-medium text-gray-900">
                {t(`settings.roles.resources.${resource.resource}`)}
              </td>
              {allActions.map((action) => {
                const key = `${resource.resource}.${action}`
                const hasAction = resource.actions.includes(action)
                const isDisabled = disabledKeys?.includes(key) ?? false
                return (
                  <td key={action} className="px-3 py-2 text-center">
                    {hasAction ? (
                      <input
                        type="checkbox"
                        checked={!!permissions[key]}
                        onChange={() => onChange(key)}
                        disabled={isDisabled}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                    ) : (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
