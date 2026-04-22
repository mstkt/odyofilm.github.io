#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress SQL dump parser — odyofilm migration
Çıktı: posts.json (published posts + categories + video embeds)
"""
import re
import json

SQL_FILE = r"F:\ODYOFILM\backup-4.10.2025_22-53-22_odyofilm\mysql\pagzi857_odyofilm.sql"
OUT_FILE = r"F:\ODYOFILM\odyofilm-github\posts.json"

print("SQL dosyası okunuyor...", flush=True)
with open(SQL_FILE, encoding="utf-8", errors="replace") as f:
    sql = f.read()
print(f"Dosya boyutu: {len(sql):,} karakter", flush=True)


# ── state-machine satır ayrıştırıcı ─────────────────────────────────────────
def parse_insert_values(values_chunk):
    """VALUES (...),(...) bloğunu satırlara ayır — nested parens & strings OK."""
    rows = []
    i = 0
    n = len(values_chunk)
    while i < n:
        while i < n and values_chunk[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1
        depth = 1
        in_str = False
        escape = False
        chars = []
        while i < n and depth > 0:
            c = values_chunk[i]
            if escape:
                chars.append(c)
                escape = False
            elif c == '\\':
                chars.append(c)
                escape = True
            elif c == "'" and not in_str:
                in_str = True
                chars.append(c)
            elif c == "'" and in_str:
                in_str = False
                chars.append(c)
            elif not in_str and c == '(':
                depth += 1
                chars.append(c)
            elif not in_str and c == ')':
                depth -= 1
                if depth > 0:
                    chars.append(c)
            else:
                chars.append(c)
            i += 1
        rows.append(''.join(chars))
    return rows


def split_row(row_str):
    """Virgülle ayrılmış değerleri ayır — string içindeki virgülleri atla."""
    values = []
    buf = []
    in_str = False
    escape = False
    for c in row_str:
        if escape:
            buf.append(c)
            escape = False
        elif c == '\\':
            buf.append(c)
            escape = True
        elif c == "'" and not in_str:
            in_str = True
            buf.append(c)
        elif c == "'" and in_str:
            in_str = False
            buf.append(c)
        elif c == ',' and not in_str:
            values.append(clean_val(''.join(buf).strip()))
            buf = []
        else:
            buf.append(c)
    if buf:
        values.append(clean_val(''.join(buf).strip()))
    return values


def clean_val(v):
    if v == 'NULL':
        return None
    if v.startswith("'") and v.endswith("'"):
        v = v[1:-1]
        v = v.replace("\\'", "'")
        v = v.replace('\\"', '"')
        v = v.replace("\\n", "\n")
        v = v.replace("\\r", "\r")
        v = v.replace("\\t", "\t")
        v = v.replace("\\\\", "\\")
        return v
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def extract_table(sql_text, table_name):
    """Bir tablonun TÜM INSERT bloklarındaki satırları birleştirerek döndür."""
    pattern = rf"INSERT INTO `{table_name}` \(([^)]+)\) VALUES "
    all_rows = []
    cols = None

    for m in re.finditer(pattern, sql_text):
        if cols is None:
            cols = [c.strip().strip('`') for c in m.group(1).split(',')]

        # VALUES başlangıcı: match sonrası
        chunk_start = m.end()
        # Bu INSERT'in sonu: en yakın ';\n' veya dosya sonu
        chunk_end = sql_text.find(';\n', chunk_start)
        if chunk_end == -1:
            chunk_end = len(sql_text)

        values_chunk = sql_text[chunk_start:chunk_end]
        raw_rows = parse_insert_values(values_chunk)

        for raw in raw_rows:
            vals = split_row(raw)
            if len(vals) >= len(cols):
                all_rows.append(dict(zip(cols, vals[:len(cols)])))

    return all_rows


# ── tabloları parse et ──────────────────────────────────────────────────────
print("wp_posts parse ediliyor...", flush=True)
posts_rows = extract_table(sql, "wp_posts")
print(f"  {len(posts_rows)} satır", flush=True)

print("wp_postmeta parse ediliyor...", flush=True)
meta_rows = extract_table(sql, "wp_postmeta")
print(f"  {len(meta_rows)} satır", flush=True)

print("wp_terms parse ediliyor...", flush=True)
terms_rows = extract_table(sql, "wp_terms")
print(f"  {len(terms_rows)} satır", flush=True)

print("wp_term_taxonomy parse ediliyor...", flush=True)
taxonomy_rows = extract_table(sql, "wp_term_taxonomy")
print(f"  {len(taxonomy_rows)} satır", flush=True)

print("wp_term_relationships parse ediliyor...", flush=True)
rel_rows = extract_table(sql, "wp_term_relationships")
print(f"  {len(rel_rows)} satır", flush=True)

print("wp_options parse ediliyor...", flush=True)
options_rows = extract_table(sql, "wp_options")
print(f"  {len(options_rows)} satır", flush=True)

# ── site meta ───────────────────────────────────────────────────────────────
site_meta = {}
for opt in options_rows:
    if opt.get("option_name") in ("blogname", "blogdescription", "siteurl", "home"):
        site_meta[opt["option_name"]] = opt.get("option_value")
print(f"\nSite: {site_meta.get('blogname')} | {site_meta.get('siteurl')}", flush=True)

# ── kategori haritası ────────────────────────────────────────────────────────
terms_by_id = {t["term_id"]: t for t in terms_rows}
taxonomy_by_ttid = {t["term_taxonomy_id"]: t for t in taxonomy_rows}

category_map = {}
for ttid, tt in taxonomy_by_ttid.items():
    if tt.get("taxonomy") in ("category", "post_tag"):
        term = terms_by_id.get(tt["term_id"], {})
        category_map[ttid] = {
            "name": term.get("name", ""),
            "slug": term.get("slug", ""),
            "taxonomy": tt.get("taxonomy"),
        }

post_categories = {}
for rel in rel_rows:
    pid = rel.get("object_id")
    ttid = rel.get("term_taxonomy_id")
    if pid and ttid in category_map:
        post_categories.setdefault(pid, []).append(category_map[ttid])

# ── postmeta haritası ────────────────────────────────────────────────────────
post_meta_map = {}
for m in meta_rows:
    pid = m.get("post_id")
    key = m.get("meta_key", "")
    val = m.get("meta_value")
    if pid:
        post_meta_map.setdefault(pid, {})[key] = val

# ── attachment guid haritası ─────────────────────────────────────────────────
attachment_guid = {}
for p in posts_rows:
    if p.get("post_type") == "attachment":
        attachment_guid[p["ID"]] = p.get("guid", "")

print(f"Attachment (görsel) sayısı: {len(attachment_guid)}", flush=True)


# ── video tespiti ─────────────────────────────────────────────────────────────
def extract_videos(content, postmeta):
    videos = []

    def add_yt(vid):
        if vid and len(vid) == 11 and not any(v["id"] == vid for v in videos):
            videos.append({"type": "youtube", "id": vid})

    def add_vim(vid):
        if vid and not any(v["id"] == vid for v in videos):
            videos.append({"type": "vimeo", "id": vid})

    text = content or ""

    # iframe embed'ler
    for vid in re.findall(r'youtube\.com/embed/([A-Za-z0-9_\-]{11})', text):
        add_yt(vid)
    for vid in re.findall(r'youtu\.be/([A-Za-z0-9_\-]{11})', text):
        add_yt(vid)
    for vid in re.findall(r'[?&]v=([A-Za-z0-9_\-]{11})', text):
        add_yt(vid)
    for vid in re.findall(r'vimeo\.com/(?:video/)?(\d{5,11})', text):
        add_vim(vid)

    # postmeta: td_last_set_video önce (en temiz URL)
    for key in ("td_last_set_video", "td_post_video"):
        val = postmeta.get(key) or ""
        if val:
            for vid in re.findall(r'youtube\.com/embed/([A-Za-z0-9_\-]{11})', val):
                add_yt(vid)
            for vid in re.findall(r'youtu\.be/([A-Za-z0-9_\-]{11})', val):
                add_yt(vid)
            for vid in re.findall(r'[?&]v=([A-Za-z0-9_\-]{11})', val):
                add_yt(vid)
            for vid in re.findall(r'vimeo\.com/(?:video/)?(\d{5,11})', val):
                add_vim(vid)

    return videos


# ── ana dönüşüm ──────────────────────────────────────────────────────────────
published = []
for p in posts_rows:
    if p.get("post_status") != "publish":
        continue
    if p.get("post_type") not in ("post", "page"):
        continue

    pid = p["ID"]
    meta = post_meta_map.get(pid, {})

    thumb_id = meta.get("_thumbnail_id")
    thumb_url = ""
    if thumb_id:
        try:
            thumb_url = attachment_guid.get(int(thumb_id), "")
        except (ValueError, TypeError):
            pass

    cats = post_categories.get(pid, [])
    categories = [c["name"] for c in cats if c.get("taxonomy") == "category"]
    tags = [c["name"] for c in cats if c.get("taxonomy") == "post_tag"]

    content = p.get("post_content", "") or ""
    videos = extract_videos(content, meta)

    # shortcode temizle
    clean = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', content).strip()

    published.append({
        "id": pid,
        "title": p.get("post_title", ""),
        "slug": p.get("post_name", ""),
        "date": str(p.get("post_date", "")),
        "modified": str(p.get("post_modified", "")),
        "type": p.get("post_type"),
        "excerpt": (p.get("post_excerpt") or "").strip(),
        "content": clean,
        "categories": categories,
        "tags": tags,
        "thumbnail_url": thumb_url,
        "videos": videos,
    })

published.sort(key=lambda x: x["date"], reverse=True)

# ── özet ─────────────────────────────────────────────────────────────────────
only_posts = [p for p in published if p["type"] == "post"]
print(f"\n✓ Publish post: {len(only_posts)} | page: {sum(1 for p in published if p['type']=='page')}", flush=True)

all_cats = {}
for p in only_posts:
    for c in p["categories"]:
        all_cats[c] = all_cats.get(c, 0) + 1

print("\nKategoriler:", flush=True)
for cat, count in sorted(all_cats.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}", flush=True)

has_video = [p for p in only_posts if p["videos"]]
no_video = [p for p in only_posts if not p["videos"]]
yt = sum(1 for p in only_posts for v in p["videos"] if v["type"] == "youtube")
vim = sum(1 for p in only_posts for v in p["videos"] if v["type"] == "vimeo")

print(f"\nVideo embed'li: {len(has_video)} | embed'siz: {len(no_video)}", flush=True)
print(f"YouTube: {yt} | Vimeo: {vim}", flush=True)

print("\nİlk 10 yazı:", flush=True)
for p in only_posts[:10]:
    vids = p["videos"]
    vid_str = f"[{vids[0]['type']}:{vids[0]['id']}]" if vids else "[video yok]"
    print(f"  [{p['id']}] {p['title'][:55]:<55} {p['date'][:10]}  {vid_str}", flush=True)

print("\nVideo embed'siz yazılar:", flush=True)
for p in no_video[:15]:
    print(f"  [{p['id']}] {p['title'][:65]}  {p['date'][:10]}", flush=True)

# ── kaydet ───────────────────────────────────────────────────────────────────
output = {
    "site": site_meta,
    "post_count": len(only_posts),
    "posts": published,
}
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n✓ Kaydedildi: {OUT_FILE}", flush=True)
