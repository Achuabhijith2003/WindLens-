"""Probe live Elexon BMRS API endpoints to verify WINDFOR historical access."""

import httpx
import json

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
HEADERS = {"Accept": "application/json", "User-Agent": "WindLens-Phase2-Verification/1.0"}

def test_endpoint(name: str, url: str, params: dict):
    print(f"\n--- Testing: {name} ---")
    print(f"URL: {url}")
    print(f"Params: {params}")
    try:
        with httpx.Client(timeout=15.0, headers=HEADERS) as client:
            resp = client.get(url, params=params)
            print(f"Status Code: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('content-type', '')}")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    print(f"Response: JSON List with {len(data)} items")
                    if data:
                        print("First item sample:", json.dumps(data[0], indent=2))
                elif isinstance(data, dict):
                    print(f"Response: JSON Dict with keys: {list(data.keys())}")
                    if "data" in data and isinstance(data["data"], list):
                        print(f"'data' list length: {len(data['data'])}")
                        if data["data"]:
                            print("First data item sample:", json.dumps(data["data"][0], indent=2))
                    else:
                        print("Sample:", json.dumps({k: str(v)[:100] for k, v in data.items()}, indent=2))
            else:
                print(f"Error text: {resp.text[:300]}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    # 1. Test FUELHH stream with WIND
    test_endpoint(
        "FUELHH stream (publish range Jan 1-2, 2026, fuelType=WIND)",
        f"{BASE_URL}/datasets/FUELHH/stream",
        {"publishDateTimeFrom": "2026-01-01T00:00:00Z", "publishDateTimeTo": "2026-01-01T02:00:00Z", "fuelType": "WIND"}
    )

    # 2. Test WINDFOR stream (publish range Dec 31, 2025 to Jan 1, 2026)
    test_endpoint(
        "WINDFOR stream (publish range Dec 31, 2025 to Jan 1, 2026)",
        f"{BASE_URL}/datasets/WINDFOR/stream",
        {"publishDateTimeFrom": "2025-12-31T00:00:00Z", "publishDateTimeTo": "2025-12-31T06:00:00Z"}
    )

    # 3. Test WINDFOR standard dataset
    test_endpoint(
        "WINDFOR standard dataset",
        f"{BASE_URL}/datasets/WINDFOR",
        {"publishDateTimeFrom": "2025-12-31T00:00:00Z", "publishDateTimeTo": "2025-12-31T06:00:00Z"}
    )

    # 4. Test forecast/generation/wind/history with from and to
    test_endpoint(
        "forecast/generation/wind/history (from/to)",
        f"{BASE_URL}/forecast/generation/wind/history",
        {"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T04:00:00Z"}
    )

    # 5. Test forecast/generation/wind/history with publishDateTime
    test_endpoint(
        "forecast/generation/wind/history (publishDateTime)",
        f"{BASE_URL}/forecast/generation/wind/history",
        {"publishDateTimeFrom": "2025-12-31T00:00:00Z", "publishDateTimeTo": "2025-12-31T06:00:00Z"}
    )

    # 6. Test forecast/generation/wind/evolution
    test_endpoint(
        "forecast/generation/wind/evolution",
        f"{BASE_URL}/forecast/generation/wind/evolution",
        {"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T04:00:00Z"}
    )

    # 7. Test forecast/generation/wind/latest
    test_endpoint(
        "forecast/generation/wind/latest",
        f"{BASE_URL}/forecast/generation/wind/latest",
        {}
    )

