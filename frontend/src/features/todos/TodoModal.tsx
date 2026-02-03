import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import { useAuth } from '@/lib/auth'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2 } from 'lucide-react'

// Helper functions for date calculations
function getNextMonday(from: Date): Date {
  const date = new Date(from)
  const day = date.getDay()
  const daysUntilMonday = day === 0 ? 1 : 8 - day
  date.setDate(date.getDate() + daysUntilMonday)
  return date
}

function getFirstMondayOfNextMonth(from: Date): Date {
  const date = new Date(from.getFullYear(), from.getMonth() + 1, 1)
  const day = date.getDay()
  const daysUntilMonday = day === 0 ? 1 : day === 1 ? 0 : 8 - day
  date.setDate(date.getDate() + daysUntilMonday)
  return date
}

function getFirstMondayOfNextQuarter(from: Date): Date {
  const currentQuarter = Math.floor(from.getMonth() / 3)
  const nextQuarterMonth = (currentQuarter + 1) * 3
  const year = nextQuarterMonth >= 12 ? from.getFullYear() + 1 : from.getFullYear()
  const month = nextQuarterMonth % 12
  const date = new Date(year, month, 1)
  const day = date.getDay()
  const daysUntilMonday = day === 0 ? 1 : day === 1 ? 0 : 8 - day
  date.setDate(date.getDate() + daysUntilMonday)
  return date
}

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0]
}

const USERS_QUERY = gql`
  query UsersForTodo {
    users {
      id
      email
      firstName
      lastName
      isActive
    }
  }
`

const CREATE_TODO = gql`
  mutation CreateTodo(
    $text: String!
    $isPublic: Boolean!
    $reminderDate: Date
    $assignedToId: Int
    $contractId: Int
    $contractItemId: Int
    $customerId: Int
  ) {
    createTodo(
      text: $text
      isPublic: $isPublic
      reminderDate: $reminderDate
      assignedToId: $assignedToId
      contractId: $contractId
      contractItemId: $contractItemId
      customerId: $customerId
    ) {
      success
      error
      todo {
        id
        text
        reminderDate
        isPublic
        isCompleted
        entityType
        entityName
        entityId
        createdByName
        assignedToId
        assignedToName
      }
    }
  }
`

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  isActive: boolean
}

export type TodoContext = {
  type: 'contract' | 'contract_item' | 'customer'
  id: number
  name: string
}

interface TodoModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  context?: TodoContext
  onSuccess?: () => void
}

export function TodoModal({ open, onOpenChange, context, onSuccess }: TodoModalProps) {
  const { t } = useTranslation()
  const { user: currentUser } = useAuth()
  const [text, setText] = useState('')
  const [reminderDate, setReminderDate] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [assignedToId, setAssignedToId] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const { data: usersData } = useQuery(USERS_QUERY, { skip: !open })
  const [createTodo, { loading }] = useMutation(CREATE_TODO)

  const users = (usersData?.users || []).filter((u: User) => u.isActive && u.id) as User[]

  // Calculate date suggestions
  const dateSuggestions = useMemo(() => {
    const today = new Date()
    return {
      nextWeek: formatDateForInput(getNextMonday(today)),
      nextMonth: formatDateForInput(getFirstMondayOfNextMonth(today)),
      nextQuarter: formatDateForInput(getFirstMondayOfNextQuarter(today)),
    }
  }, [])

  // Reset form when modal opens - default assignee to current user
  useEffect(() => {
    if (open) {
      setText('')
      setReminderDate('')
      setIsPublic(true)
      setAssignedToId(currentUser?.id ? String(currentUser.id) : '')
      setError(null)
    }
  }, [open, currentUser?.id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!text.trim()) {
      setError(t('todos.errorTextRequired'))
      return
    }

    if (!context) {
      setError(t('todos.errorContextRequired'))
      return
    }

    try {
      const variables: Record<string, unknown> = {
        text: text.trim(),
        isPublic,
        reminderDate: reminderDate || null,
        assignedToId: assignedToId ? parseInt(assignedToId) : null,
      }

      // Set the appropriate entity ID based on context type
      if (context.type === 'contract') {
        variables.contractId = context.id
      } else if (context.type === 'contract_item') {
        variables.contractItemId = context.id
      } else if (context.type === 'customer') {
        variables.customerId = context.id
      }

      const { data } = await createTodo({ variables })

      if (data?.createTodo?.success) {
        onOpenChange(false)
        onSuccess?.()
      } else {
        setError(data?.createTodo?.error || t('todos.errorCreate'))
      }
    } catch (err) {
      setError(t('todos.errorCreate'))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t('todos.addTodo')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* Context display */}
            {context && (
              <div className="grid gap-2">
                <Label className="text-muted-foreground">{t('todos.linkedTo')}</Label>
                <div className="text-sm font-medium">{context.name}</div>
              </div>
            )}

            {/* Todo text */}
            <div className="grid gap-2">
              <Label htmlFor="todo-text">{t('todos.description')}</Label>
              <Textarea
                id="todo-text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={t('todos.descriptionPlaceholder')}
                rows={3}
                data-testid="todo-text-input"
              />
            </div>

            {/* Reminder date */}
            <div className="grid gap-2">
              <Label htmlFor="reminder-date">{t('todos.reminderDate')}</Label>
              <Input
                id="reminder-date"
                type="date"
                value={reminderDate}
                onChange={(e) => setReminderDate(e.target.value)}
                data-testid="todo-reminder-date"
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setReminderDate(dateSuggestions.nextWeek)}
                  className="text-xs"
                >
                  {t('todos.nextWeek')}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setReminderDate(dateSuggestions.nextMonth)}
                  className="text-xs"
                >
                  {t('todos.nextMonth')}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setReminderDate(dateSuggestions.nextQuarter)}
                  className="text-xs"
                >
                  {t('todos.nextQuarter')}
                </Button>
              </div>
            </div>

            {/* Assign to */}
            <div className="grid gap-2">
              <Label htmlFor="assigned-to">{t('todos.assignTo')}</Label>
              <Select value={assignedToId || '__none__'} onValueChange={(val) => setAssignedToId(val === '__none__' ? '' : val)}>
                <SelectTrigger id="assigned-to" data-testid="todo-assigned-to">
                  <SelectValue placeholder={t('todos.assignToPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">{t('todos.unassigned')}</SelectItem>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={String(user.id)}>
                      {user.firstName && user.lastName
                        ? `${user.firstName} ${user.lastName}`
                        : user.email}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Public checkbox */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is-public"
                checked={isPublic}
                onCheckedChange={(checked) => setIsPublic(checked === true)}
                data-testid="todo-is-public"
              />
              <Label htmlFor="is-public" className="text-sm font-normal cursor-pointer">
                {t('todos.shareWithTeam')}
              </Label>
            </div>

            {/* Error message */}
            {error && (
              <div className="text-sm text-destructive">{error}</div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={loading} data-testid="todo-submit">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('todos.add')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
