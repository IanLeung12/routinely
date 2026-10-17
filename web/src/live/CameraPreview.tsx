import { useEffect, useState, type ReactNode } from 'react'
import './cameraPreview.css'

type CameraPreviewProps = {
  port?: number
  children: ReactNode
  probe?: () => Promise<boolean>
}

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1'])

async function defaultProbe(port: number): Promise<boolean> {
  if (!LOCAL_HOSTNAMES.has(window.location.hostname)) return false
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 1000)
  try {
    const response = await fetch(`http://127.0.0.1:${port}/health`, { signal: controller.signal })
    const body = await response.json()
    return body?.ok === true
  } catch {
    return false
  } finally {
    clearTimeout(timeout)
  }
}

export function CameraPreview({ port = 8765, children, probe }: CameraPreviewProps) {
  const [available, setAvailable] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    let cancelled = false
    const run = probe ?? (() => defaultProbe(port))
    run().then((ok) => {
      if (!cancelled) setAvailable(ok)
    })
    return () => {
      cancelled = true
    }
  }, [port, probe])

  if (!available) return <>{children}</>

  return (
    <div className="camera-preview">
      <button
        type="button"
        className="btn btn--secondary camera-preview__toggle"
        aria-pressed={showPreview}
        onClick={() => setShowPreview((shown) => !shown)}
      >
        Show camera preview (this device only)
      </button>
      {showPreview ? (
        <div className="camera-preview__box">
          <img className="camera-preview__video" src={`http://127.0.0.1:${port}/preview.mjpg`} alt="" />
          <span className="camera-preview__badge">Preview · not recorded · this device only</span>
          <div className="camera-preview__overlay">{children}</div>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

export default CameraPreview
