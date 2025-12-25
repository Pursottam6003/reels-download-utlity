import React, { useState } from 'react'

export default function SearchBar({ onSearch, loading }) {
  const [url, setUrl] = useState('')

  function submit(e) {
    e.preventDefault()
    if (!url) return
    onSearch(url)
  }

  return (
    <form className="search-compact" onSubmit={submit}>
      <input
        type="text"
        placeholder="Paste YouTube or Instagram link"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        aria-label="video-url"
      />
      <button type="submit" className="btn primary large" disabled={loading}>
        {loading ? 'Searching…' : 'Get Links'}
      </button>
    </form>
  )
}
