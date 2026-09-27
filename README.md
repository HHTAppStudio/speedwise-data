# speedwise-data

Pipeline dữ liệu camera của app **Speedwise**. Tải vị trí camera **chính thức** do thành phố/quận/bang/quốc gia công bố (open data), chuẩn hoá về schema data pack của app, rồi xuất ra thư mục `public/` (GitHub Pages phục vụ thư mục này, app tự tải về). Mỹ: 1 pack/bang (mph). Ngoài Mỹ: 1 pack/quốc gia (km/h).

Chỉ dùng thư viện chuẩn Python 3 — không cần `pip install`. Hầu hết nguồn không cần key; nguồn cần key (Thuỵ Điển; Hàn Quốc — đang tắt) tự bỏ qua khi thiếu key — xem **Key API**.

## Chạy

```sh
python3 build_packs.py                      # tải mọi nguồn đang bật, ghi public/, manifest.json, REPORT.md
python3 build_packs.py --only dc-ddot-ase   # chỉ chạy 1 (hoặc vài, cách nhau dấu phẩy) nguồn; nguồn khác giữ camera cũ
python3 build_packs.py --offline            # không gọi mạng, dùng cache/ của lần chạy trước (để thử sửa mapping)
python3 -m unittest -v                      # test, chỉ dùng fixtures/, không cần mạng
```

Sau khi chạy: đọc `REPORT.md` (mỗi nguồn tải OK/lỗi, số dòng, số camera, lý do bị loại, tổng theo bang), rồi commit.

Lưu ý:
- **Socrata chặn IP ngoài Mỹ** (data.cityofchicago.org, data.sf.gov, data.montgomerycountymd.gov, data.nola.gov, data.edmonton.ca, data.calgary.ca trả 403). Chạy từ Việt Nam cần VPN Mỹ; GitHub Actions không bị.
- **Brazil / Colombia chặn IP Việt Nam**: dados.antt.gov.br (từ chối), ckan.pbh.gov.br (403), sig.simur.gov.co (timeout). Qua VPN Mỹ thì đọc được.
- Python cài từ python.org trên macOS không đọc chứng chỉ gốc của hệ thống → script tự xuất từ keychain ra `cache/macos-roots.pem` (chỉ trên Mac).
- Python ≥ 3.13 từ chối chứng chỉ gốc GRCA của chính phủ Đài Loan ("Missing Subject Key Identifier") → script tắt riêng cờ `VERIFY_X509_STRICT` (chuỗi chứng chỉ vẫn được xác minh, như Python 3.12).
- **data.gov.sg** không key bị giới hạn tốc độ (code 24, chờ ~10 giây) → script tự chờ 12 giây rồi gọi lại.
- Một nguồn lỗi không làm dừng các nguồn khác: camera của nguồn đó được **giữ từ pack cũ**, REPORT ghi lý do.

## Key API

Một số nguồn cần key miễn phí. Key **chỉ** đọc từ biến môi trường, không bao giờ ghi vào repo hay in ra log:

| Biến | Nguồn | Cách đăng ký |
|---|---|---|
| `TRAFIKVERKET_API_KEY` | Thuỵ Điển `se-trv-atk` | Đăng ký tài khoản bằng email tại https://data.trafikverket.se (cổng API của Trafikverket), chấp nhận license, xác nhận email, rồi tạo key trong trang tài khoản. Miễn phí, data CC0. |
| `DATA_GO_KR_KEY` | Hàn Quốc qua API (`kr-datagokr-cameras`, đang `enabled: false`). **Không cần** — Hàn Quốc đang lấy bằng nút tải file (`kr-std`, không key) | https://www.data.go.kr → đăng ký → dataset 15028200 → "활용신청"; key "일반 인증키 (Decoding)". |

