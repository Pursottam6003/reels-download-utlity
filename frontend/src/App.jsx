import React, { useState } from 'react'
import NavBar from './components/NavBar'
import SearchBar from './components/SearchBar'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') || ''

function api(path) {
  if (!API_BASE) return path
  return `${API_BASE}${path}`
}

function humanSize(bytes) {
  if (!bytes && bytes !== 0) return 'unknown'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = Number(bytes)
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(v >= 10 ? 0 : 1)} ${units[i]}`
}

function dedupeFormatsByUrl(formats) {
  // Keep only formats that have a direct URL and deduplicate by URL.
  // If multiple entries share the same URL, prefer the one with larger height or filesize.
  const map = new Map()
  for (const f of formats || []) {
    if (!f || !f.url) continue
    const key = f.url
    const existing = map.get(key)
    if (!existing) {
      map.set(key, f)
      continue
    }
    // prefer one with higher resolution or filesize
    const existingScore = (existing.height || 0) * 2 + (existing.filesize || 0)
    const newScore = (f.height || 0) * 2 + (f.filesize || 0)
    if (newScore > existingScore) map.set(key, f)
  }
  return Array.from(map.values())
}

function groupFormats(formats) {
  const deduped = dedupeFormatsByUrl(formats)
  const audio = []
  const video = []
  for (const f of deduped) {
    const ext = (f.ext || '').toLowerCase()
    if (ext.includes('m4a') || ext === 'mp3' || (f.format_note || '').toLowerCase().includes('audio')) {
      audio.push(f)
    } else {
      video.push(f)
    }
  }
  // sort video by descending height (best first)
  video.sort((a, b) => (b.height || 0) - (a.height || 0))
  // sort audio by filesize desc
  audio.sort((a, b) => (b.filesize || 0) - (a.filesize || 0))
  return { audio, video }
}

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSearch(url) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const resp = await fetch(api('/download'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!resp.ok) throw new Error(await resp.text())
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const grouped = result ? groupFormats(result.formats) : { audio: [], video: [] }

  return (
    <div className="app-root">
      <NavBar />
      <main className="center-card">
        <div className="card">
          <h1 className="title">Reel Downloader</h1>
          <p className="subtitle">Paste a YouTube or Instagram URL to extract download options</p>

          <SearchBar onSearch={handleSearch} loading={loading} />

          {error && <div className="error">{error}</div>}

          {result && (
            <div className="meta">
              <div className="meta-left">
                {/* Use backend proxy for thumbnails to avoid hotlinking / CORS issues */}
                <img
                  src={result.thumbnail ? `${api('/stream')}?url=${encodeURIComponent(result.thumbnail)}` : undefined}
                  alt="thumb"
                  className="thumb-large"
                  onError={(e) => {
                    // fallback to direct thumbnail if proxy fails
                    if (result.thumbnail && e.currentTarget.src.indexOf('/stream?url=') !== -1) {
                      e.currentTarget.src = result.thumbnail
                    }
                  }}
                />
              </div>
              <div className="meta-right">
                <h2 className="video-title">{result.title}</h2>
                <p className="muted">{result.uploader} • {Math.round(result.duration || 0)}s</p>

                <div className="panel">
                  <div className="panel-row"><strong>Formats:</strong> {result.formats.length}</div>
                  <div className="panel-row"><strong>Video ID:</strong> {result.id}</div>
                </div>

                <h3>Video</h3>
                <div className="formats">
                  {grouped.video.map((f) => (
                    <div key={f.format_id} className="format">
                      <div className="format-info">
                        <div className="fmt-id">{f.format_id}</div>
                        <div className="fmt-desc">{f.ext} • {f.height || 'auto'}p • {humanSize(f.filesize)}</div>
                      </div>
                      <div className="actions">
                        {f.url ? (
                          <a
                            href={`${api('/stream')}?download=1&filename=${encodeURIComponent((result.title || 'video') + '.' + (f.ext||'mp4'))}&url=${encodeURIComponent(f.url)}`}
                            className="btn primary"
                          >
                            Download
                          </a>
                        ) : (
                          <button disabled className="btn disabled">No URL</button>
                        )}
                        {f.url && (
                          <a className="btn outline" href={`${api('/stream')}?url=${encodeURIComponent(f.url)}`} target="_blank" rel="noreferrer">Stream</a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <h3>Audio</h3>
                <div className="formats">
                  {grouped.audio.map((f) => (
                    <div key={f.format_id} className="format">
                      <div className="format-info">
                        <div className="fmt-id">{f.format_id}</div>
                        <div className="fmt-desc">{f.ext} • {humanSize(f.filesize)}</div>
                      </div>
                      <div className="actions">
                        {f.url ? (
                          <a href={f.url} target="_blank" rel="noreferrer" className="btn primary">Download</a>
                        ) : (
                          <button disabled className="btn disabled">No URL</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
