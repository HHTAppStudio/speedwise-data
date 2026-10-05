# REPORT — Speedwise data pipeline

Lần chạy: 2026-10-05 (UTC). Sinh tự động bởi `build_packs.py` — đừng sửa phần trên dòng đánh dấu.

## Nguồn

| Nguồn | Vùng | Tier | Tải | Ngày dataset | Dòng | Camera | Vào pack | Bị loại (lý do) |
|---|---|---|---|---|---:|---:|---:|---|
| `dc-ddot-ase` | US-DC | A | OK | 2026-10-04 | 327 | 283 | 282 | loại không dùng: Stop Sign: 34; loại không dùng: Truck Restriction: 10; gộp trùng ≤ 30 m: 1 |
| `chi-speed` | US-IL | A | OK | 2026-08-25 | 209 | 326 | 326 | — |
| `chi-redlight` | US-IL | A | OK | 2026-09-15 | 300 | 300 | 299 | gộp trùng ≤ 30 m: 1 |
| `moco-speed` | US-MD | A | OK | 2026-10-01 | 785 | 151 | 148 | kỳ cũ hơn quarter_name: 559; toạ độ bằng 0: 54; thiếu toạ độ: 21; gộp trùng ≤ 30 m: 3 |
| `moco-redlight` | US-MD | A | OK | 2026-10-01 | 190 | 39 | 38 | kỳ cũ hơn quarter_name: 134; toạ độ bằng 0: 17; gộp trùng ≤ 30 m: 1 |
| `sf-speed` | US-CA | A | OK | 2026-08-25 | 56 | 56 | 56 | — |
| `sf-redlight` | US-CA | A | OK | 2026-09-29 | 19 | 18 | 18 | trùng id trong nguồn: 1 |
| `nola-cams` | US-LA | A | OK | 2024-11-28 | 103 | 38 | 38 | không hoạt động: active=No: 61; trùng id trong nguồn: 4 |
| `sea-atsc` | US-WA | B | OK | 2026-08-05 | 114 | 100 | 100 | loại không dùng: Block-the-Box: 8; loại không dùng: Transit Lane: 6 |
| `bal-redlight` | US-MD | B | OK | 2025-05-07 | 180 | 180 | 180 | — |
| `bal-speed-fixed` | US-MD | B | OK | 2026-02-17 | 21 | 21 | 21 | — |
| `bal-speed-portable` | US-MD | B | OK | 2026-05-28 | 128 | 128 | 128 | — |
| `arl-speed` | US-VA | B | OK | 2026-10-05 | 46 | 35 | 35 | không hoạt động: Active=No: 2; lọc Retired=1745899200000: 2; lọc Retired=1747281600000: 2; lọc Retired=1757908800000: 2; lọc Retired=1742443200000: 1; lọc Retired=1756094400000: 1; lọc Retired=1757649600000: 1 |
| `tac-ae` | US-WA | B | OK | 2026-10-04 | 23 | 22 | 22 | trùng id trong nguồn: 1 |
| `bel-speed` | US-WA | B | OK | 2026-09-28 | 14 | 8 | 5 | không hoạt động: OperationalStatus=Planned: 6; gộp trùng ≤ 30 m: 3 |
| `de-redlight` | US-DE | B | OK | — | 60 | 60 | 60 | — |
| `nyc-dof-derived` | US-NY | A-derived | OK | 2026-08-27 | 2763 | 2763 | 2763 | — |
| `qc-mtmd` | CA | A | OK | 2026-09-10 | 160 | 160 | 160 | — |
| `tor-rlc` | CA | A | OK | 2026-10-03 | 301 | 301 | 295 | gộp trùng ≤ 30 m: 6 |
| `ott-rlc` | CA | A | OK | 2026-08-12 | 88 | 86 | 86 | thiếu toạ độ: 2 |
| `york-rlc` | CA | A | OK | 2025-08-01 | 55 | 55 | 55 | — |
| `ham-rlc` | CA | A | OK | 2026-10-03 | 51 | 51 | 51 | — |
| `peel-rlc` | CA | A | OK | 2026-03-05 | 37 | 37 | 37 | — |
| `king-rlc` | CA | A | OK | 2025-01-09 | 7 | 7 | 7 | — |
| `edm-isd` | CA | A | OK | 2026-10-05 | 67 | 67 | 67 | — |
| `cal-isc` | CA | A | OK | 2026-10-01 | 57 | 57 | 57 | — |
| `ia-ate` | US-IA | B | OK | — | 348 | 156 | 156 | lọc approvalstatus=2-Denied: 192 |
| `caba-fijas` | AR | A | OK | — | 224 | 94 | 90 | loại không dùng: Analítica de video: 95; trùng id trong nguồn: 35; gộp trùng ≤ 30 m: 4 |
| `antt-radares` | BR | A | OK | 2026-08-28 | 1256 | 1122 | 1080 | trùng id trong nguồn: 134; gộp trùng ≤ 30 m: 42 |
| `bh-fiscalizacao` | BR | A | OK | 2026-09-15 | 447 | 396 | 219 | gộp trùng ≤ 30 m: 177; loại không dùng: Detector de Conversão-Retorno em local Proibido: 28; loại không dùng: Detector de Invasão de Faixa de Exclusiva - MOVE: 23 |
| `bog-salvavidas` | CO | A | OK | 2026-08-24 | 128 | 44 | 40 | lọc ESTADO_PUNTO=Desmontada - novedad: 53; loại không dùng: C14, C32: 23; lọc ESTADO_PUNTO=None: 8; gộp trùng ≤ 30 m: 4 |
| `es-dgt-radares` | ES | A | OK | 2025-12-18 | 784 | 784 | 722 | gộp trùng ≤ 30 m: 62 |
| `es-cat-radars` | ES | A | OK | — | 247 | 230 | 230 | thiếu toạ độ: 16; toạ độ ngoài khung bang: 1 |
| `no-nvdb-atk` | NO | A | OK | 2026-10-04 | 461 | 461 | 438 | gộp trùng ≤ 30 m: 23 |
| `se-trv-atk` | SE | A | OK | 2026-10-02 | 2795 | 2795 | 2795 | — |
| `be-bxl-speedcameras` | BE | A | OK | — | 132 | 132 | 129 | gộp trùng ≤ 30 m: 3 |
| `lu-geoportail-radars` | LU | A | OK | 2024-10-24 | 45 | 45 | 45 | — |
| `de-ka-blitzer` | DE | A | OK | 2025-02-19 | 37 | 37 | 33 | gộp trùng ≤ 30 m: 4 |
| `sg-spf-speed` | SG | A | OK | 2024-06-06 | 91 | 91 | 47 | gộp trùng ≤ 30 m: 44 |
| `sg-spf-fixed` | SG | A | OK | 2025-11-13 | 20 | 20 | 11 | gộp trùng ≤ 30 m: 9 |
| `sg-spf-redlight` | SG | A | OK | 2025-11-13 | 240 | 240 | 0 | gộp trùng ≤ 30 m: 240 |
| `sg-spf-dtrls` | SG | A | OK | 2025-12-02 | 240 | 240 | 235 | gộp trùng ≤ 30 m: 5 |
| `hk-td-rlc` | HK | A | OK | 2026-06-26 | 230 | 230 | 222 | gộp trùng ≤ 30 m: 8 |
| `hk-td-sec` | HK | A | OK | 2026-06-16 | 164 | 164 | 164 | — |
| `tw-npa-speed` | TW | A | OK | 2026-10-05 | 1896 | 1890 | 1885 | gộp trùng ≤ 30 m: 5; trùng id trong nguồn: 4; lọc CityName=設置縣市: 1; toạ độ ngoài khung bang: 1 |
| `tw-ntpc-fixed` | TW | A | OK | — | 173 | 173 | 1 | gộp trùng ≤ 30 m: 172 |
| `tw-ntpc-section` | TW | A | OK | 2026-08-11 | 50 | 50 | 19 | gộp trùng ≤ 30 m: 31 |
| `au-act-cameras` | AU | A | OK | 2026-08-21 | 1263 | 1204 | 1126 | gộp trùng ≤ 30 m: 78; trùng id trong nguồn: 35; loại không dùng: None: 4; lọc decommissioned_camera_date=2020-01-23T00:00:00.000: 3; lọc decommissioned_camera_date=2016-03-01T00:00:00.000: 2; lọc decommissioned_camera_date=2016-11-01T00:00:00.000: 2; lọc decommissioned_camera_date=2017-06-01T00:00:00.000: 2; lọc decommissioned_camera_date=2022-04-03T00:00:00.000: 2; lọc decommissioned_camera_date=2002-06-17T00:00:00.000: 1; lọc decommissioned_camera_date=2007-01-17T00:00:00.000: 1; lọc decommissioned_camera_date=2008-04-23T00:00:00.000: 1; lọc decommissioned_camera_date=2008-08-29T00:00:00.000: 1; lọc decommissioned_camera_date=2009-05-13T00:00:00.000: 1; lọc decommissioned_camera_date=2017-08-01T00:00:00.000: 1; lọc decommissioned_camera_date=2024-10-22T00:00:00.000: 1; thiếu toạ độ: 1; toạ độ ngoài khung bang: 1 |
| `au-nsw-fixed` | AU | A | OK | 2021-05-27 | 67 | 67 | 66 | gộp trùng ≤ 30 m: 1 |
| `au-nsw-school` | AU | A | OK | 2021-05-27 | 59 | 59 | 49 | gộp trùng ≤ 30 m: 10 |
| `au-nsw-redlight` | AU | A | OK | 2021-05-27 | 221 | 221 | 220 | gộp trùng ≤ 30 m: 1 |
| `kr-std` | KR | A | OK | 2026-08-21 | 43724 | 29183 | 25772 | loại không dùng: 4: 8037; loại không dùng: 04: 3425; gộp trùng ≤ 30 m: 3411; trùng id trong nguồn: 1540; loại không dùng: 99: 1461; loại không dùng: 3: 65; loại không dùng: 03: 13 |

