import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, formatMonthYear, formatCurrency, formatNumber, formatPercent, parseGermanNumber } from './utils'

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

  it('returns "-" for empty string', () => {
    expect(formatCurrency('')).toBe('-')
  })

  it('returns "-" for non-numeric string', () => {
    expect(formatCurrency('abc')).toBe('-')
  })

  it('formats a EUR value with German locale', () => {
    const result = formatCurrency(1234.56)
    // German locale uses . as thousands sep and , as decimal
    expect(result).toContain('1.234,56')
    expect(result).toContain('€')
  })

  it('accepts string input', () => {
    const result = formatCurrency('12824.48')
    expect(result).toContain('12.824,48')
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

  it('supports custom currency', () => {
    const result = formatCurrency(100, { currency: 'USD' })
    expect(result).toContain('100')
    expect(result).toContain('$')
  })

  it('supports fraction digit options', () => {
    const result = formatCurrency(1234.567, { maximumFractionDigits: 0 })
    expect(result).toContain('1.235')
    expect(result).not.toContain(',56')
  })
})

describe('formatNumber', () => {
  it('returns "-" for null', () => {
    expect(formatNumber(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatNumber(undefined)).toBe('-')
  })

  it('returns "-" for empty string', () => {
    expect(formatNumber('')).toBe('-')
  })

  it('formats a number with German locale', () => {
    expect(formatNumber(1234567)).toBe('1.234.567')
  })

  it('accepts string input', () => {
    expect(formatNumber('1234.5')).toContain('1.234,5')
  })

  it('supports fraction digit options', () => {
    const result = formatNumber(42, { minimumFractionDigits: 2 })
    expect(result).toBe('42,00')
  })
})

describe('formatPercent', () => {
  it('returns "-" for null', () => {
    expect(formatPercent(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatPercent(undefined)).toBe('-')
  })

  it('formats a decimal as percentage with German locale', () => {
    const result = formatPercent(0.035)
    expect(result).toContain('3,5')
    expect(result).toContain('%')
  })

  it('accepts string input', () => {
    const result = formatPercent('0.125')
    expect(result).toContain('12,5')
    expect(result).toContain('%')
  })

  it('supports custom fraction digits', () => {
    const result = formatPercent(0.1234, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    expect(result).toContain('12,34')
    expect(result).toContain('%')
  })
})

describe('parseGermanNumber', () => {
  it('converts comma decimal to dot decimal', () => {
    expect(parseGermanNumber('42,50')).toBe('42.50')
  })

  it('removes thousand-separator dots', () => {
    expect(parseGermanNumber('1.234,56')).toBe('1234.56')
  })

  it('handles plain integers', () => {
    expect(parseGermanNumber('100')).toBe('100')
  })

  it('handles empty string', () => {
    expect(parseGermanNumber('')).toBe('')
  })
})
