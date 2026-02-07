import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Bug, Lightbulb, MessageCircle, X, Camera, RefreshCw, Loader2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { captureScreenshot, formatBytes, getDataUrlSize } from '@/lib/screenshot'

const SUBMIT_FEEDBACK_MUTATION = gql`
  mutation SubmitFeedback($input: FeedbackInput!) {
    submitFeedback(input: $input) {
      success
      error
      taskUrl
    }
  }
`

type FeedbackType = 'BUG' | 'FEATURE' | 'GENERAL'

interface FeedbackTypeOption {
  type: FeedbackType
  icon: React.ReactNode
  labelKey: string
  descriptionKey: string
}

const FEEDBACK_TYPES: FeedbackTypeOption[] = [
  {
    type: 'BUG',
    icon: <Bug className="h-5 w-5" />,
    labelKey: 'feedback.types.bug',
    descriptionKey: 'feedback.types.bugDescription',
  },
  {
    type: 'FEATURE',
    icon: <Lightbulb className="h-5 w-5" />,
    labelKey: 'feedback.types.feature',
    descriptionKey: 'feedback.types.featureDescription',
  },
  {
    type: 'GENERAL',
    icon: <MessageCircle className="h-5 w-5" />,
    labelKey: 'feedback.types.general',
    descriptionKey: 'feedback.types.generalDescription',
  },
]

interface FeedbackModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FeedbackModal({ open, onOpenChange }: FeedbackModalProps) {
  const { t } = useTranslation()
  const [feedbackType, setFeedbackType] = useState<FeedbackType | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [screenshotError, setScreenshotError] = useState<string | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [titleError, setTitleError] = useState(false)

  const [submitFeedback, { loading, error: mutationError }] = useMutation(SUBMIT_FEEDBACK_MUTATION)

  // Capture screenshot when modal opens
  useEffect(() => {
    if (open && !screenshot && !screenshotError) {
      handleCaptureScreenshot()
    }
  }, [open])

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setFeedbackType(null)
      setTitle('')
      setDescription('')
      setScreenshot(null)
      setScreenshotError(null)
      setShowSuccess(false)
      setTitleError(false)
    }
  }, [open])

  const handleCaptureScreenshot = async () => {
    setIsCapturing(true)
    setScreenshotError(null)

    // Small delay to let modal render
    await new Promise((resolve) => setTimeout(resolve, 100))

    const result = await captureScreenshot()

    if (result.success && result.dataUrl) {
      setScreenshot(result.dataUrl)
    } else {
      setScreenshotError(result.error || 'Failed to capture screenshot')
    }

    setIsCapturing(false)
  }

  const handleClose = () => {
    onOpenChange(false)
  }

  const handleSubmit = async () => {
    if (!feedbackType) return

    if (!title.trim()) {
      setTitleError(true)
      return
    }
    setTitleError(false)

    try {
      const result = await submitFeedback({
        variables: {
          input: {
            type: feedbackType,
            title: title.trim(),
            description: description.trim() || null,
            screenshot: screenshot || null,
            pageUrl: window.location.href,
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            userAgent: navigator.userAgent,
          },
        },
      })

      if (result.data?.submitFeedback?.success) {
        setShowSuccess(true)
        // Auto-close after showing success
        setTimeout(() => {
          handleClose()
        }, 2000)
      }
    } catch (e) {
      console.error('Failed to submit feedback:', e)
    }
  }

  const handleRemoveScreenshot = () => {
    setScreenshot(null)
    setScreenshotError(null)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]" data-feedback-ignore>
        <DialogHeader>
          <DialogTitle>{t('feedback.title')}</DialogTitle>
        </DialogHeader>

        {showSuccess ? (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <Check className="h-8 w-8 text-green-600" />
            </div>
            <p className="mt-4 text-lg font-medium">{t('feedback.success')}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t('feedback.successDescription')}</p>
          </div>
        ) : (
          <>
            {/* Step 1: Select type */}
            {!feedbackType ? (
              <div className="grid gap-3 py-4">
                <p className="text-sm text-muted-foreground">{t('feedback.selectType')}</p>
                {FEEDBACK_TYPES.map((option) => (
                  <button
                    key={option.type}
                    onClick={() => setFeedbackType(option.type)}
                    className="flex items-center gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-muted"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                      {option.icon}
                    </div>
                    <div>
                      <p className="font-medium">{t(option.labelKey)}</p>
                      <p className="text-sm text-muted-foreground">{t(option.descriptionKey)}</p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              /* Step 2: Fill details */
              <div className="grid gap-4 py-4">
                {/* Type indicator */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{t('feedback.type')}:</span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-sm">
                    {FEEDBACK_TYPES.find((o) => o.type === feedbackType)?.icon}
                    {t(FEEDBACK_TYPES.find((o) => o.type === feedbackType)?.labelKey || '')}
                  </span>
                  <button
                    onClick={() => setFeedbackType(null)}
                    className="ml-auto text-sm text-muted-foreground hover:text-foreground"
                  >
                    {t('feedback.changeType')}
                  </button>
                </div>

                {/* Title */}
                <div className="grid gap-2">
                  <Label htmlFor="title">
                    {t('feedback.titleLabel')} <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="title"
                    value={title}
                    onChange={(e) => {
                      setTitle(e.target.value)
                      if (titleError) setTitleError(false)
                    }}
                    placeholder={t('feedback.titlePlaceholder')}
                    className={titleError ? 'border-red-500' : ''}
                    disabled={loading}
                  />
                  {titleError && (
                    <p className="text-sm text-red-500">{t('feedback.titleRequired')}</p>
                  )}
                </div>

                {/* Description */}
                <div className="grid gap-2">
                  <Label htmlFor="description">{t('feedback.descriptionLabel')}</Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder={t('feedback.descriptionPlaceholder')}
                    rows={3}
                    disabled={loading}
                  />
                </div>

                {/* Screenshot */}
                <div className="grid gap-2">
                  <Label>{t('feedback.screenshot')}</Label>
                  {isCapturing ? (
                    <div className="flex items-center justify-center rounded-lg border border-dashed p-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <span className="ml-2 text-sm text-muted-foreground">
                        {t('feedback.capturing')}
                      </span>
                    </div>
                  ) : screenshot ? (
                    <div className="relative">
                      <img
                        src={screenshot}
                        alt="Screenshot preview"
                        className="max-h-40 w-full rounded-lg border object-contain"
                      />
                      <div className="absolute right-2 top-2 flex gap-1">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={handleCaptureScreenshot}
                          disabled={loading}
                        >
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={handleRemoveScreenshot}
                          disabled={loading}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatBytes(getDataUrlSize(screenshot))}
                      </p>
                    </div>
                  ) : screenshotError ? (
                    <div className="rounded-lg border border-dashed p-4 text-center">
                      <p className="text-sm text-muted-foreground">{screenshotError}</p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCaptureScreenshot}
                        className="mt-2"
                        disabled={loading}
                      >
                        <Camera className="mr-2 h-4 w-4" />
                        {t('feedback.retryScreenshot')}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleCaptureScreenshot}
                      disabled={loading}
                    >
                      <Camera className="mr-2 h-4 w-4" />
                      {t('feedback.captureScreenshot')}
                    </Button>
                  )}
                </div>

                {/* Error display */}
                {mutationError && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                    <p className="text-sm text-red-600">{mutationError.message}</p>
                  </div>
                )}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={loading}>
                {t('common.cancel')}
              </Button>
              {feedbackType && (
                <Button onClick={handleSubmit} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('feedback.submit')}
                </Button>
              )}
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
