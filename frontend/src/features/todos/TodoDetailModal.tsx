import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, useLazyQuery, useMutation, gql } from '@apollo/client'
import { formatDate, formatDateTime } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Calendar, User, Send, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

const TODO_DETAIL_QUERY = gql`
  query TodoDetailModal($todoId: Int!) {
    todo(todoId: $todoId) {
      id
      text
      reminderDate
      isPublic
      isCompleted
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
      customerName
      contractCustomerId
      commentCount
      comments {
        id
        text
        authorId
        authorName
        createdAt
      }
    }
  }
`

const USERS_QUERY = gql`
  query UsersForTodoDetailModal {
    users {
      id
      email
      firstName
      lastName
      isActive
    }
  }
`

const UPDATE_TODO = gql`
  mutation UpdateTodoFromModal(
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
    }
  }
`

const DELETE_TODO = gql`
  mutation DeleteTodoFromModal($todoId: Int!) {
    deleteTodo(todoId: $todoId) {
      success
      error
    }
  }
`

const ADD_COMMENT = gql`
  mutation AddTodoCommentFromModal($todoId: Int!, $text: String!) {
    addTodoComment(todoId: $todoId, text: $text) {
      success
      error
    }
  }
`

interface TodoComment {
  id: number
  text: string
  authorId: number
  authorName: string
  createdAt: string
}

interface TodoData {
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
  customerName: string | null
  contractCustomerId: number | null
  commentCount: number
  comments: TodoComment[]
}

interface TodoDetailModalProps {
  todoId: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
  canEdit: boolean
  canReassign?: boolean
  onRefresh: () => void
}

