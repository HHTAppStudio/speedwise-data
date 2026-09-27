# REPORT — Speedwise data pipeline

Lần chạy: 2026-09-27 (UTC). Sinh tự động bởi `build_packs.py` — đừng sửa phần trên dòng đánh dấu.

## Nguồn

| Nguồn | Bang | Tier | Tải | Ngày dataset | Dòng | Camera | Vào pack | Bị loại (lý do) |
|---|---|---|---|---|---:|---:|---:|---|
| `dc-ddot-ase` | US-DC | A | OK | 2026-09-26 | 327 | 283 | 282 | loại không dùng: Stop Sign: 34; loại không dùng: Truck Restriction: 10; gộp trùng ≤ 30 m: 1 |
| `chi-speed` | US-IL | A | OK | 2026-08-25 | 209 | 326 | 326 | — |
| `chi-redlight` | US-IL | A | OK | 2026-09-15 | 300 | 300 | 299 | gộp trùng ≤ 30 m: 1 |
| `moco-speed` | US-MD | A | OK | 2026-07-01 | 785 | 151 | 148 | kỳ cũ hơn quarter_name: 559; toạ độ bằng 0: 54; thiếu toạ độ: 21; gộp trùng ≤ 30 m: 3 |
| `moco-redlight` | US-MD | A | OK | 2026-07-01 | 190 | 39 | 38 | kỳ cũ hơn quarter_name: 134; toạ độ bằng 0: 17; gộp trùng ≤ 30 m: 1 |
| `sf-speed` | US-CA | A | OK | 2026-08-25 | 56 | 56 | 56 | — |
| `sf-redlight` | US-CA | A | OK | 2026-08-18 | 19 | 18 | 18 | trùng id trong nguồn: 1 |
| `nola-cams` | US-LA | A | OK | 2024-11-28 | 103 | 38 | 38 | không hoạt động: active=No: 61; trùng id trong nguồn: 4 |
| `sea-atsc` | US-WA | B | OK | 2026-08-05 | 114 | 100 | 100 | loại không dùng: Block-the-Box: 8; loại không dùng: Transit Lane: 6 |
| `bal-redlight` | US-MD | B | OK | 2025-05-07 | 180 | 180 | 180 | — |
| `bal-speed-fixed` | US-MD | B | OK | 2026-02-17 | 21 | 21 | 21 | — |
| `bal-speed-portable` | US-MD | B | OK | 2026-05-28 | 128 | 128 | 128 | — |
| `arl-speed` | US-VA | B | OK | 2026-09-26 | 47 | 35 | 35 | không hoạt động: Active=No: 2; lọc Retired=1745899200000: 2; lọc Retired=1747281600000: 2; lọc Retired=1756094400000: 2; lọc Retired=1757908800000: 2; lọc Retired=1742443200000: 1; lọc Retired=1757649600000: 1 |
| `tac-ae` | US-WA | B | OK | 2026-09-26 | 23 | 22 | 22 | trùng id trong nguồn: 1 |
| `bel-speed` | US-WA | B | OK | 2026-08-26 | 14 | 8 | 5 | không hoạt động: OperationalStatus=Planned: 6; gộp trùng ≤ 30 m: 3 |
| `de-redlight` | US-DE | B | OK | — | 60 | 60 | 60 | — |

## Theo bang

| Bang | Pack | Version | Camera | speed | redLight | schoolZone |
|---|---|---:|---:|---:|---:|---:|
| US-CA | `packs/us-ca.v1.json` | 1 | 74 | 56 | 18 | 0 |
| US-DC | `packs/us-dc.v1.json` | 1 | 282 | 221 | 61 | 0 |
| US-DE | `packs/us-de.v1.json` | 1 | 60 | 0 | 60 | 0 |
| US-IL | `packs/us-il.v1.json` | 1 | 625 | 326 | 299 | 0 |
| US-LA | `packs/us-la.v1.json` | 1 | 38 | 2 | 6 | 30 |
| US-MD | `packs/us-md.v1.json` | 1 | 515 | 148 | 218 | 149 |
| US-VA | `packs/us-va.v1.json` | 1 | 35 | 0 | 0 | 35 |
| US-WA | `packs/us-wa.v1.json` | 1 | 127 | 14 | 39 | 74 |