## Theo vùng

| Vùng | Pack | Đơn vị | KB | Version | Camera | speed | redLight | schoolZone | combined | mobile |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR | `packs/ar.v1.json` | kmh | 36 | 1 | 90 | 90 | 0 | 0 | 0 | 0 |
| AU | `packs/au.v1.json` | kmh | 637 | 1 | 1461 | 79 | 0 | 49 | 233 | 1100 |
| BE | `packs/be.v1.json` | kmh | 54 | 1 | 129 | 129 | 0 | 0 | 0 | 0 |
| BR | `packs/br.v2.json` | kmh | 654 | 2 | 1299 | 1189 | 110 | 0 | 0 | 0 |
| CA | `packs/ca.v3.json` | kmh | 345 | 3 | 815 | 11 | 664 | 0 | 10 | 130 |
| CO | `packs/co.v2.json` | kmh | 17 | 2 | 40 | 36 | 0 | 0 | 4 | 0 |
| DE | `packs/de.v1.json` | kmh | 14 | 1 | 33 | 33 | 0 | 0 | 0 | 0 |
| ES | `packs/es.v1.json` | kmh | 395 | 1 | 952 | 952 | 0 | 0 | 0 | 0 |
| HK | `packs/hk.v1.json` | kmh | 162 | 1 | 386 | 164 | 222 | 0 | 0 | 0 |
| KR | `packs/kr.v1.json` | kmh | 7898 | 1 | 25772 | 9586 | 15882 | 0 | 304 | 0 |
| LU | `packs/lu.v1.json` | kmh | 20 | 1 | 45 | 45 | 0 | 0 | 0 | 0 |
| NO | `packs/no.v2.json` | kmh | 183 | 2 | 438 | 438 | 0 | 0 | 0 | 0 |
| SE | `packs/se.v2.json` | kmh | 1147 | 2 | 2795 | 2795 | 0 | 0 | 0 | 0 |
| SG | `packs/sg.v1.json` | kmh | 131 | 1 | 293 | 23 | 235 | 0 | 0 | 35 |
| TW | `packs/tw.v3.json` | kmh | 803 | 3 | 1905 | 1905 | 0 | 0 | 0 | 0 |
| US-CA | `packs/us-ca.v2.json` | mph | 30 | 2 | 74 | 56 | 18 | 0 | 0 | 0 |
| US-DC | `packs/us-dc.v4.json` | mph | 116 | 4 | 282 | 221 | 61 | 0 | 0 | 0 |
| US-DE | `packs/us-de.v1.json` | mph | 24 | 1 | 60 | 0 | 60 | 0 | 0 | 0 |
| US-IA | `packs/us-ia.v1.json` | mph | 64 | 1 | 156 | 13 | 0 | 0 | 0 | 143 |
| US-IL | `packs/us-il.v1.json` | mph | 256 | 1 | 625 | 326 | 299 | 0 | 0 | 0 |
| US-LA | `packs/us-la.v1.json` | mph | 16 | 1 | 38 | 2 | 6 | 30 | 0 | 0 |
| US-MD | `packs/us-md.v2.json` | mph | 215 | 2 | 515 | 148 | 218 | 149 | 0 | 0 |
| US-NY | `packs/us-ny.v2.json` | mph | 1184 | 2 | 2763 | 0 | 636 | 2127 | 0 | 0 |
| US-VA | `packs/us-va.v4.json` | mph | 15 | 4 | 35 | 0 | 0 | 35 | 0 | 0 |
| US-WA | `packs/us-wa.v3.json` | mph | 52 | 3 | 127 | 14 | 39 | 74 | 0 | 0 |

