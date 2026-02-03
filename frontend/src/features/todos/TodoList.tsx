import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMutation, gql } from '@apollo/client'
import { format, parseISO } from 'date-fns'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Trash2, Calendar, User, UserCheck, Pencil, X, Check } from 'lucide-react'
import { cn } from '@/lib/utils'

const UPDATE_TODO = gql`
  mutation UpdateTodo(
    $todoId: Int!
    $text: String
    $reminderDate: Date
    $isPublic: Boolean
    $isCompleted: Boolean
  ) {
    updateTodo(
      todoId: $todoId
      text: $text
      reminderDate: $reminderDate
      isPublic: $isPublic
      isCompleted: $isCompleted
    ) {
      success
      error
      todo {
        id
        text
        reminderDate
        isPublic
        isCompleted
        assignedToId
        assignedToName
      }
    }
  }
`

const DELETE_TODO = gql`
  mutation DeleteTodo($todoId: Int!) {
    deleteTodo(todoId: $todoId) {
      success
      error
    }
  }
`

export interface TodoItem {
  id: number
  text: string
  reminderDate: string | null
  isPublic: boolean
  isCompleted: boolean
  entityType: string
  entityName: string
  entityId: number
  createdById: number
  createdByName: string
  assignedToId: number | null
  assignedToName: string | null
  contractId: number | null
  contractItemId: number | null
  customerId: number | null
}

interface TodoListProps {
  todos: TodoItem[]
  showCreator?: boolean
  onUpdate?: () => void
  canDelete?: (todo: TodoItem) => boolean
  currentUserId?: number
}

export function TodoList({ todos, showCreator = false, onUpdate, canDelete, currentUserId }: TodoListProps) {
  const { t } = useTranslation()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [editReminderDate, setEditReminderDate] = useState('')
  const [editIsPublic, setEditIsPublic] = useState(false)

  const [updateTodo] = useMutation(UPDATE_TODO)
  const [deleteTodo] = useMutation(DELETE_TODO)

  const handleToggleComplete = async (todo: TodoItem) => {
    try {
      await updateTodo({
        variables: {
          todoId: todo.id,
          isCompleted: !todo.isCompleted,
        },
        optimisticResponse: {
          updateTodo: {
            __typename: 'TodoUpdateResult',
            success: true,
            error: null,
            todo: {
              __typename: 'TodoItemType',
              id: todo.id,
              text: todo.text,
              reminderDate: todo.reminderDate,
              isPublic: todo.isPublic,
              isCompleted: !todo.isCompleted,
            },
          },
        },
      })
      onUpdate?.()
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const handleDelete = async (todo: TodoItem) => {
    if (!confirm(t('todos.confirmDelete'))) return

    try {
      await deleteTodo({
        variables: { todoId: todo.id },
      })
      onUpdate?.()
    } catch (error) {
      console.error('Failed to delete todo:', error)
    }
  }

  const startEdit = (todo: TodoItem) => {
    setEditingId(todo.id)
    setEditText(todo.text)
    setEditReminderDate(todo.reminderDate || '')
    setEditIsPublic(todo.isPublic)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditText('')
    setEditReminderDate('')
    setEditIsPublic(false)
  }

  const handleSaveEdit = async (todo: TodoItem) => {
    if (!editText.trim()) return

    try {
      const result = await updateTodo({
        variables: {
          todoId: todo.id,
          text: editText.trim(),
          reminderDate: editReminderDate || null,
          isPublic: editIsPublic,
        },
      })

      if (result.data?.updateTodo?.success) {
        setEditingId(null)
        onUpdate?.()
      } else {
        alert(result.data?.updateTodo?.error || 'Failed to update todo')
      }
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null
    return format(parseISO(dateStr), 'dd.MM.yyyy')
  }

  const getEntityLink = (todo: TodoItem): string => {
    if (todo.contractId) {
      return `/contracts/${todo.contractId}`
    }
    if (todo.contractItemId && todo.entityName) {
      // Contract item - link to parent contract
      // The entityName contains the contract info
      return `/contracts/${todo.contractId || ''}`
    }
    if (todo.customerId) {
      return `/customers/${todo.customerId}`
    }
    return '#'
  }

  const canEdit = (todo: TodoItem) => {
    // Only creator can edit
    if (currentUserId) {
      return todo.createdById === currentUserId
    }
    // If no currentUserId provided, assume creator (for backwards compatibility)
    return true
  }

  if (todos.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        {t('todos.noTodos')}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {todos.map((todo) => (
        <div
          key={todo.id}
          className={cn(
            'flex items-start gap-3 p-3 rounded-lg border bg-card',
            todo.isCompleted && 'opacity-60'
          )}
          data-testid={`todo-item-${todo.id}`}
        >
          {/* Checkbox */}
          <Checkbox
            checked={todo.isCompleted}
            onCheckedChange={() => handleToggleComplete(todo)}
            className="mt-0.5"
            data-testid={`todo-checkbox-${todo.id}`}
            disabled={editingId === todo.id}
          />

          {/* Content */}
          <div className="flex-1 min-w-0">
            {editingId === todo.id ? (
              /* Edit Mode */
              <div className="space-y-2">
                <Input
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  placeholder={t('todos.descriptionPlaceholder')}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveEdit(todo)
                    if (e.key === 'Escape') cancelEdit()
                  }}
                />
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-3 w-3 text-muted-foreground" />
                    <Input
                      type="date"
                      value={editReminderDate}
                      onChange={(e) => setEditReminderDate(e.target.value)}
                      className="h-7 w-36"
                    />
                  </div>
                  <label className="flex items-center gap-2 text-muted-foreground">
                    <Checkbox
                      checked={editIsPublic}
                      onCheckedChange={(checked) => setEditIsPublic(checked === true)}
                    />
                    {t('todos.shareWithTeam')}
                  </label>
                </div>
              </div>
            ) : (
              /* View Mode */
              <>
                {/* Todo text */}
                <p
                  className={cn(
                    'text-sm',
                    todo.isCompleted && 'line-through text-muted-foreground'
                  )}
                >
                  {todo.text}
                </p>

                {/* Meta info */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-muted-foreground">
                  {/* Entity link */}
                  <Link
                    to={getEntityLink(todo)}
                    className="hover:text-primary hover:underline"
                  >
                    {todo.entityName}
                  </Link>

                  {/* Reminder date */}
                  {todo.reminderDate && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(todo.reminderDate)}
                    </span>
                  )}

                  {/* Assignee */}
                  {todo.assignedToName && (
                    <span className="flex items-center gap-1">
                      <UserCheck className="h-3 w-3" />
                      {todo.assignedToName}
                    </span>
                  )}

                  {/* Creator (for team todos) */}
                  {showCreator && (
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {todo.createdByName}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1">
            {editingId === todo.id ? (
              /* Edit Mode Actions */
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-green-600"
                  onClick={() => handleSaveEdit(todo)}
                  data-testid={`todo-save-${todo.id}`}
                >
                  <Check className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  onClick={cancelEdit}
                  data-testid={`todo-cancel-${todo.id}`}
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            ) : (
              /* View Mode Actions */
              <>
                {canEdit(todo) && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                    onClick={() => startEdit(todo)}
                    data-testid={`todo-edit-${todo.id}`}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                )}
                {(!canDelete || canDelete(todo)) && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDelete(todo)}
                    data-testid={`todo-delete-${todo.id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
