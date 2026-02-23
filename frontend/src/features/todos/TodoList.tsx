import { useState, useRef, createRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMutation, gql } from '@apollo/client'
import { formatDate } from '@/lib/utils'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Calendar, User, UserCheck, Pencil, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { TodoDetailModal } from './TodoDetailModal'

const UPDATE_TODO = gql`
  mutation UpdateTodo(
    $todoId: Int!
    $text: String
    $reminderDate: Date
    $isPublic: Boolean
    $isCompleted: Boolean
    $assignedToId: Int
  ) {
    updateTodo(
      todoId: $todoId
      text: $text
      reminderDate: $reminderDate
      isPublic: $isPublic
      isCompleted: $isCompleted
      assignedToId: $assignedToId
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

export interface TodoItem {
  id: number
  text: string
  reminderDate: string | null
  isPublic: boolean
  isCompleted: boolean
  completedAt: string | null
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
  commentCount: number
}

interface TodoListProps {
  todos: TodoItem[]
  showCreator?: boolean
  onUpdate?: () => void
  currentUserId?: number
}

export function TodoList({ todos, showCreator = false, onUpdate, currentUserId }: TodoListProps) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const effectiveUserId = currentUserId ?? user?.id ?? 0

  // Detail modal state
  const [detailTodoId, setDetailTodoId] = useState<number | null>(null)
  const [detailCanEdit, setDetailCanEdit] = useState(false)

  // Date input refs - one per todo
  const dateInputRefs = useRef<Map<number, React.RefObject<HTMLInputElement>>>(new Map())
  const getDateInputRef = (todoId: number) => {
    if (!dateInputRefs.current.has(todoId)) {
      dateInputRefs.current.set(todoId, createRef<HTMLInputElement>())
    }
    return dateInputRefs.current.get(todoId)!
  }

  const [updateTodo] = useMutation(UPDATE_TODO)

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

  const handleInlineDateChange = async (todo: TodoItem, newDate: string) => {
    try {
      const result = await updateTodo({
        variables: {
          todoId: todo.id,
          reminderDate: newDate || null,
        },
      })
      if (result.data?.updateTodo?.success) {
        onUpdate?.()
      }
    } catch (error) {
      console.error('Failed to update date:', error)
    }
  }

  const openDetail = (todo: TodoItem) => {
    setDetailTodoId(todo.id)
    setDetailCanEdit(todo.createdById === effectiveUserId)
  }


  const getEntityLink = (todo: TodoItem): string => {
    if (todo.contractId) {
      return `/contracts/${todo.contractId}`
    }
    if (todo.customerId) {
      return `/customers/${todo.customerId}`
    }
    return '#'
  }

  const canEdit = (todo: TodoItem) => {
    if (effectiveUserId) {
      return todo.createdById === effectiveUserId
    }
    return true
  }

  const canEditDate = (todo: TodoItem) => {
    if (!effectiveUserId) return true
    return todo.createdById === effectiveUserId || todo.assignedToId === effectiveUserId
  }

  if (todos.length === 0) {
    return (
      <div className="text-center py-4 text-muted-foreground text-sm">
        {t('todos.noTodos')}
      </div>
    )
  }

  return (
    <>
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
            />

            {/* Content */}
            <div className="flex-1 min-w-0">
              {/* Todo text */}
              <p
                className={cn(
                  'text-sm',
                  todo.isCompleted && 'line-through text-muted-foreground'
                )}
              >
                {todo.text}
              </p>

              {/* Entity link - own line */}
              <div className="mt-1">
                <Link
                  to={getEntityLink(todo)}
                  className="text-xs text-muted-foreground hover:text-primary hover:underline"
                >
                  {todo.entityName}
                </Link>
              </div>

              {/* Date, Comment count, Assignee line */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-muted-foreground">
                {/* Date - clickable for inline editing */}
                <span
                  className={cn(
                    'flex items-center gap-1',
                    canEditDate(todo) && 'cursor-pointer hover:text-primary'
                  )}
                  onClick={() => {
                    if (canEditDate(todo)) {
                      const ref = getDateInputRef(todo.id)
                      ref.current?.showPicker()
                    }
                  }}
                >
                  <Calendar className={cn('h-3 w-3', !todo.reminderDate && 'opacity-50')} />
                  {todo.reminderDate ? formatDate(todo.reminderDate) : (
                    <span className="opacity-50">{t('todos.noDate')}</span>
                  )}
                </span>
                <input
                  type="date"
                  ref={getDateInputRef(todo.id)}
                  className="sr-only"
                  value={todo.reminderDate || ''}
                  onChange={(e) => handleInlineDateChange(todo, e.target.value)}
                  tabIndex={-1}
                />

                {/* Comment count - clickable */}
                <span
                  className="flex items-center gap-1 cursor-pointer hover:text-primary"
                  onClick={() => openDetail(todo)}
                >
                  <MessageSquare className="h-3 w-3" />
                  {todo.commentCount || 0}
                </span>

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
            </div>

            {/* Action button */}
            <div className="flex items-center gap-1">
              {canEdit(todo) && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-primary"
                  onClick={() => openDetail(todo)}
                  data-testid={`todo-edit-${todo.id}`}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Shared Todo Detail Modal */}
      <TodoDetailModal
        todoId={detailTodoId}
        open={detailTodoId !== null}
        onOpenChange={(open) => { if (!open) setDetailTodoId(null) }}
        canEdit={detailCanEdit}
        onRefresh={() => onUpdate?.()}
      />
    </>
  )
}
