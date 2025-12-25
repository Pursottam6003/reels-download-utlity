# reels-downloader-backend (MVP)

Small FastAPI backend that uses yt-dlp to extract direct stream URLs and metadata for videos (YouTube, Instagram Reels, Shorts, etc.). This project returns metadata and a direct streaming URL; it does not host or store media.

Quickstart (dev):

1. Create a virtualenv and install deps:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app locally:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

3. POST /download with JSON: { "url": "https://..." }

Notes / production:
- This returns direct URLs from the source CDN (which can be temporary/signed).
- Do NOT store copyrighted content. Add TOS / DMCA and disclaimers if you publicize this app.
- Add rate limiting, monitoring, and request validation before public deployment.
