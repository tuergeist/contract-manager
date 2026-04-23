import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MentionInput, MentionUser } from './MentionInput'

const USERS: MentionUser[] = [
  { id: '1', email: 'alice@example.com', firstName: 'Alice', lastName: 'Smith' },
  { id: '2', email: 'bob@example.com', firstName: 'Bob', lastName: 'Jones' },
  { id: '3', email: 'carol@example.com', firstName: null, lastName: null },
]

describe('MentionInput', () => {
  it('shows mention dropdown when typing @', () => {
    const onChange = vi.fn()
    render(<MentionInput value="" onChange={onChange} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '@' } })

    expect(screen.getByTestId('mention-dropdown')).toBeInTheDocument()
    expect(screen.getByText('Alice Smith')).toBeInTheDocument()
    expect(screen.getByText('Bob Jones')).toBeInTheDocument()
  })

  it('filters users by typed query', () => {
    const onChange = vi.fn()
    const { rerender } = render(<MentionInput value="" onChange={onChange} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '@ali' } })
    rerender(<MentionInput value="@ali" onChange={onChange} users={USERS} />)
    fireEvent.change(input, { target: { value: '@ali' } })

    expect(screen.getByText('Alice Smith')).toBeInTheDocument()
    expect(screen.queryByText('Bob Jones')).toBeNull()
  })

  it('inserts mention on click', () => {
    const onChange = vi.fn()
    render(<MentionInput value="" onChange={onChange} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '@' } })

    const option = screen.getByText('Alice Smith')
    fireEvent.mouseDown(option)

    expect(onChange).toHaveBeenLastCalledWith('@alice.smith ')
  })

  it('does not trigger mention in middle of word', () => {
    const onChange = vi.fn()
    render(<MentionInput value="" onChange={onChange} users={USERS} />)

    const input = screen.getByRole('textbox') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'email@domain' } })

    expect(screen.queryByTestId('mention-dropdown')).toBeNull()
  })

  it('submits on Enter when no dropdown is open', () => {
    const onSubmit = vi.fn()
    const onChange = vi.fn()
    render(<MentionInput value="hello" onChange={onChange} onSubmit={onSubmit} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onSubmit).toHaveBeenCalled()
  })

  it('Enter selects mention when dropdown is open instead of submitting', () => {
    const onSubmit = vi.fn()
    const onChange = vi.fn()
    render(<MentionInput value="" onChange={onChange} onSubmit={onSubmit} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '@al' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onSubmit).not.toHaveBeenCalled()
    expect(onChange).toHaveBeenLastCalledWith('@alice.smith ')
  })

  it('arrow keys navigate the dropdown', () => {
    const onChange = vi.fn()
    render(<MentionInput value="" onChange={onChange} users={USERS} />)

    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '@' } })

    fireEvent.keyDown(input, { key: 'ArrowDown' })
    fireEvent.keyDown(input, { key: 'Enter' })

    // Second user is Bob
    expect(onChange).toHaveBeenLastCalledWith('@bob.jones ')
  })
})
