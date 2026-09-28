"""NYC (D04, docs/04_TECH_SPEC.md mục 11.4): suy vị trí camera school-zone speed / red light từ vé phạt công khai của
Sở Tài chính NYC (DOF, NYC Open Data "Parking Violations Issued – Fiscal Year …"), rồi geocode giao lộ bằng NYC Geoclient v2.

NYC không công bố toạ độ camera. Vé camera ghi vị trí dạng chữ, bị cắt thành 2 trường 20 ký tự:
  street_name "SB KNAPP ST @ HARKNE" + intersecting_street "SS AVE" → "SB KNAPP ST @ HARKNESS AVE".
Chỉ gom số vé theo địa điểm bằng Socrata `$group` — không tải từng vé, không đọc biển số hay trường cá nhân nào.
Kết quả geocode được cache ở cache/nyc_geocode.json (commit vào repo) để lần sau không gọi lại.
"""

import collections
import datetime as dt
import json
import math
import os
import re
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

GEOCLIENT_URL = "https://api.nyc.gov/geoclient/v2/intersection.json"
GEOCODE_MIN_INTERVAL = 0.2  # ≤ 5 request/giây (ràng buộc D04)
GEOCODE_SAVE_EVERY = 100
# Mỗi request Geoclient mất ~1,3 s → gọi song song vài luồng; khoảng cách giữa 2 lần bắt đầu request vẫn ≥ 0,2 s.
GEOCODE_WORKERS = 4
FIELD_WIDTH = 20  # street_name / intersecting_street bị cắt ở 20 ký tự
SOCRATA_LIMIT = 50000
MAX_SEGMENT_METERS = 1500.0
# "STREETS INTERSECT TWICE" (đường có dải phân cách): hỏi thêm compassDirection N và S; 2 nút cách nhau ≤ mức này → lấy điểm giữa.
MAX_TWIN_METERS = 150.0
SAMPLE_COUNT = 5

# violation_county → borough của Geoclient (các mã có trong dữ liệu FY2026–FY2027).
BOROUGHS = {"MN": "MANHATTAN", "BX": "BRONX", "BK": "BROOKLYN", "QN": "QUEENS", "ST": "STATEN ISLAND"}
# Geoclient viết tắt tên borough trong `firstBoroughName`.
GEOCLIENT_BOROUGH_NAMES = {"STATEN IS": "STATEN ISLAND"}
DIRECTION_CODES = {"N": "NB", "S": "SB", "E": "EB", "W": "WB"}
_FISCAL_YEAR_NAME = re.compile(r"^Parking Violations Issued - Fiscal Year (\d{4})$")
# "SB KNAPP ST …" (tiền tố) hoặc "4TH AVE (N/B) @ …" (trong ngoặc).
_PREFIX_DIRECTION = re.compile(r"^\s*([NSEW])B\s+")
_PAREN_DIRECTION = re.compile(r"\s*\(\s*([NSEW])\s*/\s*B\s*\)\s*")
# Phần sau chỗ cắt bắt đầu bằng loại đường hoặc "@" → chỗ cắt nhiều khả năng là khoảng trắng ("… @ DYRE" + "AVE").
_STARTS_WITH_SUFFIX = re.compile(
    r"^(?:@|(?:ST|AVE?|RD|BLVD|BL|PL|DR|PKWY|PWY|LN|CT|TER|EXPWY|EXPY|HWY|TPKE|WAY|SQ|LOOP|PLZ|PLAZA|CIR|OVAL)\b)")


def split_direction(text):
    """"SB KNAPP ST @ …" / "ATLANTIC AVE (E/B) @ …" → ("SB", phần còn lại). Không có hướng → (None, text)."""
    match = _PREFIX_DIRECTION.match(text)
    if match:
        return DIRECTION_CODES[match.group(1)], text[match.end():].strip()
    match = _PAREN_DIRECTION.search(text)
    if match:
        return DIRECTION_CODES[match.group(1)], (text[:match.start()] + " " + text[match.end():]).strip()
    return None, text.strip()


def clean_name(text):
    """Tên đường gửi Geoclient: bỏ dấu chấm ("N.CONDUIT AVE" → "N CONDUIT AVE"), gộp khoảng trắng, chữ hoa."""
    return re.sub(r"\s+", " ", text.replace(".", " ")).strip().upper()


