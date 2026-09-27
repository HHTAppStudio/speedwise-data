"""Test cho build_packs.py — chỉ dùng fixtures/ (dòng thật lưu từ lần tải đầu), không gọi mạng.

Chạy: python3 -m unittest -v
"""

import copy
import datetime as dt
import json
import os
import random
import tempfile
import unittest

import build_packs as bp

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = dt.date(2026, 9, 27)
BBOXES = bp.read_json(os.path.join(HERE, "state_bboxes.json"))
SOURCES = {s["id"]: s for s in bp.read_json(os.path.join(HERE, "sources.json"))}


def fixture(source_id):
    return bp.read_json(os.path.join(HERE, "fixtures", source_id + ".json"))


def fixture_rows(source_id):
    return bp.parse_raw(SOURCES[source_id], fixture(source_id)["raw"])


def normalize(source_id, rows=None):
    source = SOURCES[source_id]
    rows = fixture_rows(source_id) if rows is None else rows
    day = bp.dataset_date_from(source, bp.fixture_metadata(fixture(source_id)), rows)
    return bp.normalize_source(source, rows, day, TODAY, BBOXES)


class DirectionTests(unittest.TestCase):
    def test_eight_directions_and_none(self):
        cases = {
            "3900 BLK GEORGIA AVE NW N/B": 0,
            "KANSAS AVE NE/B @ BUCHANAN ST NW": 45,
            "Eastbound": 90,
            "9TH ST SE/B @ BARNABY ST SE": 135,
            "SB 15th Ave NW @ NW 80th St": 180,
            "7200 blk Piney Branch Rd NW sw/b": 225,
            "WB": 270,
            "POTOMAC RIVER FWY NW/B @ 25TH ST NW": 315,
            "North": 0,
            "Southbound": 180,
        }
        for text, heading in cases.items():
            with self.subTest(text=text):
                self.assertEqual(bp.heading_for(bp.parse_direction(text)), heading)
        # Không có hướng, hoặc nhiều hướng khác nhau → null (không đoán).
        for text in (None, "", "US 13 @ DIVISION ST", "DC295 SW 0.05 MILE S/O EXIT 1", "6000 Hillen Rd SB and NB", "Light St SB & Pratt St EB"):
            with self.subTest(text=text):
                self.assertIsNone(bp.parse_direction(text))


class NormalizeTests(unittest.TestCase):
    def test_ids_are_stable_across_runs(self):
        for source_id in SOURCES:
            if not os.path.exists(os.path.join(HERE, "fixtures", source_id + ".json")):
                continue
            with self.subTest(source=source_id):
                first, _ = normalize(source_id)
                rows = fixture_rows(source_id)
                random.Random(7).shuffle(rows)
                second, _ = normalize(source_id, rows)
                self.assertTrue(first)
                self.assertEqual(sorted(c["id"] for c in first), sorted(c["id"] for c in second))
                prefix = "%s-%s-" % (SOURCES[source_id]["region"].lower(), source_id)
                for camera in first:
                    self.assertTrue(camera["id"].startswith(prefix))
                    self.assertRegex(camera["id"][len(prefix):], r"^[a-z0-9]+(-[a-z]+b)?(-start|-end)?$")  # -start/-end: 2 đầu đoạn đo tốc độ trung bình

    def test_chicago_row_with_two_approaches_gives_two_cameras(self):
        rows = [row for row in fixture_rows("chi-speed")
                if not bp.is_empty(row.get("first_approach")) and not bp.is_empty(row.get("second_approach"))]
        self.assertTrue(rows, "fixture Chicago phải có dòng 2 approach")
        row = rows[0]
        cameras, _ = normalize("chi-speed", [row])
        self.assertEqual(len(cameras), 2)
        self.assertEqual({(c["lat"], c["lon"]) for c in cameras}, {(round(float(row["latitude"]), 6), round(float(row["longitude"]), 6))})
        expected = {bp.heading_for(bp.parse_direction(row["first_approach"])), bp.heading_for(bp.parse_direction(row["second_approach"]))}
        self.assertEqual({c["heading"] for c in cameras}, expected)
        self.assertEqual(len(expected), 2)
        key = bp.key_part(row["location_id"])
        self.assertEqual({c["id"] for c in cameras},
                         {"us-il-chi-speed-%s-%s" % (key, bp.direction_suffix(bp.parse_direction(row[f]))) for f in ("first_approach", "second_approach")})
        self.assertEqual({c["type"] for c in cameras}, {"speed"})
        self.assertEqual({c["postedLimit"] for c in cameras}, {None})

    def test_dc_drops_stop_sign_and_truck_rows(self):
        rows = fixture_rows("dc-ddot-ase")
        enforcement = {row["ENFORCEMENT_TYPE"] for row in rows}
        self.assertTrue({"Stop Sign", "Truck Restriction"} <= enforcement, "fixture DC phải có dòng stop sign + truck")
        cameras, rejects = normalize("dc-ddot-ase")
        kept_sites = {c["id"].rsplit("-", 1)[1] for c in cameras}
        for row in rows:
            if row["ENFORCEMENT_TYPE"] in ("Stop Sign", "Truck Restriction"):
                self.assertNotIn(str(row["SITE_CODE"]), kept_sites)
        self.assertEqual(rejects["loại không dùng: Stop Sign"], sum(r["ENFORCEMENT_TYPE"] == "Stop Sign" for r in rows))
        self.assertEqual(rejects["loại không dùng: Truck Restriction"], sum(r["ENFORCEMENT_TYPE"] == "Truck Restriction" for r in rows))
        self.assertEqual({c["type"] for c in cameras}, {"speed", "redLight"})
        for camera in cameras:
            self.assertEqual(camera["source"], "openData")
            self.assertEqual(camera["confidence"], 90)  # tier A, ACTIVE_STATUS = Active

    def test_coordinates_outside_state_bbox_are_dropped(self):
        rows = fixture_rows("dc-ddot-ase")
        good, _ = normalize("dc-ddot-ase", rows)
        moved = copy.deepcopy(rows)
        for row in moved:
            row["_lat"], row["_lon"] = 40.7532, -73.9800  # Manhattan, ngoài khung DC
        moved[0]["_lat"], moved[0]["_lon"] = 0, 0
        cameras, rejects = normalize("dc-ddot-ase", moved)
        self.assertTrue(good)
        self.assertEqual(cameras, [])
        self.assertEqual(rejects["toạ độ ngoài khung bang"], len(good) - 1)
        self.assertEqual(rejects["toạ độ bằng 0"], 1)

    def test_status_filters_and_confidence(self):
        # Arlington: bỏ Active=No và dòng có Retired; Active trống → giữ nhưng confidence "không rõ trạng thái".
        rows = fixture_rows("arl-speed")
        cameras, rejects = normalize("arl-speed", rows)
        by_key = {c["id"].rsplit("-", 1)[1]: c for c in cameras}
        for row in rows:
            key = bp.key_part(row["ID"])
            if row["Active"] == "No" or not bp.is_empty(row["Retired"]):
                self.assertNotIn(key, by_key)
            elif row["Active"] == "Yes":
                self.assertEqual(by_key[key]["confidence"], 80)
            else:
                self.assertEqual(by_key[key]["confidence"], 75)
        self.assertTrue(any(k.startswith("không hoạt động") or k.startswith("lọc Retired") for k in rejects))
        # Baltimore red light: tier B không có trạng thái (75), dataset sửa lần cuối > 12 tháng → −10.
        baltimore, _ = normalize("bal-redlight")
        self.assertTrue(baltimore)
        self.assertEqual({c["confidence"] for c in baltimore}, {65})

    def test_limit_and_road_are_never_guessed(self):
        self.assertEqual(bp.parse_limit("35 MPH"), 35)
        self.assertEqual(bp.parse_limit(25), 25)
        self.assertIsNone(bp.parse_limit("35 MPH / 20 MPH during school zone hours"))
        self.assertIsNone(bp.parse_limit("NA"))
        self.assertIsNone(bp.parse_limit(None))
        self.assertEqual(bp.clean_road("3900 BLK GEORGIA AVE NW S/B"), "3900 Blk Georgia Ave NW")
        self.assertEqual(bp.clean_road("N Calvert St @ E Baltimore St NB"), "N Calvert St & E Baltimore St")
        self.assertEqual(bp.clean_road("NY AVE E/B @ BLADENSBURG RD NE"), "NY Ave & Bladensburg Rd NE")
        self.assertEqual(bp.clean_road("CHURCHMANS RD @ I 95 (SB RAMP)", strip_directions=False), "Churchmans Rd & I 95 (SB Ramp)")
        self.assertIsNone(bp.clean_road("NA"))


