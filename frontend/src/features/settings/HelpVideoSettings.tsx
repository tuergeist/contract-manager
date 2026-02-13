import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation } from '@apollo/client'
import { Plus, X, Loader2 } from 'lucide-react'
import {
  ROUTE_KEYS,
  HELP_VIDEO_LINKS_QUERY,
  UPDATE_HELP_VIDEO_LINKS_MUTATION,
  HelpVideoLinksEntry,
} from '@/lib/helpVideoLinks'

interface ConfigEntry {
  routeKey: string
  links: { url: string; label: string }[]
}

export function HelpVideoSettings() {
  const { t } = useTranslation()
  const { data, refetch } = useQuery<{ helpVideoLinks: HelpVideoLinksEntry[] }>(
    HELP_VIDEO_LINKS_QUERY
  )
  const [updateLinks, { loading: saving }] = useMutation(UPDATE_HELP_VIDEO_LINKS_MUTATION)
  const [entries, setEntries] = useState<ConfigEntry[]>([])
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (data?.helpVideoLinks) {
      setEntries(
        data.helpVideoLinks.map((e) => ({
          routeKey: e.routeKey,
          links: e.links.map((l) => ({ url: l.url, label: l.label || '' })),
        }))
      )
    }
  }, [data])

  const usedKeys = new Set(entries.map((e) => e.routeKey))

  const addEntry = () => {
    const available = ROUTE_KEYS.find((r) => !usedKeys.has(r.key))
    if (available) {
      setEntries([...entries, { routeKey: available.key, links: [{ url: '', label: '' }] }])
    }
  }

  const removeEntry = (index: number) => {
    setEntries(entries.filter((_, i) => i !== index))
  }

  const updateRouteKey = (index: number, key: string) => {
    const updated = [...entries]
    updated[index] = { ...updated[index], routeKey: key }
    setEntries(updated)
  }

  const addLink = (entryIndex: number) => {
    const updated = [...entries]
    updated[entryIndex] = {
      ...updated[entryIndex],
      links: [...updated[entryIndex].links, { url: '', label: '' }],
    }
    setEntries(updated)
  }

  const removeLink = (entryIndex: number, linkIndex: number) => {
    const updated = [...entries]
    const newLinks = updated[entryIndex].links.filter((_, i) => i !== linkIndex)
    if (newLinks.length === 0) {
      setEntries(entries.filter((_, i) => i !== entryIndex))
    } else {
      updated[entryIndex] = { ...updated[entryIndex], links: newLinks }
      setEntries(updated)
    }
  }

  const updateLink = (entryIndex: number, linkIndex: number, field: 'url' | 'label', value: string) => {
    const updated = [...entries]
    const newLinks = [...updated[entryIndex].links]
    newLinks[linkIndex] = { ...newLinks[linkIndex], [field]: value }
    updated[entryIndex] = { ...updated[entryIndex], links: newLinks }
    setEntries(updated)
  }

  const handleSave = async () => {
    setMessage(null)
    try {
      const validEntries = entries
        .filter((e) => e.links.some((l) => l.url.trim()))
        .map((e) => ({
          routeKey: e.routeKey,
          links: e.links
            .filter((l) => l.url.trim())
            .map((l) => ({
              url: l.url.trim(),
              label: l.label.trim() || null,
            })),
        }))

      await updateLinks({ variables: { entries: validEntries } })
      refetch()
      setMessage({ type: 'success', text: t('helpVideo.settings.saved') })
    } catch {
      setMessage({ type: 'error', text: t('helpVideo.settings.saveFailed') })
    }
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('helpVideo.settings.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('helpVideo.settings.description')}</p>

      <div className="mt-4 space-y-4">
        {entries.map((entry, entryIndex) => (
          <div key={entryIndex} className="rounded-md border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center gap-2">
              <select
                value={entry.routeKey}
                onChange={(e) => updateRouteKey(entryIndex, e.target.value)}
                className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {ROUTE_KEYS.map((r) => (
                  <option
                    key={r.key}
                    value={r.key}
                    disabled={usedKeys.has(r.key) && r.key !== entry.routeKey}
                  >
                    {t(r.labelKey)} ({r.key})
                  </option>
                ))}
              </select>
              <button
                onClick={() => removeEntry(entryIndex)}
                className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-3 space-y-2">
              {entry.links.map((link, linkIndex) => (
                <div key={linkIndex} className="flex items-center gap-2">
                  <input
                    type="url"
                    value={link.url}
                    onChange={(e) => updateLink(entryIndex, linkIndex, 'url', e.target.value)}
                    placeholder={t('helpVideo.settings.urlPlaceholder')}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <input
                    type="text"
                    value={link.label}
                    onChange={(e) => updateLink(entryIndex, linkIndex, 'label', e.target.value)}
                    placeholder={t('helpVideo.settings.labelPlaceholder')}
                    className="w-48 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => removeLink(entryIndex, linkIndex)}
                    className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => addLink(entryIndex)}
                className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
              >
                <Plus className="h-3 w-3" />
                {t('helpVideo.settings.addLink')}
              </button>
            </div>
          </div>
        ))}

        <div className="flex items-center justify-between">
          <button
            onClick={addEntry}
            disabled={usedKeys.size >= ROUTE_KEYS.length}
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" />
            {t('helpVideo.settings.addScreen')}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('common.save')}
          </button>
        </div>

        {message && (
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}
      </div>
    </div>
  )
}
