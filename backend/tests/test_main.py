from fastapi.testclient import TestClient
from unittest.mock import patch
import pytest

from backend.main import app

client = TestClient(app)


def fake_extract_info(self_or_url, *args, **kwargs):
    # when called as bound method, first arg will be the url; support both shapes
    return {
        "id": "abc123",
        "title": "Test Video",
        "uploader": "tester",
        "thumbnail": "http://example.com/thumb.jpg",
        "duration": 12,
        "formats": [
            {"format_id": "18", "ext": "mp4", "format_note": "360p", "height": 360, "width": 640, "filesize": 11111, "url": "http://cdn/test360.mp4"},
            {"format_id": "22", "ext": "mp4", "format_note": "720p", "height": 720, "width": 1280, "filesize": 33333, "url": "http://cdn/test720.mp4"},
        ],
    }


@patch("backend.main.yt_dlp.YoutubeDL.extract_info", new=fake_extract_info)
def test_download_returns_metadata_and_download_url():
    # stub a lightweight redis client in app.state so the rate limiter passes
    class StubRedis:
        async def incr(self, key):
            return 1

        async def expire(self, key, seconds):
            return True

        async def ttl(self, key):
            return -1

    app.state.redis = StubRedis()

    resp = client.post("/download", json={"url": "http://example.com/watch?v=1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Video"
    assert data["uploader"] == "tester"
    assert "formats" in data and isinstance(data["formats"], list)
    assert data["download_url"].endswith("test720.mp4")