class MergeTests(unittest.TestCase):
    def test_merges_duplicates_within_30_meters(self):
        cameras, _ = normalize("bal-speed-fixed")
        base = cameras[0]
        near = dict(base, id=base["id"] + "x", lat=round(base["lat"] + 0.00009, 6), confidence=base["confidence"] - 5)  # ~10 m
        opposite = dict(near, id=base["id"] + "y",
                        heading=None if base["heading"] is None else (base["heading"] + 180) % 360)
        far = dict(base, id=base["id"] + "z", lat=round(base["lat"] + 0.0009, 6))  # ~100 m
        self.assertLess(bp.meters_between(base["lat"], base["lon"], near["lat"], near["lon"]), 11)
        tiers = {base["sourceId"]: "B"}
        kept, merged = bp.merge_duplicates([near, base, far], tiers)
        self.assertEqual(merged, {near["id"]: base["id"]})
        self.assertEqual({c["id"] for c in kept}, {base["id"], far["id"]})
        if base["heading"] is not None:
            kept, merged = bp.merge_duplicates([base, opposite], tiers)
            self.assertEqual(len(kept), 2)
        # Confidence bằng nhau → giữ nguồn tier A.
        twin = dict(near, id="us-md-other-1", sourceId="other", confidence=base["confidence"])
        kept, merged = bp.merge_duplicates([base, twin], {base["sourceId"]: "B", "other": "A"})
        self.assertEqual([c["id"] for c in kept], ["us-md-other-1"])