**Tổng: 1756 camera ở 8 bang/khu vực.**

<!-- PHẦN VIẾT TAY: build_packs.py giữ nguyên mọi thứ bên dưới dòng này -->



## Kiểm tra vị trí (2026-09-27)

Chọn ngẫu nhiên 3 camera DC + 3 camera Chicago (seed 20260927), tra ngược toạ độ bằng CLGeocoder của Apple (cùng dữ liệu với Apple Maps), so với `roadName`. Bấm link để mở Apple Maps.

| Camera | Loại / hướng | `roadName` | Apple trả về | Kết quả |
|---|---|---|---|---|
| [`us-dc-dc-ddot-ase-1569`](https://maps.apple.com/?ll=38.917398,-76.975407&q=us-dc-dc-ddot-ase-1569) | speed / 270 | 1800 Blk New York Ave NE | 1850 New York Ave NE, Washington | ✅ đúng đoạn đường |
| [`us-dc-dc-ddot-ase-2502`](https://maps.apple.com/?ll=38.917181,-76.973158&q=us-dc-dc-ddot-ase-2502) | redLight / 90 | NY Ave & Bladensburg Rd NE | 2245–2265 New York Ave NE, Washington | ✅ đúng giao lộ (NY Ave tại Bladensburg Rd) |
| [`us-dc-dc-ddot-ase-1726`](https://maps.apple.com/?ll=38.882735,-76.9341&q=us-dc-dc-ddot-ase-1726) | speed / 135 | 4800 Blk Benning Rd SE | 4801 Benning Rd SE, Washington | ✅ đúng đoạn đường |
| [`us-il-chi-redlight-3553nharlemave-nb`](https://maps.apple.com/?ll=41.94499,-87.80689&q=us-il-chi-redlight-3553nharlemave-nb) | redLight / 0 | 3553 N Harlem Ave | 3555 N Harlem Ave, Chicago | ✅ |
| [`us-il-chi-redlight-2411w63rdst-eb`](https://maps.apple.com/?ll=41.77917,-87.68406&q=us-il-chi-redlight-2411w63rdst-eb) | redLight / 90 | 2411 W 63rd St | 2413 W 63rd St, Chicago | ✅ |
| [`us-il-chi-redlight-25nciceroave-nb`](https://maps.apple.com/?ll=41.88157,-87.74521&q=us-il-chi-redlight-25nciceroave-nb) | redLight / 0 | 25 N Cicero Ave | 4759 W Washington Blvd, Chicago | ✅ góc Cicero Ave & Washington Blvd (25 N Cicero nằm ngay giao lộ này) |

Kết quả: 6/6 đúng đường/giao lộ.

## Ghi chú dữ liệu

- Máy ở Việt Nam bị Socrata (Chicago, Montgomery, SF, New Orleans) chặn 403 theo IP; chạy qua VPN Mỹ thì bình thường. GitHub Actions (máy Mỹ) không bị.
- Montgomery County: quý mới nhất là 2024 Q4; 75 site có toạ độ 0/trống → bị loại (không geocode, không lấy từ nguồn khác).
- New Orleans: portal ghi "may not reflect accurate location information"; dataset cập nhật lần cuối 2024-11-28 (> 12 tháng) → confidence 60 − 10 = 50. Mã `function`: `RLC` → redLight; `FS` → speed (không có trường học/giờ school zone); `TFS` → schoolZone (luôn có `school_hour`). 4 dòng trùng `camid` (cùng camera ghi 2 lần) → giữ 1.
- Bellevue: 8 camera "In Service" là 4 cặp a/b cùng vị trí, không có trường hướng → gộp còn 5 (heading null, cảnh báo cả 2 chiều).
- Delaware: không có ngày cập nhật dataset → `lastConfirmedAt` null.
- DC: ngày dataset lấy từ item ArcGIS Online `03d94dc6579949ae9d7c9dd8ffebeb89` (layer MapServer không có `editingInfo`). Arlington: lấy `GeoSyncDate` lớn nhất.
