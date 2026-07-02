import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Sparkles, Bug, Zap, Shield, Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'
import { isNewer } from '@/lib/versionCheck'

/** Raw changelog on the default branch — always reflects the latest release. */
const CHANGELOG_RAW_URL =
  'https://raw.githubusercontent.com/tuergeist/contract-manager/main/frontend/public/changelogs.json'

interface ChangelogEntry {
  version: string
  date: string
  title: string
  description: string
  type: 'feature' | 'bugfix' | 'improvement' | 'security'
  details: string[]
}

const TYPE_CONFIG = {
  feature: { icon: Sparkles, color: 'bg-green-100 text-green-800' },
  bugfix: { icon: Bug, color: 'bg-red-100 text-red-800' },
  improvement: { icon: Zap, color: 'bg-blue-100 text-blue-800' },
  security: { icon: Shield, color: 'bg-orange-100 text-orange-800' },
} as const

interface ChangelogModalProps {
  open: boolean
  onClose: () => void
  /** Only entries strictly newer than this version are shown. */
  currentVersion: string
}

export function ChangelogModal({
  open,
  onClose,
  currentVersion,
}: ChangelogModalProps) {
  const { t } = useTranslation()
  const [entries, setEntries] = useState<ChangelogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(false)
    fetch(CHANGELOG_RAW_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: ChangelogEntry[]) => {
        setEntries(
          (Array.isArray(data) ? data : []).filter((e) =>
            isNewer(e.version, currentVersion)
          )
        )
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [open, currentVersion])

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="changelog-modal">
        <DialogHeader>
          <DialogTitle>{t('updateBanner.modalTitle')}</DialogTitle>
          <DialogDescription>
            {t('updateBanner.modalSubtitle', { current: currentVersion })}
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
          {loading ? (
            <div className="py-12 text-center">
              <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <div className="py-12 text-center text-sm text-gray-500">
              {t('common.error')}
            </div>
          ) : entries.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-500">
              {t('about.changelog.noEntries')}
            </div>
          ) : (
            entries.map((entry, i) => {
              const config = TYPE_CONFIG[entry.type] || TYPE_CONFIG.feature
              const Icon = config.icon
              return (
                <div key={i} className="rounded-lg border bg-white p-4">
                  <div className="mb-1 flex items-center gap-2">
                    <Badge variant="secondary" className={config.color}>
                      <Icon className="mr-1 h-3 w-3" />
                      {t(`about.changelog.${entry.type}`)}
                    </Badge>
                    <span className="text-sm text-gray-500">
                      v{entry.version} · {formatDate(entry.date)}
                    </span>
                  </div>
                  <h3 className="mt-1 text-base font-semibold">{entry.title}</h3>
                  <p className="mt-1 text-sm text-gray-600">{entry.description}</p>
                  {entry.details.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {entry.details.map((detail, j) => (
                        <li
                          key={j}
                          className="flex items-start gap-2 text-sm text-gray-600"
                        >
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                          {detail}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
