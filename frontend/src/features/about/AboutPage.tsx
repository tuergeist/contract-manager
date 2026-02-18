import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, Sparkles, Bug, Zap, Shield, Loader2 } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'

interface VersionInfo {
  version: string
  buildDate: string
}

interface LicenseEntry {
  name?: string
  Name?: string
  version?: string
  Version?: string
  licenses?: string
  license?: string
  License?: string
}

interface ChangelogEntry {
  version: string
  date: string
  title: string
  description: string
  type: 'feature' | 'bugfix' | 'improvement' | 'security'
  details: string[]
}

function normalizeEntry(entry: LicenseEntry) {
  return {
    name: entry.name || entry.Name || '',
    version: entry.version || entry.Version || '',
    license: entry.licenses || entry.license || entry.License || '',
  }
}

const TYPE_CONFIG = {
  feature: { icon: Sparkles, color: 'bg-green-100 text-green-800' },
  bugfix: { icon: Bug, color: 'bg-red-100 text-red-800' },
  improvement: { icon: Zap, color: 'bg-blue-100 text-blue-800' },
  security: { icon: Shield, color: 'bg-orange-100 text-orange-800' },
} as const

export function AboutPage() {
  const { t } = useTranslation()
  const [backendVersion, setBackendVersion] = useState<VersionInfo | null>(null)
  const [frontendLicenses, setFrontendLicenses] = useState<LicenseEntry[]>([])
  const [backendLicenses, setBackendLicenses] = useState<LicenseEntry[]>([])
  const [searchFe, setSearchFe] = useState('')
  const [searchBe, setSearchBe] = useState('')
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([])
  const [changelogLoading, setChangelogLoading] = useState(true)

  const feVersion = import.meta.env.VITE_BUILD_VERSION || 'dev'
  const feBuildDate = import.meta.env.VITE_BUILD_DATE || ''

  useEffect(() => {
    fetch('/api/version/')
      .then((r) => r.json())
      .then(setBackendVersion)
      .catch(() => setBackendVersion({ version: 'dev', buildDate: '' }))

    fetch('/licenses-frontend.json')
      .then((r) => r.json())
      .then((data) => {
        // license-checker-rsync2 returns an object keyed by package name
        if (data && !Array.isArray(data)) {
          const entries = Object.entries(data).map(([key, val]) => {
            const v = val as LicenseEntry
            const atIndex = key.lastIndexOf('@')
            const name = atIndex > 0 ? key.substring(0, atIndex) : key
            const version = atIndex > 0 ? key.substring(atIndex + 1) : v.version || ''
            return { name, version, licenses: v.licenses || v.license || '' }
          })
          setFrontendLicenses(entries)
        } else if (Array.isArray(data)) {
          setFrontendLicenses(data)
        }
      })
      .catch(() => setFrontendLicenses([]))

    fetch('/api/version/licenses/')
      .then((r) => r.json())
      .then(setBackendLicenses)
      .catch(() => setBackendLicenses([]))

    fetch('/changelogs.json')
      .then((r) => r.json())
      .then((data: ChangelogEntry[]) => setChangelog(data))
      .catch(() => setChangelog([]))
      .finally(() => setChangelogLoading(false))
  }, [])

  const filteredFe = useMemo(() => {
    const term = searchFe.toLowerCase()
    return frontendLicenses
      .map(normalizeEntry)
      .filter((e) => !term || e.name.toLowerCase().includes(term))
  }, [frontendLicenses, searchFe])

  const filteredBe = useMemo(() => {
    const term = searchBe.toLowerCase()
    return backendLicenses
      .map(normalizeEntry)
      .filter((e) => !term || e.name.toLowerCase().includes(term))
  }, [backendLicenses, searchBe])

  const formatDate = (dateStr: string) => {
    if (!dateStr) return ''
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  const formatChangelogDate = (dateStr: string) => {
    if (!dateStr) return ''
    try {
      return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('about.title')}</h1>

      <Tabs defaultValue="changelog">
        <TabsList>
          <TabsTrigger value="changelog">{t('about.changelog.tab')}</TabsTrigger>
          <TabsTrigger value="about">{t('about.changelog.aboutTab')}</TabsTrigger>
        </TabsList>

        <TabsContent value="changelog" className="mt-6">
          {changelogLoading ? (
            <div className="text-center py-12">
              <Loader2 className="w-6 h-6 mx-auto animate-spin text-gray-400" />
            </div>
          ) : changelog.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>{t('about.changelog.noEntries')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {changelog.map((entry, i) => {
                const config = TYPE_CONFIG[entry.type] || TYPE_CONFIG.feature
                const Icon = config.icon
                return (
                  <div key={i} className="rounded-lg border bg-white p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="secondary" className={config.color}>
                            <Icon className="w-3 h-3 mr-1" />
                            {t(`about.changelog.${entry.type}`)}
                          </Badge>
                          <span className="text-sm text-gray-500">
                            v{entry.version} · {formatChangelogDate(entry.date)}
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold mt-2">{entry.title}</h3>
                        <p className="text-gray-600 mt-1">{entry.description}</p>
                        {entry.details.length > 0 && (
                          <ul className="mt-3 space-y-1">
                            {entry.details.map((detail, j) => (
                              <li key={j} className="flex items-start gap-2 text-sm text-gray-600">
                                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />
                                {detail}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="about" className="mt-6 space-y-6">
          {/* Version Info */}
          <div className="rounded-lg border bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold">{t('about.versionInfo')}</h2>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-medium text-gray-500">{t('about.frontend')}</h3>
                <p className="text-lg font-mono">{feVersion}</p>
                {feBuildDate && (
                  <p className="text-sm text-gray-500">{formatDate(feBuildDate)}</p>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-sm font-medium text-gray-500">{t('about.backend')}</h3>
                <p className="text-lg font-mono">{backendVersion?.version || '...'}</p>
                {backendVersion?.buildDate && (
                  <p className="text-sm text-gray-500">{formatDate(backendVersion.buildDate)}</p>
                )}
              </div>
            </div>
          </div>

          {/* Frontend Dependencies */}
          <div className="rounded-lg border bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {t('about.frontendDependencies')}
                <span className="ml-2 text-sm font-normal text-gray-500">({filteredFe.length})</span>
              </h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchFe}
                  onChange={(e) => setSearchFe(e.target.value)}
                  placeholder={t('about.searchPackages')}
                  className="rounded-lg border py-1.5 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
            <LicenseTable entries={filteredFe} />
          </div>

          {/* Backend Dependencies */}
          <div className="rounded-lg border bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {t('about.backendDependencies')}
                <span className="ml-2 text-sm font-normal text-gray-500">({filteredBe.length})</span>
              </h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchBe}
                  onChange={(e) => setSearchBe(e.target.value)}
                  placeholder={t('about.searchPackages')}
                  className="rounded-lg border py-1.5 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
            <LicenseTable entries={filteredBe} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function LicenseTable({ entries }: { entries: { name: string; version: string; license: string }[] }) {
  const { t } = useTranslation()

  if (entries.length === 0) {
    return <p className="text-sm text-gray-500">{t('about.noDependencies')}</p>
  }

  return (
    <div className="max-h-96 overflow-y-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-white">
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2 pr-4 font-medium">{t('about.packageName')}</th>
            <th className="pb-2 pr-4 font-medium">{t('about.packageVersion')}</th>
            <th className="pb-2 font-medium">{t('about.packageLicense')}</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, i) => (
            <tr key={`${entry.name}-${i}`} className="border-b last:border-0">
              <td className="py-1.5 pr-4 font-mono text-xs">{entry.name}</td>
              <td className="py-1.5 pr-4 text-gray-600">{entry.version}</td>
              <td className="py-1.5 text-gray-600">{entry.license}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
