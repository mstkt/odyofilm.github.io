"""
Vimeo post'larını tarayıp YouTube karşılıklarını bulan script.
Çıktı: vimeo_youtube_map.csv (gözden geçirme için)
"""

import os
import re
import subprocess
import json
import csv
import time
import sys

sys.stdout.reconfigure(encoding="utf-8")

POSTS_DIR = "_posts"
OUTPUT_CSV = "vimeo_youtube_map.csv"

def search_youtube(query, retries=2):
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["python", "-m", "yt_dlp", "--dump-json", "--no-download",
                 "--no-warnings", f"ytsearch1:{query}"],
                capture_output=True, text=True, timeout=20
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip().split('\n')[0])
                return data.get("id"), data.get("title"), data.get("webpage_url")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
    return None, None, None

def extract_frontmatter(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"')
    return fm

def main():
    files = [f for f in os.listdir(POSTS_DIR) if f.endswith(".md")]
    vimeo_files = []
    for filename in files:
        path = os.path.join(POSTS_DIR, filename)
        fm = extract_frontmatter(path)
        if fm and fm.get("video_type") == "vimeo":
            vimeo_files.append((filename, fm))

    print(f"Toplam Vimeo post: {len(vimeo_files)}")

    results = []
    for i, (filename, fm) in enumerate(vimeo_files):
        title = fm.get("title", "")
        vimeo_id = fm.get("video_id", "")
        query = f"{title} official music video"
        print(f"[{i+1}/{len(vimeo_files)}] Aranıyor: {title}")

        yt_id, yt_title, yt_url = search_youtube(query)

        results.append({
            "filename": filename,
            "post_title": title,
            "vimeo_id": vimeo_id,
            "youtube_id": yt_id or "",
            "youtube_title": yt_title or "",
            "youtube_url": yt_url or "",
            "confirmed": ""  # manuel onay için boş bırak
        })

        # CSV'e her adımda yaz (crash durumunda kayıp olmasın)
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

        time.sleep(0.5)  # rate limiting

    print(f"\nTamamlandı. Sonuçlar: {OUTPUT_CSV}")
    print("CSV'i aç, 'confirmed' sütununa doğru eşleşmeler için 'YES', yanlışlar için 'NO' yaz.")
    print("Sonra apply_youtube_ids.py scriptini çalıştır.")

if __name__ == "__main__":
    main()
