import { useState, useRef, DragEvent, ChangeEvent, ReactNode } from 'react'

interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
  multiple?: boolean
  accept?: string
  className?: string
  children: ReactNode
  activeContent?: ReactNode
}

export function FileDropZone({
  onFilesSelected,
  disabled = false,
  multiple = true,
  accept,
  className = '',
  children,
  activeContent,
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dragCounter = useRef(0)

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled) return
    dragCounter.current += 1
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled) return
    dragCounter.current -= 1
    if (dragCounter.current <= 0) {
      dragCounter.current = 0
      setIsDragging(false)
    }
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled) return
    setIsDragging(false)
    dragCounter.current = 0

    const droppedFiles = Array.from(e.dataTransfer.files || [])
    if (droppedFiles.length === 0) return

    const files = multiple ? droppedFiles : droppedFiles.slice(0, 1)
    onFilesSelected(files)
  }

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    if (selectedFiles.length === 0) return
    onFilesSelected(selectedFiles)
    e.target.value = ''
  }

  const handleClick = () => {
    if (!disabled) inputRef.current?.click()
  }

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
      className={`${className} ${isDragging ? 'ring-2 ring-blue-500 ring-offset-2 bg-blue-50' : ''} ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'} transition`}
      data-dragging={isDragging}
    >
      {isDragging && activeContent ? activeContent : children}
      <input
        ref={inputRef}
        type="file"
        multiple={multiple}
        accept={accept}
        disabled={disabled}
        onChange={handleInputChange}
        className="hidden"
      />
    </div>
  )
}
