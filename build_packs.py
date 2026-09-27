#!/usr/bin/env python3
"""Speedwise data pipeline.

Tải vị trí camera chính thức (open data của thành phố/quận/bang/quốc gia), chuẩn hoá về schema
data pack của app (docs/04_TECH_SPEC.md mục 2.2, 11, 12), rồi ghi:
  public/packs/us-xx.vN.json (mph) · public/packs/<cc>.vN.json (km/h) · public/regions.json · manifest.json · REPORT.md

Chạy:  python3 build_packs.py [--only id1,id2] [--offline]
Chỉ dùng thư viện chuẩn Python 3.
"""

import argparse
import collections
import csv
import datetime as dt
import glob
import hashlib
import html
import io
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
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

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
# Key API trên máy (KEY=giá trị mỗi dòng, không commit). CI dùng GitHub Actions secrets → biến môi trường.
LOCAL_KEYS_PATH = os.path.expanduser("~/.speedwise/keys.env")

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
MAX_LIMIT = {"mph": 85, "kmh": 140}
# Pack lớn hơn mức này → ghi JSON rút gọn (bỏ khoảng trắng, bỏ trường null). Lớn hơn mức tối đa → dừng.
COMPACT_PACK_BYTES = 3 * 1024 * 1024
MAX_PACK_BYTES = 8 * 1024 * 1024
# Đoạn đo tốc độ trung bình → 2 camera speed (đầu/cuối), roadName kết thúc bằng hậu tố này (docs/04_TECH_SPEC.md mục 12.3).
SECTION_SUFFIX = " · average speed section"
MAX_PAGES = 100

# Vùng mới của CR-D2 (docs/04_TECH_SPEC.md mục 12.4) — thêm vào template regions.json nếu chưa có.
ADDED_REGIONS = [
    {"code": "HK", "name": "Hong Kong", "countryCode": "HK", "countryName": "Hong Kong", "status": "full", "cameraCount": 0},
    {"code": "AR", "name": "Argentina", "countryCode": "AR", "countryName": "Argentina", "status": "full", "cameraCount": 0},
    {"code": "CO", "name": "Colombia", "countryCode": "CO", "countryName": "Colombia", "status": "full", "cameraCount": 0},
]

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