class OutputTests(unittest.TestCase):
    def test_version_changes_only_when_content_changes(self):
        cameras, _ = normalize("dc-ddot-ase")
        with tempfile.TemporaryDirectory() as tmp:
            packs = bp.write_packs({"US-DC": cameras}, {}, tmp, TODAY, "2026-09-27T00:00:00Z")
            self.assertEqual(packs["US-DC"]["version"], 1)
            first = bp.read_json(os.path.join(tmp, "us-dc.v1.json"))
            self.assertEqual(first["region"], "US-DC")
            self.assertEqual(first["unit"], "mph")
            again = bp.write_packs({"US-DC": list(reversed(cameras))}, {"regions": packs}, tmp, dt.date(2026, 10, 4), "2026-10-04T00:00:00Z")
            self.assertEqual(again["US-DC"], packs["US-DC"])
            self.assertEqual(bp.read_json(os.path.join(tmp, "us-dc.v1.json")), first)
            changed = copy.deepcopy(cameras)
            changed[0]["postedLimit"] = 99
            bumped = bp.write_packs({"US-DC": changed}, {"regions": again}, tmp, dt.date(2026, 10, 4), "2026-10-04T00:00:00Z")
            self.assertEqual(bumped["US-DC"]["version"], 2)
            self.assertEqual(sorted(os.listdir(tmp)), ["us-dc.v2.json"])

    def test_regions_json(self):
        template = {"version": 1, "regions": [
            {"code": "US-NY", "name": "New York", "countryCode": "US", "countryName": "United States",
             "status": "full", "cameraCount": 24, "updatedAt": "2026-09-26", "packURL": "packs/us-ny.v0.json", "packVersion": 0},
            {"code": "US-DC", "name": "District of Columbia", "countryCode": "US", "countryName": "United States",
             "status": "full", "cameraCount": 0},
            {"code": "CH", "name": "Switzerland", "countryCode": "CH", "countryName": "Switzerland",
             "status": "blocked", "cameraCount": 0, "legalNote": "Camera warning apps are illegal in Switzerland."},
        ]}
        packs = {"US-DC": {"version": 3, "hash": "x", "file": "packs/us-dc.v3.json", "cameraCount": 282, "updatedAt": "2026-09-27"}}
        sources = [SOURCES["dc-ddot-ase"]]
        info = {"dc-ddot-ase": {"updatedAt": "2026-09-26", "cameraCount": 282}}
        config = bp.build_regions(template, None, packs, sources, info)
        regions = {r["code"]: r for r in config["regions"]}
        self.assertNotIn("packURL", regions["US-NY"])
        self.assertNotIn("packVersion", regions["US-NY"])
        self.assertEqual(regions["US-NY"]["cameraCount"], 0)
        self.assertEqual(regions["US-DC"]["packURL"], "packs/us-dc.v3.json")
        self.assertEqual(regions["US-DC"]["packVersion"], 3)
        self.assertEqual(regions["US-DC"]["cameraCount"], 282)
        self.assertEqual(regions["US-DC"]["coverageNote"], "Washington, DC")
        self.assertEqual(regions["CH"], template["regions"][2])
        self.assertEqual(config["version"], 2)
        dc_source = config["sources"][0]
        self.assertEqual(set(dc_source), {"id", "region", "name", "publisher", "license", "attribution", "landingURL", "updatedAt", "cameraCount"})
        self.assertIn("CC BY 4.0", dc_source["attribution"])
        # Chạy lại, không đổi nội dung → giữ version; đổi → +1.
        self.assertEqual(bp.build_regions(template, config, packs, sources, info)["version"], 2)
        info2 = {"dc-ddot-ase": {"updatedAt": "2026-10-03", "cameraCount": 282}}
        self.assertEqual(bp.build_regions(template, config, packs, sources, info2)["version"], 3)

    def test_fixtures_are_small_real_samples(self):
        for name in os.listdir(os.path.join(HERE, "fixtures")):
            source_id = name[:-len(".json")]
            with self.subTest(fixture=name):
                self.assertIn(source_id, SOURCES)
                raw = fixture(source_id)["raw"]
                items = fixture_rows(source_id) if isinstance(raw, str) else raw["features"] if isinstance(raw, dict) else raw
                if SOURCES[source_id]["format"] == "datex2-predefined-locations":
                    items = {row["id"] for row in items}  # 1 đoạn = 2 dòng (đầu/cuối) → đếm theo location
                self.assertTrue(0 < len(items) <= bp.FIXTURE_ROWS)


