import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowUpCircle, X } from 'lucide-react'
import { useUpdateStatus, CURRENT_VERSION } from '@/lib/versionCheck'
import { ChangelogModal } from './ChangelogModal'

const DISMISS_KEY = 'updateBannerDismissedVersion'

/**
 * Thin green line shown at the top of the app when a newer released version is
 * available on GitHub. "View changelog" opens a modal listing all released
 * changes newer than the installed version (fetched from the repo). Dismissable
 * per version (remembered in localStorage) so it reappears for the next release.
 */
export function UpdateBanner() {
  const { t } = useTranslation()
  const { updateAvailable, latestVersion } = useUpdateStatus()
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISS_KEY)
  )
  const [modalOpen, setModalOpen] = useState(false)

  if (!updateAvailable || !latestVersion) return null
  if (dismissed === latestVersion) return null

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, latestVersion)
    setDismissed(latestVersion)
  }

  return (
    <>
      <div
        className="flex items-center justify-center gap-3 bg-green-600 px-4 py-1.5 text-sm text-white"
        data-testid="update-banner"
      >
        <ArrowUpCircle className="h-4 w-4 shrink-0" />
        <span>
          {t('updateBanner.message', {
            version: latestVersion,
            current: CURRENT_VERSION,
          })}
        </span>
        <button
          onClick={() => setModalOpen(true)}
          className="font-medium underline underline-offset-2 hover:text-green-100"
          data-testid="update-banner-link"
        >
          {t('updateBanner.action')}
        </button>
        <button
          onClick={handleDismiss}
          className="ml-2 rounded p-0.5 hover:bg-green-700"
          aria-label={t('updateBanner.dismiss')}
          data-testid="update-banner-dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <ChangelogModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        currentVersion={CURRENT_VERSION}
      />
    </>
  )
}
