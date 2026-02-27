import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const REVENUE_GOALS_QUERY = gql`
  query RevenueGoals($year: Int!) {
    revenueGoals(year: $year) {
      id
      year
      revenueType
      targetAmount
    }
  }
`

const SET_REVENUE_GOAL = gql`
  mutation SetRevenueGoal($year: Int!, $revenueType: String!, $targetAmount: Decimal!) {
    setRevenueGoal(year: $year, revenueType: $revenueType, targetAmount: $targetAmount) {
      success
      error
      goal {
        id
        year
        revenueType
        targetAmount
      }
    }
  }
`

const DELETE_REVENUE_GOAL = gql`
  mutation DeleteRevenueGoal($year: Int!, $revenueType: String!) {
    deleteRevenueGoal(year: $year, revenueType: $revenueType) {
      success
      error
    }
  }
`

interface RevenueGoal {
  id: number
  year: number
  revenueType: string
  targetAmount: string
}

const REVENUE_TYPES = [
  { key: 'recurring', i18nKey: 'products.revenueTypes.recurring' },
  { key: 'advanced_development', i18nKey: 'products.revenueTypes.advancedDevelopment' },
  { key: 'training_implementation', i18nKey: 'products.revenueTypes.trainingImplementation' },
] as const

export function RevenueGoalSettings() {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [goals, setGoals] = useState<Record<string, string>>({
    recurring: '',
    advanced_development: '',
    training_implementation: '',
  })
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const { data, loading } = useQuery<{ revenueGoals: RevenueGoal[] }>(REVENUE_GOALS_QUERY, {
    variables: { year: selectedYear },
  })
  const [setRevenueGoal] = useMutation(SET_REVENUE_GOAL)
  const [deleteRevenueGoal] = useMutation(DELETE_REVENUE_GOAL)

  useEffect(() => {
    if (data?.revenueGoals) {
      const newGoals: Record<string, string> = {
        recurring: '',
        advanced_development: '',
        training_implementation: '',
      }
      for (const goal of data.revenueGoals) {
        newGoals[goal.revenueType] = goal.targetAmount
      }
      setGoals(newGoals)
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    setSaving(true)
    try {
      for (const rt of REVENUE_TYPES) {
        const value = goals[rt.key]?.trim()
        if (value && parseFloat(value) > 0) {
          const { data: result } = await setRevenueGoal({
            variables: {
              year: selectedYear,
              revenueType: rt.key,
              targetAmount: value,
            },
          })
          if (!result?.setRevenueGoal?.success) {
            setMessage({ type: 'error', text: result?.setRevenueGoal?.error || t('settings.revenueGoals.saveFailed') })
            setSaving(false)
            return
          }
        } else {
          // If cleared, delete the goal
          await deleteRevenueGoal({
            variables: { year: selectedYear, revenueType: rt.key },
          })
        }
      }
      setMessage({ type: 'success', text: t('settings.revenueGoals.saved') })
    } catch {
      setMessage({ type: 'error', text: t('settings.revenueGoals.saveFailed') })
    } finally {
      setSaving(false)
    }
  }

  const years = Array.from({ length: 5 }, (_, i) => currentYear - 1 + i)
  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.revenueGoals.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.revenueGoals.description')}</p>

      <div className="mt-4 space-y-4">
        <div className="max-w-xs">
          <label className="block text-sm font-medium text-gray-700">{t('settings.revenueGoals.year')}</label>
          <select
            value={selectedYear}
            onChange={(e) => {
              setSelectedYear(parseInt(e.target.value))
              setMessage(null)
            }}
            className={inputClass}
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="flex items-center gap-2 py-4">
            <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
          </div>
        ) : (
          <div className="space-y-3">
            {REVENUE_TYPES.map((rt) => (
              <div key={rt.key} className="max-w-md">
                <label className="block text-sm font-medium text-gray-700">
                  {t(rt.i18nKey)}
                </label>
                <div className="relative mt-1">
                  <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500 text-sm">EUR</span>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={goals[rt.key]}
                    onChange={(e) => setGoals({ ...goals, [rt.key]: e.target.value })}
                    placeholder="0"
                    className="mt-0 block w-full rounded-md border border-gray-300 py-2 pl-12 pr-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('settings.revenueGoals.save')}
          </button>
        </div>

        {message && (
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}
      </div>
    </div>
  )
}