def join_candidates(street_name, intersecting):
    """Ghép lại chuỗi địa điểm bị cắt ở 20 ký tự. Socrata bỏ khoảng trắng ở 2 đầu mỗi trường, nên:
    street_name < 20 ký tự → ký tự thứ 20 là khoảng trắng → nối có khoảng trắng.
    = 20 ký tự → không biết chỗ cắt nằm giữa từ ("HARKNE" + "SS AVE") hay trước một từ mới ("@ DYRE" + "AVE") →
    trả cả 2 cách, cách có vẻ đúng hơn đứng trước; Geoclient và danh sách tên đường đã geocode được sẽ chọn."""
    street_name = (street_name or "").strip()
    intersecting = (intersecting or "").strip()
    if not intersecting:
        return [street_name]
    spaced = street_name + " " + intersecting
    if len(street_name) < FIELD_WIDTH:
        return [spaced]
    glued = street_name + intersecting
    if street_name[-1].isdigit() and intersecting[0].isdigit():
        return [glued, spaced]  # "@ 1" + "27TH ST" → "127TH ST"
    if street_name[-1].isalnum() and _STARTS_WITH_SUFFIX.match(intersecting):
        return [spaced, glued]  # "@ 224TH" + "ST", "@ DYRE" + "AVE"
    return [glued, spaced]


def parse_location(text):
    """Chuỗi địa điểm đầy đủ → {"direction", "street", "cross"} (giao lộ) hoặc {"direction", "street", "between": (a, b)}
    (đoạn giữa 2 giao lộ: "NB 7 AVE. 46TH ST - 41ST ST"). Không đọc được → None."""
    direction, rest = split_direction(text)
    if "@" in rest:
        street, _, cross = rest.partition("@")
        street, cross = clean_name(street), clean_name(cross)
        if not street or not cross:
            return None
        return {"direction": direction, "street": street, "cross": cross}
    segment = re.match(r"^(.+?)\.\s+(.+?)\s+-\s+(.+)$", rest)
    if segment:
        street, first, second = (clean_name(part) for part in segment.groups())
        if street and first and second:
            return {"direction": direction, "street": street, "between": (first, second)}
    return None


def complete_fragment(fragment, known):
    """Tên đường bị cắt cụt ở cuối chuỗi 40 ký tự ("SPRINGFIELD BL") → tên duy nhất trong danh sách tên đã geocode được
    bắt đầu bằng đoạn đó ("SPRINGFIELD BLVD"). Không có hoặc nhiều hơn 1 → giữ nguyên."""
    if fragment in known:
        return fragment
    matches = sorted(name for name in known if name.startswith(fragment))
    return matches[0] if len(matches) == 1 else fragment


def window_slices(today, days, fiscal_year):
    """Các khoảng ~1 tuần [đầu, cuối] (ngày 1–8, 9–16, 17–24, 25–cuối tháng) trong cửa sổ `days` ngày gần nhất và trong
    năm tài chính NYC `fiscal_year` (1/7 năm trước → 30/6). Truy vấn `$group` dài bị ngắt kết nối sau ~60 giây;
    1 tuần chạy vài giây."""
    start = max(today - dt.timedelta(days=days), dt.date(fiscal_year - 1, 7, 1))
    end = min(today, dt.date(fiscal_year, 6, 30))
    slices = []
    while start <= end:
        if start.day < 25:
            stop = start.replace(day=next(day for day in (8, 16, 24) if day >= start.day))
        else:
            stop = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        stop = min(stop, end)
        slices.append((start, stop))
        start = stop + dt.timedelta(days=1)
    return slices


def aggregate(groups, min_tickets):
    """Dòng `$group` của nhiều dataset / khoảng thời gian → {(code, county, street_name, intersecting): [vé, ngày mới nhất]}.
    Trả (giữ lại ≥ min_tickets, số địa điểm bị loại vì ít vé)."""
    totals = {}
    for row in groups:
        key = (str(row["violation_code"]), row.get("violation_county"),
               (row.get("street_name") or "").strip(), (row.get("intersecting_street") or "").strip())
        entry = totals.setdefault(key, [0, ""])
        entry[0] += int(row["tickets"])
        entry[1] = max(entry[1], (row.get("last_ticket") or "")[:10])
    kept = {key: value for key, value in totals.items() if value[0] >= min_tickets}
    return kept, len(totals) - len(kept)


def meters_between(lat1, lon1, lat2, lon2):
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


