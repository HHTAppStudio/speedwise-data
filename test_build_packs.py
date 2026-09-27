"""Test cho build_packs.py — chỉ dùng fixtures/ (dòng thật lưu từ lần tải đầu), không gọi mạng.

Chạy: python3 -m unittest -v
"""

import copy
import datetime as dt
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
                    self.assertRegex(camera["id"][len(prefix):], r"^[a-z0-9]+(-[a-z]+b)?$")

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
                items = raw["features"] if isinstance(raw, dict) else raw
                self.assertTrue(0 < len(items) <= bp.FIXTURE_ROWS)


if __name__ == "__main__":
    unittest.main()
