import { describe, it, expect } from 'vitest'
import { matchRoute } from './helpVideoLinks'

describe('matchRoute', () => {
  it('matches exact paths', () => {
    expect(matchRoute('/customers', '/customers')).toBe(true)
  })

  it('matches paths with param segments', () => {
    expect(matchRoute('/customers/:id', '/customers/123')).toBe(true)
  })

  it('matches nested param paths', () => {
    expect(matchRoute('/contracts/:id/edit', '/contracts/42/edit')).toBe(true)
  })

  it('rejects when segment count differs', () => {
    expect(matchRoute('/customers/:id', '/customers')).toBe(false)
  })

  it('rejects different static segments', () => {
    expect(matchRoute('/products', '/customers')).toBe(false)
  })

  it('matches root path', () => {
    expect(matchRoute('/', '/')).toBe(true)
  })

  it('rejects root vs nested', () => {
    expect(matchRoute('/', '/customers')).toBe(false)
  })
})