- **Trên máy:** tạo file `~/.speedwise/keys.env` (ngoài repo), mỗi dòng `TEN_BIEN=giá_trị`. `build_packs.py` tự đọc file này (không ghi đè biến môi trường đã có).
- **GitHub Actions:** repo → Settings → Secrets and variables → Actions → New repository secret, đặt đúng tên biến ở trên.
- **Thiếu key** → nguồn đó bị bỏ qua (REPORT ghi `skipped: no key (TÊN_BIẾN)`), camera cũ của nguồn đó trong pack được giữ, các nguồn khác chạy bình thường.

## Cấu trúc

| File | Vai trò |
|---|---|
| `sources.json` | Danh sách nguồn + cách map trường (bảng dưới) |
| `state_bboxes.json` | Khung toạ độ từng bang/quốc gia — toạ độ ngoài khung bị loại |
| `build_packs.py` | Script chính |
| `test_build_packs.py` | Unittest |
| `fixtures/<id>.json` | ≤ 5 dòng thật của mỗi nguồn, lưu tự động ở lần tải đầu (chỉ dùng cho test) |
| `public/regions.json` | Danh sách vùng cho app (+ `sources` để hiện attribution) |
| `public/packs/us-xx.vN.json` | Data pack từng bang Mỹ (`unit: "mph"`) |
| `public/packs/<cc>.vN.json` | Data pack từng quốc gia ngoài Mỹ (`ca`, `br`…; `unit: "kmh"`) |
| `manifest.json` | Hash nội dung + version hiện tại của từng pack |
| `REPORT.md` | Báo cáo lần chạy gần nhất. Phần dưới dòng `<!-- PHẦN VIẾT TAY … -->` là viết tay, script giữ nguyên |
| `cache/` | Dữ liệu thô lần tải gần nhất (không commit) |

## Quy tắc chuẩn hoá

- `source` luôn `"openData"`, thêm `sourceId` = id nguồn.
- **Hướng** (hướng xe chạy bị giám sát): tách từ chữ — NB/N/B/Northbound → 0, NEB → 45, EB → 90, SEB → 135, SB → 180, SWB → 225, WB → 270, NWB → 315. Không có hướng, hoặc chuỗi có nhiều hướng khác nhau → `null`.
- **Limit**: chỉ lấy khi nguồn ghi đúng một con số, theo đơn vị của pack (mph ở Mỹ, tối đa 85; km/h ngoài Mỹ, tối đa 140). Không có / nhiều số ("35 MPH / 20 MPH during school zone hours") → `null`. **Không đoán.**
- **Hướng tiếng khác**: nguồn khai `directionWords` (ví dụ Québec `"en direction est": "E"`, Bogotá `"(S-N)": "N"`). Chữ như "Rue Sainte-Catherine Est" không phải hướng → không khớp.
- `roadName`: bỏ chữ hướng, "@"/"at" → "&", chuẩn hoá hoa/thường khi nguồn viết toàn chữ hoa.
- **Confidence**: `baseConfidence` khi dòng có trạng thái active; nguồn không có trạng thái → tối đa 80 (tier A) / 75 (tier B); `typeConfidence` ghi đè theo loại (điểm đặt camera **mobile** được duyệt: 60 — docs/04_TECH_SPEC.md mục 12.3); dataset cập nhật > 12 tháng → −10; tối thiểu 50.
- `lastConfirmedAt` = ngày cập nhật dataset, hoặc ngày go-live của camera nếu mới hơn. Go-live trong tương lai → chưa đưa vào.
- **ID ổn định** (vote của người dùng gắn vào id): `<region>-<sourceId>-<key>[-<nb|sb|…>]`. Hậu tố hướng chỉ có ở nguồn tách theo approach. Không có key → 10 ký tự đầu SHA1 của `lat|lon|type|heading`.
- **Đoạn đo tốc độ trung bình** (DGT tramo, Luxembourg LineString…): 2 camera `speed` tại điểm đầu và cuối, id thêm hậu tố `-start` / `-end`, `roadName` kết thúc bằng `" · average speed section"` (docs/04_TECH_SPEC.md mục 12.3).
- **Gộp trùng** trong cùng bang: cùng type, hướng lệch ≤ 30° (hoặc cả hai null), cách ≤ 30 m → giữ bản confidence cao hơn (bằng nhau thì tier A).
- **Version**: pack chỉ tăng version khi hash nội dung đổi; file version cũ bị xoá. `regions.json` tăng `version` khi nội dung đổi. `updatedAt` của vùng = ngày pack đổi version gần nhất.
- `regions.json` lấy template `../Speedwise/Resources/DataPacks/regions.json` (khi chạy trong repo app); không có thì dùng chính `public/regions.json` hiện tại. Vùng mới của CR-D2 (HK, AR, CO) thêm từ `ADDED_REGIONS` trong `build_packs.py` nếu template chưa có. Bang Mỹ không có pack → "Community only" (không `packURL`, `cameraCount` 0).
- **Trạng thái pháp lý** (docs/04_TECH_SPEC.md mục 12.4): vùng `comingSoon` có pack ≥ 1 camera → `full` (bỏ `legalNote` "Not available yet"). Vùng `restricted` / `blocked` (BE, DE, LU…) **không bao giờ** bị pipeline đổi, và không có `packURL` dù pack vẫn được sinh ra.
- **Kích thước pack**: > 3 MB → ghi JSON rút gọn (không khoảng trắng, bỏ trường null — app coi trường thiếu là null). > 8 MB → script dừng (cần quyết định tách pack). Pack Hàn Quốc (`kr`) đã ~7,7 MB — nếu workflow đỏ vì > 8 MB thì cần tách KR theo tỉnh/thành (cần sửa app).

