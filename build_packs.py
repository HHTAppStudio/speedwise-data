#!/usr/bin/env python3
"""Speedwise data pipeline.

Tải vị trí camera chính thức (open data của thành phố/quận/bang Mỹ), chuẩn hoá về schema
data pack của app (docs/04_TECH_SPEC.md mục 2.2), rồi ghi:
  public/packs/us-xx.vN.json · public/regions.json · manifest.json · REPORT.md

Chạy:  python3 build_packs.py [--only id1,id2] [--offline]
Chỉ dùng thư viện chuẩn Python 3.
"""

import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(ROOT, "public")
PACKS_DIR = os.path.join(PUBLIC_DIR, "packs")
CACHE_DIR = os.path.join(ROOT, "cache")
FIXTURES_DIR = os.path.join(ROOT, "fixtures")
SOURCES_PATH = os.path.join(ROOT, "sources.json")
BBOXES_PATH = os.path.join(ROOT, "state_bboxes.json")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")
REPORT_PATH = os.path.join(ROOT, "REPORT.md")
REGIONS_OUT_PATH = os.path.join(PUBLIC_DIR, "regions.json")
REGIONS_TEMPLATE_PATH = os.path.join(ROOT, "..", "Speedwise", "Resources", "DataPacks", "regions.json")

USER_AGENT = "SpeedwiseDataPipeline/1.0 (henry3dai@gmail.com)"
RETRIES = 3
TIMEOUT_SECONDS = 60

CAMERA_TYPES = ("speed", "redLight", "schoolZone", "combined", "mobile")
# Confidence khi nguồn không có trường trạng thái (hoặc giá trị trạng thái không rõ).
NO_STATUS_CONFIDENCE = {"A": 80, "B": 75}
STALE_PENALTY = 10
STALE_DAYS = 365
MIN_CONFIDENCE = 50
MERGE_METERS = 30.0
MERGE_DEGREES = 30.0
FIXTURE_ROWS = 5

REPORT_MANUAL_MARKER = "<!-- PHẦN VIẾT TAY: build_packs.py giữ nguyên mọi thứ bên dưới dòng này -->"

# ---------------------------------------------------------------------------
# Hướng
# ---------------------------------------------------------------------------

HEADINGS = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
DIRECTION_WORDS = {
    "north": "N", "northeast": "NE", "east": "E", "southeast": "SE",
    "south": "S", "southwest": "SW", "west": "W", "northwest": "NW",
}
# NB, N/B, NEB, NE/B, Northbound, North-bound … (không phân biệt hoa/thường).
_DIRECTION_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:(NE|NW|SE|SW|N|E|S|W)\s?/?\s?B"
    r"|(northeast|northwest|southeast|southwest|north|east|south|west)[\s-]?bound)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
# Giá trị của một trường chỉ chứa hướng ("N", "North", "SB").
_BARE_DIRECTION = re.compile(r"^\s*(NE|NW|SE|SW|N|E|S|W|northeast|northwest|southeast|southwest|north|east|south|west)\s*$", re.IGNORECASE)


def _direction_codes(text):
    codes = []
    for match in _DIRECTION_TOKEN.finditer(text):
        if match.group(1):
            codes.append(match.group(1).upper())
        else:
            codes.append(DIRECTION_WORDS[match.group(2).lower()])
    return codes


def parse_direction(text):
    """Trả mã hướng ("N", "SW"…) hoặc None. Nhiều hướng khác nhau trong cùng chuỗi → None (không đoán)."""
    if text is None:
        return None
    text = str(text).replace("\xa0", " ")
    bare = _BARE_DIRECTION.match(text)
    if bare:
        word = bare.group(1)
        return DIRECTION_WORDS.get(word.lower(), word.upper())
    codes = set(_direction_codes(text))
    if len(codes) == 1:
        return codes.pop()
    return None


def heading_for(code):
    return None if code is None else HEADINGS[code]


def direction_suffix(code):
    return code.lower() + "b"


# ---------------------------------------------------------------------------
# Tên đường
# ---------------------------------------------------------------------------