class InternationalTests(unittest.TestCase):
    """CR-D2 (docs/04_TECH_SPEC.md mục 12): nguồn ngoài Mỹ, pack km/h, trạng thái pháp lý."""

    def test_utm_to_wgs84_matches_reference_points(self):
        # Giá trị chuẩn: Esri GeometryServer project (EPSG:31983 SIRGAS 2000 / UTM 23S, EPSG:25831 ETRS89 / UTM 31N → 4326).
        cases = [
            ((23, True, 611000, 7796000), (-19.929228672390234, -43.939387597506098)),  # Belo Horizonte
            ((31, False, 430000, 4582000), (41.386483660778822, 2.1627668805099147)),   # Barcelona (Catalonia)
        ]
        for args, (lat, lon) in cases:
            with self.subTest(args=args):
                got_lat, got_lon = bp.utm_to_wgs84(*args)
                self.assertAlmostEqual(got_lat, lat, places=7)
                self.assertAlmostEqual(got_lon, lon, places=7)

    def test_csv_with_decimal_comma_and_wkt_utm(self):
        # Buenos Aires: dấu ";" + dấu phẩy thập phân; chỉ Cinemómetro → speed.
        rows = fixture_rows("caba-fijas")
        speed_rows = [row for row in rows if row["tipo_de_fiscalizador"] == "Cinemómetro"]
        self.assertTrue(speed_rows)
        cameras, rejects = normalize("caba-fijas", rows)
        self.assertEqual(len(cameras), len(speed_rows))
        self.assertEqual(rejects["loại không dùng: Analítica de video"], len(rows) - len(speed_rows))
        row = speed_rows[0]
        self.assertEqual(row["_lat"], float(row["latitud"].replace(",", ".")))
        self.assertLess(row["_lat"], -34)
        self.assertIn(cameras[0]["roadName"], {bp.clean_road(r["ubicación"]) for r in speed_rows})
        self.assertEqual(bp.parse_number("1.234,5", decimal_comma=True), 1234.5)
        self.assertEqual(bp.parse_number("-58,432050", decimal_comma=True), -58.43205)
        # Toạ độ WKT theo UTM (kiểu Belo Horizonte) → WGS84.
        source = {"format": "csv", "csv": {"delimiter": ";"}, "utm": {"zone": 23, "south": True}, "fieldMap": {"wkt": "GEOMETRIA"}}
        parsed = bp.parse_raw(source, "ID;GEOMETRIA\n1;POINT (611000 7796000)\n2;\n")
        self.assertAlmostEqual(parsed[0]["_lat"], -19.9292287, places=6)
        self.assertAlmostEqual(parsed[0]["_lon"], -43.9393876, places=6)
        self.assertEqual((parsed[1]["_lat"], parsed[1]["_lon"]), (None, None))

    def test_quebec_types_french_direction_and_mobile_confidence(self):
        rows = fixture_rows("qc-mtmd")
        cameras, _ = normalize("qc-mtmd", rows)
        by_key = {c["id"].rsplit("-", 1)[1]: c for c in cameras}
        for row in rows:
            camera = by_key[row["urlImage"].rsplit("idSite=", 1)[1]]
            expected_type = SOURCES["qc-mtmd"]["typeMap"]["values"][row["typeAppareil"]]
            self.assertEqual(camera["type"], expected_type)
            self.assertEqual(camera["confidence"], 60 if expected_type == "mobile" else 80)
        headings = {row["description"]: by_key[row["urlImage"].rsplit("idSite=", 1)[1]]["heading"] for row in rows}
        self.assertEqual(headings["Chemin McDougall en direction est, entre Le Boulevard et l'avenue Cedar"], 90)
        # "Rue Sainte-Catherine Est" là tên đường, không phải hướng.
        self.assertIsNone(headings["Rue Sainte-Catherine Est, à l'intersection de la rue D'Iberville"])

    def test_iowa_keeps_only_approved_sites(self):
        rows = fixture_rows("ia-ate")
        self.assertIn("2-Denied", {row["approvalstatus"] for row in rows})
        cameras, rejects = normalize("ia-ate", rows)
        self.assertEqual(len(cameras), sum(row["approvalstatus"] == "1-Approved" for row in rows))
        self.assertEqual(rejects["lọc approvalstatus=2-Denied"], sum(row["approvalstatus"] == "2-Denied" for row in rows))
        for camera in cameras:
            self.assertEqual(camera["confidence"], 60 if camera["type"] == "mobile" else 75)
            self.assertIsNotNone(camera["heading"])  # "(EB)", "(NB)"… trong tên
            self.assertNotIn("(", camera["roadName"])
        layer = {"fields": [{"name": "approvalstatus", "domain": {"codedValues": [{"code": 1, "name": "1-Approved"}, {"code": 2, "name": "2-Denied"}]}}]}
        decoded = bp.decode_coded_values({"features": [{"properties": {"approvalstatus": 1}}]}, layer, ["approvalstatus"])
        self.assertEqual(decoded["features"][0]["properties"]["approvalstatus"], "1-Approved")
        with self.assertRaises(ValueError):
            bp.decode_coded_values({"features": []}, layer, ["fixedormobile"])

    def test_country_pack_is_kmh_and_large_packs_are_compacted(self):
        cameras, _ = normalize("qc-mtmd")
        dc, _ = normalize("dc-ddot-ase")
        with tempfile.TemporaryDirectory() as tmp:
            bp.write_packs({"CA": cameras, "US-DC": dc}, {}, tmp, TODAY, "2026-09-27T00:00:00Z")
            self.assertEqual(bp.read_json(os.path.join(tmp, "ca.v1.json"))["unit"], "kmh")
            self.assertEqual(bp.read_json(os.path.join(tmp, "us-dc.v1.json"))["unit"], "mph")
        self.assertEqual(bp.parse_limit(110, "kmh"), 110)
        self.assertIsNone(bp.parse_limit(110))
        many = [dict(cameras[0], id="ca-x-%d" % i, heading=None, postedLimit=None) for i in range(9000)]
        pack = {"region": "CA", "version": 1, "generatedAt": "2026-09-27T00:00:00Z", "unit": "kmh", "cameras": many}
        self.assertGreater(len(json.dumps(pack, indent=2, ensure_ascii=False).encode("utf-8")), bp.COMPACT_PACK_BYTES)
        text = bp.pack_text(pack)
        self.assertNotIn(": ", text)
        compact = json.loads(text)
        self.assertEqual(set(compact), set(pack))
        self.assertEqual(set(compact["cameras"][0]), {k for k, v in many[0].items() if v is not None})
        self.assertNotIn("heading", compact["cameras"][0])
        huge = [dict(c, roadName="x" * 300) for c in many * 4]
        with self.assertRaises(SystemExit):
            bp.pack_text({"region": "CA", "version": 1, "generatedAt": "2026-09-27T00:00:00Z", "unit": "kmh", "cameras": huge})

    def test_legal_status_is_never_changed_for_restricted_or_blocked_regions(self):
        def entry(code, status, note=None):
            region = {"code": code, "name": code, "countryCode": code, "countryName": code, "status": status, "cameraCount": 0}
            if note:
                region["legalNote"] = note
            return region
        template = {"version": 3, "regions": [
            entry("BE", "restricted", "Legal status under review. Not available yet."),
            entry("LU", "blocked", "Camera warning apps are illegal in Luxembourg. Alerts are disabled here."),
            entry("DE", "restricted", "German law restricts use of camera warnings while driving. Not available yet."),
            entry("SG", "comingSoon", "Not available yet. Coming in a later version."),
            entry("KR", "comingSoon", "Not available yet. Coming in a later version."),
            entry("CA", "full"),
        ]}
        packs = {code: {"version": 1, "hash": "x", "file": "packs/%s.v1.json" % code.lower(), "cameraCount": 10, "updatedAt": "2026-09-27"}
                 for code in ("BE", "LU", "DE", "SG", "CA")}
        config = bp.build_regions(template, None, packs, [], {})
        regions = {r["code"]: r for r in config["regions"]}
        for code, original in zip(("BE", "LU", "DE"), template["regions"][:3]):
            with self.subTest(region=code):
                self.assertEqual(regions[code], original)
                self.assertNotIn("packURL", regions[code])
        self.assertEqual(regions["SG"]["status"], "full")
        self.assertNotIn("legalNote", regions["SG"])
        self.assertEqual(regions["SG"]["packURL"], "packs/sg.v1.json")
        self.assertEqual(regions["KR"], template["regions"][4])  # chưa có pack → giữ comingSoon
        self.assertEqual(regions["CA"]["packURL"], "packs/ca.v1.json")
        for code in ("HK", "AR", "CO"):
            self.assertEqual(regions[code]["status"], "full")


