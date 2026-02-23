import { useEffect } from 'react'

export function useDocumentTitle(title: string | undefined | null) {
  useEffect(() => {
    if (title) document.title = `${title} - Contract Manager`
    return () => { document.title = 'Contract Manager' }
  }, [title])
}
