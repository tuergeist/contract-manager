import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { UserManagement } from './UserManagement'
import { RoleManagement } from './RoleManagement'

export function TeamSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  // Determine active sub-tab from URL
  const getActiveSubTab = () => {
    if (location.pathname.includes('/roles')) return 'roles'
    return 'users'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'roles':
        navigate('/settings/team/roles')
        break
      default:
        navigate('/settings/team')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="users">{t('settings.team.users')}</TabsTrigger>
        <TabsTrigger value="roles">{t('settings.team.roles')}</TabsTrigger>
      </TabsList>

      <TabsContent value="users">
        <UserManagement />
      </TabsContent>

      <TabsContent value="roles">
        <RoleManagement />
      </TabsContent>
    </Tabs>
  )
}
