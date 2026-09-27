#!/bin/sh
# Chép regions.json + mọi pack trong public/ vào bản đóng gói của app
# (../Speedwise/Resources/DataPacks/). Xoá pack bang cũ trong app không còn được regions.json trỏ tới.
# Chạy sau build_packs.py: sh sync_to_app.sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
src="$here/public"
dest="$here/../Speedwise/Resources/DataPacks"

if [ ! -f "$src/regions.json" ]; then
    echo "Không thấy $src/regions.json — chạy build_packs.py trước." >&2
    exit 1
fi
if [ ! -d "$dest" ]; then
    echo "Không thấy thư mục app $dest — script phải nằm trong data-pipeline/ của repo app." >&2
    exit 1
fi

# Tên file pack mà regions.json đang trỏ tới ("packs/us-dc.v1.json" → "us-dc.v1.json").
referenced=$(python3 -c '
import json, os, sys
config = json.load(open(sys.argv[1]))
for region in config["regions"]:
    if region.get("packURL"):
        print(os.path.basename(region["packURL"]))
' "$src/regions.json")

for name in $referenced; do
    if [ ! -f "$src/packs/$name" ]; then
        echo "regions.json trỏ tới packs/$name nhưng file không có trong public/packs/." >&2
        exit 1
    fi
done

cp "$src/regions.json" "$dest/regions.json"
echo "chép regions.json"
for file in "$src"/packs/*.json; do
    cp "$file" "$dest/"
    echo "chép $(basename "$file")"
done

# Pack cũ trong app (tên dạng <vùng>.v<N>.json) mà regions.json không còn trỏ tới → xoá.
for file in "$dest"/*.v*.json; do
    [ -e "$file" ] || continue
    name=$(basename "$file")
    if ! printf '%s\n' $referenced | grep -qx "$name"; then
        rm "$file"
        echo "xoá $name (không còn trong regions.json)"
    fi
done
