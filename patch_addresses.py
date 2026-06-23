#!/usr/bin/env python3
"""Patch listings.json: update Naver Map links to use exact coordinates (lat,lng search).
This is more precise than dong-level text search and requires no external geocoding API.
"""
import json, re, sys
from urllib.parse import quote

def extract_lat_lng(link_url):
    m = re.search(r'lat=([\d.]+)&lng=([\d.]+)', link_url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None

def naver_coords(lat, lng):
    # Naver Map coordinate search — shows a pin at exact GPS location
    return f"https://map.naver.com/p/search/{lat},{lng}"

def main():
    with open("listings.json", encoding="utf-8") as f:
        data = json.load(f)

    listings = data["listings"]
    updated = skipped = 0

    for r in listings:
        if r["platform"] == "ziptoss":
            lat, lng = extract_lat_lng(r.get("link", ""))
            if lat and lng:
                r["naver"] = naver_coords(lat, lng)
                r["lat"] = lat
                r["lng"] = lng
                updated += 1
            else:
                skipped += 1
        # 33m2 already has full address with building number → naver URL already precise

    print(f"Updated {updated} Ziptoss listings to coordinate-based Naver Map URLs.")
    print(f"Skipped {skipped} (no lat/lng in link).")

    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print("listings.json saved.")

if __name__ == "__main__":
    main()
