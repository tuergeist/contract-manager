import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, formatMonthYear, formatCurrency } from './utils'

describe('formatDate', () => {
  it('returns "-" for null', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatDate(undefined)).toBe('-')
  })

  it('formats a valid date string as dd.mm.yyyy', () => {
    expect(formatDate('2026-03-15')).toBe('15.03.2026')
  })

  it('formats a date with time component', () => {
    expect(formatDate('2026-01-05T14:30:00Z')).toBe('05.01.2026')
  })
})

describe('formatDateTime', () => {
  it('returns "-" for null', () => {
    expect(formatDateTime(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatDateTime(undefined)).toBe('-')
  })

  it('formats a valid datetime string as dd.mm.yyyy HH:mm', () => {
    // Use a fixed timezone offset to avoid flakiness
    const result = formatDateTime('2026-03-15T14:30:00')
    expect(result).toMatch(/15\.03\.2026 \d{2}:\d{2}/)
  })
})

describe('formatMonthYear', () => {
  it('returns "-" for null', () => {
    expect(formatMonthYear(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatMonthYear(undefined)).toBe('-')
  })

  it('formats a valid date as mm.yyyy', () => {
    expect(formatMonthYear('2026-03-15')).toBe('03.2026')
  })
})

describe('formatCurrency', () => {
  it('returns "-" for null', () => {
    expect(formatCurrency(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatCurrency(undefined)).toBe('-')
  })

  it('formats a EUR value with German locale', () => {
    const result = formatCurrency(1234.56)
    // German locale uses . as thousands sep and , as decimal
    expect(result).toContain('1.234,56')
    expect(result).toContain('€')
  })

  it('formats zero', () => {
    const result = formatCurrency(0)
    expect(result).toContain('0')
    expect(result).toContain('€')
  })

  it('supports compact notation', () => {
    const result = formatCurrency(1500000, { compact: true })
    expect(result).toContain('€')
    // Compact should shorten the number (e.g. "1,5 Mio." in de-DE)
    expect(result.length).toBeLessThan(formatCurrency(1500000)!.length)
  })
})