class Geoclient:
    """NYC Geoclient v2 `intersection` + cache JSON {"BOROUGH|STREET|CROSS": kết quả}. Kết quả lỗi cũng được cache
    (lần sau không hỏi lại). Không có key → chỉ dùng cache; địa điểm chưa có trong cache trả `MISSING_KEY`.
    `hits`: số lần dùng kết quả đã có trong file cache lúc bắt đầu chạy."""

    MISSING_KEY = {"error": "missing key"}

    def __init__(self, cache_path, key, get_json, sleep=time.sleep, clock=time.monotonic):
        self.cache_path = cache_path
        self.key = key
        self.get_json = get_json
        self.sleep = sleep
        self.clock = clock
        self.calls = 0
        self.hits = 0
        self._last_call = None
        self._unsaved = 0
        self._lock = threading.Lock()
        self.cache = {}
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as handle:
                self.cache = json.load(handle)
        self._preloaded = set(self.cache)

    def known_names(self):
        """Tên đường (chữ hoa, như trên vé) của mọi giao lộ đã geocode thành công."""
        names = set()
        for cache_key, result in self.cache.items():
            if "lat" in result:
                names.update(cache_key.split("|")[1:])
        return names

    def intersection(self, street, cross, borough):
        cache_key = "|".join((borough, street, cross))
        with self._lock:
            if cache_key in self.cache:
                self.hits += cache_key in self._preloaded
                return self.cache[cache_key]
        if not self.key:
            return self.MISSING_KEY
        result = self._request(street, cross, borough)
        if result.get("error", "").startswith("STREETS INTERSECT TWICE"):
            result = twin_midpoint([self._request(street, cross, borough, compass) for compass in ("N", "S")], result)
        with self._lock:
            self.cache[cache_key] = result
            self._unsaved += 1
            if self._unsaved >= GEOCODE_SAVE_EVERY:
                self._write()
        return result

    def prefetch(self, queries):
        """Geocode trước (song song) các giao lộ (street, cross, borough) chưa có trong cache — kết quả giống hệt gọi lần lượt."""
        missing = sorted({q for q in queries if "|".join((q[2], q[0], q[1])) not in self.cache})
        if self.key and missing:
            with ThreadPoolExecutor(GEOCODE_WORKERS) as pool:
                list(pool.map(lambda q: self.intersection(*q), missing))

    def _request(self, street, cross, borough, compass=None):
        with self._lock:
            if self._last_call is not None:
                wait = GEOCODE_MIN_INTERVAL - (self.clock() - self._last_call)
                if wait > 0:
                    self.sleep(wait)
            self._last_call = self.clock()
            self.calls += 1
        params = {"crossStreetOne": street, "crossStreetTwo": cross, "borough": borough}
        if compass:
            params["compassDirection"] = compass
        response = self.get_json("%s?%s" % (GEOCLIENT_URL, urllib.parse.urlencode(params)), {"Ocp-Apim-Subscription-Key": self.key})
        return parse_geoclient(response)

    def save(self):
        with self._lock:
            self._write()

    def _write(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as handle:
            json.dump(self.cache, handle, indent=1, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
        self._unsaved = 0


def parse_geoclient(response):
    """Phản hồi Geoclient → {"lat", "lon", "borough", "node"} hoặc {"error": thông điệp}."""
    data = (response or {}).get("intersection") or {}
    code = data.get("geosupportReturnCode")
    if code in ("00", "01") and data.get("latitude") and data.get("longitude"):
        borough = data.get("firstBoroughName")
        return {"lat": round(float(data["latitude"]), 6), "lon": round(float(data["longitude"]), 6),
                "borough": GEOCLIENT_BOROUGH_NAMES.get(borough, borough), "node": data.get("lionNodeNumber")}
    return {"error": (data.get("message") or "return code %s" % code)[:120]}


def twin_midpoint(results, fallback):
    """2 nút của giao lộ trên đường có dải phân cách (compass N, S) → điểm giữa, node "a x b". Xa nhau > 150 m → giữ lỗi."""
    if len(results) != 2 or any("lat" not in r for r in results) or results[0]["borough"] != results[1]["borough"]:
        return fallback
    a, b = results
    if a["node"] == b["node"]:
        return a
    if meters_between(a["lat"], a["lon"], b["lat"], b["lon"]) > MAX_TWIN_METERS:
        return {"error": fallback["error"] + " (2 nút cách nhau > %d m)" % MAX_TWIN_METERS}
    return {"lat": round((a["lat"] + b["lat"]) / 2, 6), "lon": round((a["lon"] + b["lon"]) / 2, 6), "borough": a["borough"],
            "node": "x".join(sorted((a["node"], b["node"])))}


def _geocode_pair(geoclient, street, cross, borough, known, truncated):
    """Giao lộ street & cross; chuỗi bị cắt ở 40 ký tự → hoàn thiện tên cuối từ danh sách tên đã biết.
    → (kết quả, tên cross đã dùng)."""
    if truncated:
        cross = complete_fragment(cross, known)
    return geoclient.intersection(street, cross, borough), cross


def locate(location_texts, borough, geoclient, known, truncated=False):
    """Thử lần lượt các cách ghép chuỗi địa điểm, cách có tên đường đã biết đứng trước. → (vị trí, lý do loại).
    Vị trí: {"lat", "lon", "node", "direction", "road"}. truncated: intersecting_street dài đủ 20 ký tự (có thể bị cắt)."""
    parsed = [(text, parse_location(text)) for text in location_texts]
    parsed = [(text, p) for text, p in parsed if p is not None]
    if not parsed:
        return None, "địa chỉ không đọc được"
    parsed.sort(key=lambda item: 0 if item[1]["street"] in known and item[1].get("cross", "") in known else 1)
    reason = "geocode không ra giao lộ"
    for _, location in parsed:
        if "cross" in location:
            result, cross = _geocode_pair(geoclient, location["street"], location["cross"], borough, known, truncated)
            if result is Geoclient.MISSING_KEY:
                return None, "chưa geocode (thiếu key)"
            if "lat" not in result:
                continue
            if result["borough"] != borough:
                reason = "geocode ra sai borough"
                continue
            known.update((location["street"], cross))
            return {"lat": result["lat"], "lon": result["lon"], "node": result["node"], "direction": location["direction"],
                    "road": "%s @ %s" % (location["street"], cross)}, None
        ends = []
        for other in location["between"]:
            result, other = _geocode_pair(geoclient, location["street"], other, borough, known, truncated and other == location["between"][1])
            if result is Geoclient.MISSING_KEY:
                return None, "chưa geocode (thiếu key)"
            if "lat" in result and result["borough"] == borough:
                ends.append((result, other))
        if len(ends) == 2:
            (a, name_a), (b, name_b) = ends
            if meters_between(a["lat"], a["lon"], b["lat"], b["lon"]) > MAX_SEGMENT_METERS:
                reason = "đoạn giữa 2 giao lộ quá dài"
                continue
            nodes = "x".join(sorted(str(end["node"]) for end, _ in ends))
            return {"lat": round((a["lat"] + b["lat"]) / 2, 6), "lon": round((a["lon"] + b["lon"]) / 2, 6), "node": nodes,
                    "direction": location["direction"], "road": "%s (%s - %s)" % (location["street"], name_a, name_b)}, None
    return None, reason


def fiscal_year_datasets(catalog):
    """Catalog Socrata → {năm tài chính: id dataset} của các dataset "Parking Violations Issued - Fiscal Year NNNN"."""
    datasets = {}
    for result in catalog.get("results", []):
        resource = result.get("resource") or {}
        match = _FISCAL_YEAR_NAME.match(resource.get("name") or "")
        if match:
            datasets[int(match.group(1))] = resource["id"]
    return datasets


def fetch_ticket_groups(source, get_json, today):
    """Số vé camera theo địa điểm trong `windowDays` ngày gần nhất, từ mọi dataset năm tài chính giao với cửa sổ đó.
    Kiểm tra mô tả của từng mã vi phạm: khác `violationDescriptions` → lỗi (mã đổi nghĩa, cần người xem)."""
    codes = source["violationDescriptions"]
    datasets = fiscal_year_datasets(get_json(source["catalog"]))
    groups, used = [], []
    where_codes = " OR ".join("violation_code=%d" % int(code) for code in sorted(codes, key=int))
    for fiscal_year in sorted(datasets):
        slices = window_slices(today, source["windowDays"], fiscal_year)
        if not slices:
            continue
        used.append(datasets[fiscal_year])
        for start, stop in slices:
            query = urllib.parse.urlencode({
                "$select": "violation_code,violation_description,violation_county,street_name,intersecting_street,"
                           "count(*) AS tickets,max(issue_date) AS last_ticket",
                "$where": "(%s) AND issue_date between '%sT00:00:00' and '%sT23:59:59'" % (where_codes, start, stop),
                "$group": "violation_code,violation_description,violation_county,street_name,intersecting_street",
                "$limit": SOCRATA_LIMIT,
            })
            rows = get_json(source["endpoint"].format(id=datasets[fiscal_year]) + "?" + query)
            if not isinstance(rows, list):
                raise ValueError("Socrata %s không trả mảng JSON" % datasets[fiscal_year])
            if len(rows) >= SOCRATA_LIMIT:
                raise ValueError("Socrata %s %s: ≥ %d nhóm — cần chia nhỏ hơn" % (datasets[fiscal_year], start, SOCRATA_LIMIT))
            for row in rows:
                code, description = str(row.get("violation_code")), row.get("violation_description")
                if code not in codes:
                    raise ValueError("Socrata trả mã vi phạm ngoài danh sách: %s" % code)
                if description is not None and description != codes[code]:
                    raise ValueError("mã %s đổi mô tả: %r (cần %r)" % (code, description, codes[code]))
            groups.extend(rows)
    if not used:
        raise ValueError("catalog không có dataset Parking Violations Issued nào trong %d ngày gần nhất" % source["windowDays"])
    return groups, used


def build_rows(kept, source, geoclient):
    """Địa điểm ≥ ngưỡng → dòng camera cho build_packs (định dạng phẳng) + thống kê cho REPORT.
    Cùng loại + cùng giao lộ (node LION) + cùng hướng → 1 camera (cộng vé, lấy ngày mới nhất). Vé ghi cùng giao lộ
    theo nhiều cách ("E 80TH ST" / "E80TH ST") → tên có nhiều khoảng trắng hơn (rồi theo thứ tự chữ): không phụ thuộc
    số vé, để cửa sổ 12 tháng trượt không làm đổi tên (và version pack)."""
    type_prefix = {code: "sz" if camera_type == "schoolZone" else "rl"
                   for code, camera_type in source["typeMap"]["values"].items()}
    known = geoclient.known_names()
    rejected = collections.Counter()
    cameras = {}
    # Chuỗi đầy đủ (không bị cắt ở 40 ký tự) trước, để có thêm tên đường mà hoàn thiện các chuỗi bị cắt.
    order = sorted(kept.items(), key=lambda item: (len(item[0][3]) >= FIELD_WIDTH, -item[1][0], tuple(p or "" for p in item[0])))
    # Geocode song song cách ghép đầu tiên của các chuỗi không bị cắt; phần còn lại (cách ghép khác, chuỗi cụt) đi lần lượt.
    first = []
    for (code, county, street_name, intersecting), _ in order:
        if county in BOROUGHS and len(intersecting) < FIELD_WIDTH:
            location = parse_location(join_candidates(street_name, intersecting)[0])
            if location and "cross" in location:
                first.append((location["street"], location["cross"], BOROUGHS[county]))
    geoclient.prefetch(first)
    for (code, county, street_name, intersecting), (tickets, last_ticket) in order:
        borough = BOROUGHS.get(county)
        if borough is None:
            rejected["không có borough (violation_county=%s)" % county] += 1
            continue
        position, reason = locate(join_candidates(street_name, intersecting), borough, geoclient, known,
                                  truncated=len(intersecting) >= FIELD_WIDTH)
        if position is None:
            rejected[reason] += 1
            continue
        key = "%s%s%s" % (type_prefix[code], position["node"], (position["direction"] or "").lower())
        camera = cameras.get(key)
        if camera is None:
            cameras[key] = {"violation_code": code, "key": key, "road": position["road"], "direction": position["direction"],
                            "borough": borough, "tickets": tickets, "last_ticket": last_ticket,
                            "lat": position["lat"], "lon": position["lon"]}
        else:
            camera["tickets"] += tickets
            camera["last_ticket"] = max(camera["last_ticket"], last_ticket)
            camera["road"] = max(camera["road"], position["road"], key=lambda road: (road.count(" "), road))
    return [cameras[key] for key in sorted(cameras)], dict(rejected)


def fetch(source, get_json, today, cache_dir):
    """→ (dòng camera đã geocode, thống kê). Key Geoclient đọc từ biến môi trường `geocodeKeyEnv` (không bắt buộc khi
    mọi địa điểm đã có trong cache)."""
    groups, datasets = fetch_ticket_groups(source, get_json, today)
    kept, below = aggregate(groups, source["minTickets"])
    geoclient = Geoclient(os.path.join(cache_dir, source["geocodeCache"]), os.environ.get(source["geocodeKeyEnv"], "").strip(),
                          get_json)
    try:
        rows, rejected = build_rows(kept, source, geoclient)
    finally:
        if geoclient.calls:
            geoclient.save()
    stats = {
        "datasets": datasets,
        "window": [(today - dt.timedelta(days=source["windowDays"])).isoformat(), today.isoformat()],
        "tickets": sum(int(row["tickets"]) for row in groups),
        "minTickets": source["minTickets"],
        "locations": len(kept),
        "belowThreshold": below,
        "geocodeOK": len(kept) - sum(rejected.values()),
        "rejected": rejected,
        "cameras": len(rows),
        "geocodeCalls": geoclient.calls,
        "cacheHits": geoclient.hits,
        "samples": [{k: row[k] for k in ("violation_code", "road", "direction", "borough", "tickets", "lat", "lon")}
                    for row in sorted(rows, key=lambda r: -r["tickets"])[:SAMPLE_COUNT]],
    }
    return rows, stats
