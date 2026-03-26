import ReactMarkdown from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from './useChat'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        )}
        data-testid={`chat-message-${message.role}`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-table:my-1 prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-th:bg-gray-200 prose-table:text-xs">
            {message.content ? (
              <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                {message.content}
              </ReactMarkdown>
            ) : (
              <span className="inline-flex items-center gap-1 text-gray-400">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse animation-delay-200">●</span>
                <span className="animate-pulse animation-delay-400">●</span>
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