export function TodoDetailModal({ todoId, open, onOpenChange, canEdit, canReassign, onRefresh }: TodoDetailModalProps) {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canDeleteTodo = hasPermission('todos', 'delete')
  const canChangeAssignee = canEdit || canReassign
  const [editingText, setEditingText] = useState(false)
  const [text, setText] = useState('')
  const [reminderDate, setReminderDate] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [assignedToId, setAssignedToId] = useState<string>('')
  const [newComment, setNewComment] = useState('')

  const { data: usersData } = useQuery(USERS_QUERY, { skip: !open || !canChangeAssignee })
  const users = (usersData?.users || []).filter(
    (u: { id: string; isActive: boolean }) => u.isActive
  )

  const [updateTodo] = useMutation(UPDATE_TODO)
  const [deleteTodoMutation] = useMutation(DELETE_TODO)
  const [addCommentMutation] = useMutation(ADD_COMMENT)

  const [fetchTodoDetail, { data: detailData, loading }] = useLazyQuery(TODO_DETAIL_QUERY, {
    fetchPolicy: 'network-only',
  })

  const todo: TodoData | null = detailData?.todo ?? null

  // Fetch when modal opens or todoId changes
  useMemo(() => {
    if (todoId && open) {
      setEditingText(false)
      setNewComment('')
      fetchTodoDetail({ variables: { todoId } })
    }
  }, [todoId, open])

  // Sync form state when todo data arrives
  useMemo(() => {
    if (todo) {
      setText(todo.text)
      setReminderDate(todo.reminderDate || '')
      setIsPublic(todo.isPublic)
      setAssignedToId(todo.assignedToId ? String(todo.assignedToId) : '')
    }
  }, [todo?.id, todo?.text, todo?.reminderDate, todo?.isPublic, todo?.assignedToId])

  const handleSaveField = async (updates: Record<string, unknown>) => {
    if (!todo) return
    try {
      const result = await updateTodo({ variables: { todoId: todo.id, ...updates } })
      if (result.data?.updateTodo?.success) {
        fetchTodoDetail({ variables: { todoId: todo.id } })
        onRefresh()
      }
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const handleSaveText = () => {
    if (!text.trim()) return
    handleSaveField({ text: text.trim() })
    setEditingText(false)
  }

  const handleSubmitComment = async () => {
    if (!newComment.trim() || !todo) return
    try {
      const result = await addCommentMutation({
        variables: { todoId: todo.id, text: newComment.trim() },
      })
      if (result.data?.addTodoComment?.success) {
        setNewComment('')
        fetchTodoDetail({ variables: { todoId: todo.id } })
        onRefresh()
      }
    } catch (error) {
      console.error('Failed to add comment:', error)
    }
  }

  const handleDelete = async () => {
    if (!todo) return
    if (!confirm(t('todos.confirmDelete'))) return
    try {
      const result = await deleteTodoMutation({ variables: { todoId: todo.id } })
      if (result.data?.deleteTodo?.success) {
        onOpenChange(false)
        onRefresh()
      }
    } catch (error) {
      console.error('Failed to delete todo:', error)
    }
  }

  const handleToggleComplete = async () => {
    if (!todo) return
    try {
      const result = await updateTodo({ variables: { todoId: todo.id, isCompleted: !todo.isCompleted } })
      if (result.data?.updateTodo?.success) {
        onRefresh()
        if (!todo.isCompleted) {
          onOpenChange(false)
        } else {
          fetchTodoDetail({ variables: { todoId: todo.id } })
        }
      }
    } catch (error) {
      console.error('Failed to toggle todo:', error)
    }
  }


  const getEntityLink = (t: TodoData): string => {
    if (t.contractId) return `/contracts/${t.contractId}`
    if (t.customerId) return `/customers/${t.customerId}`
    return '#'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {todo && (
              <Checkbox
                checked={todo.isCompleted}
                onCheckedChange={() => handleToggleComplete()}
              />
            )}
            <span className={cn(todo?.isCompleted && 'line-through text-muted-foreground')}>
              {todo?.entityName}
            </span>
          </DialogTitle>
        </DialogHeader>

        {loading && !todo ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : todo && (
          <div className="flex gap-6">
            {/* Left: text + comments */}
            <div className="flex-1 min-w-0 space-y-4">
              {/* Todo text */}
              {editingText && canEdit ? (
                <div className="space-y-2">
                  <Textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={t('todos.descriptionPlaceholder')}
                    rows={3}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') { setEditingText(false); setText(todo.text) }
                    }}
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleSaveText} disabled={!text.trim()}>
                      {t('common.save')}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => { setEditingText(false); setText(todo.text) }}>
                      {t('common.cancel')}
                    </Button>
                  </div>
                </div>
              ) : (
                <div
                  className={cn(
                    'p-3 bg-gray-50 rounded-lg',
                    canEdit && 'cursor-pointer hover:bg-gray-100'
                  )}
                  onClick={() => canEdit && setEditingText(true)}
                >
                  <p className="text-sm whitespace-pre-wrap">{todo.text}</p>
                </div>
              )}

              {/* Comments section */}
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">{t('todos.comments')}</h4>
                <div className="max-h-60 overflow-y-auto space-y-3">
                  {todo.comments.length === 0 ? (
                    <p className="text-center text-sm text-muted-foreground py-4">
                      {t('todos.noComments')}
                    </p>
                  ) : (
                    todo.comments.map((comment) => (
                      <div key={comment.id} className="p-3 border rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <User className="h-3 w-3 text-muted-foreground" />
                          <span className="text-sm font-medium">{comment.authorName}</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(comment.createdAt)}
                          </span>
                        </div>
                        <p className="text-sm">{comment.text}</p>
                      </div>
                    ))
                  )}
                </div>

                {/* Add comment */}
                <div className="flex gap-2 mt-3">
                  <Input
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder={t('todos.addCommentPlaceholder')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSubmitComment()
                      }
                    }}
                  />
                  <Button onClick={handleSubmitComment} disabled={!newComment.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Right sidebar: metadata */}
            <div className="w-48 shrink-0 space-y-4 text-sm">
              {/* Entity link */}
              <div>
                <p className="text-xs text-muted-foreground mb-1">{t('todos.linkedTo')}</p>
                <Link
                  to={getEntityLink(todo)}
                  className="text-primary hover:underline text-sm"
                  onClick={() => onOpenChange(false)}
                >
                  {todo.entityName}
                </Link>
                {todo.customerName && todo.contractCustomerId && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    (<Link
                      to={`/customers/${todo.contractCustomerId}`}
                      className="hover:text-primary hover:underline"
                      onClick={() => onOpenChange(false)}
                    >{todo.customerName}</Link>)
                  </p>
                )}
              </div>

              {/* Date */}
              <div>
                <p className="text-xs text-muted-foreground mb-1">{t('todos.reminderDate')}</p>
                {canEdit ? (
                  <Input
                    type="date"
                    value={reminderDate}
                    onChange={(e) => {
                      setReminderDate(e.target.value)
                      handleSaveField({ reminderDate: e.target.value || null })
                    }}
                    className="h-8 text-sm"
                  />
                ) : (
                  <p className="text-sm">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(todo.reminderDate) || '-'}
                    </span>
                  </p>
                )}
              </div>

              {/* Assignee */}
              <div>
                <p className="text-xs text-muted-foreground mb-1">{t('todos.assignee')}</p>
                {canChangeAssignee ? (
                  <Select
                    value={assignedToId || '__none__'}
                    onValueChange={(val) => {
                      const newVal = val === '__none__' ? '' : val
                      setAssignedToId(newVal)
                      handleSaveField({ assignedToId: newVal ? parseInt(newVal) : null })
                    }}
                  >
                    <SelectTrigger className="h-8 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">{t('todos.unassigned')}</SelectItem>
                      {users.map((u: { id: string; email: string; firstName: string; lastName: string }) => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.firstName && u.lastName ? `${u.firstName} ${u.lastName}` : u.email}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm">{todo.assignedToName || '-'}</p>
                )}
              </div>

              {/* Public toggle */}
              {canEdit && (
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox
                    checked={isPublic}
                    onCheckedChange={(checked) => {
                      const newVal = checked === true
                      setIsPublic(newVal)
                      handleSaveField({ isPublic: newVal })
                    }}
                  />
                  {t('todos.shareWithTeam')}
                </label>
              )}

              {/* Delete */}
              {canEdit && canDeleteTodo && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={handleDelete}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  {t('todos.delete')}
                </Button>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