def parse_direction(text, extra_words=None):
    """Trả mã hướng ("N", "SW"…) hoặc None. Nhiều hướng khác nhau trong cùng chuỗi → None (không đoán).
    extra_words: {cụm từ ngôn ngữ khác: mã} của nguồn, ví dụ {"en direction est": "E"} (khớp nguyên từ, không phân biệt hoa/thường)."""
    if text is None:
        return None
    text = str(text).replace("\xa0", " ")
    bare = _BARE_DIRECTION.match(text)
    if bare:
        word = bare.group(1)
        return DIRECTION_WORDS.get(word.lower(), word.upper())
    codes = set(_direction_codes(text))
    for phrase, code in (extra_words or {}).items():
        if re.search(r"(?<!\w)%s(?!\w)" % re.escape(phrase), text, flags=re.IGNORECASE):
            codes.add(code)
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
    # "O'RIORDAN" → "O'Riordan"; sở hữu cách "QUEEN'S" → "Queen's".
    return "'".join(part.lower() if index and part.upper() == "S" else part.capitalize()
                    for index, part in enumerate(word.split("'")))


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
        text = re.sub(r"\(\s*\)", " ", text)  # "(EB)" đã bỏ chữ hướng → ngoặc rỗng
    text = re.sub(r"\s+(?:@|at)\s+(?:the\s+)?junction\s+with\s+", " & ", text, flags=re.IGNORECASE)  # Hong Kong
    text = re.sub(r"\s+(?:@|at)\s+", " & ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s+", " ", text).strip(" &@,-/")
    text = re.sub(r"\s+(?:and|&)$", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None
    if not re.search(r"[a-z]", text):
        position = {"first": True}

        def replace(match):
            # Từ đầu tên đường, kể cả ngay sau "&" ("… & ON LAI STREET" → "& On Lai Street"), luôn viết hoa chữ đầu.
            starts_name = position["first"] or match.string[:match.start()].rstrip().endswith("&")
            result = _case_word(match, starts_name)
            position["first"] = False
            return result

        text = re.sub(r"[^\W_]+(?:'[^\W_]+)*", replace, text)  # cả chữ có dấu ("MARÍA")
        text = _ROUTE_PREFIX.sub(lambda m: m.group(1).upper() + m.group(2), text)
        # Đại lộ mang tên bang viết tắt ở DC: "NY Ave", "RI Ave", "MA Ave".
        text = re.sub(r"\b([A-Z][a-z])(?= Ave\b)", lambda m: m.group(1).upper(), text)
    return re.sub(r"\bblk\b", "Blk", text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Giá trị
# ---------------------------------------------------------------------------

def parse_limit(value, unit="mph"):
    """Số nguyên (theo đơn vị của pack) khi nguồn ghi đúng một con số hợp lý; ngược lại None (không đoán)."""
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
    return number if 5 <= number <= MAX_LIMIT[unit] else None


def pack_unit(region):
    """Pack Mỹ theo bang dùng mph; pack quốc gia ngoài Mỹ dùng km/h."""
    return "mph" if region.startswith("US-") else "kmh"


def parse_number(value, decimal_comma=False):
    """"-34,6230642" (dấu phẩy thập phân) hoặc "45.49" → float; không đọc được → None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if decimal_comma and "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value):
    """epoch (s hoặc ms), ISO 8601, m/d/Y, hoặc chuỗi YYYYMMDD[HHMMSS] (Hong Kong, Singapore) → datetime.date."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000.0 if abs(value) > 1e11 else float(value)
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc).date()
    text = str(value).strip()
    compact = re.fullmatch(r"((?:19|20)\d{2})(\d{2})(\d{2})(?:\d{6})?", text)
    if compact:
        try:
            return dt.date(*(int(part) for part in compact.groups()))
        except ValueError:
            pass
    if re.fullmatch(r"-?\d+", text):
        return parse_date(int(text))
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return dt.datetime.strptime(text.rstrip("Z"), fmt).date()
        except ValueError:
            continue
    try:
        # Có múi giờ ("2025-12-18T09:56:52.406+01:00", DATEX II) → ngày UTC.
        moment = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return moment.astimezone(dt.timezone.utc).date() if moment.tzinfo else moment.date()
    except ValueError:
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


def format_fields(template, row):
    """"{rodovia} km {km_m} · {sentido}" → giá trị các trường của dòng; trường trống → ""."""
    return re.sub(r"\{([^}]+)\}", lambda m: "" if is_empty(row.get(m.group(1))) else str(row.get(m.group(1))).strip(), template)


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


def utm_to_wgs84(zone, south, x, y):
    """UTM (WGS84/ETRS89/SIRGAS 2000 — cùng ellipsoid tới mức cm) → (lat, lon) độ. Chuỗi Krüger bậc 3, sai số cỡ mm trong múi."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    n = f / (2 - f)
    big_a = a / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    beta = (n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96, n ** 2 / 48 + n ** 3 / 15, 17 * n ** 3 / 480)
    delta = (2 * n - 2 * n ** 2 / 3 - 2 * n ** 3, 7 * n ** 2 / 3 - 8 * n ** 3 / 5, 56 * n ** 3 / 15)
    xi = (y - (10000000.0 if south else 0.0)) / (k0 * big_a)
    eta = (x - 500000.0) / (k0 * big_a)
    xi_p = xi - sum(b * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, b in enumerate(beta, 1))
    eta_p = eta - sum(b * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, b in enumerate(beta, 1))
    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    lat = chi + sum(d * math.sin(2 * j * chi) for j, d in enumerate(delta, 1))
    lon = math.radians(zone * 6 - 183) + math.atan2(math.sinh(eta_p), math.cos(xi_p))
    return math.degrees(lat), math.degrees(lon)


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

GEOJSON_FORMATS = ("arcgis-geojson", "socrata-geojson", "wfs-geojson", "geojson", "datagovsg-poll-download")
# Mảng JSON các dòng phẳng, toạ độ ở cặp trường lat/lon (hoặc `point` GeoJSON của Socrata).
FLAT_JSON_FORMATS = ("socrata-json", "datagovsg-datastore", "ntpc-json", "datagokr-api", "datagokr-std-download")


def _point_lon_lat(geometry):
    """Point, hoặc MultiPoint chỉ có 1 điểm → (lon, lat); hình khác → (None, None)."""
    geometry = geometry or {}
    coords = geometry.get("coordinates")
    if geometry.get("type") == "MultiPoint" and coords and len(coords) == 1:
        coords = coords[0]
    elif geometry.get("type") != "Point":
        coords = None
    return (coords[0], coords[1]) if coords else (None, None)


_WKT_POINT = re.compile(r"^\s*POINT\s*\(\s*(\S+)\s+(\S+)\s*\)\s*$", re.IGNORECASE)


def _csv_lat_lon(source, row):
    """Toạ độ của một dòng CSV: cặp trường lat/lon, cặp x/y, hoặc WKT "POINT (x y)"; `utm` → đổi sang WGS84."""
    field_map = source["fieldMap"]
    decimal_comma = source.get("csv", {}).get("decimalComma", False)
    if field_map.get("wkt"):
        match = _WKT_POINT.match(str(row.get(field_map["wkt"]) or ""))
        x, y = (parse_number(match.group(1)), parse_number(match.group(2))) if match else (None, None)
    elif field_map.get("x"):
        x, y = parse_number(row.get(field_map["x"]), decimal_comma), parse_number(row.get(field_map["y"]), decimal_comma)
    else:
        lat, lon = parse_number(row.get(field_map["lat"]), decimal_comma), parse_number(row.get(field_map["lon"]), decimal_comma)
        return lat, lon
    if x is None or y is None:
        return None, None
    if source.get("utm"):
        if not (100000 <= x <= 900000 and 0 <= y <= 10000000):
            return None, None  # UTM ngoài phạm vi (ví dụ nguồn mất dấu thập phân) → bị loại, không sửa tay
        return utm_to_wgs84(source["utm"]["zone"], source["utm"].get("south", False), x, y)
    return y, x


def _line_ends(geometry):
    """LineString (hoặc MultiLineString 1 đường) → [(lon, lat) đầu, (lon, lat) cuối]; hình khác → None."""
    geometry = geometry or {}
    coords = geometry.get("coordinates")
    if geometry.get("type") == "MultiLineString" and coords and len(coords) == 1:
        coords = coords[0]
    elif geometry.get("type") != "LineString":
        return None
    return [coords[0][:2], coords[-1][:2]] if coords and len(coords) >= 2 else None


def _fixed_width_records(text, skip_lines):
    """Văn bản cột thẳng hàng (Catalonia radars.txt): cột bắt đầu ở vị trí từng chữ tiêu đề; dòng trống bị bỏ."""
    lines = text.splitlines()[skip_lines:]
    header = lines[0]
    starts = [match.start() for match in re.finditer(r"\S+", header)]
    names = header.split()
    bounds = list(zip(starts, starts[1:] + [None]))
    return [{name: line[start:end].strip() for name, (start, end) in zip(names, bounds)}
            for line in lines[1:] if line.strip()]


def _xml_local(tag):
    return tag.rsplit("}", 1)[-1]


def _xml_child(element, *path):
    """Đi theo tên thẻ (bỏ namespace); không có → None."""
    for name in path:
        if element is None:
            return None
        element = next((child for child in element if _xml_local(child.tag) == name), None)
    return element


def _xml_text(element, *path):
    found = _xml_child(element, *path)
    return found.text.strip() if found is not None and found.text else None


def _xml_coordinates(element):
    coords = next((e for e in element.iter() if _xml_local(e.tag) == "pointCoordinates"), None)
    return (parse_number(_xml_text(coords, "latitude")), parse_number(_xml_text(coords, "longitude"))) if coords is not None else (None, None)


def _datex2_km(reference_point):
    meters = parse_number(_xml_text(reference_point, "referencePointDistance"))
    return None if meters is None else ("%.3f" % (meters / 1000.0)).rstrip("0").rstrip(".")


def _datex2_reference(reference_point):
    return {"road": _xml_text(reference_point, "roadName", "value") or _xml_text(reference_point, "roadNumber"),
            "province": _xml_text(reference_point, "administrativeArea", "value")}


def parse_datex2_locations(text):
    """DATEX II PredefinedLocationsPublication (DGT radares) → dòng phẳng.
    Point → 1 dòng. Linear (tramo đo tốc độ trung bình) → 2 dòng `_section` "start"/"end" tại điểm from/to; `km` = "đầu–cuối"."""
    root = ET.fromstring(text)
    published = next((e.text for e in root.iter() if _xml_local(e.tag) == "publicationTime"), None)
    rows = []
    for location_set in (e for e in root.iter() if _xml_local(e.tag) == "predefinedLocationSet"):
        set_name = _xml_text(location_set, "predefinedLocationSetName", "value")
        for location in (c for c in location_set if _xml_local(c.tag) == "predefinedLocation"):
            inner = _xml_child(location, "predefinedLocation")
            if inner is None:
                continue
            kind = inner.get("{http://www.w3.org/2001/XMLSchema-instance}type", "").rsplit(":", 1)[-1]
            base = {"id": location.get("id"), "set": set_name, "kind": kind, "publicationTime": published}
            if kind == "Point":
                reference = _xml_child(inner, "referencePoint")
                lat, lon = _xml_coordinates(inner)
                rows.append(dict(base, km=_datex2_km(reference), _lat=lat, _lon=lon, **_datex2_reference(reference)))
            elif kind == "Linear":
                primary = _xml_child(inner, "referencePointLinear", "referencePointPrimaryLocation", "referencePoint")
                secondary = _xml_child(inner, "referencePointLinear", "referencePointSecondaryLocation", "referencePoint")
                km_values = [k for k in (_datex2_km(primary), _datex2_km(secondary)) if k is not None]
                km = "–".join(sorted(km_values, key=float)) if km_values else None
                linear = _xml_child(inner, "tpeglinearLocation")
                for section, end in (("start", "from"), ("end", "to")):
                    point = _xml_child(linear, end)
                    lat, lon = _xml_coordinates(point) if point is not None else (None, None)
                    rows.append(dict(base, km=km, _lat=lat, _lon=lon, _section=section, **_datex2_reference(primary)))
            else:
                rows.append(dict(base, _lat=None, _lon=None))
    return rows


# NVDB vegkategori → cách viết số đường trên biển báo Na Uy.
NVDB_ROAD_PREFIX = {"E": "E", "R": "Rv", "F": "Fv", "K": "Kv", "P": "Pv", "S": "Sv"}
_WKT_ANY_POINT = re.compile(r"^\s*POINT\s*Z?\s*\(\s*([^\s)]+)\s+([^\s)]+)", re.IGNORECASE)


def parse_nvdb_objects(objects):
    """NVDB API Les v4 vegobjekter (inkluder=egenskaper,lokasjon,metadata,geometri; srid=4326) → dòng phẳng.
    Trường = tên egenskap ("Navn", "Kontollretning"…). WKT srid 4326 của NVDB theo thứ tự trục EPSG: vĩ độ trước."""
    rows = []
    for obj in objects:
        row = {prop["navn"]: prop.get("verdi") for prop in obj.get("egenskaper", [])}
        row["id"] = obj.get("id")
        row["sist_modifisert"] = (obj.get("metadata") or {}).get("sist_modifisert")
        references = (obj.get("lokasjon") or {}).get("vegsystemreferanser") or []
        system = references[0].get("vegsystem", {}) if references else {}
        prefix = NVDB_ROAD_PREFIX.get(system.get("vegkategori"))
        row["vegsystem"] = "%s%s" % (prefix, system["nummer"]) if prefix and system.get("nummer") is not None else None
        match = _WKT_ANY_POINT.match(((obj.get("geometri") or {}).get("wkt")) or "")
        row["_lat"], row["_lon"] = (parse_number(match.group(1)), parse_number(match.group(2))) if match else (None, None)
        rows.append(row)
    return rows


def parse_trafikverket_items(items):
    """Trafikverket TrafficSafetyCamera v1 → dòng phẳng; toạ độ từ Geometry.WGS84 "POINT (lon lat)".
    Số đường chỉ có chữ số ("25") → "Väg 25" như cách gọi ở Thuỵ Điển; "E4" giữ nguyên."""
    rows = []
    for item in items:
        row = dict(item)
        match = _WKT_POINT.match(str(dig(item, "Geometry.WGS84") or ""))
        row["_lon"], row["_lat"] = (parse_number(match.group(1)), parse_number(match.group(2))) if match else (None, None)
        number = str(item.get("RoadNumber") or "").strip()
        row["road"] = ("Väg " + number) if number.isdigit() else (number or None)
        rows.append(row)
    return rows


_POPUP_CELL = re.compile(r"<th>(.*?)</th>\s*<td>(.*?)</td>", re.DOTALL)


def popup_fields(text):
    """Trường PopupInfo (bảng HTML <th>tên</th><td>giá trị</td> do lớp KML sinh ra — CSDI Hong Kong) → dict."""
    return {html.unescape(name).strip(): html.unescape(value).strip() for name, value in _POPUP_CELL.findall(str(text or ""))}


def section_rows(row, fields):
    """Đoạn đo tốc độ trung bình ghi toạ độ đầu/cuối trong 4 trường (New Taipei). Đoạn 2 chiều ghi nhiều giá trị cách nhau
    khoảng trắng — giá trị thứ i của cả 4 trường là chiều thứ i. → 2 dòng/chiều ("start"/"end"); nhiều chiều thì key thêm "d<i>"."""
    values = {name: str(row.get(field) or "").split() for name, field in fields.items()}
    count = len(values["startLat"])
    if count == 0 or any(len(v) != count for v in values.values()):
        return [dict(row, _lat=None, _lon=None)]
    rows = []
    for index in range(count):
        suffix = "d%d" % (index + 1) if count > 1 else ""
        for section in ("start", "end"):
            rows.append(dict(row, _lat=values[section + "Lat"][index], _lon=values[section + "Lon"][index],
                             _section=section, _keySuffix=suffix))
    return rows


def parse_raw(source, raw):
    """Dữ liệu thô của một nguồn → danh sách dict phẳng; toạ độ đặt ở "_lat"/"_lon"."""
    rows = _parse_rows(source, raw)
    rule = source.get("sectionField")
    if rule:
        # Mã vị trí trong đoạn đo tốc độ trung bình (Hàn Quốc 단속구간위치구분: 1 = 시점 đầu, 2 = 종점 cuối).
        # Chỉ tính là đoạn khi độ dài đoạn > 0 — vài cơ quan ghi mã nhưng độ dài 0 (camera điểm).
        for row in rows:
            code = str(row.get(rule["field"]) or "").strip()
            length = parse_number(row.get(rule["lengthField"])) if rule.get("lengthField") else 1
            if length and length > 0 and code in rule["start"] + rule["end"]:
                row["_section"] = "start" if code in rule["start"] else "end"
    second = source.get("secondPoint")
    if second:
        # Vị trí camera thứ hai của cùng dòng (NSW lat_2/long_2) → thêm 1 dòng, key thêm "p2".
        rows += [dict(row, _lat=row[second["lat"]], _lon=row[second["lon"]], _keySuffix="p2")
                 for row in rows if not is_empty(row.get(second["lat"])) and not is_empty(row.get(second["lon"]))]
    return rows


def _parse_rows(source, raw):
    fmt = source["format"]
    rows = []
    if fmt in GEOJSON_FORMATS:
        if not isinstance(raw, dict) or "features" not in raw:
            raise ValueError("phản hồi không phải GeoJSON FeatureCollection")
        if (raw.get("properties") or {}).get("exceededTransferLimit") or raw.get("exceededTransferLimit"):
            raise ValueError("máy chủ cắt bớt kết quả (exceededTransferLimit) — cần phân trang")
        field_map = source.get("fieldMap", {})
        for feature in raw["features"]:
            row = dict(feature.get("properties") or {})
            if source.get("popupTable"):
                row.update(popup_fields(row.get(source["popupTable"])))
            ends = _line_ends(feature.get("geometry")) if source.get("lineSections") else None
            if ends:
                # Đoạn đo tốc độ trung bình (Luxembourg): 1 dòng ở đầu, 1 dòng ở cuối.
                for section, (lon, lat) in zip(("start", "end"), ends):
                    rows.append(dict(row, _lon=lon, _lat=lat, _section=section))
                continue
            row["_lon"], row["_lat"] = _point_lon_lat(feature.get("geometry"))
            if row["_lat"] is None and field_map.get("lat"):
                # Geometry trống nhưng dataset có trường toạ độ riêng (Bogotá LATITUD/LONGITUD).
                row["_lat"], row["_lon"] = row.get(field_map["lat"]), row.get(field_map["lon"])
            rows.append(row)
    elif fmt in FLAT_JSON_FORMATS:
        if not isinstance(raw, list):
            raise ValueError("phản hồi %s không phải mảng JSON" % fmt)
        field_map = source["fieldMap"]
        for item in raw:
            row = dict(item)
            if source.get("sectionFields"):
                rows.extend(section_rows(row, source["sectionFields"]))
                continue
            if field_map.get("point"):
                point = item.get(field_map["point"]) or {}
                coords = point.get("coordinates") if isinstance(point, dict) else None
                row["_lon"], row["_lat"] = (coords[0], coords[1]) if coords else (None, None)
            else:
                row["_lat"], row["_lon"] = item.get(field_map.get("lat")), item.get(field_map.get("lon"))
            rows.append(row)
    elif fmt == "csv":
        if not isinstance(raw, str):
            raise ValueError("dữ liệu CSV không phải văn bản")
        options = source.get("csv", {})
        if options.get("fixedWidth"):
            items = _fixed_width_records(raw, options.get("skipLines", 0))
        else:
            items = csv.DictReader(io.StringIO(raw), delimiter=options.get("delimiter", ","))
        for item in items:
            row = {key.strip(): value for key, value in item.items() if key is not None}
            row["_lat"], row["_lon"] = _csv_lat_lon(source, row)
            rows.append(row)
    elif fmt == "datex2-predefined-locations":
        if not isinstance(raw, str):
            raise ValueError("dữ liệu DATEX II không phải văn bản XML")
        rows = parse_datex2_locations(raw)
    elif fmt == "nvdb-v4":
        if not isinstance(raw, list):
            raise ValueError("dữ liệu NVDB không phải mảng vegobjekter")
        rows = parse_nvdb_objects(raw)
    elif fmt == "trafikverket-post":
        if not isinstance(raw, list):
            raise ValueError("dữ liệu Trafikverket không phải mảng")
        rows = parse_trafikverket_items(raw)
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
    unit = pack_unit(region)
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

        if camera_type in source.get("typeConfidence", {}):
            confidence = source["typeConfidence"][camera_type]
        elif status_active:
            confidence = source["baseConfidence"]
        else:
            confidence = min(source["baseConfidence"], NO_STATUS_CONFIDENCE[source["tier"]])
        if stale:
            confidence -= STALE_PENALTY
        confidence = max(MIN_CONFIDENCE, confidence)

        if field_map.get("roadFormat"):
            road_text = format_fields(field_map["roadFormat"], row)
            if field_map.get("roadPattern"):
                road_match = re.search(field_map["roadPattern"], road_text, flags=re.DOTALL)
                road_text = road_match.group(1) if road_match else road_text
            # Trường trống → bỏ dấu "·" / "km" treo ("E6 · " → "E6", "A-2 km " → "A-2").
            road_text = re.sub(r"\s+km\s*(?=·|$)", " ", road_text)
            road_text = re.sub(r"^(?:\s*·)+|(?:·\s*)+$", "", road_text.strip()).strip()
            road = clean_road(road_text, strip_directions=False)
        else:
            road_fields = [f for f in field_map.get("road") or [] if not is_empty(row.get(f))][:1]
            road_text = first_value(row, road_fields)
            if field_map.get("roadPattern") and road_text is not None:
                road_match = re.search(field_map["roadPattern"], str(road_text), flags=re.DOTALL)
                road_text = road_match.group(1) if road_match else road_text
            road = clean_road(road_text, strip_directions=bool(road_fields) and road_fields[0] in (field_map.get("direction") or []))
        section = row.get("_section")
        if section:
            road = road + SECTION_SUFFIX if road else SECTION_SUFFIX.strip(" ·").capitalize()
        limit = parse_limit(row.get(field_map["limit"]), unit) if field_map.get("limit") else None
        # Góc la bàn của nguồn (độ). `bearingOffset`: 180 khi nguồn ghi hướng ống kính (chụp trực diện xe đi tới).
        bearing = parse_number(row.get(field_map["bearing"])) if field_map.get("bearing") else None
        bearing_heading = None
        if bearing is not None and 0 <= bearing <= 360:
            bearing_heading = int(round(bearing + source.get("bearingOffset", 0))) % 360
        key_value = row.get(field_map["key"]) if field_map.get("key") else None
        if field_map.get("keyPattern") and not is_empty(key_value):
            key_match = re.search(field_map["keyPattern"], str(key_value))
            key_value = key_match.group(1) if key_match else None
        key = "" if is_empty(key_value) else key_part(key_value)
        if key and row.get("_keySuffix"):
            key += row["_keySuffix"]  # camera thứ 2 của dòng (NSW "p2") / chiều thứ i của đoạn (New Taipei "d1")

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
            variants = [(parse_direction(first_value(row, field_map.get("direction")), source.get("directionWords")), False)]

        for code, suffixed in variants:
            heading = bearing_heading if bearing_heading is not None else heading_for(code)
            if key:
                camera_key = key + ("-" + direction_suffix(code) if suffixed else "")
            else:
                seed = "%.5f|%.5f|%s|%s" % (lat, lon, camera_type, heading)
                camera_key = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
            if section:
                camera_key += "-" + section
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


def pack_text(pack):
    """JSON của pack: thụt lề như các file khác; > 3 MB → rút gọn (không khoảng trắng, bỏ trường null), schema giữ nguyên.
    Vẫn > 8 MB → dừng (cần quyết định tách pack)."""
    text = json.dumps(pack, indent=2, ensure_ascii=False) + "\n"
    if len(text.encode("utf-8")) > COMPACT_PACK_BYTES:
        compact = dict(pack, cameras=[{k: v for k, v in camera.items() if v is not None} for camera in pack["cameras"]])
        text = json.dumps(compact, separators=(",", ":"), ensure_ascii=False) + "\n"
    size = len(text.encode("utf-8"))
    if size > MAX_PACK_BYTES:
        raise SystemExit("Pack %s nặng %.1f MB > 8 MB — dừng, cần quyết định tách pack (docs/05_TASKS.md D05)." % (pack["region"], size / 1048576))
    return text


def write_packs(region_cameras, manifest, packs_dir, today, now_iso):
    """Ghi pack cho vùng có nội dung mới (version + 1), giữ nguyên vùng không đổi. Mỹ: mph, ngoài Mỹ: km/h.
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
        pack = {"region": region, "version": version, "generatedAt": now_iso, "unit": pack_unit(region), "cameras": cameras}
        with open(os.path.join(packs_dir, name), "w", encoding="utf-8") as handle:
            handle.write(pack_text(pack))
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
    source_info: {id: {"updatedAt": "YYYY-MM-DD"|None, "cameraCount": int}}.
    Trạng thái pháp lý (mục 12.4): `comingSoon` có pack → `full`; `restricted`/`blocked` không bao giờ đổi và không có packURL."""
    coverage = collections.OrderedDict()
    for source in sources:
        if source_info.get(source["id"], {}).get("cameraCount", 0) > 0:
            notes = coverage.setdefault(source["region"], [])
            if source["coverage"] not in notes:
                notes.append(source["coverage"])

    known = {entry["code"] for entry in template["regions"]}
    regions = []
    for entry in template["regions"] + [r for r in ADDED_REGIONS if r["code"] not in known]:
        region = dict(entry)
        for field in ("packURL", "packVersion", "coverageNote"):
            region.pop(field, None)
        pack = packs.get(region["code"])
        if pack and region["status"] == "comingSoon":
            region["status"] = "full"
            region.pop("legalNote", None)
        if pack and region["status"] == "full":
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
    # Python ≥ 3.13 bật VERIFY_X509_STRICT: chứng chỉ gốc GRCA của chính phủ Đài Loan (data.ntpc.gov.tw, opdadm.moi.gov.tw)
    # thiếu Subject Key Identifier → bị từ chối. Bỏ riêng cờ này (như Python 3.12 trên CI); chuỗi chứng chỉ vẫn được xác minh.
    context.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
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


def _http_get(url, accept, decode, headers=None, data=None):
    """GET (hoặc POST khi có `data`). Lỗi trả về chỉ gồm thông điệp của urllib — không bao giờ chứa body gửi đi (có thể chứa key)."""
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        _SSL_CONTEXT = _ssl_context()
    safe_url = urllib.parse.quote(url, safe=":/?&=*,'()$%+@;!~#")
    request = urllib.request.Request(safe_url, data=data, headers=dict({"User-Agent": USER_AGENT, "Accept": accept}, **(headers or {})))
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_SSL_CONTEXT) as response:
                return decode(response.read())
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            last_error = error
            if attempt + 1 < RETRIES:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def http_get_json(url, headers=None, data=None):
    def decode(body):
        data = json.loads(body.decode("utf-8"))
        if isinstance(data, dict) and "error" in data and "features" not in data:
            raise ValueError("máy chủ báo lỗi: %s" % json.dumps(data["error"])[:200])
        return data
    return _http_get(url, "application/json", decode, headers, data)


def http_get_text(url, encoding="utf-8-sig"):
    return _http_get(url, "text/csv, text/plain, application/xml, */*", lambda body: body.decode(encoding))


class MissingKey(Exception):
    """Nguồn cần key API mà biến môi trường chưa có → bỏ qua nguồn, không phải lỗi."""


def load_local_keys(path=LOCAL_KEYS_PATH):
    """Đọc KEY=giá trị từ ~/.speedwise/keys.env vào biến môi trường (không ghi đè biến đã có, không in giá trị)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            name, sep, value = line.strip().partition("=")
            if sep and name and not name.startswith("#"):
                os.environ.setdefault(name.strip(), value.strip().strip("'\""))


def source_api_key(source):
    """Giá trị key của nguồn (từ biến môi trường `apiKeyEnv`); nguồn không cần key → None; thiếu → MissingKey."""
    name = source.get("apiKeyEnv")
    if not name:
        return None
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingKey(name)
    return value


def fetch_nvdb(endpoint, headers):
    """NVDB API Les v4: đi theo `metadata.neste.href` tới khi trang trả 0 đối tượng."""
    objects, url = [], endpoint
    for _ in range(MAX_PAGES):
        page = http_get_json(url, headers)
        objects.extend(page.get("objekter", []))
        following = (page.get("metadata") or {}).get("neste") or {}
        if not page.get("objekter") or not following.get("href"):
            return objects
        url = following["href"]
    raise ValueError("NVDB: quá %d trang" % MAX_PAGES)


def fetch_trafikverket(source, key):
    """Trafikverket Open API: POST một QUERY XML; trả mảng đối tượng `objecttype`. Key chỉ nằm trong body gửi đi."""
    query = source["query"]
    body = '<REQUEST><LOGIN authenticationkey=%s/><QUERY objecttype=%s schemaversion=%s/></REQUEST>' % (
        quoteattr(key), quoteattr(query["objecttype"]), quoteattr(query["schemaversion"]))
    response = http_get_json(source["endpoint"], {"Content-Type": "text/xml"}, body.encode("utf-8"))
    result = (dig(response, "RESPONSE.RESULT") or [{}])[0]
    if "ERROR" in result:
        raise ValueError("Trafikverket báo lỗi: %s" % str(result["ERROR"].get("MESSAGE", "")).replace(key, "***")[:150])
    return result.get(query["objecttype"], [])


DATAGOVSG_RATE_LIMITED = 24
DATAGOVSG_WAIT_SECONDS = 12
DATAGOVSG_PAGE = 1000


def datagovsg_json(url):
    """API data.gov.sg: không key thì bị giới hạn tốc độ (code 24 "TOO_MANY_REQUESTS", chờ ~10 giây) → chờ rồi gọi lại."""
    for _ in range(RETRIES + 1):
        response = http_get_json(url)
        if not (isinstance(response, dict) and response.get("code") == DATAGOVSG_RATE_LIMITED):
            return response
        time.sleep(DATAGOVSG_WAIT_SECONDS)
    raise ValueError("data.gov.sg: vẫn bị giới hạn tốc độ sau %d lần chờ" % RETRIES)


def fetch_datagovsg_datastore(endpoint):
    """data.gov.sg `datastore_search` (CKAN): phân trang `offset` tới khi đủ `total` dòng."""
    records = []
    for _ in range(MAX_PAGES):
        separator = "&" if "?" in endpoint else "?"
        result = datagovsg_json("%s%slimit=%d&offset=%d" % (endpoint, separator, DATAGOVSG_PAGE, len(records)))["result"]
        records.extend(result["records"])
        if not result["records"] or len(records) >= result["total"]:
            return records
    raise ValueError("data.gov.sg: quá %d trang" % MAX_PAGES)


def fetch_datagovsg_poll_download(endpoint):
    """data.gov.sg `poll-download`: trả link tải tạm (S3, hết hạn sau 1 giờ) → tải file GeoJSON."""
    response = datagovsg_json(endpoint)
    url = (response.get("data") or {}).get("url")
    if not url:
        raise ValueError("data.gov.sg poll-download không trả link: %s" % str(response.get("errorMsg"))[:120])
    return http_get_json(url)


NTPC_PAGE_SIZE = 1000


def fetch_ntpc(endpoint):
    """Cổng open data New Taipei: /api/datasets/<uuid>/json, phân trang `page` (từ 0) / `size` tới khi trang thiếu dòng."""
    rows = []
    for page in range(MAX_PAGES):
        separator = "&" if "?" in endpoint else "?"
        batch = http_get_json("%s%spage=%d&size=%d" % (endpoint, separator, page, NTPC_PAGE_SIZE))
        if not isinstance(batch, list):
            raise ValueError("New Taipei: trang %d không phải mảng JSON" % page)
        rows.extend(batch)
        if len(batch) < NTPC_PAGE_SIZE:
            return rows
    raise ValueError("New Taipei: quá %d trang" % MAX_PAGES)


DATAGOKR_PAGE = 1000
DATAGOKR_MIN_INTERVAL = 0.25  # ≤ 5 request/giây (ràng buộc D05)


def datagokr_items(response):
    """Phản hồi JSON của api.data.go.kr → (dòng, totalCount). Lỗi (key sai, hết lượt…) → ValueError, không kèm key."""
    header = dig(response, "response.header") or {}
    if header.get("resultCode") not in ("00", "0"):
        message = header.get("resultMsg") or dig(response, "OpenAPI_ServiceResponse.cmmMsgHeader.errMsg") or "không rõ"
        raise ValueError("data.go.kr báo lỗi: %s" % str(message)[:120])
    body = dig(response, "response.body") or {}
    items = body.get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return items, int(body.get("totalCount") or 0)


def fetch_datagokr(endpoint, key):
    """api.data.go.kr (표준데이터): phân trang `pageNo` / `numOfRows`, key ở tham số `serviceKey` (chỉ nằm trong URL gửi đi)."""
    rows = []
    for page in range(1, MAX_PAGES + 1):
        separator = "&" if "?" in endpoint else "?"
        url = "%s%sserviceKey=%s&type=json&pageNo=%d&numOfRows=%d" % (
            endpoint, separator, urllib.parse.quote(key, safe=""), page, DATAGOKR_PAGE)
        try:
            items, total = datagokr_items(http_get_json(url))
        except RuntimeError as error:
            raise RuntimeError(str(error).replace(key, "***")) from None
        rows.extend(items)
        if not items or len(rows) >= total:
            return rows
        time.sleep(DATAGOKR_MIN_INTERVAL)
    raise ValueError("data.go.kr: quá %d trang" % MAX_PAGES)


DATAGOKR_DOWNLOAD_PAGE = 10000


def fetch_datagokr_std_download(endpoint, dataset_pk):
    """Nút "tải file" của dataset chuẩn trên data.go.kr (không cần key — bạn duyệt 2026-09-27, docs/06_DECISIONS.md):
    `columList.json?pk=<id>&ext=JSON` cho tên bảng + danh sách cột + tổng số dòng, rồi `standard.json` trả từng trang 10.000 dòng."""
    header = http_get_json("%s/columList.json?pk=%s&ext=JSON" % (endpoint, dataset_pk))
    table, total = header["tableVO"], int(header["totalCount"])
    rows = []
    for page in range(1, MAX_PAGES + 1):
        query = [("publicDataPk", dataset_pk), ("svcTableNm", table["svcTableNm"]), ("perPage", DATAGOKR_DOWNLOAD_PAGE),
                 ("page", page), ("totalCount", total)] + [("colNmList", column) for column in table["colNmList"]]
        batch = http_get_json("%s/standard.json?%s" % (endpoint, urllib.parse.urlencode(query)))
        if not isinstance(batch, list):
            raise ValueError("data.go.kr: trang %d không phải mảng JSON" % page)
        rows.extend(batch)
        if not batch or len(rows) >= total:
            if len(rows) < total:
                raise ValueError("data.go.kr: chỉ nhận %d/%d dòng" % (len(rows), total))
            return rows
        time.sleep(DATAGOKR_MIN_INTERVAL)
    raise ValueError("data.go.kr: quá %d trang" % MAX_PAGES)


def latest_ckan_resource(package, rule):
    """CKAN `package_show` → URL resource mới nhất (theo `created`) có tên khớp `namePattern` và đúng `format`.
    Dùng cho dataset mà file đổi tên mỗi kỳ (Belo Horizonte, ANTT)."""
    matches = [r for r in package["result"]["resources"]
               if re.search(rule["namePattern"], r.get("name") or "") and (r.get("format") or "").upper() == rule["format"].upper()]
    if not matches:
        raise ValueError("CKAN: không có resource %s khớp %s" % (rule["format"], rule["namePattern"]))
    return max(matches, key=lambda r: r.get("created") or "")["url"]


def decode_coded_values(raw, layer_info, fields):
    """ArcGIS: đổi mã số của các trường có coded-value domain thành tên ("1" → "1-Approved"), tra bảng trong `<layer>?f=json`."""
    tables = {}
    for field in layer_info.get("fields", []):
        if field["name"] in fields and (field.get("domain") or {}).get("codedValues"):
            tables[field["name"]] = {cv["code"]: cv["name"] for cv in field["domain"]["codedValues"]}
    missing = set(fields) - set(tables)
    if missing:
        raise ValueError("layer không có bảng mã cho trường: %s" % ", ".join(sorted(missing)))
    for feature in raw["features"]:
        props = feature.get("properties") or {}
        for name, table in tables.items():
            if props.get(name) is not None:
                props[name] = table.get(props[name], props[name])
    return raw


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
    """≤ 5 dòng thô, ưu tiên đủ các trường hợp khác nhau (loại, trạng thái, số approach). CSV: giữ dạng văn bản + dòng tiêu đề.
    DATEX II: giữ ≤ 2 location mỗi tập (điểm + đoạn). Văn bản cột cố định: giữ phần đầu + tiêu đề + 5 dòng đầu."""
    if source["format"] == "datex2-predefined-locations":
        root = ET.fromstring(raw)
        for location_set in [e for e in root.iter() if _xml_local(e.tag) == "predefinedLocationSet"]:
            for extra in [c for c in location_set if _xml_local(c.tag) == "predefinedLocation"][2:]:
                location_set.remove(extra)
        return ET.tostring(root, encoding="unicode")
    if source.get("csv", {}).get("fixedWidth"):
        lines = raw.splitlines()
        head = source["csv"].get("skipLines", 0) + 1
        return "\n".join(lines[:head] + [line for line in lines[head:] if line.strip()][:FIXTURE_ROWS]) + "\n"
    delimiter = source.get("csv", {}).get("delimiter", ",")
    if isinstance(raw, str):
        lines = list(csv.reader(io.StringIO(raw), delimiter=delimiter))
        header = lines[0]
        items = [(line, dict(zip(header, line))) for line in lines[1:] if line]
    elif isinstance(raw, dict):
        items = [(feature, feature.get("properties", {})) for feature in raw["features"]]
    else:
        items = [(item, item) for item in raw]
    type_field = source["typeMap"].get("field")
    active_field = (source["fieldMap"].get("active") or {}).get("field")

    def signature(item, props):
        geometry = item.get("geometry") if isinstance(raw, dict) else None
        return (props.get(type_field) if type_field else None,
                props.get(active_field) if active_field else None,
                sum(1 for f in source.get("approaches", []) if not is_empty(props.get(f))),
                (geometry or {}).get("type"))

    chosen, seen = [], set()
    for item, props in items:
        sig = signature(item, props)
        if sig not in seen:
            seen.add(sig)
            chosen.append(item)
    for item, _ in items:
        if len(chosen) >= FIXTURE_ROWS:
            break
        if item not in chosen:
            chosen.append(item)
    chosen = chosen[:FIXTURE_ROWS]
    if isinstance(raw, str):
        out = io.StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(chosen)
        return out.getvalue()
    return dict(raw, features=chosen) if isinstance(raw, dict) else chosen


def fetch_source(source, offline):
    """→ (raw, metadata). Online: lưu cache/<id>.json; lần tải đầu lưu fixtures/<id>.json."""
    cache_path = os.path.join(CACHE_DIR, source["id"] + ".json")
    if offline:
        cached = read_json(cache_path)
        if cached is None:
            raise RuntimeError("--offline: chưa có cache/%s.json" % source["id"])
        return cached["raw"], cached["metadata"]
    key = source_api_key(source)
    endpoint = source["endpoint"]
    if source.get("ckanResource"):
        endpoint = latest_ckan_resource(http_get_json(endpoint), source["ckanResource"])
    if source["format"] in ("csv", "datex2-predefined-locations"):
        raw = http_get_text(endpoint, source.get("csv", {}).get("encoding", "utf-8-sig"))
    elif source["format"] == "nvdb-v4":
        raw = fetch_nvdb(endpoint, source.get("headers"))
    elif source["format"] == "trafikverket-post":
        raw = fetch_trafikverket(source, key)
    elif source["format"] == "datagovsg-datastore":
        raw = fetch_datagovsg_datastore(endpoint)
    elif source["format"] == "datagovsg-poll-download":
        raw = fetch_datagovsg_poll_download(endpoint)
    elif source["format"] == "ntpc-json":
        raw = fetch_ntpc(endpoint)
    elif source["format"] == "datagokr-api":
        raw = fetch_datagokr(endpoint, key)
    elif source["format"] == "datagokr-std-download":
        raw = fetch_datagokr_std_download(endpoint, source["datasetPk"])
    else:
        raw = http_get_json(endpoint, source.get("headers"))
    if source.get("codedValues"):
        raw = decode_coded_values(raw, http_get_json(source["codedValues"]["url"]), source["codedValues"]["fields"])
    metadata = None
    if source.get("metadata"):
        try:
            get = datagovsg_json if source["format"].startswith("datagovsg") else http_get_json
            metadata = get(source["metadata"]["url"])
        except (RuntimeError, ValueError):
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
        "| Nguồn | Vùng | Tier | Tải | Ngày dataset | Dòng | Camera | Vào pack | Bị loại (lý do) |",
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
        elif result["status"] == "nokey":
            status = "skipped: no key (%s) — giữ %d camera cũ" % (result["error"], kept_by_source.get(result["id"], 0))
        else:
            status = "LỖI: %s — giữ %d camera từ pack cũ" % (result["error"], kept_by_source.get(result["id"], 0))
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            result["id"], result["region"], result["tier"], status.replace("|", "/"),
            result.get("datasetDate") or "—",
            result["rows"] if result["rows"] is not None else "—",
            result["cameras"] if result["cameras"] is not None else "—",
            region_counts.get(result["id"], 0), reason_text.replace("|", "/")))
    lines += ["", "## Theo vùng", "",
              "| Vùng | Pack | Đơn vị | KB | Version | Camera | speed | redLight | schoolZone | combined | mobile |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    total = 0
    for region in sorted(packs):
        pack = packs[region]
        path = os.path.join(PUBLIC_DIR, pack["file"])
        cameras = read_json(path)["cameras"]
        by_type = collections.Counter(c["type"] for c in cameras)
        total += pack["cameraCount"]
        lines.append("| %s | `%s` | %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            region, pack["file"], pack_unit(region), math.ceil(os.path.getsize(path) / 1024), pack["version"], pack["cameraCount"],
            by_type["speed"], by_type["redLight"], by_type["schoolZone"], by_type["combined"], by_type["mobile"]))
    lines += ["", "**Tổng: %d camera ở %d vùng.**" % (total, len(packs)), "", REPORT_MANUAL_MARKER]
    manual = manual_section.strip("\n")
    return "\n".join(lines) + "\n" + ("\n" + manual + "\n" if manual else "")


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
    load_local_keys()

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
            except MissingKey as missing:
                result.update(status="nokey", error=str(missing))
                print("   bỏ qua: chưa có key %s" % missing, flush=True)
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
    known = {r["code"] for r in template["regions"] + ADDED_REGIONS}
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
    no_key = [r["id"] for r in results if r["status"] == "nokey"]
    print("Xong: %d camera, %d vùng. Nguồn lỗi: %s. Thiếu key: %s" % (
        total, len(packs), ", ".join(failed) or "không", ", ".join(no_key) or "không"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
