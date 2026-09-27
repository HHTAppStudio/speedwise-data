# REPORT — Speedwise data pipeline

Lần chạy: 2026-09-27 (UTC). Sinh tự động bởi `build_packs.py` — đừng sửa phần trên dòng đánh dấu.

## Nguồn

| Nguồn | Vùng | Tier | Tải | Ngày dataset | Dòng | Camera | Vào pack | Bị loại (lý do) |
|---|---|---|---|---|---:|---:|---:|---|
| `dc-ddot-ase` | US-DC | A | OK | 2026-09-27 | 327 | 283 | 282 | loại không dùng: Stop Sign: 34; loại không dùng: Truck Restriction: 10; gộp trùng ≤ 30 m: 1 |
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
| `arl-speed` | US-VA | B | OK | 2026-09-27 | 47 | 35 | 35 | không hoạt động: Active=No: 2; lọc Retired=1745899200000: 2; lọc Retired=1747281600000: 2; lọc Retired=1756094400000: 2; lọc Retired=1757908800000: 2; lọc Retired=1742443200000: 1; lọc Retired=1757649600000: 1 |
| `tac-ae` | US-WA | B | OK | 2026-09-26 | 23 | 22 | 22 | trùng id trong nguồn: 1 |
| `bel-speed` | US-WA | B | OK | 2026-08-26 | 14 | 8 | 5 | không hoạt động: OperationalStatus=Planned: 6; gộp trùng ≤ 30 m: 3 |
| `de-redlight` | US-DE | B | OK | — | 60 | 60 | 60 | — |
| `qc-mtmd` | CA | A | OK | 2026-09-10 | 160 | 160 | 160 | — |
| `tor-rlc` | CA | A | OK | 2026-09-26 | 301 | 301 | 295 | gộp trùng ≤ 30 m: 6 |
| `ott-rlc` | CA | A | OK | 2026-08-12 | 88 | 86 | 86 | thiếu toạ độ: 2 |
| `york-rlc` | CA | A | OK | 2025-08-01 | 55 | 55 | 55 | — |
| `ham-rlc` | CA | A | OK | 2026-09-26 | 51 | 51 | 51 | — |
| `peel-rlc` | CA | A | OK | 2026-03-05 | 37 | 37 | 37 | — |
| `king-rlc` | CA | A | OK | 2025-01-09 | 7 | 7 | 7 | — |
| `edm-isd` | CA | A | OK | 2026-09-14 | 67 | 67 | 67 | — |
| `cal-isc` | CA | A | OK | 2026-09-01 | 57 | 57 | 57 | — |
| `ia-ate` | US-IA | B | OK | — | 348 | 156 | 156 | lọc approvalstatus=2-Denied: 192 |
| `caba-fijas` | AR | A | OK | — | 224 | 94 | 90 | loại không dùng: Analítica de video: 95; trùng id trong nguồn: 35; gộp trùng ≤ 30 m: 4 |
| `antt-radares` | BR | A | OK | 2026-08-28 | 1256 | 1122 | 1080 | trùng id trong nguồn: 134; gộp trùng ≤ 30 m: 42 |
| `bh-fiscalizacao` | BR | A | OK | 2026-09-15 | 447 | 396 | 219 | gộp trùng ≤ 30 m: 177; loại không dùng: Detector de Conversão-Retorno em local Proibido: 28; loại không dùng: Detector de Invasão de Faixa de Exclusiva - MOVE: 23 |
| `bog-salvavidas` | CO | A | OK | 2026-08-24 | 128 | 54 | 48 | lọc ESTADO_PUNTO=Desmontada - novedad: 43; loại không dùng: C14, C32: 23; lọc ESTADO_PUNTO=None: 8; gộp trùng ≤ 30 m: 6 |

## Theo vùng

| Vùng | Pack | Đơn vị | KB | Version | Camera | speed | redLight | schoolZone | combined | mobile |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR | `packs/ar.v1.json` | kmh | 36 | 1 | 90 | 90 | 0 | 0 | 0 | 0 |
| BR | `packs/br.v1.json` | kmh | 552 | 1 | 1299 | 1189 | 110 | 0 | 0 | 0 |
| CA | `packs/ca.v1.json` | kmh | 345 | 1 | 815 | 11 | 664 | 0 | 10 | 130 |
| CO | `packs/co.v1.json` | kmh | 20 | 1 | 48 | 44 | 0 | 0 | 4 | 0 |
| US-CA | `packs/us-ca.v1.json` | mph | 30 | 1 | 74 | 56 | 18 | 0 | 0 | 0 |
| US-DC | `packs/us-dc.v2.json` | mph | 116 | 2 | 282 | 221 | 61 | 0 | 0 | 0 |
| US-DE | `packs/us-de.v1.json` | mph | 24 | 1 | 60 | 0 | 60 | 0 | 0 | 0 |
| US-IA | `packs/us-ia.v1.json` | mph | 64 | 1 | 156 | 13 | 0 | 0 | 0 | 143 |
| US-IL | `packs/us-il.v1.json` | mph | 256 | 1 | 625 | 326 | 299 | 0 | 0 | 0 |
| US-LA | `packs/us-la.v1.json` | mph | 16 | 1 | 38 | 2 | 6 | 30 | 0 | 0 |
| US-MD | `packs/us-md.v1.json` | mph | 215 | 1 | 515 | 148 | 218 | 149 | 0 | 0 |
| US-VA | `packs/us-va.v2.json` | mph | 15 | 2 | 35 | 0 | 0 | 35 | 0 | 0 |
| US-WA | `packs/us-wa.v1.json` | mph | 52 | 1 | 127 | 14 | 39 | 74 | 0 | 0 |

**Tổng: 4164 camera ở 13 vùng.**

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
