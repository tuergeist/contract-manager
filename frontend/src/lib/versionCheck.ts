import { useQuery, gql } from '@apollo/client'
import { useMemo } from 'react'

export const LATEST_VERSION_QUERY = gql`
  query LatestVersion {
    latestVersion
  }
`

/** Running build version, baked in at build time (see Dockerfile.prod). */
export const CURRENT_VERSION: string =
  (import.meta.env.VITE_BUILD_VERSION as string | undefined) || 'dev'

/** Parse a plain ``x.y.z`` semver string into a comparable tuple. */
export function parseVersion(
  value: string | null | undefined
): [number, number, number] | null {
  if (!value) return null
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(value.trim().replace(/^v/, ''))
  if (!match) return null
  return [Number(match[1]), Number(match[2]), Number(match[3])]
}

/** True when ``latest`` is strictly newer than ``current``. */
export function isNewer(
  latest: string | null | undefined,
  current: string | null | undefined
): boolean {
  const l = parseVersion(latest)
  const c = parseVersion(current)
  if (!l || !c) return false
  for (let i = 0; i < 3; i++) {
    if (l[i] > c[i]) return true
    if (l[i] < c[i]) return false
  }
  return false
}

export interface UpdateStatus {
  /** The newer version, or null when up to date / unknown. */
  latestVersion: string | null
  currentVersion: string
  updateAvailable: boolean
}

/**
 * Poll the backend for the newest released version and compare it against the
 * running build. Returns ``updateAvailable`` only when a strictly newer semver
 * tag exists. Fails silently (no update) when offline or on a ``dev`` build.
 */
export function useUpdateStatus(): UpdateStatus {
  const { data } = useQuery<{ latestVersion: string | null }>(
    LATEST_VERSION_QUERY,
    {
      // Refetch occasionally in long-lived sessions; backend caches for 1h.
      pollInterval: 60 * 60 * 1000,
      fetchPolicy: 'cache-and-network',
      errorPolicy: 'ignore',
    }
  )

  return useMemo(() => {
    const latest = data?.latestVersion ?? null
    const updateAvailable = isNewer(latest, CURRENT_VERSION)
    return {
      latestVersion: updateAvailable ? latest : null,
      currentVersion: CURRENT_VERSION,
      updateAvailable,
    }
  }, [data])
}
