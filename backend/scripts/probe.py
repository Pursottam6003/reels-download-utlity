import sys
import json
from fastapi.testclient import TestClient

from backend.main import app


def main():
    if len(sys.argv) < 2:
        print("Usage: probe.py <url>")
        sys.exit(2)

    url = sys.argv[1]
    client = TestClient(app)
    resp = client.post("/download", json={"url": url})
    print(f"status: {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("failed to decode json:", e)
        print(resp.text)


if __name__ == "__main__":
    main()
