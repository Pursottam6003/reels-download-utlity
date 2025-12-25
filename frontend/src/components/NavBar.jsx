import React from 'react'

export default function NavBar() {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="3" width="18" height="18" rx="4" fill="#0ea5e9" />
            <path d="M7 12.5L10 10l4 5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="logo-text">Reel Downloader</span>
        </div>
      </div>
    </header>
  )
}
