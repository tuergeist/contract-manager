import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, AlertCircle } from 'lucide-react'
import { KPICard } from './KPICard'
import { TodoList, type TodoItem } from '@/features/todos'
import { Checkbox } from '@/components/ui/checkbox'

const DASHBOARD_KPIS_QUERY = gql`
  query DashboardKPIs {
    dashboardKpis {
      totalActiveContracts
      totalContractValue
      annualRecurringRevenue
      yearToDateRevenue
      currentYearForecast
      nextYearForecast
    }
  }
`

const MY_TODOS_QUERY = gql`
  query MyTodos($limit: Int) {
    myTodos(limit: $limit) {
      id
      text
      reminderDate
      isPublic
      isCompleted
      completedAt
      entityType
      entityName
      entityId
      createdById
      createdByName
      assignedToId
      assignedToName
      contractId
      contractItemId
      customerId
    }
  }
`

const TEAM_TODOS_QUERY = gql`
  query TeamTodos($limit: Int) {
    teamTodos(limit: $limit) {
      id
      text
      reminderDate
      isPublic
      isCompleted
      completedAt
      entityType
      entityName
      entityId
      createdById
      createdByName
      assignedToId
      assignedToName
      contractId
      contractItemId
      customerId
    }
  }
`

interface DashboardKPIs {
  totalActiveContracts: number
  totalContractValue: string
  annualRecurringRevenue: string
  yearToDateRevenue: string
  currentYearForecast: string
  nextYearForecast: string
}

interface DashboardKPIsData {
  dashboardKpis: DashboardKPIs
}

interface TodosData {
  myTodos?: TodoItem[]
  teamTodos?: TodoItem[]
}

export function Dashboard() {
  const { t } = useTranslation()
  const [showMyRecentlyClosed, setShowMyRecentlyClosed] = useState(false)
  const [showTeamRecentlyClosed, setShowTeamRecentlyClosed] = useState(false)

  const { data: kpisData, loading: kpisLoading, error: kpisError } = useQuery<DashboardKPIsData>(DASHBOARD_KPIS_QUERY)
  const { data: myTodosData, loading: myTodosLoading, refetch: refetchMyTodos } = useQuery<TodosData>(MY_TODOS_QUERY, {
    variables: { limit: 50 },  // Fetch more to account for filtering
  })
  const { data: teamTodosData, loading: teamTodosLoading, refetch: refetchTeamTodos } = useQuery<TodosData>(TEAM_TODOS_QUERY, {
    variables: { limit: 50 },  // Fetch more to account for filtering
  })

  const handleTodoUpdate = () => {
    refetchMyTodos()
    refetchTeamTodos()
  }

  // Filter todos: hide completed > 2 days ago, unless showing recently closed (up to 14 days)
  const myTodos = useMemo(() => {
    const todos = myTodosData?.myTodos || []
    const now = new Date()
    const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000)
    const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)

    return todos.filter((todo) => {
      if (!todo.isCompleted) return true
      if (!todo.completedAt) return true
      const completedDate = new Date(todo.completedAt)
      if (showMyRecentlyClosed) {
        return completedDate >= fourteenDaysAgo
      }
      return completedDate >= twoDaysAgo
    })
  }, [myTodosData, showMyRecentlyClosed])

  const teamTodos = useMemo(() => {
    const todos = teamTodosData?.teamTodos || []
    const now = new Date()
    const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000)
    const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)

    return todos.filter((todo) => {
      if (!todo.isCompleted) return true
      if (!todo.completedAt) return true
      const completedDate = new Date(todo.completedAt)
      if (showTeamRecentlyClosed) {
        return completedDate >= fourteenDaysAgo
      }
      return completedDate >= twoDaysAgo
    })
  }, [teamTodosData, showTeamRecentlyClosed])

  if (kpisLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (kpisError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-destructive">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p>{t('common.error')}: {kpisError.message}</p>
      </div>
    )
  }

  const kpis = kpisData?.dashboardKpis

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('dashboard.title')}</h1>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
        <KPICard
          title={t('dashboard.kpis.totalActiveContracts')}
          value={kpis?.totalActiveContracts ?? 0}
          explanation={t('dashboard.kpis.totalActiveContractsExplanation')}
        />
        <KPICard
          title={t('dashboard.kpis.totalContractValue')}
          value={parseFloat(kpis?.totalContractValue ?? '0')}
          explanation={t('dashboard.kpis.totalContractValueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.annualRecurringRevenue')}
          value={parseFloat(kpis?.annualRecurringRevenue ?? '0')}
          explanation={t('dashboard.kpis.annualRecurringRevenueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.yearToDateRevenue')}
          value={parseFloat(kpis?.yearToDateRevenue ?? '0')}
          explanation={t('dashboard.kpis.yearToDateRevenueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.currentYearForecast')}
          value={parseFloat(kpis?.currentYearForecast ?? '0')}
          explanation={t('dashboard.kpis.currentYearForecastExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.nextYearForecast')}
          value={parseFloat(kpis?.nextYearForecast ?? '0')}
          explanation={t('dashboard.kpis.nextYearForecastExplanation')}
          isCurrency
        />
      </div>

      {/* Todos Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* My Todos */}
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">{t('todos.myTodos')}</h2>
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
              <Checkbox
                checked={showMyRecentlyClosed}
                onCheckedChange={(checked) => setShowMyRecentlyClosed(checked === true)}
              />
              {t('todos.showRecentlyClosed')}
            </label>
          </div>
          {myTodosLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <TodoList
              todos={myTodos}
              onUpdate={handleTodoUpdate}
              canDelete={() => true}
            />
          )}
        </div>

        {/* Team Todos */}
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">{t('todos.teamTodos')}</h2>
            <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
              <Checkbox
                checked={showTeamRecentlyClosed}
                onCheckedChange={(checked) => setShowTeamRecentlyClosed(checked === true)}
              />
              {t('todos.showRecentlyClosed')}
            </label>
          </div>
          {teamTodosLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <TodoList
              todos={teamTodos}
              showCreator
              onUpdate={handleTodoUpdate}
              canDelete={() => false}
            />
          )}
        </div>
      </div>

    </div>
  )
}
