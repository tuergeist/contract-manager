import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { FileDropZone } from './FileDropZone'

function makeFile(name: string, type = 'text/plain'): File {
  return new File(['content'], name, { type })
}

describe('FileDropZone', () => {
  it('opens file picker on click and calls onFilesSelected with selected files', () => {
    const onFilesSelected = vi.fn()
    const { container } = render(
      <FileDropZone onFilesSelected={onFilesSelected}>
        <span>Upload</span>
      </FileDropZone>
    )

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).toBeTruthy()
    expect(input.multiple).toBe(true)

    const files = [makeFile('a.txt'), makeFile('b.txt')]
    Object.defineProperty(input, 'files', { value: files, configurable: true })
    fireEvent.change(input)

    expect(onFilesSelected).toHaveBeenCalledTimes(1)
    expect(onFilesSelected.mock.calls[0][0]).toHaveLength(2)
    expect(onFilesSelected.mock.calls[0][0][0].name).toBe('a.txt')
  })

  it('handles drop event with multiple files', () => {
    const onFilesSelected = vi.fn()
    render(
      <FileDropZone onFilesSelected={onFilesSelected}>
        <span data-testid="zone">Drop here</span>
      </FileDropZone>
    )

    const zone = screen.getByTestId('zone').parentElement as HTMLElement
    const files = [makeFile('c.pdf', 'application/pdf'), makeFile('d.png', 'image/png')]

    fireEvent.drop(zone, {
      dataTransfer: { files, items: files.map(() => ({})) },
    })

    expect(onFilesSelected).toHaveBeenCalledTimes(1)
    expect(onFilesSelected.mock.calls[0][0]).toHaveLength(2)
  })

  it('limits to single file when multiple=false', () => {
    const onFilesSelected = vi.fn()
    render(
      <FileDropZone onFilesSelected={onFilesSelected} multiple={false}>
        <span data-testid="zone">Drop</span>
      </FileDropZone>
    )

    const zone = screen.getByTestId('zone').parentElement as HTMLElement
    const files = [makeFile('a.txt'), makeFile('b.txt')]

    fireEvent.drop(zone, { dataTransfer: { files, items: files.map(() => ({})) } })

    expect(onFilesSelected.mock.calls[0][0]).toHaveLength(1)
    expect(onFilesSelected.mock.calls[0][0][0].name).toBe('a.txt')
  })

  it('does not fire when disabled', () => {
    const onFilesSelected = vi.fn()
    render(
      <FileDropZone onFilesSelected={onFilesSelected} disabled>
        <span data-testid="zone">Drop</span>
      </FileDropZone>
    )

    const zone = screen.getByTestId('zone').parentElement as HTMLElement
    const files = [makeFile('a.txt')]
    fireEvent.drop(zone, { dataTransfer: { files, items: [{}] } })

    expect(onFilesSelected).not.toHaveBeenCalled()
  })

  it('shows activeContent while dragging', () => {
    render(
      <FileDropZone
        onFilesSelected={vi.fn()}
        activeContent={<span data-testid="active">ACTIVE</span>}
      >
        <span data-testid="idle">IDLE</span>
      </FileDropZone>
    )

    expect(screen.getByTestId('idle')).toBeInTheDocument()
    expect(screen.queryByTestId('active')).toBeNull()

    const zone = screen.getByTestId('idle').parentElement as HTMLElement
    fireEvent.dragEnter(zone, { dataTransfer: { items: [{}], files: [] } })

    expect(screen.getByTestId('active')).toBeInTheDocument()
  })

  it('ignores drops with no files', () => {
    const onFilesSelected = vi.fn()
    render(
      <FileDropZone onFilesSelected={onFilesSelected}>
        <span data-testid="zone">Drop</span>
      </FileDropZone>
    )

    const zone = screen.getByTestId('zone').parentElement as HTMLElement
    fireEvent.drop(zone, { dataTransfer: { files: [], items: [] } })

    expect(onFilesSelected).not.toHaveBeenCalled()
  })
})