_KEEP_UPPER = {"NW", "NE", "SW", "SE", "MLK", "NB", "SB", "EB", "WB", "NEB", "NWB", "SEB", "SWB"}
_SMALL_WORDS = {"AND", "AT", "BY", "OF", "ON", "TO"}
_ROUTE_PREFIX = re.compile(r"\b(Us|Sr|De|Md|Va|Wa|Ca|Il|Dc|La|Nj)(\s?-?\s?)(?=\d)")


def _case_word(match, is_first):
    word = match.group(0)
    upper = word.upper()
    if upper in _KEEP_UPPER:
        return upper
    if not is_first and upper in _SMALL_WORDS:
        return word.lower()
    if word[0].isdigit():
        return word.lower()
    if any(ch.isdigit() for ch in word):
        return upper
    return "'".join(part.capitalize() for part in word.split("'"))


def clean_road(text, strip_directions=True):
    """Đổi "@"/"at" thành "&", chuẩn hoá hoa/thường khi nguồn viết toàn chữ hoa.
    strip_directions: bỏ chữ hướng (dùng khi chính chuỗi này là nơi đọc ra hướng của camera)."""
    if text is None:
        return None
    text = str(text).replace("\xa0", " ").strip()
    if not text or text.upper() in {"NA", "N/A", "NONE", "NULL"}:
        return None
    if strip_directions:
        # "SB and NB", "EB/WB" → bỏ cả cụm; rồi bỏ từng chữ hướng còn lại.
        text = re.sub(_DIRECTION_TOKEN.pattern + r"\s*(?:and|&|/)\s*" + _DIRECTION_TOKEN.pattern, " ", text, flags=re.IGNORECASE)
        text = _DIRECTION_TOKEN.sub(" ", text)
    text = re.sub(r"\s+(?:@|at)\s+", " & ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s+", " ", text).strip(" &@,-/")
    text = re.sub(r"\s+(?:and|&)$", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None
    if not re.search(r"[a-z]", text):
        position = {"first": True}

        def replace(match):
            result = _case_word(match, position["first"])
            position["first"] = False
            return result

        text = re.sub(r"[A-Za-z0-9']+", replace, text)
        text = _ROUTE_PREFIX.sub(lambda m: m.group(1).upper() + m.group(2), text)
        # Đại lộ mang tên bang viết tắt ở DC: "NY Ave", "RI Ave", "MA Ave".
        text = re.sub(r"\b([A-Z][a-z])(?= Ave\b)", lambda m: m.group(1).upper(), text)
    return re.sub(r"\bblk\b", "Blk", text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Giá trị
# ---------------------------------------------------------------------------

def parse_limit(value):
    """Số nguyên mph khi nguồn ghi đúng một con số hợp lý; ngược lại None (không đoán)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = value
    else:
        numbers = re.findall(r"\d+(?:\.\d+)?", str(value))
        if len(numbers) != 1:
            return None
        number = float(numbers[0])
    number = int(round(number))
    return number if 5 <= number <= 85 else None


def parse_date(value):
    """epoch (s hoặc ms), ISO 8601, hoặc m/d/Y → datetime.date."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000.0 if abs(value) > 1e11 else float(value)
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc).date()
    text = str(value).strip()
    if re.fullmatch(r"-?\d+", text):
        return parse_date(int(text))
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(text.rstrip("Z"), fmt).date()
        except ValueError:
            continue
    return None


def iso_day(day):
    return None if day is None else day.isoformat() + "T00:00:00Z"


def is_empty(value):
    return value is None or (isinstance(value, str) and value.replace("\xa0", " ").strip() in {"", "NA", "N/A"})


def key_part(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def dig(obj, dotted):
    for part in dotted.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def first_value(row, fields):
    for field in fields or []:
        value = row.get(field)
        if not is_empty(value):
            return value
    return None


def meters_between(lat1, lon1, lat2, lon2):
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def headings_match(h1, h2):
    if h1 is None and h2 is None:
        return True
    if h1 is None or h2 is None:
        return False
    diff = abs(h1 - h2) % 360
    return min(diff, 360 - diff) <= MERGE_DEGREES


# ---------------------------------------------------------------------------
# Đọc dữ liệu thô
# ---------------------------------------------------------------------------

def parse_raw(source, raw):
    """Dữ liệu thô của một nguồn → danh sách dict phẳng; toạ độ đặt ở "_lat"/"_lon"."""
    fmt = source["format"]
    rows = []
    if fmt in ("arcgis-geojson", "socrata-geojson"):
        if not isinstance(raw, dict) or "features" not in raw:
            raise ValueError("phản hồi không phải GeoJSON FeatureCollection")
        if (raw.get("properties") or {}).get("exceededTransferLimit") or raw.get("exceededTransferLimit"):
            raise ValueError("máy chủ cắt bớt kết quả (exceededTransferLimit) — cần phân trang")
        for feature in raw["features"]:
            row = dict(feature.get("properties") or {})
            geometry = feature.get("geometry") or {}
            coords = geometry.get("coordinates") if geometry.get("type") == "Point" else None
            row["_lon"], row["_lat"] = (coords[0], coords[1]) if coords else (None, None)
            rows.append(row)
    elif fmt == "socrata-json":
        if not isinstance(raw, list):
            raise ValueError("phản hồi Socrata không phải mảng JSON")
        field_map = source["fieldMap"]
        for item in raw:
            row = dict(item)
            if field_map.get("point"):
                point = item.get(field_map["point"]) or {}
                coords = point.get("coordinates") if isinstance(point, dict) else None
                row["_lon"], row["_lat"] = (coords[0], coords[1]) if coords else (None, None)
            else:
                row["_lat"], row["_lon"] = item.get(field_map.get("lat")), item.get(field_map.get("lon"))
            rows.append(row)
    else:
        raise ValueError("format không hỗ trợ: %s" % fmt)
    return rows


def dataset_date_from(source, metadata, rows):
    """Ngày cập nhật dataset: từ metadata, hoặc giá trị lớn nhất của `rowDateField`."""
    day = None
    if metadata is not None and source.get("metadata"):
        day = parse_date(dig(metadata, source["metadata"]["dateKey"]))
    if day is None and source.get("rowDateField"):
        dates = [parse_date(row.get(source["rowDateField"])) for row in rows]
        dates = [d for d in dates if d is not None]
        day = max(dates) if dates else None
    return day


# ---------------------------------------------------------------------------
# Chuẩn hoá
# ---------------------------------------------------------------------------

def _passes_filter(row, rule):
    value = row.get(rule["field"])
    if "in" in rule:
        return value in rule["in"]
    if "notIn" in rule:
        return value not in rule["notIn"]
    if rule.get("empty"):
        return is_empty(value)
    raise ValueError("filter không hợp lệ: %s" % rule)


def _camera_type(source, row):
    type_map = source["typeMap"]
    if "const" in type_map:
        camera_type = type_map["const"]
        raw_value = camera_type
    else:
        raw_value = row.get(type_map["field"])
        camera_type = type_map["values"].get(raw_value)
    if camera_type == "speed" and type_map.get("schoolZoneIfField") and not is_empty(row.get(type_map["schoolZoneIfField"])):
        camera_type = "schoolZone"
    return camera_type, raw_value


def _latest_period_rows(source, rows):
    field = source.get("latestPeriodField")
    if not field:
        return rows, 0
    periods = [row.get(field) for row in rows if not is_empty(row.get(field))]
    if not periods:
        return rows, 0
    latest = max(periods, key=source_period_sort_key)
    kept = [row for row in rows if row.get(field) == latest]
    return kept, len(rows) - len(kept)


def source_period_sort_key(value):
    """Sắp xếp kỳ ("FY2026 Q1", "2026 Q3", "Q3 2026"…): năm rồi quý, theo các con số trong chuỗi."""
    text = str(value)
    year = max((int(y) for y in re.findall(r"(?:19|20)\d{2}", text)), default=0)
    if year == 0:
        short = re.findall(r"FY\s?(\d{2})\b", text, flags=re.IGNORECASE)
        year = 2000 + int(short[0]) if short else 0
    quarter = re.findall(r"Q\s?([1-4])", text, flags=re.IGNORECASE)
    return (year, int(quarter[0]) if quarter else 0, text)


def normalize_source(source, rows, dataset_day, today, bboxes):
    """Dòng thô → (danh sách camera theo schema CameraDTO, Counter lý do bị loại)."""
    rejects = collections.Counter()
    rows, older = _latest_period_rows(source, rows)
    if older:
        rejects["kỳ cũ hơn %s" % source["latestPeriodField"]] += older

    field_map = source["fieldMap"]
    region = source["region"]
    bbox = bboxes[region]
    active_rule = field_map.get("active")
    stale = dataset_day is not None and (today - dataset_day).days > STALE_DAYS
    cameras = []
    seen_ids = set()

    for row in rows:
        failed = next((rule for rule in source.get("filters", []) if not _passes_filter(row, rule)), None)
        if failed:
            rejects["lọc %s=%s" % (failed["field"], row.get(failed["field"]))] += 1
            continue

        camera_type, raw_type = _camera_type(source, row)
        if camera_type is None:
            rejects["loại không dùng: %s" % raw_type] += 1
            continue
        if camera_type not in CAMERA_TYPES:
            rejects["type ngoài enum: %s" % camera_type] += 1
            continue

        status_active = False
        if active_rule:
            status_value = row.get(active_rule["field"])
            if status_value in active_rule.get("inactiveValues", []):
                rejects["không hoạt động: %s=%s" % (active_rule["field"], status_value)] += 1
                continue
            status_active = status_value in active_rule["activeValues"]

        try:
            lat, lon = float(row.get("_lat")), float(row.get("_lon"))
        except (TypeError, ValueError):
            rejects["thiếu toạ độ"] += 1
            continue
        if lat == 0 or lon == 0 or math.isnan(lat) or math.isnan(lon):
            rejects["toạ độ bằng 0"] += 1
            continue
        if not (bbox["minLat"] <= lat <= bbox["maxLat"] and bbox["minLon"] <= lon <= bbox["maxLon"]):
            rejects["toạ độ ngoài khung bang"] += 1
            continue

        go_live = parse_date(row.get(field_map["goLive"])) if field_map.get("goLive") else None
        if go_live is not None and go_live > today:
            rejects["chưa hoạt động (go-live %s)" % go_live.isoformat()] += 1
            continue
        confirmed = max((d for d in (dataset_day, go_live) if d is not None), default=None)

        if status_active:
            confidence = source["baseConfidence"]
        else:
            confidence = min(source["baseConfidence"], NO_STATUS_CONFIDENCE[source["tier"]])
        if stale:
            confidence -= STALE_PENALTY
        confidence = max(MIN_CONFIDENCE, confidence)

        road_fields = [f for f in field_map.get("road") or [] if not is_empty(row.get(f))][:1]
        road = clean_road(first_value(row, road_fields),
                          strip_directions=bool(road_fields) and road_fields[0] in (field_map.get("direction") or []))
        limit = parse_limit(row.get(field_map["limit"])) if field_map.get("limit") else None
        key_value = row.get(field_map["key"]) if field_map.get("key") else None
        key = "" if is_empty(key_value) else key_part(key_value)

        if source.get("approaches"):
            directions = []
            for field in source["approaches"]:
                code = parse_direction(row.get(field))
                if not is_empty(row.get(field)) and code is None:
                    rejects["approach không đọc được hướng: %s" % row.get(field)] += 1
                if code is not None and code not in directions:
                    directions.append(code)
            if not directions:
                rejects["không có approach"] += 1
                continue
            variants = [(code, True) for code in directions]
        else:
            variants = [(parse_direction(first_value(row, field_map.get("direction"))), False)]

        for code, suffixed in variants:
            heading = heading_for(code)
            if key:
                camera_key = key + ("-" + direction_suffix(code) if suffixed else "")
            else:
                seed = "%.5f|%.5f|%s|%s" % (lat, lon, camera_type, heading)
                camera_key = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
            camera_id = "%s-%s-%s" % (region.lower(), source["id"], camera_key)
            if camera_id in seen_ids:
                rejects["trùng id trong nguồn"] += 1
                continue
            seen_ids.add(camera_id)
            cameras.append({
                "id": camera_id,
                "type": camera_type,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "heading": heading,
                "postedLimit": limit,
                "roadName": road,
                "source": "openData",
                "sourceId": source["id"],
                "confidence": confidence,
                "lastConfirmedAt": iso_day(confirmed),
                "confirmCount": 0,
                "denyCount": 0,
                "active": True,
            })
    return cameras, rejects


def merge_duplicates(cameras, tiers):
    """Gộp camera trùng trong cùng bang: cùng type, hướng lệch ≤ 30° (hoặc cả hai null), cách ≤ 30 m.
    Giữ bản confidence cao hơn; bằng nhau thì tier A; rồi id nhỏ hơn. Trả (giữ lại, {id bị gộp: id giữ})."""
    tier_rank = {"A": 0, "B": 1}
    ordered = sorted(cameras, key=lambda c: (-c["confidence"], tier_rank[tiers[c["sourceId"]]], c["id"]))
    kept = []
    merged = {}
    for camera in ordered:
        winner = next((k for k in kept
                       if k["type"] == camera["type"]
                       and headings_match(k["heading"], camera["heading"])
                       and meters_between(k["lat"], k["lon"], camera["lat"], camera["lon"]) <= MERGE_METERS), None)
        if winner is None:
            kept.append(camera)
        else:
            merged[camera["id"]] = winner["id"]
    return sorted(kept, key=lambda c: c["id"]), merged


# ---------------------------------------------------------------------------
# Version, regions.json
# ---------------------------------------------------------------------------

def content_hash(cameras):
    payload = json.dumps(sorted(cameras, key=lambda c: c["id"]), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def pack_file_name(region, version):
    return "%s.v%d.json" % (region.lower(), version)


def write_packs(region_cameras, manifest, packs_dir, today, now_iso):
    """Ghi pack cho bang có nội dung mới (version + 1), giữ nguyên bang không đổi.
    Trả manifest["regions"] mới: {region: {version, hash, file, cameraCount, updatedAt}}."""
    old = manifest.get("regions", {})
    result = {}
    os.makedirs(packs_dir, exist_ok=True)
    for region in sorted(region_cameras):
        cameras = sorted(region_cameras[region], key=lambda c: c["id"])
        digest = content_hash(cameras)
        previous = old.get(region)
        if previous and previous["hash"] == digest and os.path.exists(os.path.join(packs_dir, os.path.basename(previous["file"]))):
            result[region] = previous
            continue
        version = (previous["version"] if previous else 0) + 1
        name = pack_file_name(region, version)
        pack = {"region": region, "version": version, "generatedAt": now_iso, "unit": "mph", "cameras": cameras}
        write_json(os.path.join(packs_dir, name), pack)
        for stale in glob.glob(os.path.join(packs_dir, "%s.v*.json" % region.lower())):
            if os.path.basename(stale) != name:
                os.remove(stale)
        result[region] = {"version": version, "hash": digest, "file": "packs/" + name,
                          "cameraCount": len(cameras), "updatedAt": today.isoformat()}
    for region in old:
        if region not in result:
            for stale in glob.glob(os.path.join(packs_dir, "%s.v*.json" % region.lower())):
                os.remove(stale)
    return result


def build_regions(template, existing, packs, sources, source_info):
    """template/existing: regions.json dạng dict. packs: manifest["regions"]. sources: danh sách nguồn enabled.
    source_info: {id: {"updatedAt": "YYYY-MM-DD"|None, "cameraCount": int}}."""
    coverage = collections.OrderedDict()
    for source in sources:
        if source_info.get(source["id"], {}).get("cameraCount", 0) > 0:
            notes = coverage.setdefault(source["region"], [])
            if source["coverage"] not in notes:
                notes.append(source["coverage"])

    regions = []
    for entry in template["regions"]:
        region = dict(entry)
        for field in ("packURL", "packVersion", "coverageNote"):
            region.pop(field, None)
        pack = packs.get(region["code"])
        if pack:
            region["cameraCount"] = pack["cameraCount"]
            region["updatedAt"] = pack["updatedAt"]
            region["packURL"] = pack["file"]
            region["packVersion"] = pack["version"]
            if coverage.get(region["code"]):
                region["coverageNote"] = ", ".join(coverage[region["code"]])
        elif region.get("countryCode") == "US":
            # Chưa có pack open data → "Community only".
            region["cameraCount"] = 0
            region.pop("updatedAt", None)
        regions.append(region)

    source_list = [{
        "id": source["id"],
        "region": source["region"],
        "name": source["name"],
        "publisher": source["publisher"],
        "license": source["license"],
        "attribution": source["attribution"],
        "landingURL": source["landingURL"],
        "updatedAt": source_info.get(source["id"], {}).get("updatedAt"),
        "cameraCount": source_info.get(source["id"], {}).get("cameraCount", 0),
    } for source in sources]

    config = {"version": 0, "regions": regions, "sources": source_list}
    base_version = template.get("version", 0)
    if existing is not None:
        same = dict(existing, version=0) == config
        config["version"] = existing.get("version", base_version) if same else max(existing.get("version", 0), base_version) + 1
    else:
        config["version"] = base_version + 1
    return config


# ---------------------------------------------------------------------------
# Mạng, file
# ---------------------------------------------------------------------------

def _ssl_context():
    context = ssl.create_default_context()
    if os.environ.get("SSL_CERT_FILE") or ssl.get_default_verify_paths().cafile or sys.platform != "darwin":
        return context
    # Python cài từ python.org trên macOS không đọc chứng chỉ gốc của hệ thống → xuất từ keychain một lần.
    bundle = os.path.join(CACHE_DIR, "macos-roots.pem")
    if not os.path.exists(bundle):
        os.makedirs(CACHE_DIR, exist_ok=True)
        pem = subprocess.run(["security", "find-certificate", "-a", "-p",
                              "/System/Library/Keychains/SystemRootCertificates.keychain"],
                             check=True, capture_output=True).stdout
        with open(bundle, "wb") as handle:
            handle.write(pem)
    context.load_verify_locations(bundle)
    return context


_SSL_CONTEXT = None


def http_get_json(url):
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        _SSL_CONTEXT = _ssl_context()
    safe_url = urllib.parse.quote(url, safe=":/?&=*,'()$%+@;!~#")
    request = urllib.request.Request(safe_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_SSL_CONTEXT) as response:
                data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict) and "error" in data and "features" not in data:
                raise ValueError("máy chủ báo lỗi: %s" % json.dumps(data["error"])[:200])
            return data
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            last_error = error
            if attempt + 1 < RETRIES:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, obj):
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            if handle.read() == text:
                return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def fixture_sample(source, raw):
    """≤ 5 dòng thô, ưu tiên đủ các trường hợp khác nhau (loại, trạng thái, số approach)."""
    is_geojson = isinstance(raw, dict)
    items = raw["features"] if is_geojson else raw
    type_field = source["typeMap"].get("field")
    active_field = (source["fieldMap"].get("active") or {}).get("field")

    def signature(item):
        props = item.get("properties", {}) if is_geojson else item
        return (props.get(type_field) if type_field else None,
                props.get(active_field) if active_field else None,
                sum(1 for f in source.get("approaches", []) if not is_empty(props.get(f))))

    chosen, seen = [], set()
    for item in items:
        sig = signature(item)
        if sig not in seen:
            seen.add(sig)
            chosen.append(item)
    for item in items:
        if len(chosen) >= FIXTURE_ROWS:
            break
        if item not in chosen:
            chosen.append(item)
    chosen = chosen[:FIXTURE_ROWS]
    return dict(raw, features=chosen) if is_geojson else chosen


def fetch_source(source, offline):
    """→ (raw, metadata). Online: lưu cache/<id>.json; lần tải đầu lưu fixtures/<id>.json."""
    cache_path = os.path.join(CACHE_DIR, source["id"] + ".json")
    if offline:
        cached = read_json(cache_path)
        if cached is None:
            raise RuntimeError("--offline: chưa có cache/%s.json" % source["id"])
        return cached["raw"], cached["metadata"]
    raw = http_get_json(source["endpoint"])
    metadata = None
    if source.get("metadata"):
        try:
            metadata = http_get_json(source["metadata"]["url"])
        except RuntimeError:
            metadata = None
    os.makedirs(CACHE_DIR, exist_ok=True)
    write_json(cache_path, {"raw": raw, "metadata": metadata})
    fixture_path = os.path.join(FIXTURES_DIR, source["id"] + ".json")
    if not os.path.exists(fixture_path):
        os.makedirs(FIXTURES_DIR, exist_ok=True)
        date_value = dig(metadata, source["metadata"]["dateKey"]) if metadata and source.get("metadata") else None
        write_json(fixture_path, {"metadata": {source["metadata"]["dateKey"]: date_value} if source.get("metadata") else None,
                                  "raw": fixture_sample(source, raw)})
    return raw, metadata


def fixture_metadata(fixture):
    """Metadata lưu trong fixture là dạng phẳng {"a.b": value} → dict lồng để `dig` đọc được."""
    flat = fixture.get("metadata")
    if not flat:
        return None
    nested = {}
    for dotted, value in flat.items():
        node = nested
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return nested


# ---------------------------------------------------------------------------
# Báo cáo
# ---------------------------------------------------------------------------

def render_report(today, results, packs, region_counts, merged_by_source, kept_by_source, manual_section):
    lines = [
        "# REPORT — Speedwise data pipeline",
        "",
        "Lần chạy: %s (UTC). Sinh tự động bởi `build_packs.py` — đừng sửa phần trên dòng đánh dấu." % today.isoformat(),
        "",
        "## Nguồn",
        "",
        "| Nguồn | Bang | Tier | Tải | Ngày dataset | Dòng | Camera | Vào pack | Bị loại (lý do) |",
        "|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for result in results:
        reasons = dict(result["rejects"])
        if merged_by_source.get(result["id"]):
            reasons["gộp trùng ≤ 30 m"] = merged_by_source[result["id"]]
        reason_text = "; ".join("%s: %d" % (k, v) for k, v in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))) or "—"
        if result["status"] == "ok":
            status = "OK"
        elif result["status"] == "skipped":
            status = "không chạy (--only), giữ %d camera cũ" % kept_by_source.get(result["id"], 0)
        else:
            status = "LỖI: %s — giữ %d camera từ pack cũ" % (result["error"], kept_by_source.get(result["id"], 0))
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            result["id"], result["region"], result["tier"], status.replace("|", "/"),
            result.get("datasetDate") or "—",
            result["rows"] if result["rows"] is not None else "—",
            result["cameras"] if result["cameras"] is not None else "—",
            region_counts.get(result["id"], 0), reason_text.replace("|", "/")))
    lines += ["", "## Theo bang", "", "| Bang | Pack | Version | Camera | speed | redLight | schoolZone |", "|---|---|---:|---:|---:|---:|---:|"]
    total = 0
    for region in sorted(packs):
        pack = packs[region]
        cameras = read_json(os.path.join(PUBLIC_DIR, pack["file"]))["cameras"]
        by_type = collections.Counter(c["type"] for c in cameras)
        total += pack["cameraCount"]
        lines.append("| %s | `%s` | %d | %d | %d | %d | %d |" % (
            region, pack["file"], pack["version"], pack["cameraCount"], by_type["speed"], by_type["redLight"], by_type["schoolZone"]))
    lines += ["", "**Tổng: %d camera ở %d bang/khu vực.**" % (total, len(packs)), "", REPORT_MANUAL_MARKER]
    return "\n".join(lines) + "\n" + (manual_section if manual_section else "\n")


