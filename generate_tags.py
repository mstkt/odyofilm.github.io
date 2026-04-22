#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, re

with open("posts.json", encoding="utf-8") as f:
    data = json.load(f)

tags = set()
for p in data["posts"]:
    if p["type"] == "post":
        for t in p.get("tags", []):
            if t:
                tags.add(t)

os.makedirs("tags", exist_ok=True)

for tag in tags:
    slug = re.sub(r'[^\w\-]', '-', tag).strip('-').lower()
    slug = re.sub(r'-+', '-', slug)
    tag_dir = os.path.join("tags", slug)
    os.makedirs(tag_dir, exist_ok=True)
    content = f'''---
layout: tag
title: "{tag.replace('"', '\\"')}"
tag: "{tag.replace('"', '\\"')}"
permalink: /tags/{slug}/
---
'''
    with open(os.path.join(tag_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(content)

print(f"{len(tags)} tag sayfası oluşturuldu → tags/")
