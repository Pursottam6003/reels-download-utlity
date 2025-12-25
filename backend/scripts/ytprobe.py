import sys
import json
import yt_dlp


def main():
    if len(sys.argv) < 2:
        print("Usage: ytprobe.py <url>")
        sys.exit(2)

    url = sys.argv[1]
    ydl_opts = {"skip_download": True, "nocheckcertificate": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"error: {e}")
            sys.exit(1)

    # if playlist-like, pick first
    if isinstance(info, dict) and info.get("entries"):
        entries = info.get("entries")
        if entries:
            info = entries[0]

    print(json.dumps({
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "formats_count": len(info.get("formats", []) or []),
    }, indent=2))


if __name__ == "__main__":
    main()