def read_manual_section():
    if not os.path.exists(REPORT_PATH):
        return ""
    with open(REPORT_PATH, encoding="utf-8") as handle:
        text = handle.read()
    return text.split(REPORT_MANUAL_MARKER, 1)[1] if REPORT_MANUAL_MARKER in text else ""


# ---------------------------------------------------------------------------
# Chạy
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="Speedwise: open data → data packs")
    parser.add_argument("--only", help="chỉ chạy các nguồn này (id, cách nhau bởi dấu phẩy); nguồn khác giữ camera từ pack cũ")
    parser.add_argument("--offline", action="store_true", help="không gọi mạng, dùng cache/ của lần chạy trước")
    args = parser.parse_args(argv)

    today = dt.datetime.now(dt.timezone.utc).date()
    now_iso = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources = [s for s in read_json(SOURCES_PATH) if s.get("enabled")]
    only = set(args.only.split(",")) if args.only else None
    if only and not only <= {s["id"] for s in sources}:
        parser.error("nguồn không có hoặc đang tắt: %s" % ", ".join(sorted(only - {s["id"] for s in sources})))
    bboxes = read_json(BBOXES_PATH)
    manifest = read_json(MANIFEST_PATH, {})
    tiers = {s["id"]: s["tier"] for s in sources}

    old_cameras = collections.defaultdict(list)
    for region, pack in manifest.get("regions", {}).items():
        old_pack = read_json(os.path.join(PUBLIC_DIR, pack["file"]))
        for camera in (old_pack or {}).get("cameras", []):
            old_cameras[camera.get("sourceId")].append(camera)

    results = []
    region_cameras = collections.defaultdict(list)
    kept_by_source = {}
    source_dates = {}
    for source in sources:
        result = {"id": source["id"], "region": source["region"], "tier": source["tier"],
                  "rows": None, "cameras": None, "rejects": collections.Counter()}
        results.append(result)
        if only and source["id"] not in only:
            result["status"] = "skipped"
        else:
            print("… %s" % source["id"], flush=True)
            try:
                raw, metadata = fetch_source(source, args.offline)
                rows = parse_raw(source, raw)
                day = dataset_date_from(source, metadata, rows)
                cameras, rejects = normalize_source(source, rows, day, today, bboxes)
                result.update(status="ok", rows=len(rows), cameras=len(cameras), rejects=rejects,
                              datasetDate=day.isoformat() if day else None)
                source_dates[source["id"]] = result["datasetDate"]
                region_cameras[source["region"]].extend(cameras)
                print("   %d dòng → %d camera" % (len(rows), len(cameras)), flush=True)
                continue
            except Exception as error:  # một nguồn lỗi không làm dừng các nguồn khác
                result.update(status="error", error=("%s: %s" % (type(error).__name__, error))[:180])
                print("   LỖI: %s" % result["error"], flush=True)
        kept = old_cameras.get(source["id"], [])
        kept_by_source[source["id"]] = len(kept)
        region_cameras[source["region"]].extend(kept)
        previous = next((s for s in (read_json(REGIONS_OUT_PATH) or {}).get("sources", []) if s["id"] == source["id"]), None)
        source_dates[source["id"]] = previous.get("updatedAt") if previous else None
        result["datasetDate"] = source_dates[source["id"]]

    merged_by_source = collections.Counter()
    final_cameras = {}
    for region, cameras in region_cameras.items():
        if not cameras:
            continue
        by_id = {c["id"]: c for c in cameras}
        kept, merged = merge_duplicates(cameras, tiers)
        for loser in merged:
            merged_by_source[by_id[loser]["sourceId"]] += 1
        final_cameras[region] = kept

    packs = write_packs(final_cameras, manifest, PACKS_DIR, today, now_iso)
    region_counts = collections.Counter(c["sourceId"] for cams in final_cameras.values() for c in cams)
    source_info = {s["id"]: {"updatedAt": source_dates.get(s["id"]), "cameraCount": region_counts.get(s["id"], 0)} for s in sources}

    existing = read_json(REGIONS_OUT_PATH)
    template = read_json(REGIONS_TEMPLATE_PATH) or existing
    if template is None:
        raise SystemExit("Không tìm thấy template regions.json (%s) và chưa có public/regions.json" % REGIONS_TEMPLATE_PATH)
    known = {r["code"] for r in template["regions"]}
    for region in packs:
        if region not in known:
            print("CẢNH BÁO: %s có pack nhưng không có trong template regions.json" % region)
    write_json(REGIONS_OUT_PATH, build_regions(template, existing, packs, sources, source_info))
    write_json(MANIFEST_PATH, {"regions": packs})

    report = render_report(today, results, packs, region_counts, merged_by_source, kept_by_source, read_manual_section())
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        handle.write(report)
    total = sum(p["cameraCount"] for p in packs.values())
    failed = [r["id"] for r in results if r["status"] == "error"]
    print("Xong: %d camera, %d bang. Nguồn lỗi: %s" % (total, len(packs), ", ".join(failed) or "không"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
