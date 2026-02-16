import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePersistedState } from './usePersistedState'

// Mock localStorage since jsdom's implementation is incomplete
const store: Record<string, string> = {}
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => { store[key] = value }),
  removeItem: vi.fn((key: string) => { delete store[key] }),
  clear: vi.fn(() => { Object.keys(store).forEach(k => delete store[k]) }),
  get length() { return Object.keys(store).length },
  key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
}

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

describe('usePersistedState', () => {
  beforeEach(() => {
    Object.keys(store).forEach(k => delete store[k])
    vi.clearAllMocks()
  })

  it('returns default value when localStorage is empty', () => {
    const { result } = renderHook(() => usePersistedState('test-key', 'hello'))
    expect(result.current[0]).toBe('hello')
  })

  it('reads existing value from localStorage', () => {
    store['test-key'] = '"world"'
    const { result } = renderHook(() => usePersistedState('test-key', 'hello'))
    expect(result.current[0]).toBe('world')
  })

  it('falls back to default on corrupt JSON', () => {
    store['test-key'] = '{invalid'
    const { result } = renderHook(() => usePersistedState('test-key', 'hello'))
    expect(result.current[0]).toBe('hello')
  })

  it('writes state changes to localStorage', () => {
    const { result } = renderHook(() => usePersistedState('test-key', 'hello'))
    act(() => {
      result.current[1]('updated')
    })
    expect(result.current[0]).toBe('updated')
    expect(store['test-key']).toBe('"updated"')
  })

  it('works with object values', () => {
    const defaultVal = { count: 0 }
    const { result } = renderHook(() => usePersistedState('test-obj', defaultVal))
    expect(result.current[0]).toEqual({ count: 0 })

    act(() => {
      result.current[1]({ count: 5 })
    })
    expect(JSON.parse(store['test-obj'])).toEqual({ count: 5 })
  })
})
