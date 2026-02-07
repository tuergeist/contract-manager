/**
 * Screenshot capture utility using html2canvas
 */
import html2canvas from 'html2canvas'

export interface ScreenshotResult {
  success: boolean
  dataUrl?: string
  error?: string
}

/**
 * Capture a screenshot of the current page
 * @param quality - JPEG quality (0-1), default 0.8
 * @param maxWidth - Maximum width for compression, default 1920
 * @returns Promise with screenshot data URL or error
 */
export async function captureScreenshot(
  quality: number = 0.8,
  maxWidth: number = 1920
): Promise<ScreenshotResult> {
  try {
    // Capture the entire document body
    const canvas = await html2canvas(document.body, {
      // Logging disabled for production
      logging: false,
      // Use higher scale for better quality, will be compressed later
      scale: window.devicePixelRatio || 1,
      // Ignore certain elements that might cause issues
      ignoreElements: (element: Element) => {
        // Ignore feedback button/modal itself to avoid recursion
        return element.hasAttribute('data-feedback-ignore')
      },
      // Handle cross-origin images
      useCORS: true,
      allowTaint: true,
    })

    // Compress if needed
    let finalCanvas = canvas
    if (canvas.width > maxWidth) {
      finalCanvas = compressCanvas(canvas, maxWidth)
    }

    // Convert to JPEG for smaller file size
    const dataUrl = finalCanvas.toDataURL('image/jpeg', quality)

    return {
      success: true,
      dataUrl,
    }
  } catch (error) {
    console.error('Screenshot capture failed:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Screenshot capture failed',
    }
  }
}

/**
 * Compress a canvas to a maximum width while maintaining aspect ratio
 */
function compressCanvas(canvas: HTMLCanvasElement, maxWidth: number): HTMLCanvasElement {
  const ratio = maxWidth / canvas.width
  const newWidth = maxWidth
  const newHeight = canvas.height * ratio

  const compressedCanvas = document.createElement('canvas')
  compressedCanvas.width = newWidth
  compressedCanvas.height = newHeight

  const ctx = compressedCanvas.getContext('2d')
  if (ctx) {
    ctx.drawImage(canvas, 0, 0, newWidth, newHeight)
  }

  return compressedCanvas
}

/**
 * Get the size of a base64 data URL in bytes
 */
export function getDataUrlSize(dataUrl: string): number {
  // Remove data URL prefix
  const base64 = dataUrl.split(',')[1] || ''
  // Calculate size: base64 is ~33% larger than original
  return Math.round((base64.length * 3) / 4)
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
