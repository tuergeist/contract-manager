import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, gql } from '@apollo/client'
import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import { MessageSquare, Plus, Pencil, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

// =============================================================================
// GraphQL
// =============================================================================

const CONTRACT_COMMENTS_QUERY = gql`
  query ContractComments($contractId: ID!) {
    contractComments(contractId: $contractId) {
      id
      text
      author { id firstName lastName }
      createdAt
      updatedAt
      canEdit
      canDelete
    }
  }
`

const CUSTOMER_COMMENTS_QUERY = gql`
  query CustomerComments($customerId: ID!) {
    customerComments(customerId: $customerId) {
      id
      text
      author { id firstName lastName }
      createdAt
      updatedAt
      canEdit
      canDelete
    }
  }
`

const ADD_CONTRACT_COMMENT = gql`
  mutation AddContractComment($contractId: ID!, $text: String!) {
    addContractComment(contractId: $contractId, text: $text) {
      success
      error
      comment { id text author { id firstName lastName } createdAt updatedAt canEdit canDelete }
    }
  }
`

const UPDATE_CONTRACT_COMMENT = gql`
  mutation UpdateContractComment($commentId: ID!, $text: String!) {
    updateContractComment(commentId: $commentId, text: $text) {
      success
      error
      comment { id text author { id firstName lastName } createdAt updatedAt canEdit canDelete }
    }
  }
`

const DELETE_CONTRACT_COMMENT = gql`
  mutation DeleteContractComment($commentId: ID!) {
    deleteContractComment(commentId: $commentId) {
      success
      error
    }
  }
`

const ADD_CUSTOMER_COMMENT = gql`
  mutation AddCustomerComment($customerId: ID!, $text: String!) {
    addCustomerComment(customerId: $customerId, text: $text) {
      success
      error
      comment { id text author { id firstName lastName } createdAt updatedAt canEdit canDelete }
    }
  }
`

const UPDATE_CUSTOMER_COMMENT = gql`
  mutation UpdateCustomerComment($commentId: ID!, $text: String!) {
    updateCustomerComment(commentId: $commentId, text: $text) {
      success
      error
      comment { id text author { id firstName lastName } createdAt updatedAt canEdit canDelete }
    }
  }
`

const DELETE_CUSTOMER_COMMENT = gql`
  mutation DeleteCustomerComment($commentId: ID!) {
    deleteCustomerComment(commentId: $commentId) {
      success
      error
    }
  }
`

// =============================================================================
// Types
// =============================================================================

interface Comment {
  id: string
  text: string
  author: { id: string; firstName: string; lastName: string }
  createdAt: string
  updatedAt: string
  canEdit: boolean
  canDelete: boolean
}

interface CommentsSectionProps {
  entityType: 'contract' | 'customer'
  entityId: string
}

// =============================================================================
// Helpers
// =============================================================================

function relativeTime(dateStr: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return t('comments.justNow')
  if (diffMin < 60) return t('comments.minutesAgo', { count: diffMin })
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return t('comments.hoursAgo', { count: diffH })
  const diffD = Math.floor(diffH / 24)
  return t('comments.daysAgo', { count: diffD })
}

// =============================================================================
// CommentItem
// =============================================================================

function CommentItem({
  comment,
  onEdit,
  onDelete,
}: {
  comment: Comment
  onEdit: (comment: Comment) => void
  onDelete: (comment: Comment) => void
}) {
  const { t } = useTranslation()
  const wasEdited = Math.abs(new Date(comment.updatedAt).getTime() - new Date(comment.createdAt).getTime()) > 2000

  return (
    <div className="py-2 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">
            {comment.author.firstName} {comment.author.lastName}
          </span>
          <span>&middot;</span>
          <span>{relativeTime(comment.createdAt, t)}</span>
          {wasEdited && (
            <>
              <span>&middot;</span>
              <span className="italic">{t('comments.edited')}</span>
            </>
          )}
        </div>
        {(comment.canEdit || comment.canDelete) && (
          <div className="flex items-center gap-0.5 shrink-0">
            {comment.canEdit && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => onEdit(comment)}
              >
                <Pencil className="h-3 w-3" />
              </Button>
            )}
            {comment.canDelete && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                onClick={() => onDelete(comment)}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        )}
      </div>
      <div className="mt-1 text-sm prose prose-sm max-w-none dark:prose-invert prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0">
        <ReactMarkdown remarkPlugins={[remarkBreaks]}>{comment.text}</ReactMarkdown>
      </div>
    </div>
  )
}

// =============================================================================
// CommentsSection
// =============================================================================

