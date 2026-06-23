#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scrape 33m2 API for rooms near KHU (경희대), filter to total ≤ ₩1,200,000/mo."""

import datetime
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

API = "https://api.33m2.co.kr/v1"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
KEYWORDS = ["회기", "경희대"]
BUDGET = 1_200_000
W2M = 52 / 12
KHU_DONGS = {"회기동", "휘경동", "이문동", "전농동", "청량리동", "제기동", "종암동"}
KHU_LAT, KHU_LNG = 37.589, 127.057

OPTION_MAP = {
    "REFRIGERATOR": "Fridge",
    "WASHING_MACHINE": "Washer",
    "AIR_CONDITIONER": "A/C",
    "WIFI": "WiFi",
    "BED": "Bed",
    "GAS_STOVE": "Gas range",
    "INDUCTION": "Induction",
    "DESK": "Desk",
    "WARDROBE": "Wardrobe",
    "MICROWAVE": "Microwave",
    "WATER_PURIFIER": "Water purifier",
    "DOORLOCK": "Door-lock",
    "CCTV": "CCTV",
    "TV": "TV",
    "SHOE_RACK": "Shoe rack",
    "SOFA": "Sofa",
}

TYPE_MAP = {
    # English enum (from detail API)
    "STUDIO": "Furnished studio",
    "OFFICETEL": "Officetel",
    "GOSHIWON": "Goshiwon",
    "SHARE_HOUSE": "Share house",
    "APARTMENT": "Apartment",
    "DETACHED_HOUSE": "Detached house",
    # Korean strings (from list API)
    "원룸건물": "Furnished studio",
    "오피스텔": "Officetel",
    "고시원": "Goshiwon",
    "셰어하우스": "Share house",
    "아파트": "Apartment",
    "단독주택": "Detached house",
    "빌라": "Villa",
}


def _get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == tries - 1:
                raise
            delay = (2 ** attempt) + random.uniform(0.3, 0.8)
            time.sleep(delay)


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def fetch_list(keyword):
    results = []
    page = 1
    while True:
        params = urlencode({"keyword": keyword, "size": 200, "page": page})
        url = f"{API}/rooms?{params}"
        try:
            raw = _get(url)
        except Exception as e:
            print(f"  [warn] list fetch failed keyword={keyword} page={page}: {e}")
            break
        # Actual response: {"code":"SCSS_001","data":{"rooms":{"content":[...],"last":bool}}}
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        if "rooms" in data:
            inner = data["rooms"]
            rooms = inner.get("content", [])
            is_last = inner.get("last", True)
        elif "content" in data:
            rooms = data["content"]
            is_last = data.get("last", True)
        elif isinstance(data, list):
            rooms = data
            is_last = True
        else:
            rooms = []
            is_last = True
        results.extend(rooms)
        if is_last or not rooms:
            break
        page += 1
        time.sleep(0.5)
    return results


def fetch_detail(rid):
    url = f"{API}/rooms/{rid}"
    try:
        raw = _get(url)
        # Actual response: {"code":"SCSS_001","data":{...}}
        if isinstance(raw, dict) and "data" in raw:
            return raw["data"]
        return raw
    except Exception as e:
        print(f"  [warn] detail fetch failed rid={rid}: {e}")
        return None


