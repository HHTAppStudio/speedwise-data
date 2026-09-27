# speedwise-data

Pipeline dữ liệu camera của app **Speedwise**. Tải vị trí camera **chính thức** do thành phố/quận/bang Mỹ công bố (open data), chuẩn hoá về schema data pack của app, rồi xuất ra thư mục `public/` (GitHub Pages phục vụ thư mục này, app tự tải về).

Chỉ dùng thư viện chuẩn Python 3 — không cần `pip install`. Không API key.

## Chạy

```sh
python3 build_packs.py                      # tải mọi nguồn đang bật, ghi public/, manifest.json, REPORT.md
python3 build_packs.py --only dc-ddot-ase   # chỉ chạy 1 (hoặc vài, cách nhau dấu phẩy) nguồn; nguồn khác giữ camera cũ
python3 build_packs.py --offline            # không gọi mạng, dùng cache/ của lần chạy trước (để thử sửa mapping)
python3 -m unittest -v                      # test, chỉ dùng fixtures/, không cần mạng
```

Sau khi chạy: đọc `REPORT.md` (mỗi nguồn tải OK/lỗi, số dòng, số camera, lý do bị loại, tổng theo bang), rồi commit.

Lưu ý:
- **Socrata chặn IP ngoài Mỹ** (data.cityofchicago.org, data.sf.gov, data.montgomerycountymd.gov, data.nola.gov trả 403). Chạy từ Việt Nam cần VPN Mỹ; GitHub Actions không bị.
- Python cài từ python.org trên macOS không đọc chứng chỉ gốc của hệ thống → script tự xuất từ keychain ra `cache/macos-roots.pem` (chỉ trên Mac).
- Một nguồn lỗi không làm dừng các nguồn khác: camera của nguồn đó được **giữ từ pack cũ**, REPORT ghi lý do.

## Cấu trúc

| File | Vai trò |
|---|---|
| `sources.json` | Danh sách nguồn + cách map trường (bảng dưới) |
| `state_bboxes.json` | Khung toạ độ từng bang — toạ độ ngoài khung bị loại |
| `build_packs.py` | Script chính |
| `test_build_packs.py` | Unittest |
| `fixtures/<id>.json` | ≤ 5 dòng thật của mỗi nguồn, lưu tự động ở lần tải đầu (chỉ dùng cho test) |
| `public/regions.json` | Danh sách vùng cho app (+ `sources` để hiện attribution) |
| `public/packs/us-xx.vN.json` | Data pack từng bang |
| `manifest.json` | Hash nội dung + version hiện tại của từng pack |
| `REPORT.md` | Báo cáo lần chạy gần nhất. Phần dưới dòng `<!-- PHẦN VIẾT TAY … -->` là viết tay, script giữ nguyên |
| `cache/` | Dữ liệu thô lần tải gần nhất (không commit) |

## Quy tắc chuẩn hoá

- `source` luôn `"openData"`, thêm `sourceId` = id nguồn.
- **Hướng** (hướng xe chạy bị giám sát): tách từ chữ — NB/N/B/Northbound → 0, NEB → 45, EB → 90, SEB → 135, SB → 180, SWB → 225, WB → 270, NWB → 315. Không có hướng, hoặc chuỗi có nhiều hướng khác nhau → `null`.
- **Limit**: chỉ lấy khi nguồn ghi đúng một con số (mph). Không có / nhiều số ("35 MPH / 20 MPH during school zone hours") → `null`. **Không đoán.**
- `roadName`: bỏ chữ hướng, "@"/"at" → "&", chuẩn hoá hoa/thường khi nguồn viết toàn chữ hoa.
- **Confidence**: `baseConfidence` khi dòng có trạng thái active; nguồn không có trạng thái → tối đa 80 (tier A) / 75 (tier B); dataset cập nhật > 12 tháng → −10; tối thiểu 50.
- `lastConfirmedAt` = ngày cập nhật dataset, hoặc ngày go-live của camera nếu mới hơn. Go-live trong tương lai → chưa đưa vào.
- **ID ổn định** (vote của người dùng gắn vào id): `<region>-<sourceId>-<key>[-<nb|sb|…>]`. Hậu tố hướng chỉ có ở nguồn tách theo approach. Không có key → 10 ký tự đầu SHA1 của `lat|lon|type|heading`.
- **Gộp trùng** trong cùng bang: cùng type, hướng lệch ≤ 30° (hoặc cả hai null), cách ≤ 30 m → giữ bản confidence cao hơn (bằng nhau thì tier A).
- **Version**: pack chỉ tăng version khi hash nội dung đổi; file version cũ bị xoá. `regions.json` tăng `version` khi nội dung đổi. `updatedAt` của vùng = ngày pack đổi version gần nhất.
- `regions.json` lấy template `../Speedwise/Resources/DataPacks/regions.json` (khi chạy trong repo app); không có thì dùng chính `public/regions.json` hiện tại. Bang Mỹ không có pack → "Community only" (không `packURL`, `cameraCount` 0).

## Thêm một nguồn

1. Chỉ dùng open data **chính thức** của cơ quan nhà nước (Socrata / ArcGIS REST). Không scrape HTML, không OpenStreetMap, không dữ liệu app/web thương mại.
2. Gọi metadata xem tên trường thật (`https://<domain>/api/views/<id>.json` hoặc `<layer>?f=json`).
3. Thêm 1 mục vào `sources.json`:

   | Trường | Ý nghĩa |
   |---|---|
   | `id`, `enabled`, `tier` | `tier` A = có license mở / terms cho dùng lại; B = cơ quan công khai nhưng không ghi license |
   | `region`, `coverage` | "US-DC"; `coverage` ghép vào `coverageNote` của vùng |
   | `publisher`, `name`, `landingURL`, `license`, `attribution` | Hiện trong app (màn Data sources) |
   | `endpoint`, `format` | `arcgis-geojson` (thêm `outSR=4326&f=geojson`), `socrata-json`, `socrata-geojson` |
   | `metadata` | `{"url", "dateKey"}` — nơi đọc ngày cập nhật dataset (`rowsUpdatedAt`, `editingInfo.lastEditDate`, `modified`); `null` nếu không có |
   | `rowDateField` | (tuỳ chọn) lấy ngày lớn nhất của trường này khi không có metadata |
   | `typeMap` | `{"const": "redLight"}` hoặc `{"field", "values": {giá trị nguồn: type}}`; giá trị không có trong `values` bị loại. `schoolZoneIfField`: speed → schoolZone khi trường này có giá trị |
   | `filters` | `[{"field", "in": [...]}]`, `{"notIn": [...]}`, `{"empty": true}` |
   | `fieldMap` | `lat`, `lon` (Socrata) hoặc `point`; ArcGIS dùng geometry. `key`, `road` (danh sách trường, lấy trường đầu có giá trị), `direction`, `limit`, `goLive`, `active` = `{"field", "activeValues", "inactiveValues"}` |
   | `approaches` | (tuỳ chọn) các trường approach → 1 camera cho mỗi approach |
   | `latestPeriodField` | (tuỳ chọn) chỉ giữ dòng của kỳ mới nhất (ví dụ "2024 Q4") |
   | `baseConfidence` | Confidence khi dòng active (thường 90 cho A, 80 cho B) |

4. Nếu bang chưa có trong `state_bboxes.json` thì thêm khung toạ độ.
5. `python3 build_packs.py --only <id>` → đọc REPORT.md, mở vài toạ độ trên Apple Maps xem có đúng đường không → `python3 -m unittest -v` → commit.