export function CommentsSection({ entityType, entityId }: CommentsSectionProps) {
  const { t } = useTranslation()
  const [showAddModal, setShowAddModal] = useState(false)
  const [showAllModal, setShowAllModal] = useState(false)
  const [editingComment, setEditingComment] = useState<Comment | null>(null)
  const [commentText, setCommentText] = useState('')

  // Select queries/mutations based on entity type
  const isContract = entityType === 'contract'
  const queryDoc = isContract ? CONTRACT_COMMENTS_QUERY : CUSTOMER_COMMENTS_QUERY
  const queryVars = isContract
    ? { contractId: entityId }
    : { customerId: entityId }
  const queryKey = isContract ? 'contractComments' : 'customerComments'

  const { data, loading, refetch } = useQuery(queryDoc, { variables: queryVars })
  const comments: Comment[] = data?.[queryKey] ?? []

  const [addComment, { loading: adding }] = useMutation(
    isContract ? ADD_CONTRACT_COMMENT : ADD_CUSTOMER_COMMENT,
  )
  const [updateComment, { loading: updating }] = useMutation(
    isContract ? UPDATE_CONTRACT_COMMENT : UPDATE_CUSTOMER_COMMENT,
  )
  const [deleteComment] = useMutation(
    isContract ? DELETE_CONTRACT_COMMENT : DELETE_CUSTOMER_COMMENT,
  )

  const previewComments = comments.slice(0, 3)
  const hasMore = comments.length > 3

  const handleAdd = async () => {
    if (!commentText.trim()) return
    const mutationKey = isContract ? 'addContractComment' : 'addCustomerComment'
    const vars = isContract
      ? { contractId: entityId, text: commentText.trim() }
      : { customerId: entityId, text: commentText.trim() }
    const { data: result } = await addComment({ variables: vars })
    if (result?.[mutationKey]?.success) {
      setCommentText('')
      setShowAddModal(false)
      refetch()
    }
  }

  const handleUpdate = async () => {
    if (!editingComment || !commentText.trim()) return
    const mutationKey = isContract ? 'updateContractComment' : 'updateCustomerComment'
    const { data: result } = await updateComment({
      variables: { commentId: editingComment.id, text: commentText.trim() },
    })
    if (result?.[mutationKey]?.success) {
      setCommentText('')
      setEditingComment(null)
      refetch()
    }
  }

  const handleDelete = async (comment: Comment) => {
    if (!confirm(t('comments.confirmDelete'))) return
    const mutationKey = isContract ? 'deleteContractComment' : 'deleteCustomerComment'
    const { data: result } = await deleteComment({
      variables: { commentId: comment.id },
    })
    if (result?.[mutationKey]?.success) {
      refetch()
    }
  }

  const openEdit = (comment: Comment) => {
    setEditingComment(comment)
    setCommentText(comment.text)
  }

  const openAdd = () => {
    setEditingComment(null)
    setCommentText('')
    setShowAddModal(true)
  }

  const isModalOpen = showAddModal || editingComment !== null
  const isSaving = adding || updating

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
          <MessageSquare className="h-3.5 w-3.5" />
          {t('comments.title')}
          {comments.length > 0 && (
            <span className="text-muted-foreground font-normal">({comments.length})</span>
          )}
        </p>
        <Button
          variant="ghost"
          size="sm"
          onClick={openAdd}
          className="h-7 px-2"
        >
          <Plus className="h-3 w-3 mr-1" />
          {t('comments.addComment')}
        </Button>
      </div>

      {/* Comment list preview */}
      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : comments.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">{t('comments.noComments')}</p>
      ) : (
        <div className="divide-y">
          {previewComments.map((c) => (
            <CommentItem
              key={c.id}
              comment={c}
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Show all button */}
      {hasMore && (
        <Button
          variant="link"
          size="sm"
          className="mt-1 h-auto p-0 text-xs"
          onClick={() => setShowAllModal(true)}
        >
          {t('comments.showAll')} ({comments.length})
        </Button>
      )}

      {/* Add/Edit Modal */}
      <Dialog
        open={isModalOpen}
        onOpenChange={(open) => {
          if (!open) {
            setShowAddModal(false)
            setEditingComment(null)
            setCommentText('')
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingComment ? t('comments.editComment') : t('comments.addComment')}
            </DialogTitle>
          </DialogHeader>
          <textarea
            className="w-full rounded-md border border-gray-300 p-2 text-sm min-h-[120px] focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder={t('comments.commentPlaceholder')}
            autoFocus
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowAddModal(false)
                setEditingComment(null)
                setCommentText('')
              }}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={editingComment ? handleUpdate : handleAdd}
              disabled={!commentText.trim() || isSaving}
            >
              {isSaving && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* All Comments Modal */}
      <Dialog open={showAllModal} onOpenChange={setShowAllModal}>
        <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {t('comments.allComments')} ({comments.length})
            </DialogTitle>
          </DialogHeader>
          <div className="divide-y">
            {comments.map((c) => (
              <CommentItem
                key={c.id}
                comment={c}
                onEdit={(comment) => {
                  setShowAllModal(false)
                  openEdit(comment)
                }}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
