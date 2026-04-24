"""
vimeo_youtube_map.csv dosyasında 'confirmed' = 'YES' olan satırları uygular.
video_type: vimeo -> youtube, video_id güncellenir.
"""

import os
import re
import csv

POSTS_DIR = "_posts"
INPUT_CSV = "vimeo_youtube_map.csv"

def update_post(filepath, youtube_id):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r'video_type:\s*"vimeo"', 'video_type: "youtube"', content)
    old_id = re.search(r'video_id:\s*"?(\w+)"?', content)
    if old_id:
        content = content.replace(old_id.group(0), f'video_id: "{youtube_id}"')

    # Vimeo embed paragraflarını temizle
    content = re.sub(
        r'<p><a href="https://vimeo\.com/.*?</p>\n?', '', content, flags=re.DOTALL
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Hata: {INPUT_CSV} bulunamadı. Önce find_youtube_ids.py çalıştır.")
        return

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    confirmed = [r for r in rows if r.get("confirmed", "").strip().upper() == "YES"]
    print(f"Onaylanan: {len(confirmed)} / {len(rows)}")

    updated = 0
    for row in confirmed:
        filepath = os.path.join(POSTS_DIR, row["filename"])
        if not os.path.exists(filepath):
            print(f"  BULUNAMADI: {filepath}")
            continue
        if not row["youtube_id"]:
            print(f"  YouTube ID yok: {row['filename']}")
            continue
        update_post(filepath, row["youtube_id"])
        print(f"  Güncellendi: {row['filename']} -> {row['youtube_id']}")
        updated += 1

    print(f"\nToplam güncellenen dosya: {updated}")

if __name__ == "__main__":
    main()