class EuropeTests(unittest.TestCase):
    """CR-D2 phần châu Âu: DATEX II, NVDB, Trafikverket (key), cột cố định Catalonia, đoạn LineString Luxembourg."""

    def test_datex2_tramo_gives_start_and_end_points(self):
        rows = fixture_rows("es-dgt-radares")
        cameras, rejects = normalize("es-dgt-radares", rows)
        self.assertFalse(rejects)
        by_id = {c["id"]: c for c in cameras}
        start, end = by_id["es-es-dgt-radares-cvm161274-start"], by_id["es-es-dgt-radares-cvm161274-end"]
        self.assertEqual((start["lat"], start["lon"]), (41.6088, -0.915697))  # <from>
        self.assertEqual((end["lat"], end["lon"]), (41.6192, -0.9496))        # <to>
        for camera in (start, end):
            self.assertEqual(camera["type"], "speed")
            self.assertTrue(camera["roadName"].startswith("Z-40 km "))
            self.assertTrue(camera["roadName"].endswith(bp.SECTION_SUFFIX))
        point = by_id["es-es-dgt-radares-cabinacinemometro120001"]
        self.assertEqual(point["roadName"], "A-2 km 202.33")
        self.assertIsNone(point["heading"])  # DATEX II chỉ có "positive/negative" theo lý trình, không phải la bàn
        self.assertEqual(point["lastConfirmedAt"], "2025-12-18T00:00:00Z")  # publicationTime có múi giờ +01:00
        self.assertEqual(len(cameras), len(rows))

    def test_missing_key_skips_source_without_network(self):
        source = SOURCES["se-trv-atk"]
        self.assertEqual(source["apiKeyEnv"], "TRAFIKVERKET_API_KEY")
        saved_get, saved_env = bp._http_get, os.environ.pop("TRAFIKVERKET_API_KEY", None)

        def no_network(*args, **kwargs):
            raise AssertionError("không được gọi mạng khi thiếu key")
        bp._http_get = no_network
        try:
            with self.assertRaises(bp.MissingKey) as caught:
                bp.fetch_source(source, offline=False)
            self.assertEqual(str(caught.exception), "TRAFIKVERKET_API_KEY")
            # Có key trong file local → đọc vào env; biến đã có thì không bị ghi đè.
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "keys.env")
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("# local\nTRAFIKVERKET_API_KEY='abc123'\nDATA_GO_KR_KEY=\n")
                os.environ["DATA_GO_KR_KEY"] = "from-ci"
                bp.load_local_keys(path)
                self.assertEqual(bp.source_api_key(source), "abc123")
                self.assertEqual(os.environ["DATA_GO_KR_KEY"], "from-ci")
        finally:
            bp._http_get = saved_get
            os.environ.pop("TRAFIKVERKET_API_KEY", None)
            os.environ.pop("DATA_GO_KR_KEY", None)
            if saved_env is not None:
                os.environ["TRAFIKVERKET_API_KEY"] = saved_env
        result = {"id": "se-trv-atk", "region": "SE", "tier": "A", "status": "nokey", "error": "TRAFIKVERKET_API_KEY",
                  "rows": None, "cameras": None, "rejects": {}}
        report = bp.render_report(TODAY, [result], {}, {}, {}, {"se-trv-atk": 0}, "")
        self.assertIn("skipped: no key (TRAFIKVERKET_API_KEY)", report)

    def test_trafikverket_bearing_is_camera_aim_so_heading_is_opposite(self):
        rows = fixture_rows("se-trv-atk")
        deleted = dict(rows[0], Deleted=True, Id="deleted-1")
        cameras, rejects = normalize("se-trv-atk", rows + [deleted])
        self.assertEqual(rejects["lọc Deleted=True"], 1)
        by_key = {c["id"].rsplit("-", 1)[1]: c for c in cameras}
        for row in rows:
            camera = by_key[row["Id"]]
            self.assertEqual(camera["heading"], (row["Bearing"] + 180) % 360)
            number = row["RoadNumber"]
            self.assertTrue(camera["roadName"].startswith(("Väg " + number) if number.isdigit() else number))

    def test_nvdb_wkt_is_lat_lon_and_attribution_is_verbatim(self):
        rows = fixture_rows("no-nvdb-atk")
        cameras, rejects = normalize("no-nvdb-atk", rows)
        self.assertEqual(len(cameras), len(rows))
        self.assertFalse(rejects)
        for camera in cameras:
            self.assertTrue(57.9 < camera["lat"] < 71.2 and 4.4 < camera["lon"] < 31.2)
            self.assertIsNone(camera["heading"])  # "Med/Mot metreringsretning" không phải la bàn
            self.assertNotRegex(camera["roadName"], r"\([A-Z]\d\)")
            self.assertRegex(camera["roadName"], r"^(E|Rv|Fv|Kv)\d+")
        parsed = bp.parse_nvdb_objects([{"id": 1, "egenskaper": [], "geometri": {"wkt": "POINT(61.55059135 5.6873376)"}},
                                        {"id": 2, "egenskaper": [], "geometri": {"wkt": "POINT Z (61.5505745 5.68728513 139.3)"}}])
        self.assertEqual([(r["_lat"], r["_lon"]) for r in parsed], [(61.55059135, 5.6873376), (61.5505745, 5.68728513)])
        self.assertEqual(SOURCES["no-nvdb-atk"]["attribution"], "Inneholder data under NLOD tilgjengeliggjort av Statens vegvesen")
        self.assertEqual(SOURCES["no-nvdb-atk"]["headers"], {"X-Client": "Speedwise"})

    def test_catalonia_fixed_width_utm_with_limit_and_broken_rows_dropped(self):
        rows = fixture_rows("es-cat-radars")
        cameras, _ = normalize("es-cat-radars", rows)
        self.assertEqual(len(cameras), len(rows))
        first = next(c for c in cameras if c["roadName"] == "A-2 km 445,35")
        self.assertEqual(first["postedLimit"], 120)
        self.assertTrue(40.5 < first["lat"] < 42.9 and 0.1 < first["lon"] < 3.4)
        # Dòng nguồn mất dấu thập phân (B-10, toạ độ UTM vô lý) → loại, không sửa tay.
        text = fixture("es-cat-radars")["raw"] + "B-10        18,5        80          42552972    457695385   \n"
        broken_rows = bp.parse_raw(SOURCES["es-cat-radars"], text)
        _, rejects = normalize("es-cat-radars", broken_rows)
        self.assertEqual(rejects["thiếu toạ độ"], 1)

    def test_luxembourg_linestring_section_gives_two_points(self):
        raw = fixture("lu-geoportail-radars")["raw"]
        line = next(f for f in raw["features"] if f["geometry"]["type"] == "LineString")
        cameras, _ = normalize("lu-geoportail-radars")
        section = sorted((c for c in cameras if c["id"].startswith("lu-lu-geoportail-radars-%s-" % line["properties"]["ID"])),
                         key=lambda c: c["id"])
        self.assertEqual([c["id"].rsplit("-", 1)[1] for c in section], ["end", "start"])
        coords = line["geometry"]["coordinates"]
        self.assertEqual((section[1]["lon"], section[1]["lat"]), (round(coords[0][0], 6), round(coords[0][1], 6)))
        self.assertEqual((section[0]["lon"], section[0]["lat"]), (round(coords[-1][0], 6), round(coords[-1][1], 6)))
        for camera in section:
            self.assertEqual(camera["roadName"], line["properties"]["TRANCON"] + bp.SECTION_SUFFIX)
        points = [f for f in raw["features"] if f["geometry"]["type"] == "Point"]
        self.assertEqual(len(cameras), len(points) + 2)