**Tổng: 41128 camera ở 25 vùng.**

## Vehicle-specific limits

Limit riêng theo loại xe chỉ lấy từ trường có sẵn trong dữ liệu nguồn — không suy từ luật từng nước.

| Nguồn | Vùng | Trường nguồn → loại xe | Camera có limit theo xe |
|---|---|---|---:|
| `antt-radares` | BR | `velocidade_pesado` → rv, trailer, truck | 1080 |

Không có limit theo loại xe (51 nguồn): `dc-ddot-ase`, `chi-speed`, `chi-redlight`, `moco-speed`, `moco-redlight`, `sf-speed`, `sf-redlight`, `nola-cams`, `sea-atsc`, `bal-redlight`, `bal-speed-fixed`, `bal-speed-portable`, `arl-speed`, `tac-ae`, `bel-speed`, `de-redlight`, `nyc-dof-derived`, `qc-mtmd`, `tor-rlc`, `ott-rlc`, `york-rlc`, `ham-rlc`, `peel-rlc`, `king-rlc`, `edm-isd`, `cal-isc`, `ia-ate`, `caba-fijas`, `bh-fiscalizacao`, `bog-salvavidas`, `es-dgt-radares`, `es-cat-radars`, `no-nvdb-atk`, `se-trv-atk`, `be-bxl-speedcameras`, `lu-geoportail-radars`, `de-ka-blitzer`, `sg-spf-speed`, `sg-spf-fixed`, `sg-spf-redlight`, `sg-spf-dtrls`, `hk-td-rlc`, `hk-td-sec`, `tw-npa-speed`, `tw-ntpc-fixed`, `tw-ntpc-section`, `au-act-cameras`, `au-nsw-fixed`, `au-nsw-school`, `au-nsw-redlight`, `kr-std`.

## NYC — vị trí suy từ vé phạt DOF (`nyc-dof-derived`)

- Dataset: `9mwx-gamw`, `pvqr-7yc4` · cửa sổ 2025-10-05 → 2026-10-05 · 4,003,911 vé camera
- Địa điểm (chuỗi địa chỉ trên vé) ≥ 20 vé: **3009** (bỏ 96 địa điểm ít vé hơn)
- Geocode OK: **2768 / 3009 (92.0 %)** · gọi Geoclient 0 lần, lấy từ cache 3215 lần
- Bị loại: geocode không ra giao lộ: 231; địa chỉ không đọc được: 8; không có borough (violation_county=None): 2
- Camera sau khi gộp cùng loại + giao lộ + hướng: **2763**

Mẫu 5 vị trí nhiều vé nhất (mở Apple Maps để kiểm):