## Thêm một nguồn

1. Chỉ dùng open data **chính thức** của cơ quan nhà nước (Socrata / ArcGIS REST / WFS / CKAN / file CSV-GeoJSON do cơ quan công bố). Không scrape HTML/PDF, không OpenStreetMap, không dữ liệu app/web thương mại. Danh sách nguồn quốc tế được duyệt: docs/04_TECH_SPEC.md mục 12.2 — muốn thêm nguồn khác phải hỏi trước.
2. Gọi metadata xem tên trường thật (`https://<domain>/api/views/<id>.json` hoặc `<layer>?f=json`).
3. Thêm 1 mục vào `sources.json`:

   | Trường | Ý nghĩa |
   |---|---|
   | `id`, `enabled`, `tier` | `tier` A = có license mở / terms cho dùng lại; B = cơ quan công khai nhưng không ghi license |
   | `region`, `coverage` | "US-DC" (bang Mỹ) hoặc mã quốc gia "CA", "BR"…; `coverage` ghép vào `coverageNote` của vùng |
   | `publisher`, `name`, `landingURL`, `license`, `attribution` | Hiện trong app (màn Data sources) |
   | `endpoint`, `format` | `arcgis-geojson` (thêm `outSR=4326&f=geojson`), `socrata-json`, `socrata-geojson`, `wfs-geojson` (thêm `outputFormat=geojson&srsName=EPSG:4326`), `geojson` (file GeoJSON; Point hoặc MultiPoint 1 điểm), `csv`, `datex2-predefined-locations` (XML DATEX II v1: Point → 1 camera, Linear → 2 camera đầu/cuối), `nvdb-v4` (NVDB API Les v4, tự phân trang theo `metadata.neste`), `trafikverket-post` (POST QUERY XML, cần `apiKeyEnv` + `query`), `datagovsg-datastore` (data.gov.sg `datastore_search`, phân trang `offset`), `datagovsg-poll-download` (data.gov.sg `poll-download` → link tải GeoJSON), `ntpc-json` (New Taipei `/api/datasets/<uuid>/json`, phân trang `page`/`size`), `datagokr-api` (api.data.go.kr, `serviceKey` + `pageNo`/`numOfRows`, ≤ 5 request/giây). `datagokr-std-download` (nút "tải file" của dataset chuẩn data.go.kr, không key: `columList.json` + `standard.json` từng trang 2.000 dòng; cần `datasetPk`). CKAN `datastore/dump/<id>` trả CSV → dùng format `csv` |
   | `csv` | (chỉ format `csv`) `{"delimiter": ";", "decimalComma": true, "encoding": "latin-1"}` — mặc định `,` / dấu chấm / UTF-8. Văn bản cột thẳng hàng: `{"fixedWidth": true, "skipLines": 2}` (bỏ 2 dòng đầu, cột bắt đầu ở vị trí từng chữ tiêu đề) |
   | `headers` | (tuỳ chọn) header HTTP thêm, ví dụ NVDB `{"X-Client": "Speedwise"}` |
   | `apiKeyEnv` | (tuỳ chọn) tên biến môi trường chứa key; thiếu → bỏ qua nguồn (xem **Key API**) |
   | `query` | (`trafikverket-post`) `{"objecttype": "TrafficSafetyCamera", "schemaversion": "1"}` |
   | `lineSections` | (tuỳ chọn, GeoJSON) `true` → LineString là đoạn đo tốc độ trung bình → 2 camera đầu/cuối |
