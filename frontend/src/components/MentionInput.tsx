import { useState, useRef, KeyboardEvent, ChangeEvent, useEffect } from 'react'

export interface MentionUser {
  id: string
  email: string
  firstName: string | null
  lastName: string | null
}

interface MentionInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit?: () => void
  placeholder?: string
  users: MentionUser[]
  className?: string
  disabled?: boolean
}

/**
 * Build a stable token for a mention. Always includes the full email so
 * the backend can resolve the user unambiguously, even when names collide
 * or are missing. The `firstname.lastname` form alone is not safe (two
 * users with identical names would collide).
 */
function getMentionToken(user: MentionUser, allUsers: MentionUser[]): string {
  if (user.firstName && user.lastName) {
    const candidate = `${user.firstName}.${user.lastName}`.toLowerCase()
    const collisions = allUsers.filter(
      (u) =>
        u.firstName &&
        u.lastName &&
        `${u.firstName}.${u.lastName}`.toLowerCase() === candidate,
    )
    if (collisions.length === 1) return candidate
  }
  // Fall back to full email — globally unique
  return user.email.toLowerCase()
}

function userLabel(user: MentionUser): string {
  if (user.firstName && user.lastName) {
    return `${user.firstName} ${user.lastName}`
  }
  return user.email
}

export function MentionInput({
  value,
  onChange,
  onSubmit,
  placeholder,
  users,
  className = '',
  disabled = false,
}: MentionInputProps) {
  const [showMentions, setShowMentions] = useState(false)
  const [mentionQuery, setMentionQuery] = useState('')
  const [mentionStart, setMentionStart] = useState(-1)
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredUsers = users.filter((u) => {
    const q = mentionQuery.toLowerCase()
    return (
      !q ||
      getMentionToken(u, users).includes(q) ||
      u.email.toLowerCase().includes(q) ||
      userLabel(u).toLowerCase().includes(q)
    )
  }).slice(0, 8)

  useEffect(() => {
    setActiveIndex(0)
  }, [mentionQuery])

  const detectMention = (text: string, caret: number) => {
    // Find last @ before caret, within a word boundary
    let i = caret - 1
    while (i >= 0) {
      const ch = text[i]
      if (ch === '@') {
        // Preceded by start or whitespace?
        if (i === 0 || /\s/.test(text[i - 1])) {
          const query = text.slice(i + 1, caret)
          if (/^[\w.\-]*$/.test(query)) {
            setMentionStart(i)
            setMentionQuery(query)
            setShowMentions(true)
            return
          }
        }
        break
      }
      if (/\s/.test(ch)) break
      i -= 1
    }
    setShowMentions(false)
    setMentionStart(-1)
  }

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value
    onChange(text)
    detectMention(text, e.target.selectionStart ?? text.length)
  }

  const insertMention = (user: MentionUser) => {
    if (mentionStart < 0) return
    const before = value.slice(0, mentionStart)
    const caret = inputRef.current?.selectionStart ?? value.length
    const after = value.slice(caret)
    const token = getMentionToken(user, users)
    const newText = `${before}@${token} ${after}`
    onChange(newText)
    setShowMentions(false)
    setMentionStart(-1)
    // Focus back and place caret after inserted mention
    requestAnimationFrame(() => {
      const pos = before.length + token.length + 2
      inputRef.current?.setSelectionRange(pos, pos)
      inputRef.current?.focus()
    })
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (showMentions && filteredUsers.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((i) => (i + 1) % filteredUsers.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((i) => (i - 1 + filteredUsers.length) % filteredUsers.length)
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        insertMention(filteredUsers[activeIndex])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowMentions(false)
        return
      }
    }
    if (e.key === 'Enter' && !e.shiftKey && onSubmit) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="relative flex-1">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={() => setTimeout(() => setShowMentions(false), 150)}
        placeholder={placeholder}
        disabled={disabled}
        className={`flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      />
      {showMentions && filteredUsers.length > 0 && (
        <div
          className="absolute bottom-full left-0 z-50 mb-1 w-full max-w-sm rounded-md border bg-popover shadow-md"
          data-testid="mention-dropdown"
        >
          {filteredUsers.map((user, i) => (
            <button
              key={user.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault()
                insertMention(user)
              }}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent ${i === activeIndex ? 'bg-accent' : ''}`}
            >
              <span className="font-medium">{userLabel(user)}</span>
              <span className="text-xs text-muted-foreground">@{getMentionToken(user, users)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