class AsiaPacificTests(unittest.TestCase):
    """CR-D2 phần châu Á – Thái Bình Dương: data.gov.sg, CSDI Hong Kong (PopupInfo), Đài Loan, Úc, data.go.kr (tắt, chờ key)."""

    def test_hong_kong_popup_attributes_direction_and_housing_confidence(self):
        rows = fixture_rows("hk-td-rlc")
        self.assertEqual(rows[0]["SITE_DESC_ENG"], "QUEEN'S ROAD E. (WEST BOUND) AT JUNCTION WITH QUEENSWAY")
        cameras, rejects = normalize("hk-td-rlc", rows)
        self.assertFalse(rejects)
        first = next(c for c in cameras if c["id"] == "hk-hk-td-rlc-1")
        self.assertEqual(first["heading"], 270)  # "(WEST BOUND)"
        self.assertEqual(first["roadName"], "Queen's Road E. & Queensway")
        latest = max(row["LAST_UPD_DATE"] for row in rows)  # "YYYYMMDD"
        self.assertEqual(first["lastConfirmedAt"], "%s-%s-%sT00:00:00Z" % (latest[:4], latest[4:6], latest[6:]))
        housing_rows = fixture_rows("hk-td-sec")
        housings, _ = normalize("hk-td-sec", housing_rows)
        stale = (TODAY - bp.parse_date(max(row["LAST_UPD_DATE"] for row in housing_rows))).days > bp.STALE_DAYS
        # Camera luân phiên giữa các hộp (mục 12.3) → 70; dữ liệu cũ > 12 tháng trừ 10 như mọi nguồn.
        self.assertEqual({c["confidence"] for c in housings}, {70 - (bp.STALE_PENALTY if stale else 0)})
        self.assertEqual({c["type"] for c in housings}, {"speed"})
        self.assertEqual(bp.popup_fields("<tr><th>SEC_ID</th>\n<td>7</td></tr><th>SITE_DESC_ENG</th><td>A &amp; B</td>"),
                         {"SEC_ID": "7", "SITE_DESC_ENG": "A & B"})
        self.assertEqual(bp.parse_date("20161230201814"), dt.date(2016, 12, 30))
        self.assertEqual(bp.parse_date("20220121"), dt.date(2022, 1, 21))

    def test_singapore_types_towards_road_and_rate_limit_retry(self):
        cameras, _ = normalize("sg-spf-speed")
        by_type = {c["type"] for c in cameras}
        self.assertEqual(by_type, {"speed", "mobile"})
        for camera in cameras:
            self.assertIsNone(camera["heading"])  # "towards <đường>" không phải la bàn
            if camera["type"] == "mobile":
                self.assertEqual(camera["confidence"], 50)  # 60 (điểm mobile) − 10 (dataset 2024-06-06 cũ > 12 tháng)
        fixed, _ = normalize("sg-spf-fixed")
        self.assertIn("Yishun Avenue 2 · towards Lentor Avenue", {c["roadName"] for c in fixed})
        # Bị giới hạn tốc độ (code 24) → chờ rồi gọi lại, không gọi mạng thật.
        replies = [{"code": 24, "name": "TOO_MANY_REQUESTS"}, {"code": 0, "data": {"url": "https://s3.example/x.geojson"}},
                   {"type": "FeatureCollection", "features": []}]
        calls = []
        saved_get, saved_wait = bp.http_get_json, bp.DATAGOVSG_WAIT_SECONDS
        bp.http_get_json = lambda url, *args, **kwargs: calls.append(url) or replies.pop(0)
        bp.DATAGOVSG_WAIT_SECONDS = 0
        try:
            raw = bp.fetch_datagovsg_poll_download("https://api-open.data.gov.sg/v1/public/api/datasets/d_x/poll-download")
        finally:
            bp.http_get_json, bp.DATAGOVSG_WAIT_SECONDS = saved_get, saved_wait
        self.assertEqual(raw["features"], [])
        self.assertEqual(calls[-1], "https://s3.example/x.geojson")
        self.assertEqual(len(calls), 3)

    def test_taiwan_chinese_directions_limits_and_header_row(self):
        rows = fixture_rows("tw-npa-speed")
        cameras, rejects = normalize("tw-npa-speed", rows)
        self.assertEqual(rejects["lọc CityName=設置縣市"], 1)  # dòng thứ 2 của file là mô tả cột
        self.assertEqual(len(cameras), len(rows) - 1)
        words = SOURCES["tw-npa-speed"]["directionWords"]
        # 拍攝方向 là hướng xe chạy: đối chiếu quốc lộ, "往南" luôn đi cùng "南向" (southbound) trong địa chỉ.
        cases = {"北向南": 180, "南向北": 0, "往南": 180, "西南向東北": 45, "東向西(超速闖紅燈)": 270,
                 "雙向": None, "南北雙向": None, "南向60北向70": None, "往大溪方向": None, "南向北(區間測速) 北向南(區間測速)": None}
        for text, heading in cases.items():
            with self.subTest(direct=text):
                self.assertEqual(bp.heading_for(bp.parse_direction(text, words)), heading)
        self.assertEqual(bp.parse_limit("40公里", "kmh"), 40)
        self.assertIsNone(bp.parse_limit("80公里（20噸以上大貨車限速70公里）", "kmh"))

    def test_new_taipei_two_way_section_gives_start_and_end_per_direction(self):
        rows = fixture_rows("tw-ntpc-section")
        cameras, rejects = normalize("tw-ntpc-section", rows)
        self.assertFalse(rejects)
        by_id = {c["id"]: c for c in cameras}
        # seqno 1 "(雙向)": 2 chiều → 4 điểm; seqno 5 một chiều "西向東" → 2 điểm, heading 90.
        for key in ("1d1-start", "1d1-end", "1d2-start", "1d2-end", "5-start", "5-end"):
            self.assertIn("tw-tw-ntpc-section-" + key, by_id)
        self.assertEqual((by_id["tw-tw-ntpc-section-1d2-start"]["lat"], by_id["tw-tw-ntpc-section-1d2-start"]["lon"]), (24.953133, 121.598102))
        self.assertEqual(by_id["tw-tw-ntpc-section-5-end"]["heading"], 90)
        self.assertIsNone(by_id["tw-tw-ntpc-section-1d1-start"]["heading"])
        self.assertEqual(by_id["tw-tw-ntpc-section-1d1-start"]["postedLimit"], 40)
        for camera in cameras:
            self.assertTrue(camera["roadName"].endswith(bp.SECTION_SUFFIX))
        broken = bp.section_rows({"start latitude": "1 2", "start longitude": "3", "end latitude": "", "end longitude": ""},
                                 SOURCES["tw-ntpc-section"]["sectionFields"])
        self.assertEqual([(r["_lat"], r["_lon"]) for r in broken], [(None, None)])  # số giá trị lệch nhau → không đoán

    def test_australia_act_decommissioned_and_nsw_second_camera(self):
        rows = fixture_rows("au-act-cameras")
        gone = dict(rows[0], camera_location_code="9999", decommissioned_camera_date="2020-01-23T00:00:00.000")
        cameras, rejects = normalize("au-act-cameras", rows + [gone])
        self.assertEqual(rejects["lọc decommissioned_camera_date=2020-01-23T00:00:00.000"], 1)
        by_key = {c["id"].rsplit("-", 1)[1]: c for c in cameras}
        self.assertEqual((by_key["0001a"]["type"], by_key["0001a"]["confidence"]), ("mobile", 60))
        self.assertEqual(by_key["1001"]["type"], "combined")
        self.assertEqual(by_key["20022003"]["heading"], 270)  # "HINDMARSH DRIVE WESTBOUND …"
        school = fixture_rows("au-nsw-school")
        with_second = [row for row in school if row.get("_keySuffix") == "p2"]
        self.assertEqual(len(with_second), sum(1 for f in fixture("au-nsw-school")["raw"]["features"] if f["properties"]["lat_2"] is not None))
        nsw, _ = normalize("au-nsw-school", school)
        self.assertEqual({c["type"] for c in nsw}, {"schoolZone"})
        self.assertEqual({c["confidence"] for c in nsw}, {70})  # 80 (không có trạng thái) − 10 (dữ liệu 2021)
        self.assertIn("au-au-nsw-school-184p2", {c["id"] for c in nsw})

    def test_korea_api_is_disabled_until_key_and_parses_sections(self):
        source = SOURCES["kr-datagokr-cameras"]
        self.assertFalse(source["enabled"])
        self.assertEqual(source["apiKeyEnv"], "DATA_GO_KR_KEY")
        items = [{"latitude": "34.9271974", "longitude": "127.7044802", "regltSe": "1", "lmttVe": "60", "roadRouteNm": "제철로",
                  "itlpc": "이순신대교 시점 2차로 (여수방면)", "regltSctnLcSe": "1", "ovrspdRegltSctnLt": "3.3", "referenceDate": "2026-07-29"},
                 {"latitude": "35.2071", "longitude": "127.4636", "regltSe": "01+02", "lmttVe": "50", "roadRouteNm": "섬진강대로",
                  "itlpc": "식자재마트앞", "regltSctnLcSe": "2", "ovrspdRegltSctnLt": "0", "referenceDate": "2026-07-01"},
                 {"latitude": "35.2997108", "longitude": "126.78626", "regltSe": "4", "lmttVe": "0", "roadRouteNm": "제봉로",
                  "itlpc": "중앙초등학교 앞", "regltSctnLcSe": "", "ovrspdRegltSctnLt": "", "referenceDate": "2026-08-03"}]
        response = {"response": {"header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                                 "body": {"items": items, "totalCount": "3", "numOfRows": "1000", "pageNo": "1"}}}
        parsed, total = bp.datagokr_items(response)
        self.assertEqual((len(parsed), total), (3, 3))
        self.assertEqual(bp.datagokr_items({"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": items[0]}, "totalCount": 1}}})[0], [items[0]])
        with self.assertRaises(ValueError):
            bp.datagokr_items({"OpenAPI_ServiceResponse": {"cmmMsgHeader": {"errMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"}}})
        rows = bp.parse_raw(source, items)
        cameras, rejects = bp.normalize_source(source, rows, bp.dataset_date_from(source, None, rows), TODAY, BBOXES)
        self.assertEqual(rejects["loại không dùng: 4"], 1)  # 4 = camera đỗ xe
        start = next(c for c in cameras if c["type"] == "speed")
        self.assertTrue(start["id"].endswith("-start"))  # 1 = 시점, đoạn dài 3.3 km
        self.assertEqual((start["postedLimit"], start["roadName"]), (60, "제철로 · 이순신대교 시점 2차로 (여수방면)" + bp.SECTION_SUFFIX))
        combined = next(c for c in cameras if c["type"] == "combined")
        self.assertFalse(combined["roadName"].endswith(bp.SECTION_SUFFIX))  # mã 2 nhưng độ dài 0 → camera điểm
        # Nguồn đang dùng: nút "tải file" của cùng dataset (không key) — trường viết hoa, cùng bảng mã.
        download = SOURCES["kr-std"]
        self.assertTrue(download["enabled"])
        cameras, rejects = normalize("kr-std")
        self.assertTrue(cameras)
        for camera in cameras:
            self.assertIn(camera["type"], {"speed", "redLight", "combined"})
            self.assertTrue(33.1 <= camera["lat"] <= 38.62 and 124.6 <= camera["lon"] <= 131.88)
        header = {"totalCount": 3, "tableVO": {"svcTableNm": "tn_x", "colNmList": ["LATITUDE", "LONGITUDE"]}}
        pages = [header, [{"LATITUDE": "35.1"}, {"LATITUDE": "35.2"}], [{"LATITUDE": "35.3"}]]
        urls = []
        saved_get, saved_page, saved_wait = bp.http_get_json, bp.DATAGOKR_DOWNLOAD_PAGE, bp.DATAGOKR_MIN_INTERVAL
        bp.http_get_json = lambda url, *args, **kwargs: urls.append(url) or pages.pop(0)
        bp.DATAGOKR_DOWNLOAD_PAGE, bp.DATAGOKR_MIN_INTERVAL = 2, 0
        try:
            rows = bp.fetch_datagokr_std_download("https://www.data.go.kr/download", "15028200")
        finally:
            bp.http_get_json, bp.DATAGOKR_DOWNLOAD_PAGE, bp.DATAGOKR_MIN_INTERVAL = saved_get, saved_page, saved_wait
        self.assertEqual(len(rows), 3)
        self.assertEqual(urls[0], "https://www.data.go.kr/download/columList.json?pk=15028200&ext=JSON")
        self.assertIn("page=2", urls[2])
        self.assertIn("colNmList=LATITUDE&colNmList=LONGITUDE", urls[1])
        saved = os.environ.pop("DATA_GO_KR_KEY", None)
        try:
            with self.assertRaises(bp.MissingKey):
                bp.fetch_source(source, offline=False)
        finally:
            if saved is not None:
                os.environ["DATA_GO_KR_KEY"] = saved


if __name__ == "__main__":
    unittest.main()
