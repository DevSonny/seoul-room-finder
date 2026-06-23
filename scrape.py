#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scrape 33m2, Ziptoss, and Airbnb for rooms near KHU (경희대).
Filter: rent+관리비 ≤ ₩1,200,000/mo, Line 1/6 station, no basement/rooftop."""

import datetime
import html as html_mod
import json
import math
import os
import random
import re
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

API_33M2 = "https://api.33m2.co.kr/v1"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
BUDGET = 1_200_000
W2M = 52 / 12
KHU_LAT, KHU_LNG = 37.589, 127.057
FLOOR_BAD_RE = re.compile(r"지하|반지하|옥탑")
EXCLUDED_TYPES = {
    "GOSHIWON", "고시원", "SHARE_HOUSE", "셰어하우스", "쉐어하우스",
    "하숙", "하숙집", "BOARDING", "Share house",
}

# Line 1 stations within ~1 hr of 회기
LINE1_STATIONS = {
    "회기", "청량리", "제기동", "신설동", "동대문", "종로5가", "종로3가", "종각",
    "시청", "서울역", "남영", "용산", "노량진", "대방", "신길", "영등포", "신도림",
    "신이문", "외대앞", "석계", "광운대", "월계", "노원", "창동", "쌍문", "도봉",
    "도봉산", "망월사", "회룡",
}
# Line 6 stations (all within 1 hr via Seokgye transfer)
LINE6_STATIONS = {
    "석계", "화랑대", "봉화산", "신내", "상월곡", "월곡", "고려대", "안암", "보문",
    "창신", "동묘앞", "신당", "청구", "약수", "버티고개", "한강진", "이태원", "녹사평",
    "삼각지", "효창공원앞", "공덕", "광흥창", "대흥", "새절", "응암", "역촌", "불광",
    "독바위", "연신내", "구산",
}
ALL_TARGET_STATIONS = LINE1_STATIONS | LINE6_STATIONS

OPTION_MAP = {
    "REFRIGERATOR": "Fridge", "WASHING_MACHINE": "Washer", "AIR_CONDITIONER": "A/C",
    "WIFI": "WiFi", "BED": "Bed", "GAS_STOVE": "Gas range", "INDUCTION": "Induction",
    "DESK": "Desk", "WARDROBE": "Wardrobe", "MICROWAVE": "Microwave",
    "WATER_PURIFIER": "Water purifier", "DOORLOCK": "Door-lock", "CCTV": "CCTV",
    "TV": "TV", "SHOE_RACK": "Shoe rack", "SOFA": "Sofa",
}
TYPE_MAP = {
    "STUDIO": "Furnished studio", "OFFICETEL": "Officetel", "GOSHIWON": "Goshiwon",
    "SHARE_HOUSE": "Share house", "APARTMENT": "Apartment",
    "DETACHED_HOUSE": "Detached house",
    "원룸건물": "Furnished studio", "오피스텔": "Officetel", "고시원": "Goshiwon",
    "셰어하우스": "Share house", "아파트": "Apartment",
    "단독주택": "Detached house", "빌라": "Villa",
}

# Ziptoss station search list (Line 1 + Line 6 핵심역)
ZIPTOSS_STATIONS = [
    "회기역", "청량리역", "신이문역", "외대앞역", "석계역",
    "광운대역", "월계역", "제기동역", "고려대역", "안암역",
    "월곡역", "상월곡역", "보문역", "동묘앞역",
]


# ── common helpers ─────────────────────────────────────────────────────────────

def _get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == tries - 1:
                raise
            time.sleep((2 ** attempt) + random.uniform(0.3, 0.8))


def _get_html(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt == tries - 1:
                raise
            time.sleep((2 ** attempt) + random.uniform(0.3, 0.8))


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def floor_ok(text):
    return not FLOOR_BAD_RE.search(text or "")


def near_target_line(station_str, lat, lng):
    """True if station name is in allow-list.
    Falls back to geo (≤2 km of KHU) only when station_str is empty."""
    if station_str:
        for tok in re.split(r"[,、/\s]+", station_str):
            clean = tok.strip().rstrip("역").strip()
            if clean in ALL_TARGET_STATIONS:
                return True
        return False  # station known but not Line 1/6
    if lat and lng:
        return haversine(float(lat), float(lng), KHU_LAT, KHU_LNG) <= 2.0
    return False


def reverse_geocode(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&accept-language=ko"
    req = urllib.request.Request(url, headers={'User-Agent': 'seoul-room-finder/1.0 (contact: devsonny@gmail.com)'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            address = data.get('address', {})
            
            state = address.get('state', address.get('city', ''))
            city_district = address.get('city_district', address.get('county', address.get('borough', '')))
            suburb = address.get('quarter', address.get('suburb', ''))
            road = address.get('road', '')
            house_number = address.get('house_number', '')
            
            parts = [state, city_district, suburb, road, house_number]
            parts = [p for p in parts if p]
            
            if len(parts) >= 3:
                return " ".join(parts)
            else:
                display_name = data.get('display_name', '')
                if display_name:
                    return display_name
                return ""
    except Exception as e:
        print(f"Error geocoding {lat},{lng}: {e}")
        return ""


def dedup_by_key(listings, key_fn):
    seen = set()
    out = []
    for x in listings:
        k = key_fn(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


# ── 33m2 source ────────────────────────────────────────────────────────────────

def _fetch_list_33m2(keyword):
    results = []
    page = 1
    while True:
        params = urlencode({"keyword": keyword, "size": 200, "page": page})
        url = f"{API_33M2}/rooms?{params}"
        try:
            raw = _get(url)
        except Exception as e:
            print(f"  [warn] 33m2 list failed keyword={keyword} page={page}: {e}")
            break
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


def _fetch_detail_33m2(rid):
    url = f"{API_33M2}/rooms/{rid}"
    try:
        raw = _get(url)
        if isinstance(raw, dict) and "data" in raw:
            return raw["data"]
        return raw
    except Exception as e:
        print(f"  [warn] 33m2 detail failed rid={rid}: {e}")
        return None


def _normalize_33m2(rec, detail):
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
        util_parts = (
            (["electricity"] if inc_elec else [])
            + (["water"] if inc_water else [])
            + (["gas"] if inc_gas else [])
        )
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
        "id": str(rid),
        "name": room_name,
        "platform": "33m2",
        "type": room_type,
        "rent_weekly": using_fee,
        "maintenance_weekly": mgmt_fee,
        "rent_monthly": rent_monthly,
        "maintenance_monthly": maintenance_monthly,
        "total_monthly": total_monthly,
        "deposit": deposit,
        "size_m2": round(float(size_m2 or 0), 1),
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


def fetch_33m2():
    print("[33m2] Fetching...")
    all_rooms = {}
    for kw in ["회기", "경희대"]:
        rooms = _fetch_list_33m2(kw)
        print(f"  keyword={kw} -> {len(rooms)} rooms")
        for r in rooms:
            rid = r.get("rid", r.get("id"))
            if rid:
                all_rooms[rid] = r
    print(f"  Unique: {len(all_rooms)}")

    candidates = []
    for rid, r in all_rooms.items():
        if r.get("propertyType", "") in EXCLUDED_TYPES:
            continue
        addr = r.get("addrLot", "") or r.get("town", "") or ""
        if not floor_ok(addr):
            continue
        if ((r.get("usingFee", 0) or 0) + (r.get("mgmtFee", 0) or 0)) * W2M > BUDGET:
            continue
        candidates.append(r)
    print(f"  After pre-filter: {len(candidates)}")

    listings = []
    for i, r in enumerate(candidates):
        rid = r.get("rid", r.get("id"))
        if i > 0:
            time.sleep(random.uniform(0.5, 1.0))
        detail = _fetch_detail_33m2(rid)
        norm = _normalize_33m2(r, detail)
        if norm["total_monthly"] > BUDGET:
            continue
        if not floor_ok(norm.get("address", "") + norm.get("name", "")):
            continue
        if not near_target_line(norm["station"], r.get("lat"), r.get("lng")):
            continue
        listings.append(norm)

    listings = dedup_by_key(listings, lambda x: (x["address"], x["rent_monthly"]))
    print(f"  [33m2] Final: {len(listings)}")
    return listings


# ── Ziptoss source ─────────────────────────────────────────────────────────────

def fetch_ziptoss():
    print("[Ziptoss] Fetching...")
    seen_ids = set()
    listings = []

    for stn in ZIPTOSS_STATIONS:
        url = "https://ziptoss.com/en/map/" + quote(stn) + "?contract=monthly"
        try:
            page_html = _get_html(url)
            time.sleep(random.uniform(0.8, 1.5))
        except Exception as e:
            print(f"  [warn] Ziptoss fetch failed {stn}: {e}")
            continue

        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page_html, re.DOTALL)
        if not m:
            print(f"  [warn] Ziptoss no __NEXT_DATA__ for {stn}")
            continue

        try:
            nd = json.loads(m.group(1))
            pp = nd.get("props", {}).get("pageProps", {})
            properties = pp.get("properties") or []
            info = pp.get("info") or {}
            station_label = info.get("label") or stn
        except Exception as e:
            print(f"  [warn] Ziptoss JSON parse failed {stn}: {e}")
            continue

        print(f"  {stn}: {len(properties)} properties")

        for prop in properties:
            pid = str(prop.get("id") or "")
            if not pid or pid in seen_ids:
                continue

            # Floor filter (floorCode: 20=above-ground, 10=basement, 30=rooftop)
            floor_code = prop.get("floorCode") or 20
            try:
                floor_code = int(floor_code)
            except (TypeError, ValueError):
                floor_code = 20
            if floor_code in {10, 30}:
                continue

            # Money: prices array (만원 → won), prefer "월세" contract
            prices = prop.get("prices") or []
            monthly_price = next(
                (p for p in prices if p.get("contract") == "월세"), None
            ) or (prices[0] if prices else None)
            if not monthly_price:
                continue

            rent_monthly = int((monthly_price.get("monthly") or 0) * 10000)
            deposit = int((monthly_price.get("deposit") or 0) * 10000)
            maintenance_monthly = int((prop.get("manageFee") or 0) * 10000)
            total_monthly = rent_monthly + maintenance_monthly

            if total_monthly > BUDGET or total_monthly == 0:
                continue

            # Building metadata
            building = prop.get("building") or {}
            nearest_stn = building.get("nearestStation") or ""  # e.g. "외대앞역"
            dong = building.get("dong") or ""
            sigungu = building.get("sigungu") or ""
            address_fallback = f"{sigungu} {dong}".strip()
            prop_type = building.get("type") or "Studio"

            # Exclude share houses and goshiwons from Ziptoss
            if prop_type in EXCLUDED_TYPES:
                continue

            # Lat/lng: coordinates = [lng, lat]
            coords = (building.get("point") or {}).get("coordinates") or [0, 0]
            lng = float(coords[0]) if len(coords) > 1 else 0
            lat = float(coords[1]) if len(coords) > 1 else 0

            address = reverse_geocode(lat, lng) if (lat and lng) else address_fallback
            if not address:
                address = address_fallback
            if lat and lng:
                time.sleep(1.2) # Rate limit

            size_m2 = float(prop.get("area") or 0)
            options_raw = prop.get("options") or []
            options_str = ", ".join(options_raw) if options_raw else "Full-option"

            # Name: generate from type + dong
            name = f"{prop_type}, {dong}" if dong else f"Ziptoss #{pid}"

            if not floor_ok(name + " " + address):
                continue

            # Station line filter using nearest station
            if not near_target_line(nearest_stn, lat, lng):
                continue

            link = "https://ziptoss.com/en/map/" + quote(nearest_stn or stn) + "?contract=monthly"

            seen_ids.add(pid)
            listings.append({
                "id": f"zt_{pid}",
                "name": name,
                "platform": "ziptoss",
                "type": prop_type,
                "rent_weekly": 0,
                "maintenance_weekly": 0,
                "rent_monthly": rent_monthly,
                "maintenance_monthly": maintenance_monthly,
                "total_monthly": total_monthly,
                "deposit": deposit,
                "size_m2": round(size_m2, 1),
                "size": f"{size_m2:.0f} m²" if size_m2 else "—",
                "min_weeks": 4,
                "station": nearest_stn or station_label,
                "address": address,
                "options": options_str,
                "english": "Yes — English site, English contract",
                "link": link,
                "naver": f"https://map.naver.com/p/search/{lat},{lng}" if (lat and lng) else "https://map.naver.com/p/search/" + quote(address if address else stn),
                "lat": lat,
                "lng": lng,
                "rent": f"₩{rent_monthly:,} / mo",
                "total_display": f"₩{total_monthly:,} / mo",
                "deposit_display": f"₩{deposit:,}",
                "commute": f"Near {nearest_stn or station_label}",
                "notes": f"Ziptoss monthly contract. Floor {floor_code}.",
            })

    listings = dedup_by_key(listings, lambda x: x["id"])
    print(f"  [Ziptoss] Final: {len(listings)}")
    return listings


# ── Airbnb source (best-effort) ────────────────────────────────────────────────

def _extract_airbnb_cards(obj, depth=0):
    """Recursively find listing-like objects in Airbnb's nested JSON."""
    cards = []
    if depth > 15:
        return cards
    if isinstance(obj, dict):
        has_id = "id" in obj and isinstance(obj["id"], (int, str))
        has_loc = ("lat" in obj or "latitude" in obj) and ("lng" in obj or "longitude" in obj)
        has_price = "price" in obj or "pricePerNight" in obj
        has_name = "name" in obj or "title" in obj
        if has_id and (has_loc or has_price) and has_name:
            cards.append(obj)
        else:
            for v in obj.values():
                cards.extend(_extract_airbnb_cards(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            cards.extend(_extract_airbnb_cards(item, depth + 1))
    return cards


def fetch_airbnb():
    print("[Airbnb] Fetching (best-effort)...")
    listings = []
    seen_ids = set()

    search_urls = [
        "https://www.airbnb.com/s/Hoegi--Seoul--South-Korea/homes"
        "?monthly_start_date=2026-08-01&monthly_length=4&price_max=1200000",
        "https://www.airbnb.com/s/%ED%9A%8C%EA%B8%B0%EB%8F%99/homes"
        "?monthly_start_date=2026-08-01&monthly_length=4",
    ]

    for url in search_urls:
        try:
            page_html = _get_html(url)
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"  [warn] Airbnb fetch failed: {e}")
            continue

        state = None
        m = re.search(r'data-deferred-state-0="([^"]+)"', page_html)
        if m:
            try:
                state = json.loads(html_mod.unescape(m.group(1)))
            except Exception as e:
                print(f"  [warn] Airbnb deferred-state-0 parse failed: {e}")

        if state is None:
            # Fallback: look for __NEXT_DATA__
            m2 = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                           page_html, re.DOTALL)
            if m2:
                try:
                    state = json.loads(m2.group(1))
                except Exception as e:
                    print(f"  [warn] Airbnb __NEXT_DATA__ parse failed: {e}")

        if state is None:
            print("  [warn] Airbnb: no parseable state found")
            continue

        cards = _extract_airbnb_cards(state)
        print(f"  Airbnb raw cards: {len(cards)}")

        for card in cards:
            aid = str(card.get("id", ""))
            if not aid or aid in seen_ids:
                continue
            name = card.get("name") or card.get("title") or f"Airbnb #{aid}"
            lat = float(card.get("lat") or card.get("latitude") or 0)
            lng = float(card.get("lng") or card.get("longitude") or 0)
            price_per_night = float(card.get("price") or card.get("pricePerNight") or 0)

            if lat and lng and haversine(lat, lng, KHU_LAT, KHU_LNG) > 2.5:
                continue
            if FLOOR_BAD_RE.search(name):
                continue
            if re.search(r"고시원|쉐어|셰어", name):
                continue

            total_est = int(price_per_night * 30) if price_per_night > 0 else 0
            if total_est > BUDGET and total_est > 0:
                continue

            seen_ids.add(aid)
            rent_str = f"₩{total_est:,} / mo (est.)" if total_est else "See listing"
            listings.append({
                "id": f"ab_{aid}",
                "name": name,
                "platform": "airbnb",
                "type": "Airbnb listing",
                "rent_weekly": 0,
                "maintenance_weekly": 0,
                "rent_monthly": total_est,
                "maintenance_monthly": 0,
                "total_monthly": total_est,
                "deposit": 0,
                "size_m2": 0.0,
                "size": "—",
                "min_weeks": 4,
                "station": "Near 회기 (estimated)",
                "address": "",
                "options": "See listing",
                "english": "Yes — English platform",
                "link": f"https://www.airbnb.com/rooms/{aid}",
                "naver": "https://map.naver.com/p/search/" + quote("회기역"),
                "rent": rent_str,
                "total_display": rent_str,
                "deposit_display": "N/A",
                "commute": "Near 회기 (~15 min walk to KHU)",
                "notes": "⚠ Airbnb — 층/종류/관리비 필터 일부만 적용. 가격은 박당가×30 추산. 실제 확인 필수.",
            })

    listings = dedup_by_key(listings, lambda x: x["id"])
    print(f"  [Airbnb] Final: {len(listings)}")
    return listings


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "listings.json")

    all_listings = []

    try:
        all_listings.extend(fetch_33m2())
    except Exception as e:
        print(f"[ERROR] 33m2 failed: {e}")

    try:
        all_listings.extend(fetch_ziptoss())
    except Exception as e:
        print(f"[ERROR] Ziptoss failed: {e}")

    try:
        all_listings.extend(fetch_airbnb())
    except Exception as e:
        print(f"[ERROR] Airbnb failed: {e}")

    if not all_listings:
        if os.path.exists(out_path):
            print("WARNING: all fetches failed; keeping existing listings.json")
        else:
            print("WARNING: all fetches failed; build.py will use fallback listings")
        return

    all_listings.sort(key=lambda x: x["total_monthly"])

    sources = sorted({x["platform"] for x in all_listings})
    per_source = {s: sum(1 for x in all_listings if x["platform"] == s) for s in sources}
    print(f"Total: {len(all_listings)} | Sources: {per_source}")

    result = {
        "snapshot": datetime.date.today().isoformat(),
        "budget": BUDGET,
        "sources": sources,
        "count": len(all_listings),
        "listings": all_listings,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
