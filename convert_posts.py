#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
posts.json → Jekyll _posts/ Markdown dönüşümü
"""
import json
import os
import re
from datetime import datetime

POSTS_JSON = r"F:\ODYOFILM\odyofilm-github\posts.json"
OUT_DIR    = r"F:\ODYOFILM\odyofilm-github\_posts"

with open(POSTS_JSON, encoding="utf-8") as f:
    data = json.load(f)

posts = [p for p in data["posts"] if p["type"] == "post"]
print(f"{len(posts)} post dönüştürülecek...", flush=True)

skipped = []
converted = 0

for post in posts:
    # ── tarih ve slug ────────────────────────────────────────────────────────
    date_raw = post.get("date", "2000-01-01 00:00:00")
    try:
        dt = datetime.strptime(date_raw[:19], "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y-%m-%d")
        date_full = dt.strftime("%Y-%m-%d %H:%M:%S +0300")
    except ValueError:
        date_str = "2000-01-01"
        date_full = "2000-01-01 00:00:00 +0300"

    slug = post.get("slug", "") or f"post-{post['id']}"
    # slug temizle: sadece harf, rakam, tire
    slug = re.sub(r'[^\w\-]', '-', slug).strip('-').lower()
    slug = re.sub(r'-+', '-', slug)

    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join(OUT_DIR, filename)

    # ── video bilgisi ────────────────────────────────────────────────────────
    videos = post.get("videos", [])
    video_type = ""
    video_id   = ""
    if videos:
        video_type = videos[0]["type"]
        video_id   = videos[0]["id"]

    # ── kategoriler ──────────────────────────────────────────────────────────
    categories = post.get("categories", [])
    tags       = post.get("tags", [])

    # Uncategorized / ackopek gibi gürültülü kategorileri temizle
    categories = [c for c in categories if c not in ("Uncategorized", "ackopek")]

    # ── başlık temizle ────────────────────────────────────────────────────────
    title = post.get("title", "").replace('"', '\\"').replace("'", "''")

    # ── excerpt ──────────────────────────────────────────────────────────────
    excerpt = (post.get("excerpt") or "").strip()
    excerpt = re.sub(r'\s+', ' ', excerpt)[:200]

    # ── içerik temizle ───────────────────────────────────────────────────────
    content = post.get("content", "") or ""
    # wp:block yorumlarını kaldır
    content = re.sub(r'<!--\s*/?wp:[^>]*-->', '', content)
    # gereksiz boş satırları topla
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    # zaten video embed var, içerikteki tekrar eden iframe'leri kaldır
    if video_id:
        content = re.sub(r'<iframe[^>]*' + re.escape(video_id) + r'[^>]*>.*?</iframe>', '', content, flags=re.DOTALL)
    content = content.strip()

    # ── thumbnail ────────────────────────────────────────────────────────────
    thumbnail = post.get("thumbnail_url", "")

    # ── YAML frontmatter ─────────────────────────────────────────────────────
    cats_yaml  = json.dumps(categories, ensure_ascii=False)
    tags_yaml  = json.dumps(tags, ensure_ascii=False)

    frontmatter = f"""---
layout: post
title: "{title}"
date: {date_full}
categories: {cats_yaml}
tags: {tags_yaml}
"""
    if video_type:
        frontmatter += f'video_type: "{video_type}"\n'
        frontmatter += f'video_id: "{video_id}"\n'
    if thumbnail:
        frontmatter += f'thumbnail: "{thumbnail}"\n'
    if excerpt:
        safe_excerpt = excerpt.replace('"', '\\"')
        frontmatter += f'excerpt: "{safe_excerpt}"\n'

    frontmatter += "---\n"

    # ── dosyaya yaz ──────────────────────────────────────────────────────────
    body = frontmatter
    if content:
        body += "\n" + content + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(body)

    converted += 1

print(f"\n✓ {converted} post dönüştürüldü → {OUT_DIR}", flush=True)
print(f"  Atlanan: {len(skipped)}", flush=True)

# ── özet ─────────────────────────────────────────────────────────────────────
with_video  = sum(1 for p in posts if p.get("videos"))
yt_count    = sum(1 for p in posts for v in p.get("videos",[]) if v["type"]=="youtube")
vim_count   = sum(1 for p in posts for v in p.get("videos",[]) if v["type"]=="vimeo")
print(f"  YouTube: {yt_count} | Vimeo: {vim_count} | videosuz: {len(posts)-with_video}", flush=True)