| Loại | Địa điểm | Hướng | Borough | Vé | Apple Maps |
|---|---|---|---|---:|---|
| schoolZone | CROSS BAY BLVD @ SHAD CREEK RD | SB | Queens | 52192 | [40.608645, -73.819186](https://maps.apple.com/?ll=40.608645,-73.819186&z=18) |
| schoolZone | N CONDUIT AVE @ 88TH ST | WB | Queens | 48775 | [40.670780, -73.847871](https://maps.apple.com/?ll=40.670780,-73.847871&z=18) |
| schoolZone | N CONDUIT AVE @ 127TH ST | WB | Queens | 34175 | [40.667029, -73.813256](https://maps.apple.com/?ll=40.667029,-73.813256&z=18) |
| schoolZone | CYPRESS HILLS ST @ JAMAICA AVE | SB | Brooklyn | 27302 | [40.688563, -73.875707](https://maps.apple.com/?ll=40.688563,-73.875707&z=18) |
| schoolZone | BRUCKNER BLVD @ WHITE PLAINS RD | EB | Bronx | 25403 | [40.825950, -73.859555](https://maps.apple.com/?ll=40.825950,-73.859555&z=18) |

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

## Kiểm tra vị trí — D05 phần 1 (2026-09-27)

Mỗi nguồn/quốc gia chọn ngẫu nhiên (seed 20260927), tra ngược toạ độ bằng CLGeocoder của Apple (cùng dữ liệu Apple Maps), so với `roadName`.

| Camera | Loại / hướng | `roadName` | Apple trả về | Kết quả |
|---|---|---|---|---|
| [`ca-qc-mtmd-155`](https://maps.apple.com/?ll=45.583932,-73.65019&q=ca-qc-mtmd-155) | mobile / 180 | Boulevard Henri-Bourassa Est, entre la rue Lajeunesse et … en direction sud | 3250 Boul Henri-Bourassa E, Montréal | ✅ |
| [`ca-tor-rlc-6274`](https://maps.apple.com/?ll=43.796148,-79.227542&q=ca-tor-rlc-6274) | redLight / – | Sheppard Ave E And Lapsley Rd / Washburn Way | Burrows Hall Park; tra xuôi "Lapsley Rd & Sheppard Ave E" cách 2 m | ✅ đúng giao lộ |
| [`ca-ott-rlc-79954e7ad4`](https://maps.apple.com/?ll=45.472339,-75.547958&q=ca-ott-rlc-79954e7ad4) | redLight / 0 | Jeanne D'Arc Boulevard and Vineyard Drive/ Fortune Drive | Fortune Dr, Ottawa | ✅ |
| [`ca-edm-isd-ed2056`](https://maps.apple.com/?ll=53.499319,-113.493421&q=ca-edm-isd-ed2056) | redLight / 0 | Gateway Blvd & 63 Avenue | 6111 Gateway Blvd NW, Edmonton | ✅ |
| [`ca-cal-isc-7becfb92b9`](https://maps.apple.com/?ll=51.049001,-113.991052&q=ca-cal-isc-7becfb92b9) | redLight / 90 | Memorial Drive and 28 Street S.E. | 28 St SE, Calgary | ✅ |
| [`ar-caba-fijas-253131ed0c`](https://maps.apple.com/?ll=-34.57011,-58.410626&q=ar-caba-fijas-253131ed0c) | speed / – | Av. Sarmiento - 4290 | Avenida Presidente Sarmiento, Buenos Aires | ✅ |
| [`ar-caba-fijas-1619c5c4e5`](https://maps.apple.com/?ll=-34.579106,-58.382082&q=ar-caba-fijas-1619c5c4e5) | speed / – | Paseo Del Bajo Km 6.0 | Paseo del Bajo, Buenos Aires | ✅ |
| [`br-antt-radares-92b2522f1b`](https://maps.apple.com/?ll=-11.962062,-55.516853&q=br-antt-radares-92b2522f1b) | speed / – | BR-163 km 823,6 · Crescente | Rodovia BR-163, Sinop | ✅ |
| [`br-bh-fiscalizacao-1263`](https://maps.apple.com/?ll=-19.893841,-43.924245&q=br-bh-fiscalizacao-1263) | speed / – | Av. José Cândido da Silveira, 330 | Pista de Cooper José Cândido da Silveira, Belo Horizonte | ✅ (đường chạy bộ dọc đại lộ) |
| [`co-bog-salvavidas-dei04cam1`](https://maps.apple.com/?ll=4.74653,-74.112396&q=co-bog-salvavidas-dei04cam1) | speed / 270 | Cl 139 - Cr 131 | Calle 139 # 132-1, Bogotá | ✅ |
| [`co-bog-salvavidas-dei26cam02`](https://maps.apple.com/?ll=4.570629,-74.148833&q=co-bog-salvavidas-dei26cam02) | combined / 270 | Av Villavicencio - Cr 28 | Avenida Calle 61 Sur # 28-1, Bogotá | ✅ (Av. Villavicencio = Calle 61 Sur) |
| [`us-ia-ia-ate-1400block20thavenuenwb`](https://maps.apple.com/?ll=42.526254,-94.183915&q=us-ia-ia-ate-1400block20thavenuenwb) | mobile / 270 | 1400 Block 20th Avenue N | 1406 20th Ave N, Fort Dodge | ✅ |
| [`us-ia-ia-ate-700blockw53rdstreetwb`](https://maps.apple.com/?ll=41.574558,-90.582003&q=us-ia-ia-ate-700blockw53rdstreetwb) | mobile / 270 | 700 Block W 53rd Street | 628–670 W 53rd St, Davenport | ✅ |

Kết quả: 13/13 đúng đường/giao lộ.

## Kiểm tra vị trí — D05 phần 2, châu Âu (2026-09-27)

Mỗi nguồn chọn ngẫu nhiên (seed 11), tra ngược toạ độ bằng CLGeocoder của Apple (cùng dữ liệu Apple Maps), so với `roadName`. Catalonia kiểm thêm A-2, C-32, AP-7, C-31: cả 4 đúng đường (xác nhận đổi UTM 31N → WGS84).

| Camera | Loại / hướng | `roadName` | Apple trả về | Kết quả |
|---|---|---|---|---|
| [`es-es-dgt-radares-cabinacinemometro120587`](https://maps.apple.com/?ll=38.333973,-0.552382&q=es-es-dgt-radares-cabinacinemometro120587) | speed / – | A-70 km 22.5 | A-70, Alicante | ✅ |
| [`es-es-dgt-radares-cvm164566-start`](https://maps.apple.com/?ll=41.8381,-5.0108&q=es-es-dgt-radares-cvm164566-start) | speed / – (đầu đoạn) | N-601 km 226.4–228.2 · average speed section | N-601, Medina de Rioseco (Valladolid) | ✅ |
| [`es-es-cat-radars-4c134a157e`](https://maps.apple.com/?ll=41.538229,0.459457&q=es-es-cat-radars-4c134a157e) | speed / – · 120 | A-2 km 445,35 | A-2, Soses (Lleida) | ✅ |
| [`es-es-cat-radars-f512e6008a`](https://maps.apple.com/?ll=41.136213,1.147774&q=es-es-cat-radars-f512e6008a) | speed / – · 70 | N-420a km 879,314 | T-11, Reus | ✅ gần — N-420a chạy sát T-11 ở lối vào Reus |
| [`no-no-nvdb-atk-86573550`](https://maps.apple.com/?ll=59.920433,10.632924&q=no-no-nvdb-atk-86573550) | speed / – | Rv150 · Granfosstunnelen mot Drammen | Granfosstunnelen, Oslo | ✅ |
| [`no-no-nvdb-atk-373723081`](https://maps.apple.com/?ll=59.03704,11.001823&q=no-no-nvdb-atk-373723081) | speed / – | Fv108 · Hvalertunnelen mot Skjærhalden | Hvalertunnelen, Skjærhalden | ✅ |
| [`se-se-trv-atk-18009070`](https://maps.apple.com/?ll=60.021655,14.981629&q=se-se-trv-atk-18009070) | speed / 163 | Väg 50 · Bastkärn | Bastkärn 103, Grängesberg | ✅ |
| [`se-se-trv-atk-20030010`](https://maps.apple.com/?ll=60.447902,14.517263&q=se-se-trv-atk-20030010) | speed / 324 | E16 · Sveden västgående | Sveden 4, Nås | ✅ (västgående = đi về tây; heading 324) |
| [`be-be-bxl-speedcameras-sat801gatso`](https://maps.apple.com/?ll=50.824,4.3086&q=be-be-bxl-speedcameras-sat801gatso) | speed / – | Boulevard Paepsem · vers ring | Boulevard Industriel 51, Anderlecht | ✅ đúng giao lộ (nguồn: "Bd Industrie - Bd Paepsem") |
| [`be-be-bxl-speedcameras-sat322gatso`](https://maps.apple.com/?ll=50.8372,4.2951&q=be-be-bxl-speedcameras-sat322gatso) | speed / – | Boulevard Sylvain Dupuis · vers centre | Boulevard Sylvain Dupuis, Anderlecht | ✅ |
| [`lu-lu-geoportail-radars-8`](https://maps.apple.com/?ll=49.769567,6.086697&q=lu-lu-geoportail-radars-8) | speed / – | N7 Rouscht | N 7, Mersch | ✅ |
| [`lu-lu-geoportail-radars-71-start`](https://maps.apple.com/?ll=49.68902,6.163017&q=lu-lu-geoportail-radars-71-start) | speed / – (đầu đoạn) | A7 Tunnel Grouft · average speed section | A 7, Lorentzweiler | ✅ |
| [`de-de-ka-blitzer-215`](https://maps.apple.com/?ll=49.00465,8.348733&q=de-de-ka-blitzer-215) | speed / – | Eckenerstraße 32 | Eckenerstraße 30, Karlsruhe | ✅ |
| [`de-de-ka-blitzer-21`](https://maps.apple.com/?ll=49.011274,8.370389&q=de-de-ka-blitzer-21) | speed / – | Kaiserallee 36 | Kaiserallee, Karlsruhe | ✅ |

Kết quả: 14/14 đúng đường/giao lộ.

## Ghi chú dữ liệu

- Máy ở Việt Nam bị Socrata (Chicago, Montgomery, SF, New Orleans) chặn 403 theo IP; chạy qua VPN Mỹ thì bình thường. GitHub Actions (máy Mỹ) không bị.
- Montgomery County: quý mới nhất là 2024 Q4; 75 site có toạ độ 0/trống → bị loại (không geocode, không lấy từ nguồn khác).
- New Orleans: portal ghi "may not reflect accurate location information"; dataset cập nhật lần cuối 2024-11-28 (> 12 tháng) → confidence 60 − 10 = 50. Mã `function`: `RLC` → redLight; `FS` → speed (không có trường học/giờ school zone); `TFS` → schoolZone (luôn có `school_hour`). 4 dòng trùng `camid` (cùng camera ghi 2 lần) → giữ 1.
- Bellevue: 8 camera "In Service" là 4 cặp a/b cùng vị trí, không có trường hướng → gộp còn 5 (heading null, cảnh báo cả 2 chiều).
- Delaware: không có ngày cập nhật dataset → `lastConfirmedAt` null.
- DC: ngày dataset lấy từ item ArcGIS Online `03d94dc6579949ae9d7c9dd8ffebeb89` (layer MapServer không có `editingInfo`). Arlington: lấy `GeoSyncDate` lớn nhất.
- **D05 — Canada:** Québec: `idSite` (trong `urlImage`) làm key; "Radar photo mobile" = điểm đặt được duyệt → `mobile`, confidence 60; hướng lấy từ "en direction est/ouest/nord/sud". Toronto: GeoJSON 4326 là MultiPoint 1 điểm; 6 camera cách camera khác ≤ 30 m bị gộp. Ottawa: 2 dòng không có toạ độ → loại. York: dataset trên ArcGIS Online sửa lần cuối 2025-08-01, Kingston 2025-01-09 (> 12 tháng) → −10. Edmonton: dataset ghi rõ ISD "enforce red light infractions" → `redLight`, `posted_speed` là limit km/h của đường. Calgary: ISC đo được cả tốc độ lẫn đèn đỏ nhưng Alberta bỏ phạt speed-on-green từ 2025-04-01 (mục 12.4) → `redLight`; không có limit. **Toronto ASE và Edmonton photo-radar zones không dùng** (Ontario cấm ASE từ 2025-11-14; Alberta 0 dòng).
- **D05 — Iowa:** mã `approvalstatus` / `fixedormobile` tra bảng coded value của layer: chỉ giữ `1-Approved` (156/348); `2-Mobile` → `mobile` (60), `1-Fixed` → speed (tier B không trạng thái → 75). Layer không có ngày cập nhật → `lastConfirmedAt` null.
- **D05 — Argentina (CABA):** CSV `;` + dấu phẩy thập phân, Latin-1. Chỉ `Cinemómetro` → speed (129 dòng); "Analítica de video" (95) không chắc là đèn đỏ → bỏ. 35 dòng lặp đúng cùng toạ độ (cùng km) → giữ 1. Ước tính spec 168 là tổng mọi loại.
- **D05 — Brazil:** ANTT: file đổi tên hằng tháng (`dados-dos-radares6_2026.csv`) → lấy resource CSV mới nhất qua CKAN `package_show?id=radar`; "Controlador" và "Redutor" đều là radar tốc độ; `velocidade_leve` → limit; `sentido` (Crescente/Decrescente = chiều km, không phải la bàn) giữ trong `roadName`, heading null; 134 dòng trùng hệt toạ độ (2 chiều cùng điểm) → giữ 1. Belo Horizonte: WKT UTM 23S → WGS84; chỉ "Controlador Eletrônico de Velocidade" (speed) + "Detector de Avanço de Semáforo" (redLight); bỏ làn bus (23) và cấm rẽ/quay đầu (28); nguồn tách mỗi làn một thiết bị, không có hướng → 177 thiết bị cách nhau ≤ 30 m gộp lại (heading null — cảnh báo cả 2 chiều). Một dòng `VELOCIDADE_REGULAMENTAR` = 260 → limit null.
- **D05 — Colombia (Bogotá):** chỉ `ESTADO_PUNTO = Instalada` (77/128). Loại theo mã vi phạm (Código Nacional de Tránsito): C29 = quá tốc độ → speed; C29 + D04 (vượt đèn đỏ) → combined; "C14, C32" (không nhường người đi bộ) → bỏ. "(S-N)" → heading 0, "(N-S)" → 180, "(O-E)" → 90, "(E-O)" → 270. 5 dòng geometry rỗng nhưng có `LATITUD`/`LONGITUD` của chính dataset → dùng 2 trường này.
- **D05 — mạng:** Edmonton/Calgary (Socrata), ANTT, Belo Horizonte, Bogotá chặn IP Việt Nam → lần chạy 2026-09-27 dùng VPN Mỹ. ANTT từ chối cả một số máy chủ Mỹ; nếu GitHub Actions bị chặn, pipeline giữ camera ANTT từ pack cũ và REPORT ghi lỗi.
- **D05 — Tây Ban Nha (DGT):** DATEX II `PredefinedLocationsPublication/radares`: 690 điểm "CabinasCinemometro" + 47 đoạn "CinemometrosVelocidadMedia" → mỗi đoạn 2 camera speed tại `<from>` / `<to>`, `roadName` "… km a–b · average speed section". Không có limit; hướng chỉ là `positive/negative` theo lý trình (không phải la bàn) → heading null. Ngày dataset = `publicationTime` (2025-12-18). 62 camera gộp (đầu/cuối đoạn trùng cabin điểm, hoặc 2 chiều cùng chỗ).
- **D05 — Catalonia (SCT):** `radars.txt` là văn bản cột thẳng hàng, UTM 31N ETRS89, dấu phẩy thập phân, có `Velocitat` → limit. 16 dòng toạ độ hỏng ngay ở nguồn (mất dấu thập phân, ví dụ B-10 X=42552972, hoặc X/Y là 2 giá trị Y ghép — đều là camera đoạn "PK a-b") và 1 dòng rơi ra ngoài Tây Ban Nha (A-2 km 563,2-570,1, Y=398125) → loại, không sửa tay. Không có ngày cập nhật đọc được → `lastConfirmedAt` null. License: Llicència oberta d'ús d'informació - Catalunya.
- **D05 — Na Uy (NVDB 162):** 461 ATK-punkt; WKT srid 4326 của NVDB theo thứ tự **vĩ độ trước**. `Kontollretning` = "Med/Mot metreringsretning" (theo chiều lý trình, không phải la bàn) → heading null; 162 không có limit (limit nằm ở đối tượng 105 — không dùng). Mã cặp "(P1)/(P2)" trong tên bị bỏ khỏi `roadName`. 23 camera gộp (2 chiều cùng chỗ). **NVDB 775 (đoạn ATK) chưa dùng — v2.** Attribution nguyên văn: "Inneholder data under NLOD tilgjengeliggjort av Statens vegvesen".
- **D05 — Thuỵ Điển (Trafikverket, key):** 2.794 camera, không có `Deleted=true`. **`Bearing` là hướng ống kính** (tài liệu API: "which direction the camera is aimed at"), camera ATK chụp trực diện xe đi tới → **heading = Bearing + 180°**. Kiểm bằng dữ liệu: 104 cặp camera 2 chiều cùng chỗ → 25 cặp khớp "Bearing = ống kính", 0 cặp khớp "Bearing = hướng xe"; 908 camera có chữ hướng trong tên (norr/öster/söder/västergående) → 787 lệch ≤ 60°, 4 ngược chiều. License CC0.
- **D05 — Brussels:** `radar_type` (1/2/3) không có bảng giải nghĩa công khai (trang "Attributs radar_type" trả rỗng, SLD không phân loại) → mọi camera để `speed` (mô tả dataset: camera tốc độ, có chỗ kèm đèn đỏ); không đoán đèn đỏ. `direction_fr` ("vers centre", "vers ring") giữ trong `roadName`, heading null. **BE vẫn `restricted`** — pack sinh ra nhưng không có packURL.
- **D05 — Luxembourg:** 33 Point + 6 LineString (đoạn) → 45 camera. Dataset data.public.lu "PCH : Emplacement des radars fixes" (Administration des Ponts et Chaussées, CC0), sửa 2024-10-24 (> 12 tháng → confidence 70). **LU vẫn `blocked`.**
- **D05 — Karlsruhe:** 37 Blitzer (WFS `TBA:blitzer`, CC BY 4.0), dataset sửa 2025-02-19 (> 12 tháng → 70); 4 cặp 2 chiều cùng chỗ gộp. **DE vẫn `restricted`.**

## Kiểm tra vị trí — D05 phần 3, châu Á – Thái Bình Dương (2026-09-27)

Mỗi nguồn chọn ngẫu nhiên (seed 12), tra ngược toạ độ bằng CLGeocoder của Apple (cùng dữ liệu Apple Maps), so với `roadName`. Hai mẫu chưa rõ được tra xuôi thêm (khoảng cách ghi trong cột kết quả).

| Camera | Loại / hướng | `roadName` | Apple trả về | Kết quả |
|---|---|---|---|---|
| [`sg-sg-spf-dtrls-21`](https://maps.apple.com/?ll=1.363627,103.964436&q=sg-sg-spf-dtrls-21) | redLight / – | Loyang Avenue by Pasir Ris Drive 1 · towards TPE | 5 Loyang Ave, Pasir Ris | ✅ |
| [`sg-sg-spf-dtrls-160`](https://maps.apple.com/?ll=1.32097,103.74525&q=sg-sg-spf-dtrls-160) | redLight / – | Jurong Town Hall Road by Pandan Gardens · towards AYE | Teban Gardens Rd, Jurong East; tra xuôi "Jurong Town Hall Road & Pandan Gardens" cách 31 m | ✅ đúng giao lộ |
| [`sg-sg-spf-fixed-19`](https://maps.apple.com/?ll=1.307221,103.811638&q=sg-sg-spf-fixed-19) | speed / – | Holland Road · towards Ulu Pandan Road | Holland Rd, Tanglin | ✅ |
| [`sg-sg-spf-fixed-15`](https://maps.apple.com/?ll=1.386883,103.820352&q=sg-sg-spf-fixed-15) | speed / – | Upper Thomson Road · towards Lornie Road | 771 Upper Thomson Rd | ✅ |
| [`sg-sg-spf-speed-81d7f79df6`](https://maps.apple.com/?ll=1.34634,103.89845&q=sg-sg-spf-speed-81d7f79df6) | speed / – | Kallang-Paya Lebar Expressway 7.0 Km towards Tampines Expressway | 480 Airport Rd, Hougang (lưới ±30 m quanh điểm đều trả Airport Rd) | ⚠️ chưa xác nhận — geocoder không trả tên KPE; cần xem bằng mắt trên Apple Maps |
| [`hk-hk-td-rlc-210`](https://maps.apple.com/?ll=22.390802,114.205592&q=hk-hk-td-rlc-210) | redLight / 270 | Tai Chung Kiu Road & On Lai Street | On Lai St, Sha Tin | ✅ |
| [`hk-hk-td-rlc-161`](https://maps.apple.com/?ll=22.300647,114.238288&q=hk-hk-td-rlc-161) | redLight / 315 | Lei Yue Mun Road & Ko Chiu Road | Lei Yue Mun Rd, Yau Tong | ✅ |
| [`hk-hk-td-sec-60`](https://maps.apple.com/?ll=22.464401,114.05386&q=hk-hk-td-sec-60) | speed / 180 | San Tin Highway Near L/P FA9250 (Ha Chuk Yuen) | San Tin Highway, Kam Tin | ✅ |
| [`hk-hk-td-sec-160`](https://maps.apple.com/?ll=22.444258,114.036585&q=hk-hk-td-sec-160) | speed / – | Castle Peak Road - Yuen Long (Yuen Long Town Bound) Near Lamppost CD0972 | Yoho Mall, Yuen Lung St, Yuen Long | ✅ (Castle Peak Road chạy qua Yoho Mall) |
| [`tw-tw-npa-speed-857a36928c`](https://maps.apple.com/?ll=23.310371,120.400185&q=tw-tw-npa-speed-857a36928c) | speed / – · 50 | 165線18.82公里 | County Highway 165, Dongshan, Tainan | ✅ |
| [`tw-tw-npa-speed-4b7d0c4e4f`](https://maps.apple.com/?ll=25.07305,121.536865&q=tw-tw-npa-speed-4b7d0c4e4f) | speed / 180 · 100 | 國道一號南向22.7公里 | Zhongshan Freeway (= Quốc lộ 1), Taipei | ✅ |
| [`tw-tw-npa-speed-bb3a2232d7`](https://maps.apple.com/?ll=24.71843,121.76466&q=tw-tw-npa-speed-bb3a2232d7) | speed / – · 50 | 宜16線5.5k南津路東向 | 222 Nanjin Rd, Yilan | ✅ |
| [`tw-tw-ntpc-fixed-fcab3241f2`](https://maps.apple.com/?ll=25.200483,121.67773&q=tw-tw-ntpc-fixed-fcab3241f2) | speed / 270 · 50 | 台2線47.1公里萬里隧道出口處（往金山） | N Coastal Highway (= Tỉnh lộ 2), Wanli | ✅ |
| [`tw-tw-ntpc-section-7d2-end`](https://maps.apple.com/?ll=24.971244,121.530941&q=tw-tw-ntpc-section-7d2-end) | speed / – · 60 (cuối đoạn) | 新店區環河路(中央路至白馬寺，雙向) · average speed section | Huanhe Rd, Xindian | ✅ |
| [`tw-tw-ntpc-section-3d1-end`](https://maps.apple.com/?ll=24.938468,121.677097&q=tw-tw-ntpc-section-3d1-end) | speed / – · 40 (cuối đoạn) | 臺9線33.3k至37.2k(雙向) · average speed section | Beiyi Rd Sec 7 (= Tỉnh lộ 9), Pinglin | ✅ |
| [`au-au-act-cameras-0276a`](https://maps.apple.com/?ll=-35.268,149.119417&q=au-au-act-cameras-0276a) | mobile / – | Froggartt Street Turner | 43–45 Froggatt St, Turner | ✅ (nguồn viết sai chính tả, giữ nguyên) |
| [`au-au-act-cameras-0119e`](https://maps.apple.com/?ll=-35.17682,149.14006&q=au-au-act-cameras-0119e) | mobile / – | Horse Park Dr, Forde ACT 2914, Australia | 56 Hollingsworth St, Gungahlin; tra xuôi "Horse Park Drive, Forde" cách 422 m | ✅ gần — điểm mobile trên Horse Park Dr, cạnh Hollingsworth St |
| [`au-au-nsw-fixed-291`](https://maps.apple.com/?ll=-28.73451,153.404617&q=au-au-nsw-fixed-291) | speed / – | Bangalow Road | B62, Clunes | ✅ (B62 = Bangalow Road) |
| [`au-au-nsw-fixed-266`](https://maps.apple.com/?ll=-33.13393,151.61319&q=au-au-nsw-fixed-266) | speed / – | Pacific Highway, between Nords Wharf Road and Flowers Drive | 400 Pacific Hwy, Nords Wharf | ✅ |
| [`au-au-nsw-redlight-909`](https://maps.apple.com/?ll=-33.933941,151.199249&q=au-au-nsw-redlight-909) | combined / – | Wentworth Avenue and Sutherland Steet | 184 Sutherland St, Mascot | ✅ |
| [`au-au-nsw-redlight-858`](https://maps.apple.com/?ll=-33.874378,151.216507&q=au-au-nsw-redlight-858) | combined / – | William Street & Crown Street | Cross City Tunnel, Darlinghurst | ✅ (hầm chạy dưới William St) |
| [`au-au-nsw-school-206p2`](https://maps.apple.com/?ll=-33.867397,150.987915&q=au-au-nsw-school-206p2) | schoolZone / – | Woodville Road, between Orchardleigh Street and Middleton Road | Rowland Hassall School, Woodville Rd, Old Guildford | ✅ (camera thứ 2 của dòng — `lat_2/long_2`) |

Kết quả: 21/22 đúng đường/giao lộ, 1 chưa xác nhận (SG KPE). Cộng phần 1–2: **48/49**.

## Nguồn trong mục 12.2 không có trong bảng trên (2026-09-27)

| Nguồn | Trạng thái | Lý do |
|---|---|---|
| Hàn Quốc — data.go.kr 15028200 qua API (`kr-datagokr-cameras`) | tắt (`enabled: false`) | Không cần: cùng dataset lấy bằng nút tải file (`kr-std`, không key — bạn duyệt 2026-09-27), có trong bảng Nguồn ở trên |
| Queensland — Active mobile speed camera sites (f6b5c37e…, d059503f…) | bỏ | Cả 2 file (3.686 + 104 dòng) chỉ có mã điểm + tên đường/khu vực, **không có toạ độ** |
| Đài Loan — data.gov.tw 13940 (quốc lộ, TGOS) | bỏ | Có toạ độ + OGDL, nhưng file trên tgos.tw trả **403** khi tải từ máy này qua VPN Mỹ (có thể chặn IP ngoài Đài Loan). Camera quốc lộ đã có trong 7320 (154 dòng 國道一/二/三/五號) |
| Đài Loan — data.gov.tw 7320 (NPA toàn quốc, `tw-npa-speed`) | OK | Có toạ độ + OGDL (license "1") → thêm; 1.890 camera |

## Kiểm tra vị trí — Hàn Quốc `kr-std` (2026-09-27)

Chọn ngẫu nhiên (seed 12): 3 speed, 2 redLight, 1 combined. Tra ngược bằng CLGeocoder của Apple.

| Camera | Loại / limit | `roadName` | Apple trả về | Kết quả |
|---|---|---|---|---|
| [`kr-kr-std-c74f4ca6a9`](https://maps.apple.com/?ll=35.976063,129.409967&q=kr-kr-std-c74f4ca6a9) | speed / 50 | 충무로 · 원용교동편 (철강산단→해병1사단) | Chungmu-ro, North Gyeongsang | ✅ |
| [`kr-kr-std-6a94f921be`](https://maps.apple.com/?ll=36.355683,127.368516&q=kr-kr-std-6a94f921be) | speed / 30 | 월평동로 · 갈마초 옆 월평중 삼거리 | Wolpyeongdong-ro, Daejeon | ✅ |
| [`kr-kr-std-e1fb2674e4`](https://maps.apple.com/?ll=35.114193,126.829566&q=kr-kr-std-e1fb2674e4) | speed / 30 | 눌재로 · 백마r → 만귀정 | Nuljae-ro, Gwangju | ✅ |
| [`kr-kr-std-7631f46948`](https://maps.apple.com/?ll=37.41863,127.132541&q=kr-kr-std-7631f46948) | redLight / 30 | 여수울로 · 여수초교 앞 삼거리 어린이보호구역(…) | Yeosuul-ro, Gyeonggi-do | ✅ |
| [`kr-kr-std-40b77ae857`](https://maps.apple.com/?ll=37.12996,126.915151&q=kr-kr-std-40b77ae857) | redLight / 30 | 행정서로 · 바다유치원 앞 사거리 어린이보호구역(…) | Haengjeongseo-ro 2-gil, Gyeonggi-do | ✅ (ngõ nhánh của 행정서로, tại ngã tư) |
| [`kr-kr-std-cad702721d`](https://maps.apple.com/?ll=37.574669,127.126586&q=kr-kr-std-cad702721d) | combined / 40 | 사가정로 · 아천 TG 전 100m지점 (강변북로 → 용마터널) | Sagajeong-ro, Gyeonggi-do | ✅ |

Kết quả: 6/6 đúng đường. Tổng D05: **54/55**.

## Kiểm tra vị trí — D04 NYC (2026-09-28)

Chọn ngẫu nhiên 10 camera `nyc-dof-derived` (seed 2026). Tra bằng CLGeocoder của Apple (cùng dữ liệu Apple Maps): **xuôi** "<đường 1> & <đường 2>, <borough>, NY" → khoảng cách tới toạ độ trong pack; **ngược** toạ độ → tên đường. Đúng = Apple tìm ra đúng giao lộ ghi trong `roadName`, cách ≤ 100 m.

| Camera | Loại / hướng | `roadName` | Apple tìm xuôi (khoảng cách) | Apple tra ngược | Kết quả |
|---|---|---|---|---|---|
| [`us-ny-nyc-dof-derived-rl0042529nb`](https://maps.apple.com/?ll=40.820438,-73.936227&q=us-ny-nyc-dof-derived-rl0042529nb) | redLight / 0 | Lenox Ave & W 145th St | Malcolm X Blvd & W 145th St (6 m) | W 145th St | ✅ (Lenox Ave = Malcolm X Blvd) |
| [`us-ny-nyc-dof-derived-sz0021082nb`](https://maps.apple.com/?ll=40.747022,-74.004652&q=us-ny-nyc-dof-derived-sz0021082nb) | schoolZone / 0 | 10th Ave & W 22nd St | 10th Ave & W 22nd St (1 m) | 10th Ave | ✅ |
| [`us-ny-nyc-dof-derived-sz0042863nb`](https://maps.apple.com/?ll=40.81856,-73.927316&q=us-ny-nyc-dof-derived-sz0042863nb) | schoolZone / 0 | Grand Concourse & E 149th St | Grand Concourse & E 149th St (9 m) | E 149th St | ✅ |
| [`us-ny-nyc-dof-derived-sz0044392sb`](https://maps.apple.com/?ll=40.860642,-73.93077&q=us-ny-nyc-dof-derived-sz0044392sb) | schoolZone / 180 | Broadway & W 196th St | W 196th St & Broadway (2 m) | Broadway | ✅ |
| [`us-ny-nyc-dof-derived-sz0060380eb`](https://maps.apple.com/?ll=40.775963,-73.779109&q=us-ny-nyc-dof-derived-sz0060380eb) | schoolZone / 90 | 28th Ave & 210th Pl | 28th Ave & 210th Pl (0 m) | 28th Ave | ✅ |
| [`us-ny-nyc-dof-derived-rl0037665x0090887wb`](https://maps.apple.com/?ll=40.71027,-73.771687&q=us-ny-nyc-dof-derived-rl0037665x0090887wb) | redLight / 270 | Jamaica Ave & 187th Pl | 187th Pl & Jamaica Ave (10 m) | Jamaica Ave | ✅ |
| [`us-ny-nyc-dof-derived-sz0012563eb`](https://maps.apple.com/?ll=40.574296,-73.988686&q=us-ny-nyc-dof-derived-sz0012563eb) | schoolZone / 90 | Surf Ave & W 22nd St | W 22nd St & Surf Ave (1 m) | W 22nd St | ✅ |
| [`us-ny-nyc-dof-derived-sz0054540sb`](https://maps.apple.com/?ll=40.892905,-73.843655&q=us-ny-nyc-dof-derived-sz0054540sb) | schoolZone / 180 | Baychester Ave & Edenwald Ave | Baychester Ave & Edenwald Ave (0 m) | Baychester Ave | ✅ |
| [`us-ny-nyc-dof-derived-sz0056917wb`](https://maps.apple.com/?ll=40.815667,-73.817626&q=us-ny-nyc-dof-derived-sz0056917wb) | schoolZone / 270 | Harding Ave & Calhoun Ave | Calhoun Ave & Harding Ave (0 m) | Harding Ave | ✅ |
| [`us-ny-nyc-dof-derived-sz0049613sb`](https://maps.apple.com/?ll=40.882155,-73.878126&q=us-ny-nyc-dof-derived-sz0049613sb) | schoolZone / 180 | Bainbridge Ave & E 211th St | Bainbridge Ave & E 211th St (0 m) | Bainbridge Ave | ✅ |

Kết quả: **10/10 đúng giao lộ** (0–10 m). Geocode OK 92,0 % (2.771/3.012 địa điểm ≥ 20 vé; loại 231 không ra giao lộ — tên viết tắt tự do như "RHNLNDR AV", chuỗi bị cắt ở 40 ký tự, đường giao nhau > 2 lần; 8 địa chỉ đoạn đường không có dấu chấm; 2 dòng thiếu borough). Chạy lại lần 2: gọi Geoclient 0 lần, manifest / regions.json / cache không đổi.