def normalize(rec, detail):
    rid = rec.get("rid", rec.get("id", ""))
    room_name = rec.get("roomName", rec.get("name", ""))
    property_type = rec.get("propertyType", "")
    room_type = TYPE_MAP.get(property_type, property_type)
    town = rec.get("town", "")

    using_fee = rec.get("usingFee", 0) or 0
    mgmt_fee = rec.get("mgmtFee", 0) or 0
    rent_monthly = round(using_fee * W2M)
    maintenance_monthly = round(mgmt_fee * W2M)
    total_monthly = rent_monthly + maintenance_monthly

    if detail:
        deposit = detail.get("deposit", 0) or 0
        size_m2 = detail.get("squareMeterSize") or rec.get("pyeongSize", 0) * 3.305785
        min_weeks = detail.get("minimumContractWeeks", 1) or 1
        stations = detail.get("subwayStations") or []
        basic_opts = detail.get("basicOptions") or []
        inc_elec = detail.get("includeElectricity", False)
        inc_water = detail.get("includeWater", False)
        inc_gas = detail.get("includeGas", False)
        address = detail.get("addrLot") or rec.get("addrLot", "")
    else:
        deposit = 0
        size_m2 = rec.get("pyeongSize", 0) * 3.305785
        min_weeks = 1
        stations = []
        basic_opts = []
        inc_elec = inc_water = inc_gas = False
        address = rec.get("addrLot", "")

    station = ", ".join(stations)

    opt_parts = [OPTION_MAP.get(o, o) for o in basic_opts if o in OPTION_MAP]
    if inc_elec and inc_water and inc_gas:
        opt_parts.append("all utilities included")
    elif inc_elec or inc_water or inc_gas:
        util_parts = []
        if inc_elec:
            util_parts.append("electricity")
        if inc_water:
            util_parts.append("water")
        if inc_gas:
            util_parts.append("gas")
        opt_parts.append(f"{'+'.join(util_parts)} included")
    options = ", ".join(opt_parts) if opt_parts else "Full-option"

    if "회기역" in station:
        commute = "Hoegi Stn, ~15 min walk or bus to KHU"
    elif "이문역" in station or "외대앞역" in station:
        commute = "~10–15 min to KHU"
    else:
        commute = "~20–30 min to KHU"

    notes_parts = [f"Min {min_weeks} week{'s' if min_weeks != 1 else ''}."]
    if min_weeks <= 2:
        notes_parts.append("Short-stay OK.")
    if maintenance_monthly > 0:
        notes_parts.append(f"관리비 ₩{maintenance_monthly:,}/mo included in total.")

    return {
        "id": rid,
        "name": room_name,
        "platform": "33m2",
        "type": room_type,
        "rent_weekly": using_fee,
        "maintenance_weekly": mgmt_fee,
        "rent_monthly": rent_monthly,
        "maintenance_monthly": maintenance_monthly,
        "total_monthly": total_monthly,
        "deposit": deposit,
        "size_m2": round(size_m2, 1),
        "size": f"{size_m2:.0f} m²",
        "min_weeks": min_weeks,
        "station": station,
        "address": address,
        "options": options,
        "english": "Yes — English app, foreign card OK",
        "link": f"https://web.33m2.co.kr/guest/room/{rid}",
        "naver": "https://map.naver.com/p/search/" + quote(address if address else town),
        "rent": f"₩{rent_monthly:,} / mo  (₩{using_fee:,} / week)",
        "total_display": f"₩{total_monthly:,} / mo",
        "deposit_display": f"₩{deposit:,}",
        "commute": commute,
        "notes": " ".join(notes_parts),
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "listings.json")

    # 1. Fetch all keywords, dedup by rid
    print("Fetching room lists...")
    all_rooms = {}
    for kw in KEYWORDS:
        print(f"  keyword={kw}")
        rooms = fetch_list(kw)
        print(f"  → {len(rooms)} rooms")
        for r in rooms:
            rid = r.get("rid", r.get("id"))
            if rid:
                all_rooms[rid] = r

    if not all_rooms:
        if os.path.exists(out_path):
            print("WARNING: all fetches failed; keeping existing listings.json")
        else:
            print("WARNING: all fetches failed; build.py will use fallback listings")
        return

    print(f"Total unique rooms: {len(all_rooms)}")

    # 2. Geo filter + type filter
    EXCLUDED_TYPES = {"GOSHIWON", "고시원", "SHARE_HOUSE", "셰어하우스", "쉐어하우스", "하숙", "하숙집", "BOARDING", "Share house"}
    geo_ok = []
    for rid, r in all_rooms.items():
        if r.get("propertyType", "") in EXCLUDED_TYPES:
            continue
        town = r.get("town", "")
        lat = r.get("lat") or 0.0
        lng = r.get("lng") or 0.0
        if town in KHU_DONGS:
            geo_ok.append(r)
        elif lat and lng and haversine(lat, lng, KHU_LAT, KHU_LNG) <= 1.5:
            geo_ok.append(r)
    print(f"After geo+type filter: {len(geo_ok)}")

    # 3. Budget pre-filter on list data
    budget_ok = [
        r for r in geo_ok
        if ((r.get("usingFee", 0) or 0) + (r.get("mgmtFee", 0) or 0)) * W2M <= BUDGET
    ]
    print(f"After budget pre-filter: {len(budget_ok)}")

    # 4. Fetch detail for survivors
    listings = []
    for i, r in enumerate(budget_ok):
        rid = r.get("rid", r.get("id"))
        if i > 0:
            time.sleep(random.uniform(0.5, 1.0))
        detail = fetch_detail(rid)
        norm = normalize(r, detail)
        listings.append(norm)

    # 5. Final filter, sort, dedup
    listings = [x for x in listings if x["total_monthly"] <= BUDGET]
    listings.sort(key=lambda x: x["total_monthly"])

    seen = set()
    deduped = []
    for x in listings:
        key = (x["address"], x["rent_monthly"])
        if key not in seen:
            seen.add(key)
            deduped.append(x)

    print(f"Final listings (≤₩{BUDGET:,}/mo, deduped): {len(deduped)}")

    result = {
        "snapshot": datetime.date.today().isoformat(),
        "budget": BUDGET,
        "source": "33m2 api",
        "count": len(deduped),
        "listings": deduped,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
