export type DisplayStatus = 'inProgress' | 'review' | 'ready' | 'done' | 'error'

export function mapStatus(s: string): DisplayStatus {
  switch (s) {
    case 'pending':
    case 'extracting': return 'inProgress'
    case 'extracted': return 'review'
    case 'confirmed': return 'ready'
    case 'matched': return 'done'
    case 'extraction_failed': return 'error'
    default: return 'inProgress'
  }
}

export const displayStatusColor: Record<DisplayStatus, string> = {
  inProgress: '',
  review: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
}

// Maps UI filter selection to backend status string
export function filterToBackendStatus(filter: string): string | undefined {
  switch (filter) {
    case 'review': return 'extracted'
    case 'ready': return 'confirmed'
    case 'done': return 'matched'
    default: return undefined
  }
}

// Maps backend status to the UI filter it belongs to (for backwards-compat deep-links)
export function backendStatusToFilter(backendStatus: string): string {
  switch (backendStatus) {
    case 'extracted': return 'review'
    case 'confirmed': return 'ready'
    case 'matched': return 'done'
    default: return 'all'
  }
}
