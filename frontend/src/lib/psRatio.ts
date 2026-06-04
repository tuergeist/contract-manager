/**
 * PS-ratio color helpers.
 *
 * Thresholds are tenant-configurable (see Settings → Allgemein → Verträge).
 * Coloring is monotonic with four bands:
 *
 *   ratio < amberMin                  -> red
 *   amberMin <= ratio < yellowMin     -> amber
 *   yellowMin <= ratio < greenMin     -> yellow
 *   ratio >= greenMin                 -> green
 *
 * Defaults (used when the tenant has not customized): 1.0 / 1.5 / 2.0.
 */
export interface PsRatioThresholds {
  amberMin: number
  yellowMin: number
  greenMin: number
}

export const DEFAULT_PS_RATIO_THRESHOLDS: PsRatioThresholds = {
  amberMin: 1.0,
  yellowMin: 1.5,
  greenMin: 2.0,
}

export type PsRatioBand = 'red' | 'amber' | 'yellow' | 'green'

export function psRatioBand(
  ratio: number,
  thresholds: PsRatioThresholds = DEFAULT_PS_RATIO_THRESHOLDS,
): PsRatioBand {
  if (ratio >= thresholds.greenMin) return 'green'
  if (ratio >= thresholds.yellowMin) return 'yellow'
  if (ratio >= thresholds.amberMin) return 'amber'
  return 'red'
}

/**
 * Tailwind text-color class for a PS-ratio value.
 */
export function psRatioColorClass(
  ratio: number,
  thresholds: PsRatioThresholds = DEFAULT_PS_RATIO_THRESHOLDS,
): string {
  switch (psRatioBand(ratio, thresholds)) {
    case 'green':
      return 'text-green-700'
    case 'yellow':
      return 'text-yellow-600'
    case 'amber':
      return 'text-amber-700'
    case 'red':
      return 'text-red-700'
  }
}
