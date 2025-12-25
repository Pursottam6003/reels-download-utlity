from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import httpx
import redis.asyncio as redis
from starlette.responses import StreamingResponse
import asyncio

app = FastAPI(title="reels-downloader-backend")

# Allow local dev/frontends to call this API. In production restrict origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    url: HttpUrl
    format_id: Optional[str] = None


@app.post("/download")
async def download(req: DownloadRequest, request: Request, _rl=Depends(lambda: None)) -> Dict[str, Any]:
    """Extract metadata and direct stream URLs for a given media URL.

    This endpoint does not host files. It uses yt-dlp to probe the source
    and returns available formats and a selected direct URL (temporary).
    """
    ydl_opts = {"skip_download": True, "nocheckcertificate": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(str(req.url), download=False)
    except Exception as exc:
        # bubble a usable error message to the client
        raise HTTPException(status_code=400, detail=f"failed to extract info: {exc}")

    # handle playlist-like responses by taking the first entry
    if isinstance(info, dict) and info.get("entries"):
        entries = info.get("entries")
        if entries:
            info = entries[0]

    formats: List[Dict[str, Any]] = []
    for f in info.get("formats", []) or []:
        formats.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "format_note": f.get("format_note"),
            "height": f.get("height"),
            "width": f.get("width"),
            "filesize": f.get("filesize"),
            "url": f.get("url"),
        })

    # pick the requested format if provided, otherwise choose best available with a URL
    download_url = None
    if req.format_id:
        for f in formats:
            if f.get("format_id") == req.format_id and f.get("url"):
                download_url = f.get("url")
                break

    if not download_url:
        # pick highest height (quality) that has a direct url
        sorted_formats = sorted(formats, key=lambda x: (x.get("height") or 0), reverse=True)
        for f in sorted_formats:
            if f.get("url"):
                download_url = f.get("url")
                break

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats": formats,
        "download_url": download_url,
    }


@app.get("/")
def root():
    return {"status": "ok", "message": "reels-downloader-backend"}


## --- Redis-backed simple rate limiter ------------------
RATE_LIMIT = 20  # requests
RATE_PERIOD = 60  # seconds


async def get_redis_client() -> redis.Redis:
    # created at startup and stored on app.state
    return app.state.redis


async def rate_limit_dep(request: Request):
    """Simple per-IP rate limiter using Redis INCR + EXPIRE.

    Raises HTTPException 429 when exceeded.
    """
    r: redis.Redis = await get_redis_client()
    # determine client IP
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate:{client_ip}"
    try:
        # use atomic INCR and set expiry if new
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, RATE_PERIOD)
        if current > RATE_LIMIT:
            ttl = await r.ttl(key)
            raise HTTPException(status_code=429, detail=f"rate limit exceeded, try again in {ttl}s")
    except redis.RedisError:
        # on redis errors, allow the request (fail-open) but log in real app
        return


@app.on_event("startup")
async def startup_event():
    # create redis client (default localhost, change via env var in prod)
    app.state.redis = redis.Redis()


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await app.state.redis.close()
    except Exception:
        pass


@app.get("/stream")
async def stream(url: HttpUrl, request: Request, download: bool = False, filename: Optional[str] = None, _rl=Depends(rate_limit_dep)):
    """Proxy and stream the content at `url` to the client without storing it.

    This hides the direct CDN URL from the client and allows server-side limits.
    """
    timeout = httpx.Timeout(30.0, connect=10.0)

    # Do a lightweight HEAD to get headers and status before streaming
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as head_client:
            head_resp = await head_client.head(str(url))
    except (httpx.RequestError, asyncio.TimeoutError) as exc:
        raise HTTPException(status_code=502, detail=f"upstream request failed: {exc}")

    if head_resp.status_code >= 400:
        raise HTTPException(status_code=head_resp.status_code, detail="upstream returned an error")

    content_type = head_resp.headers.get("content-type", "application/octet-stream")
    headers = {"content-type": content_type}
    if download:
        safe_name = None
        if filename:
            safe_name = filename.replace('"', "'")
        else:
            try:
                from urllib.parse import urlparse, unquote

                path = urlparse(str(url)).path
                base = unquote(path.split('/')[-1]) or 'download'
                safe_name = base
            except Exception:
                safe_name = 'download'
        headers['content-disposition'] = f'attachment; filename="{safe_name}"'

    async def stream_generator():
        # open a new client inside the generator so the stream stays alive for the iterator
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                async with client.stream("GET", str(url)) as resp:
                    if resp.status_code >= 400:
                        # surface an error to the caller
                        raise HTTPException(status_code=resp.status_code, detail="upstream returned an error")
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        yield chunk
        except (httpx.RequestError, asyncio.TimeoutError) as exc:
            # when streaming fails, stop iteration
            return

    return StreamingResponse(stream_generator(), headers=headers)

