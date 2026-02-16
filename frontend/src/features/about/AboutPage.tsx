import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Search } from 'lucide-react'

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

function normalizeEntry(entry: LicenseEntry) {
  return {
    name: entry.name || entry.Name || '',
    version: entry.version || entry.Version || '',
    license: entry.licenses || entry.license || entry.License || '',
  }
}

export function AboutPage() {
  const { t } = useTranslation()
  const [backendVersion, setBackendVersion] = useState<VersionInfo | null>(null)
  const [frontendLicenses, setFrontendLicenses] = useState<LicenseEntry[]>([])
  const [backendLicenses, setBackendLicenses] = useState<LicenseEntry[]>([])
  const [searchFe, setSearchFe] = useState('')
  const [searchBe, setSearchBe] = useState('')

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

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      <h1 className="text-2xl font-bold">{t('about.title')}</h1>

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