| `sectionFields` | (tuỳ chọn, mảng JSON) `{"startLat", "startLon", "endLat", "endLon"}` — đoạn ghi toạ độ đầu/cuối trong 4 trường; đoạn 2 chiều ghi nhiều giá trị cách nhau khoảng trắng → 2 camera/chiều, id thêm `d1`, `d2`… (New Taipei) |
| `sectionField` | (tuỳ chọn) `{"field", "start": [...], "end": [...], "lengthField"}` — mã vị trí đầu/cuối đoạn trong một trường; chỉ tính là đoạn khi `lengthField` > 0 (Hàn Quốc) |
| `popupTable` | (tuỳ chọn, GeoJSON) tên trường chứa bảng HTML `<th>tên</th><td>giá trị</td>` do lớp KML sinh ra → tách thành các trường (CSDI Hong Kong: `PopupInfo`) |
| `secondPoint` | (tuỳ chọn) `{"lat", "lon"}` — trường toạ độ của camera thứ 2 cùng dòng → thêm 1 camera, id thêm `p2` (NSW `lat_2`/`long_2`) |
   | `utm` | (tuỳ chọn) `{"zone": 23, "south": true}` — toạ độ nguồn là UTM (x/y hoặc WKT) → đổi sang WGS84 bằng `utm_to_wgs84` |
   | `ckanResource` | (tuỳ chọn) file đổi tên mỗi kỳ: `endpoint` là CKAN `package_show`, lấy resource mới nhất (theo `created`) có tên khớp `namePattern` và đúng `format` |
   | `codedValues` | (tuỳ chọn, ArcGIS) `{"url": "<layer>?f=json", "fields": [...]}` — đổi mã số sang tên trong bảng coded-value ("1" → "1-Approved") trước khi lọc |
   | `metadata` | `{"url", "dateKey"}` — nơi đọc ngày cập nhật dataset (`rowsUpdatedAt`, `editingInfo.lastEditDate`, `modified`); `null` nếu không có |
   | `rowDateField` | (tuỳ chọn) lấy ngày lớn nhất của trường này khi không có metadata |
   | `typeMap` | `{"const": "redLight"}` hoặc `{"field", "values": {giá trị nguồn: type}}`; giá trị không có trong `values` bị loại. `schoolZoneIfField`: speed → schoolZone khi trường này có giá trị |
   | `typeConfidence` | (tuỳ chọn) `{"mobile": 60}` — confidence cố định cho loại đó |
   | `directionWords` | (tuỳ chọn) `{cụm từ: mã hướng}` cho ngôn ngữ khác tiếng Anh, khớp nguyên từ |
   | `filters` | `[{"field", "in": [...]}]`, `{"notIn": [...]}`, `{"empty": true}` |
   | `fieldMap` | `bearing` (góc la bàn của nguồn, độ; kèm `bearingOffset` ở cấp nguồn — 180 khi nguồn ghi hướng ống kính, như Trafikverket), `lat`, `lon` (Socrata, CSV; với GeoJSON là dự phòng khi geometry trống) hoặc `point`; CSV còn có `x`/`y` hoặc `wkt` ("POINT (x y)"); GeoJSON/ArcGIS/WFS dùng geometry. `key` (+ `keyPattern`: regex, lấy nhóm 1), `road` (danh sách trường, lấy trường đầu có giá trị; `roadPattern`: regex, lấy nhóm 1) hoặc `roadFormat` ("{rodovia} km {km_m} · {sentido}" — ghép nhiều trường), `direction`, `limit`, `goLive`, `active` = `{"field", "activeValues", "inactiveValues"}` |
   | `approaches` | (tuỳ chọn) các trường approach → 1 camera cho mỗi approach |
   | `latestPeriodField` | (tuỳ chọn) chỉ giữ dòng của kỳ mới nhất (ví dụ "2024 Q4") |
   | `baseConfidence` | Confidence khi dòng active (thường 90 cho A, 80 cho B) |

