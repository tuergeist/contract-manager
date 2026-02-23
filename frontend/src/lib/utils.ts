import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format date as dd.mm.yyyy
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const day = d.getDate().toString().padStart(2, '0')
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const year = d.getFullYear()
  return `${day}.${month}.${year}`
}

/**
 * Format date and time as dd.mm.yyyy HH:mm
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const day = d.getDate().toString().padStart(2, '0')
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const year = d.getFullYear()
  const hours = d.getHours().toString().padStart(2, '0')
  const minutes = d.getMinutes().toString().padStart(2, '0')
  return `${day}.${month}.${year} ${hours}:${minutes}`
}

/**
 * Format date as mm.yyyy (month and year only)
 */
export function formatMonthYear(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const year = d.getFullYear()
  return `${month}.${year}`
}

/**
 * Format number as currency (EUR by default, always de-DE locale)
 */
export function formatCurrency(
  value: string | number | null | undefined,
  options?: {
    compact?: boolean
    currency?: string
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  }
): string {
  if (value === null || value === undefined || value === '') return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  const formatOptions: Intl.NumberFormatOptions = {
    style: 'currency',
    currency: options?.currency ?? 'EUR',
  }
  if (options?.compact) {
    formatOptions.notation = 'compact'
    formatOptions.maximumFractionDigits = options.maximumFractionDigits ?? 1
  }
  if (options?.minimumFractionDigits !== undefined) {
    formatOptions.minimumFractionDigits = options.minimumFractionDigits
  }
  if (options?.maximumFractionDigits !== undefined) {
    formatOptions.maximumFractionDigits = options.maximumFractionDigits
  }
  return new Intl.NumberFormat('de-DE', formatOptions).format(num)
}

/**
 * Format number with de-DE locale (no currency symbol)
 */
export function formatNumber(
  value: string | number | null | undefined,
  options?: {
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  }
): string {
  if (value === null || value === undefined || value === '') return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return new Intl.NumberFormat('de-DE', {
    minimumFractionDigits: options?.minimumFractionDigits,
    maximumFractionDigits: options?.maximumFractionDigits,
  }).format(num)
}

/**
 * Format number as percentage with de-DE locale
 */
export function formatPercent(
  value: string | number | null | undefined,
  options?: {
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  }
): string {
  if (value === null || value === undefined || value === '') return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return new Intl.NumberFormat('de-DE', {
    style: 'percent',
    minimumFractionDigits: options?.minimumFractionDigits ?? 1,
    maximumFractionDigits: options?.maximumFractionDigits ?? 1,
  }).format(num)
}

/**
 * Parse a German-formatted number string (comma as decimal separator) to a dot-decimal string.
 * E.g. "1.234,56" → "1234.56", "42,5" → "42.5"
 */
export function parseGermanNumber(value: string): string {
  return value.replace(/\./g, '').replace(',', '.')
}
