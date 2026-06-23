#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate rooms.html (responsive) + rooms.xlsx from a single data source.
Rooms near Kyung Hee University (Seoul) for a one-semester exchange student.
Snapshot date: 2026-06-23. Prices on platforms change; treat as a guide."""

import html
import json
import os
from urllib.parse import quote

SNAPSHOT = "2026-06-23"

def naver(q):
    return "https://map.naver.com/p/search/" + quote(q)

def ziptoss_en(area):
    return "https://ziptoss.com/en/map/" + quote(area) + "?contract=monthly"

# ---------------------------------------------------------------- DATA
# Fallback listings (used when listings.json is absent or unreadable).
FALLBACK_FEATURED = [
    {
        "name": "Hoegi-dong full-option studio (KHU 2 min)",
        "platform": "33m2 (English app)",
        "type": "Furnished studio",
        "rent": "₩740,000 / mo  (₩170,000 / week)",
        "deposit": "₩330,000 (fixed)",
        "size": "13 m² (4 pyeong)",
        "station": "Hoegi Stn (Line 1 / Gyeongui-Jungang / Gyeongchun)",
        "commute": "KHU back gate 2-min walk",
        "options": "Bed, wardrobe, desk, fridge, microwave, washer, A/C, door-lock, CCTV; electricity+water+gas+internet ALL included",
        "english": "Yes — English app, foreign card OK",
        "link": "https://web.33m2.co.kr/guest/room/47052",
        "naver": naver("경희대학교 후문"),
        "notes": "Cheapest turnkey option right at the campus back gate. Min 2 weeks; 5% off for 8+ weeks. No ARC needed.",
    },
    {
        "name": "Hoegi-dong full-option studio (KHU 2 min, larger)",
        "platform": "33m2 (English app)",
        "type": "Furnished studio",
        "rent": "₩880,000 / mo  (₩220,000 / week)",
        "deposit": "₩330,000 (fixed)",
        "size": "20 m² (6 pyeong)",
        "station": "Hoegi Stn (Line 1)",
        "commute": "KHU back gate 2-min walk",
        "options": "Bed, wardrobe, desk, fridge, microwave, gas range, washer, water purifier, A/C, WiFi; utilities ALL included",
        "english": "Yes — English app, foreign card OK",
        "link": "https://web.33m2.co.kr/guest/room/47054",
        "naver": naver("경희대학교 후문"),
        "notes": "More space, still walk-to-class. Min 2 weeks; 5% off for 8+ weeks.",
    },
    {
        "name": "Hoegi / KHU open studio (deposit-based)",
        "platform": "Daangn (당근, KR only)",
        "type": "Open studio",
        "rent": "₩500,000 / mo",
        "deposit": "₩5,000,000",
        "size": "Studio",
        "station": "Hoegi Stn (Line 1)",
        "commute": "~10–15 min to KHU",
        "options": "Full-option typical for the building",
        "english": "No — needs Korean or an agent; bring a helper",
        "link": "https://www.daangn.com/kr/realty/?in=%ED%9A%8C%EA%B8%B0%EB%8F%99-97&salesType=one_room",
        "naver": naver("회기역"),
        "notes": "Lowest monthly rent IF the ₩5M deposit is affordable. Standard 1-yr leases; ask about a one-semester (short) contract.",
    },
]

def load_featured():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "listings.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not data.get("listings"):
            return [{**r, "total": ""} for r in FALLBACK_FEATURED]
        out = []
        for r in data["listings"]:
            out.append({
                "name": r["name"],
                "platform": r["platform"],
                "type": r["type"],
                "rent": r["rent"],
                "total": r["total_display"],
                "deposit": r["deposit_display"],
                "size": r["size"],
                "station": r["station"],
                "commute": r["commute"],
                "options": r["options"],
                "english": r["english"],
                "link": r["link"],
                "naver": r["naver"],
                "notes": r["notes"],
            })
        return out
    except Exception:
        return [{**r, "total": ""} for r in FALLBACK_FEATURED]


# Neighborhood guide — stable, non-expiring search links.
areas = [
    ("Hoegi-dong", "회기동", "Hoegi Stn", "Line 1 · Gyeongui-Jungang · Gyeongchun",
     "5–15 min (15-min walk or bus Dongdaemun-01)", "₩450,000 – 700,000",
     "Hongneung Forest", "홍릉수목원", "경희대", "회기역",
     "Closest & most convenient. Best for direct Line-1 access."),
    ("Imun-dong / HUFS area", "이문동·외대앞", "Hankuk Univ. of FS Stn (Oedae-ap)", "Line 1",
     "~10–15 min (walk via KHU back gate)", "₩450,000 – 650,000",
     "Hankuk Univ. of Foreign Studies", "한국외국어대학교", "외대앞역", "외대앞역",
     "Back-gate access; lively student street, cheap eats."),
    ("Cheongnyangni", "청량리", "Cheongnyangni Stn", "Line 1 · Gyeongui-Jungang · Suin-Bundang · GTX-B(future)",
     "~15–20 min (1 stop + bus)", "₩500,000 – 750,000",
     "Seoul Yangnyeong Herbal Market / Gyeongdong Market", "서울약령시·경동시장", "청량리역", "경동시장",
     "Major transfer hub; markets, malls, Lotte Castle tower."),
    ("Sinimun", "신이문", "Sinimun Stn", "Line 1",
     "~20 min (1 stop to Hoegi + walk/bus)", "₩400,000 – 600,000",
     "Uireung Royal Tomb (UNESCO)", "의릉", "신이문역", "의릉",
     "Quiet & cheaper, still one stop from Hoegi."),
    ("Seokgye", "석계", "Seokgye Stn", "Line 1 · Line 6",
     "~25–30 min (2 stops on Line 1)", "₩450,000 – 650,000",
     "Gyeongchun Line Forest Trail", "경춘선숲길", "석계역", "경춘선숲길",
     "KEY Line-6 transfer point. Good if you want a Line-6 home + Line-1 commute."),
    ("Gwangwoon-dae / Wolgye", "광운대·월계", "Gwangwoon-dae Stn", "Line 1",
     "~25–30 min (3 stops on Line 1)", "₩450,000 – 650,000",
     "Gyeongchun Line Forest Trail", "경춘선숲길", "광운대", "경춘선숲길",
     "Budget pick on Line 1; calm residential."),
    ("Anam (Korea Univ.)", "안암", "Anam Stn", "Line 6",
     "~40–45 min (Line 6 → Seokgye transfer → Line 1)", "₩500,000 – 750,000",
     "Korea University", "고려대학교", "안암", "고려대학교",
     "Big student area on Line 6; lots of listings & food."),
    ("Bomun", "보문", "Bomun Stn", "Line 6 · Ui-Sinseol",
     "~45–50 min (Line 6 → Seokgye → Line 1)", "₩450,000 – 650,000",
     "Bomunsa Temple", "보문사", "보문역", "보문사",
     "Two lines; quiet, by Seongbukcheon stream."),
    ("Wolgok", "월곡", "Wolgok Stn", "Line 6",
     "~40–45 min (Line 6 → Seokgye → Line 1)", "₩400,000 – 600,000",
     "Dongduk Women's Univ.", "동덕여자대학교", "월곡역", "동덕여자대학교",
     "Cheapest Line-6 option; student neighborhood."),
]

# Platforms with English support.
platforms = [
    ("Ziptoss", "English-only site (/en)", "1 month+",
     "Negotiable", "Foreigners signing an English contract directly; biggest agency network",
     "https://ziptoss.com/en"),
    ("33m2 (삼삼엠투)", "English support, foreign card", "1 week+",
     "₩330,000 fixed", "Most listings; low fixed deposit; turnkey furnished short stays",
     "https://33m2.co.kr/landing/article_overseas"),
    ("LiveAnywhere", "EN / JP / CN", "1 month+",
     "Low / escrow", "Exchange & language students; instant foreign-card pay, email sign-up, escrow safety",
     "https://www.liveanywhere.me/en"),
    ("Wehome (위홈)", "English", "Short term+",
     "Varies", "Licensed legal homeshare; well-decorated whole units / studios",
     "https://www.wehome.me/"),
    ("Airbnb", "English", "Short term+",
     "Varies", "Fewer listings than before but still options; use the Monthly filter",
     "https://www.airbnb.com/s/Hoegi--Seoul/homes"),
]

suggestions = [
    ("Hoegi Station is your best bet", "It is a direct Line-1 stop AND served by Gyeongui-Jungang + Gyeongchun lines. KHU is a 15-min walk or one Dongdaemun-01 bus ride. Living near Hoegi keeps the commute under 20 minutes."),
    ("Keep the deposit low", "Without an ARC (Alien Registration Card, issued after arrival) landlords often want a bigger deposit. 33m2 (₩330k fixed), Ziptoss English contracts, and LiveAnywhere escrow are the safest low-deposit routes for foreigners."),
    ("One semester = watch the short-stay premium", "Turnkey short-stay platforms charge a monthly premium. If the ₩5M-deposit route is affordable, a normal studio via Ziptoss with a negotiated 4–6 month contract can be much cheaper per month."),
    ("Pay only through the platform / escrow", "Never wire money directly to a landlord before a signed contract. Check the property register (등기부등본) and use a licensed agent (공인중개사)."),
    ("Furnishing checklist", "Confirm: washer, fridge, A/C, induction/gas range, desk, bed, and WiFi are included before booking."),
    ("Hidden costs", "Ask whether maintenance fee (관리비) and utilities are separate. Korean winter gas heating can be expensive — confirm who pays."),
    ("Documents to bring", "Passport, financial proof, and (if available) ARC. Some short-stay platforms accept bookings without an ARC."),
]

# ---------------------------------------------------------------- HTML
def th(cells):
    return "<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>"

def td(label, val, is_link=False, link_text=None):
    if is_link and val:
        inner = f'<a href="{html.escape(val)}" target="_blank" rel="noopener">{html.escape(link_text or "Open")}</a>'
    else:
        inner = html.escape(str(val))
    return f'<td data-label="{html.escape(label)}">{inner}</td>'

def build_html():
    featured = load_featured()
    F = []
    for r in featured:
        F.append("<tr>"
            + td("Listing", r["name"])
            + td("Platform", r["platform"])
            + td("Type", r["type"])
            + td("Monthly rent", r["rent"])
            + td("Total /mo (incl 관리비)", r.get("total", ""))
            + td("Deposit", r["deposit"])
            + td("Size", r["size"])
            + td("Nearest station", r["station"])
            + td("Commute to KHU", r["commute"])
            + td("Options", r["options"])
            + td("English", r["english"])
            + td("Listing link", r["link"], True, "View listing")
            + td("Map", r["naver"], True, "Naver Map")
            + td("Notes", r["notes"])
            + "</tr>")
    feat_rows = "\n".join(F)

    A = []
    for (en, ko, st, line, commute, rent, lm_en, lm_ko, zarea, narea, note) in areas:
        A.append("<tr>"
            + td("Area", f"{en} ({ko})")
            + td("Nearest station", f"{st}")
            + td("Line(s)", line)
            + td("Commute to KHU", commute)
            + td("Typical rent / mo", rent)
            + td("Nearest landmark", f"{lm_en} ({lm_ko})")
            + td("Ziptoss (EN)", ziptoss_en(zarea), True, "Search rooms")
            + td("Map", naver(narea), True, "Naver Map")
            + td("Landmark map", naver(lm_ko), True, "See landmark")
            + td("Notes", note)
            + "</tr>")
    area_rows = "\n".join(A)

    P = []
    for (nm, eng, mn, dep, best, url) in platforms:
        P.append("<tr>"
            + td("Platform", nm)
            + td("English", eng)
            + td("Min stay", mn)
            + td("Deposit", dep)
            + td("Best for", best)
            + td("Open", url, True, "Visit site")
            + "</tr>")
    plat_rows = "\n".join(P)

    sug = "\n".join(
        f'<div class="card"><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></div>'
        for t, d in suggestions)

    return f"""<title>Rooms near Kyung Hee University — Exchange Student Guide</title>