4. Nếu bang/quốc gia chưa có trong `state_bboxes.json` thì thêm khung toạ độ.
5. `python3 build_packs.py --only <id>` → đọc REPORT.md, mở vài toạ độ trên Apple Maps xem có đúng đường không → `python3 -m unittest -v` → commit.

## Publish

Repo GitHub: **`HHTAppStudio/speedwise-data`** (public). GitHub Pages phục vụ thư mục `public/` tại `https://hhtappstudio.github.io/speedwise-data/` — đúng `SpeedwiseDataBaseURL` trong Info.plist của app. App kiểm tra `regions.json` tối đa 1 lần / 6 giờ; pack có `packVersion` lớn hơn bản trên máy → tự tải.

Workflow `.github/workflows/build.yml` chạy **thứ Hai 03:17 UTC**, khi bấm chạy tay, và khi push vào `main`:

1. `python -m unittest -v` — đỏ thì dừng, **không publish**.
2. `python build_packs.py` — một nguồn lỗi vẫn publish các nguồn còn lại (giữ camera cũ của nguồn lỗi, ghi lý do trong REPORT.md).
3. `public/` hoặc `manifest.json` đổi → bot commit `data: weekly update <ngày>` (kèm REPORT.md). Data không đổi → không commit.
4. Deploy `public/` lên Pages.

Chạy tay và xem log:

```sh
gh workflow run build.yml -R HHTAppStudio/speedwise-data     # chạy ngay
gh run list -R HHTAppStudio/speedwise-data -L 5               # các lần chạy gần nhất
gh run watch -R HHTAppStudio/speedwise-data                   # theo dõi lần đang chạy
gh run view <run-id> -R HHTAppStudio/speedwise-data --log     # log đầy đủ (kết quả từng nguồn ở bước "Build packs")
```

Hoặc trên web: tab **Actions** của repo → "Build data packs" → **Run workflow**.

Thêm nguồn mới rồi publish: làm theo "Thêm một nguồn" ở trên, chạy thử trên máy (`--only <id>`), commit `sources.json` (+ `state_bboxes.json` nếu có) và `git push` — push vào `main` tự chạy workflow và publish. Sau đó `git pull` để lấy commit data của bot, rồi `sh sync_to_app.sh` nếu muốn cập nhật bản đóng gói trong app.

Kiểm tra host:

```sh
curl -s https://hhtappstudio.github.io/speedwise-data/regions.json | python3 -m json.tool | head
```

## Để sau (v2)

- **Queensland** (active mobile speed camera sites): 2 file chính thức không có toạ độ, chỉ có tên đường + khu vực → chưa dùng (cần geocode từ text chính thức).
- **Đài Loan 13940** (quốc lộ, TGOS): file trả 403 từ ngoài Đài Loan; camera quốc lộ đã có trong NPA 7320.

- **NVDB 775** (đoạn ATK / streknings-ATK ở Na Uy): hiện chỉ dùng 162 ATK-punkt (điểm). 775 cần ghép đoạn theo lý trình → v2.
