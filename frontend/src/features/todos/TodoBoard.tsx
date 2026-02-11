import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import { format, parseISO } from 'date-fns'
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Calendar,
  User,
  MessageSquare,
  Pencil,
  Trash2,
  Search,
  Eye,
  EyeOff,
  GripVertical,
  Send,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

// ============================================================================
// GraphQL Queries and Mutations
// ============================================================================

const TODOS_BY_ASSIGNEE = gql`
  query TodosByAssignee($includeCompleted: Boolean) {
    todosByAssignee(includeCompleted: $includeCompleted) {
      assigneeId
      assigneeName
      isCurrentUser
      todos {
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
  }
`

const USERS_QUERY = gql`
  query UsersForTodoBoard {
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
  mutation UpdateTodoBoard(
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

const DELETE_TODO = gql`
  mutation DeleteTodoBoard($todoId: Int!) {
    deleteTodo(todoId: $todoId) {
      success
      error
    }
  }
`

const ADD_COMMENT = gql`
  mutation AddTodoComment($todoId: Int!, $text: String!) {
    addTodoComment(todoId: $todoId, text: $text) {
      success
      error
      comment {
        id
        text
        authorId
        authorName
        createdAt
      }
    }
  }
`

// ============================================================================
// Types
// ============================================================================

interface TodoComment {
  id: number
  text: string
  authorId: number
  authorName: string
  createdAt: string
}

interface TodoItem {
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
  comments: TodoComment[]
}

interface AssigneeColumn {
  assigneeId: number | null
  assigneeName: string
  isCurrentUser: boolean
  todos: TodoItem[]
}

// ============================================================================
// TodoCard Component (Draggable)
// ============================================================================

interface TodoCardProps {
  todo: TodoItem
  currentUserId: number
  onToggleComplete: (todo: TodoItem) => void
  onEdit: (todo: TodoItem) => void
  onDelete: (todo: TodoItem) => void
  onViewComments: (todo: TodoItem) => void
  isDragging?: boolean
}

function TodoCard({
  todo,
  currentUserId,
  onToggleComplete,
  onEdit,
  onDelete,
  onViewComments,
  isDragging,
}: TodoCardProps) {
  const { t } = useTranslation()

  const getEntityLink = (todo: TodoItem): string => {
    if (todo.contractId) {
      return `/contracts/${todo.contractId}`
    }
    if (todo.customerId) {
      return `/customers/${todo.customerId}`
    }
    return '#'
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null
    return format(parseISO(dateStr), 'dd.MM.yyyy')
  }

  const canEdit = todo.createdById === currentUserId

  return (
    <div
      className={cn(
        'rounded-lg border bg-white p-3 shadow-sm',
        todo.isCompleted && 'opacity-60',
        isDragging && 'opacity-50'
      )}
      data-testid={`todo-card-${todo.id}`}
    >
      {/* Header with checkbox and actions */}
      <div className="flex items-start gap-2">
        <Checkbox
          checked={todo.isCompleted}
          onCheckedChange={() => onToggleComplete(todo)}
          className="mt-0.5"
          data-testid={`todo-card-checkbox-${todo.id}`}
        />
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'text-sm',
              todo.isCompleted && 'line-through text-muted-foreground'
            )}
          >
            {todo.text}
          </p>
        </div>
        <div className="flex gap-1 shrink-0">
          {canEdit && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-primary"
                onClick={() => onEdit(todo)}
                data-testid={`todo-card-edit-${todo.id}`}
              >
                <Pencil className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                onClick={() => onDelete(todo)}
                data-testid={`todo-card-delete-${todo.id}`}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Meta info */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {/* Entity link */}
        <Link
          to={getEntityLink(todo)}
          className="hover:text-primary hover:underline truncate max-w-[150px]"
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

        {/* Public indicator */}
        <span title={todo.isPublic ? t('todos.public') : t('todos.private')}>
          {todo.isPublic ? (
            <Eye className="h-3 w-3" />
          ) : (
            <EyeOff className="h-3 w-3" />
          )}
        </span>

        {/* Comment count */}
        <button
          onClick={() => onViewComments(todo)}
          className="flex items-center gap-1 hover:text-primary"
        >
          <MessageSquare className="h-3 w-3" />
          {todo.commentCount}
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// SortableTodoCard Component (for drag-drop)
// ============================================================================

interface SortableTodoCardProps extends TodoCardProps {
  id: string
}

function SortableTodoCard({ id, ...props }: SortableTodoCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div ref={setNodeRef} style={style} className="relative group">
      <div
        {...attributes}
        {...listeners}
        className="absolute left-0 top-0 bottom-0 w-6 flex items-center justify-center cursor-grab opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="pl-4">
        <TodoCard {...props} isDragging={isDragging} />
      </div>
    </div>
  )
}

// ============================================================================
// BoardColumn Component
// ============================================================================

interface BoardColumnProps {
  column: AssigneeColumn
  currentUserId: number
  onToggleComplete: (todo: TodoItem) => void
  onEdit: (todo: TodoItem) => void
  onDelete: (todo: TodoItem) => void
  onViewComments: (todo: TodoItem) => void
  searchFilter: string
}

function BoardColumn({
  column,
  currentUserId,
  onToggleComplete,
  onEdit,
  onDelete,
  onViewComments,
  searchFilter,
}: BoardColumnProps) {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)

  // Filter todos by search
  const filteredTodos = useMemo(() => {
    if (!searchFilter) return column.todos
    const search = searchFilter.toLowerCase()
    return column.todos.filter(
      (todo) =>
        todo.text.toLowerCase().includes(search) ||
        todo.entityName.toLowerCase().includes(search)
    )
  }, [column.todos, searchFilter])

  const todoIds = filteredTodos.map((t) => `todo-${t.id}`)

  return (
    <div className="flex flex-col bg-gray-50 rounded-lg w-80 min-w-[320px] max-h-full">
      {/* Column header */}
      <div
        className="flex items-center justify-between p-3 border-b bg-gray-100 rounded-t-lg cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          {collapsed ? (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
          <h3 className="font-medium text-sm">
            {column.isCurrentUser ? t('todos.me') : column.assigneeName}
          </h3>
          <Badge variant="secondary" className="text-xs">
            {filteredTodos.length}
          </Badge>
        </div>
      </div>

      {/* Column content */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          <SortableContext items={todoIds} strategy={verticalListSortingStrategy}>
            {filteredTodos.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-4">
                {t('todos.noTodos')}
              </p>
            ) : (
              filteredTodos.map((todo) => (
                <SortableTodoCard
                  key={todo.id}
                  id={`todo-${todo.id}`}
                  todo={todo}
                  currentUserId={currentUserId}
                  onToggleComplete={onToggleComplete}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onViewComments={onViewComments}
                />
              ))
            )}
          </SortableContext>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// EditTodoModal Component
// ============================================================================

interface EditTodoModalProps {
  todo: TodoItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (updates: {
    text: string
    reminderDate: string | null
    isPublic: boolean
    assignedToId: number | null
  }) => void
}

function EditTodoModal({ todo, open, onOpenChange, onSave }: EditTodoModalProps) {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const [reminderDate, setReminderDate] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [assignedToId, setAssignedToId] = useState<string>('')

  const { data: usersData } = useQuery(USERS_QUERY, { skip: !open })
  const users = (usersData?.users || []).filter(
    (u: { id: string; isActive: boolean }) => u.isActive
  )

  // Reset form when todo changes
  useState(() => {
    if (todo) {
      setText(todo.text)
      setReminderDate(todo.reminderDate || '')
      setIsPublic(todo.isPublic)
      setAssignedToId(todo.assignedToId ? String(todo.assignedToId) : '')
    }
  })

  // Effect to update form when todo changes
  useMemo(() => {
    if (todo && open) {
      setText(todo.text)
      setReminderDate(todo.reminderDate || '')
      setIsPublic(todo.isPublic)
      setAssignedToId(todo.assignedToId ? String(todo.assignedToId) : '')
    }
  }, [todo, open])

  const handleSave = () => {
    if (!text.trim()) return
    onSave({
      text: text.trim(),
      reminderDate: reminderDate || null,
      isPublic,
      assignedToId: assignedToId ? parseInt(assignedToId) : null,
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('todos.editTodo')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium">{t('todos.description')}</label>
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={t('todos.descriptionPlaceholder')}
              className="mt-1"
              rows={3}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">{t('todos.reminderDate')}</label>
              <Input
                type="date"
                value={reminderDate}
                onChange={(e) => setReminderDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t('todos.assignee')}</label>
              <Select
                value={assignedToId || '__none__'}
                onValueChange={(val) => setAssignedToId(val === '__none__' ? '' : val)}
              >
                <SelectTrigger className="mt-1">
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
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={isPublic}
              onCheckedChange={(checked) => setIsPublic(checked === true)}
            />
            {t('todos.shareWithTeam')}
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSave} disabled={!text.trim()}>
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ============================================================================
// CommentsModal Component
// ============================================================================

interface CommentsModalProps {
  todo: TodoItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onAddComment: (text: string) => void
}

function CommentsModal({ todo, open, onOpenChange, onAddComment }: CommentsModalProps) {
  const { t } = useTranslation()
  const [newComment, setNewComment] = useState('')

  const handleSubmit = () => {
    if (!newComment.trim()) return
    onAddComment(newComment.trim())
    setNewComment('')
  }

  const formatDateTime = (dateStr: string) => {
    return format(parseISO(dateStr), 'dd.MM.yyyy HH:mm')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('todos.comments')}</DialogTitle>
        </DialogHeader>

        {todo && (
          <div className="space-y-4">
            {/* Todo text context */}
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm text-muted-foreground">{t('todos.todoText')}:</p>
              <p className="text-sm">{todo.text}</p>
            </div>

            {/* Comments list */}
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
            <div className="flex gap-2">
              <Input
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder={t('todos.addCommentPlaceholder')}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
              />
              <Button onClick={handleSubmit} disabled={!newComment.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ============================================================================
// Main TodoBoard Component
// ============================================================================

export function TodoBoard() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const currentUserId = user?.id ?? 0

  // State
  const [showCompleted, setShowCompleted] = useState(false)
  const [searchFilter, setSearchFilter] = useState('')
  const [editingTodo, setEditingTodo] = useState<TodoItem | null>(null)
  const [commentsTodo, setCommentsTodo] = useState<TodoItem | null>(null)
  const [activeDragId, setActiveDragId] = useState<string | null>(null)

  // Queries
  const { data, loading, refetch } = useQuery(TODOS_BY_ASSIGNEE, {
    variables: { includeCompleted: showCompleted },
    fetchPolicy: 'cache-and-network',
  })

  // Mutations
  const [updateTodo] = useMutation(UPDATE_TODO)
  const [deleteTodo] = useMutation(DELETE_TODO)
  const [addComment] = useMutation(ADD_COMMENT)

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  )

  const columns: AssigneeColumn[] = data?.todosByAssignee || []

  // Find a todo by id across all columns
  const findTodoById = (id: number): TodoItem | null => {
    for (const col of columns) {
      const todo = col.todos.find((t) => t.id === id)
      if (todo) return todo
    }
    return null
  }

  // Handlers
  const handleToggleComplete = async (todo: TodoItem) => {
    try {
      await updateTodo({
        variables: {
          todoId: todo.id,
          isCompleted: !todo.isCompleted,
        },
      })
      refetch()
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const handleDelete = async (todo: TodoItem) => {
    if (!confirm(t('todos.confirmDelete'))) return

    try {
      await deleteTodo({ variables: { todoId: todo.id } })
      refetch()
    } catch (error) {
      console.error('Failed to delete todo:', error)
    }
  }

  const handleSaveEdit = async (updates: {
    text: string
    reminderDate: string | null
    isPublic: boolean
    assignedToId: number | null
  }) => {
    if (!editingTodo) return

    try {
      await updateTodo({
        variables: {
          todoId: editingTodo.id,
          ...updates,
        },
      })
      refetch()
    } catch (error) {
      console.error('Failed to update todo:', error)
    }
  }

  const handleAddComment = async (text: string) => {
    if (!commentsTodo) return

    try {
      const result = await addComment({
        variables: { todoId: commentsTodo.id, text },
      })
      if (result.data?.addTodoComment?.success) {
        refetch()
        // Update the local comments list
        if (commentsTodo) {
          const updatedTodo = findTodoById(commentsTodo.id)
          if (updatedTodo) {
            setCommentsTodo({
              ...commentsTodo,
              comments: [
                ...commentsTodo.comments,
                result.data.addTodoComment.comment,
              ],
              commentCount: commentsTodo.commentCount + 1,
            })
          }
        }
      }
    } catch (error) {
      console.error('Failed to add comment:', error)
    }
  }

  // Drag handlers
  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(event.active.id as string)
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    setActiveDragId(null)

    const { active, over } = event
    if (!over) return

    // Extract todo ID from the draggable ID
    const todoId = parseInt((active.id as string).replace('todo-', ''))
    const todo = findTodoById(todoId)
    if (!todo) return

    // Determine target column (assignee)
    // The over could be a todo or a column droppable
    const overId = over.id as string
    let targetAssigneeId: number | null = null

    if (overId.startsWith('todo-')) {
      // Dropped over another todo - find which column it's in
      const overTodoId = parseInt(overId.replace('todo-', ''))
      for (const col of columns) {
        if (col.todos.find((t) => t.id === overTodoId)) {
          targetAssigneeId = col.assigneeId
          break
        }
      }
    } else if (overId.startsWith('column-')) {
      // Dropped directly on column
      targetAssigneeId = overId === 'column-unassigned' ? null : parseInt(overId.replace('column-', ''))
    }

    // Check if assignment changed
    if (targetAssigneeId !== todo.assignedToId) {
      try {
        await updateTodo({
          variables: {
            todoId: todo.id,
            assignedToId: targetAssigneeId,
          },
        })
        refetch()
      } catch (error) {
        console.error('Failed to reassign todo:', error)
      }
    }
  }

  // Get dragged todo for overlay
  const activeTodo = activeDragId
    ? findTodoById(parseInt(activeDragId.replace('todo-', '')))
    : null

  if (loading && !data) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">{t('common.loading')}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <h1 className="text-2xl font-semibold">{t('todos.board')}</h1>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder={t('common.search')}
              className="pl-9 w-64"
            />
          </div>

          {/* Show completed toggle */}
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={showCompleted}
              onCheckedChange={(checked) => setShowCompleted(checked === true)}
            />
            {t('todos.showCompleted')}
          </label>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto p-4">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 h-full">
            {columns.map((column) => (
              <BoardColumn
                key={column.assigneeId ?? 'unassigned'}
                column={column}
                currentUserId={currentUserId}
                onToggleComplete={handleToggleComplete}
                onEdit={(todo) => setEditingTodo(todo)}
                onDelete={handleDelete}
                onViewComments={(todo) => setCommentsTodo(todo)}
                searchFilter={searchFilter}
              />
            ))}
          </div>

          {/* Drag overlay */}
          <DragOverlay>
            {activeTodo && (
              <div className="w-72">
                <TodoCard
                  todo={activeTodo}
                  currentUserId={currentUserId}
                  onToggleComplete={() => {}}
                  onEdit={() => {}}
                  onDelete={() => {}}
                  onViewComments={() => {}}
                  isDragging
                />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Edit Modal */}
      <EditTodoModal
        todo={editingTodo}
        open={!!editingTodo}
        onOpenChange={(open) => !open && setEditingTodo(null)}
        onSave={handleSaveEdit}
      />

      {/* Comments Modal */}
      <CommentsModal
        todo={commentsTodo}
        open={!!commentsTodo}
        onOpenChange={(open) => !open && setCommentsTodo(null)}
        onAddComment={handleAddComment}
      />
    </div>
  )
}