<style>
:root{{--bg:#0f1419;--panel:#1a2129;--soft:#232c37;--line:#2e3a47;--text:#e8edf2;--mut:#9bb0c3;--acc:#4cc2ff;--acc2:#7ee787;--warn:#ffcb6b}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-text-size-adjust:100%}}
.wrap{{max-width:1180px;margin:0 auto;padding:20px 16px 64px}}
header.hero{{background:linear-gradient(135deg,#16324a,#1a2129);border:1px solid var(--line);border-radius:16px;padding:26px 22px;margin-bottom:22px}}
header.hero h1{{margin:0 0 6px;font-size:clamp(20px,4.5vw,30px);line-height:1.2}}
header.hero p{{margin:4px 0;color:var(--mut);font-size:15px}}
.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
.badge{{background:var(--soft);border:1px solid var(--line);color:var(--text);padding:6px 12px;border-radius:999px;font-size:13px;font-weight:600}}
.badge b{{color:var(--acc2)}}
section{{margin:30px 0}}
h2{{font-size:clamp(17px,3.5vw,22px);margin:0 0 4px;display:flex;align-items:center;gap:9px}}
h2 .dot{{width:9px;height:9px;border-radius:50%;background:var(--acc)}}
.sub{{color:var(--mut);font-size:13.5px;margin:0 0 14px}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--panel)}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:760px}}
th,td{{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{background:var(--soft);color:var(--mut);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.4px;position:sticky;top:0}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#1e2731}}
a{{color:var(--acc);text-decoration:none;font-weight:600;white-space:nowrap}}
a:hover{{text-decoration:underline}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px}}
.card h3{{margin:0 0 6px;font-size:15px;color:var(--acc2)}}
.card p{{margin:0;color:var(--mut);font-size:13.5px}}
.note{{background:#2a2417;border:1px solid #4a3f23;color:var(--warn);border-radius:12px;padding:12px 15px;font-size:13px;margin-top:10px}}
footer{{margin-top:40px;color:var(--mut);font-size:12.5px;border-top:1px solid var(--line);padding-top:16px}}
/* ---- mobile: tables become stacked cards ---- */
@media (max-width:760px){{
  table{{min-width:0}}
  thead{{display:none}}
  table,tbody,tr,td{{display:block;width:100%}}
  tr{{border:1px solid var(--line);border-radius:12px;margin:12px;background:var(--panel)}}
  tr:hover td{{background:transparent}}
  td{{border:none;border-bottom:1px solid var(--line);padding:9px 14px;display:flex;justify-content:space-between;gap:14px}}
  td:last-child{{border-bottom:none}}
  td::before{{content:attr(data-label);color:var(--mut);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;flex:0 0 42%}}
  td a{{white-space:normal;text-align:right}}
  .tablewrap{{border:none;background:transparent;overflow:visible}}
}}
</style>

<div class="wrap">
<header class="hero">
  <h1>🏠 Rooms near Kyung Hee University</h1>
  <p>A housing guide for a one-semester exchange student — Seoul Campus (Hoegi-dong, Dongdaemun-gu).</p>
  <div class="badges">
    <span class="badge">🚇 Subway <b>Line 1 / Line 6</b></span>
    <span class="badge">⏱ Commute <b>≤ 1 hour</b></span>
    <span class="badge">📅 Stay <b>4–6 months</b></span>
    <span class="badge">💰 관리비 포함 <b>~₩1,200,000 / mo</b></span>
    <span class="badge">🗣 <b>English-friendly</b> platforms</span>
    <span class="badge">🎯 Priority: <b>lower price</b></span>
  </div>
  <div class="note">⚠ Prices are a snapshot from {SNAPSHOT}. Individual listing links can expire within days; the neighborhood "Search rooms" links stay live. Always verify the current price on the platform.</div>
</header>

<section>
  <h2><span class="dot"></span>Featured live listings <span style="font-weight:400;color:var(--mut);font-size:13px">(snapshot {SNAPSHOT})</span></h2>
  <p class="sub">Concrete units found today, sorted by total monthly cost (rent + 관리비), budget ≤ ₩1,200,000. Open the link to confirm availability.</p>
  <div class="tablewrap"><table>
  {th(["Listing","Platform","Type","Monthly rent","Total /mo (incl 관리비)","Deposit","Size","Nearest station","Commute to KHU","Options","English","Listing link","Map","Notes"])}
  {feat_rows}
  </table></div>
</section>

<section>
  <h2><span class="dot"></span>Neighborhood guide — live search links</h2>
  <p class="sub">Each row links to live, filtered listings (Ziptoss English) plus a Naver Map pin for the area and its landmark. Sorted closest → cheaper. All are within 1 hour of KHU.</p>
  <div class="tablewrap"><table>
  {th(["Area","Nearest station","Line(s)","Commute to KHU","Typical rent / mo","Nearest landmark","Ziptoss (EN)","Map","Landmark map","Notes"])}
  {area_rows}
  </table></div>
</section>

<section>
  <h2><span class="dot"></span>English-friendly platforms</h2>
  <p class="sub">Recommended order for an exchange student. Ziptoss & 33m2 first; LiveAnywhere for the safest foreigner flow.</p>
  <div class="tablewrap"><table>
  {th(["Platform","English","Min stay","Deposit","Best for","Open"])}
  {plat_rows}
  </table></div>
</section>

<section>
  <h2><span class="dot"></span>My extra suggestions</h2>
  <p class="sub">Practical tips to save money and avoid trouble.</p>
  <div class="cards">
  {sug}
  </div>
</section>

<footer>
  Built {SNAPSHOT}. Rent figures are approximate, deposit-based studio ranges; short-stay furnished units (33m2 / LiveAnywhere, ₩330k deposit) run higher per month but need no large deposit.
  Sources: Ziptoss, 33m2, LiveAnywhere, Wehome, Airbnb, Daangn, Naver Map. Commute times estimated from Hoegi Station.
</footer>
</div>
"""

# ---------------------------------------------------------------- EXCEL
def build_xlsx(path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook()

    head_fill = PatternFill("solid", fgColor="16324A")
    head_font = Font(bold=True, color="FFFFFF", size=11)
    title_font = Font(bold=True, size=14, color="16324A")
    link_font = Font(color="0563C1", underline="single")
    wrap = Alignment(vertical="top", wrap_text=True)
    thin = Side(style="thin", color="D0D7DE")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def style_sheet(ws, headers, rows, link_cols, title):
        ws.cell(1, 1, title).font = title_font
        ws.cell(2, 1, f"Snapshot {SNAPSHOT} — prices change; verify on platform.").font = Font(italic=True, color="888888")
        hr = 4
        for c, h in enumerate(headers, 1):
            cell = ws.cell(hr, c, h)
            cell.fill = head_fill; cell.font = head_font; cell.alignment = wrap; cell.border = border
        for ri, row in enumerate(rows, hr + 1):
            for ci, val in enumerate(row, 1):
                cell = ws.cell(ri, ci, val)
                cell.alignment = wrap; cell.border = border
                if ci in link_cols and isinstance(val, str) and val.startswith("http"):
                    cell.hyperlink = val; cell.value = "Open link"; cell.font = link_font
        ws.freeze_panes = ws.cell(hr + 1, 1)

    # Sheet 1: Featured
    ws1 = wb.active; ws1.title = "Featured listings"
    featured = load_featured()
    h1 = ["Listing","Platform","Type","Monthly rent","Total /mo (incl 관리비)","Deposit","Size","Nearest station",
          "Commute to KHU","Options","English","Listing link","Naver Map","Notes"]
    r1 = [[r["name"],r["platform"],r["type"],r["rent"],r.get("total",""),r["deposit"],r["size"],r["station"],
           r["commute"],r["options"],r["english"],r["link"],r["naver"],r["notes"]] for r in featured]
    style_sheet(ws1, h1, r1, {12,13}, "Featured live listings — near Kyung Hee University")
    widths1 = [30,18,16,22,18,16,14,26,24,46,22,12,12,40]
    for i,w in enumerate(widths1,1): ws1.column_dimensions[chr(64+i) if i<=26 else 'A'].width = w

    # Sheet 2: Neighborhoods
    ws2 = wb.create_sheet("Neighborhood guide")
    h2 = ["Area","Nearest station","Line(s)","Commute to KHU","Typical rent / mo",
          "Nearest landmark","Ziptoss (EN) search","Area map","Landmark map","Notes"]
    r2 = [[f"{en} ({ko})", st, line, commute, rent, f"{lm_en} ({lm_ko})",
           ziptoss_en(zarea), naver(narea), naver(lm_ko), note]
          for (en,ko,st,line,commute,rent,lm_en,lm_ko,zarea,narea,note) in areas]
    style_sheet(ws2, h2, r2, {7,8,9}, "Neighborhood guide — live search links")
    widths2 = [24,30,30,34,20,34,20,14,14,40]
    for i,w in enumerate(widths2,1): ws2.column_dimensions[chr(64+i)].width = w

    # Sheet 3: Platforms
    ws3 = wb.create_sheet("Platforms")
    h3 = ["Platform","English","Min stay","Deposit","Best for","Open"]
    r3 = [[nm,eng,mn,dep,best,url] for (nm,eng,mn,dep,best,url) in platforms]
    style_sheet(ws3, h3, r3, {6}, "English-friendly rental platforms")
    widths3 = [18,26,12,16,52,12]
    for i,w in enumerate(widths3,1): ws3.column_dimensions[chr(64+i)].width = w

    # Sheet 4: Suggestions
    ws4 = wb.create_sheet("Tips")
    style_sheet(ws4, ["Tip","Detail"], [[t,d] for t,d in suggestions], set(), "Extra suggestions")
    ws4.column_dimensions['A'].width = 36; ws4.column_dimensions['B'].width = 90

    wb.save(path)

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "rooms.html"), "w", encoding="utf-8") as f:
        f.write(build_html())
    build_xlsx(os.path.join(here, "rooms.xlsx"))
    print("OK -> rooms.html, rooms.xlsx")
