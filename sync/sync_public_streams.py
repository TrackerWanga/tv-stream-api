#!/usr/bin/env python3
"""
Downloads public IPTV playlists and syncs them to KV.
Matches streams to metadata channels by name for correct IDs.
Includes rate limiting for KV free tier.
"""

import os
import re
import json
import time
import requests
from datetime import datetime, timezone

PUBLIC_SOURCES = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
]

KV_API = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/storage/kv/namespaces/{os.environ['CF_KV_NAMESPACE_ID']}"
HEADERS = {
    "Authorization": f"Bearer {os.environ['CF_API_TOKEN']}",
    "Content-Type": "application/json"
}

def kv_put(key, value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    time.sleep(0.3)  # Rate limit: ~3 writes/sec (safe for free tier)
    resp = requests.put(f"{KV_API}/values/{key}", headers=HEADERS, data=value.encode('utf-8'))
    if resp.status_code == 200:
        print(f"  ✓ {key}")
    else:
        print(f"  ✗ {key} - {resp.status_code}")
    return resp.status_code == 200

def kv_get(key):
    resp = requests.get(f"{KV_API}/values/{key}", headers=HEADERS)
    if resp.status_code == 200:
        return json.loads(resp.text)
    return None

def load_channel_index():
    light = kv_get("channels:light")
    if not light:
        print("  ⚠ No channel metadata in KV, falling back to raw IDs")
        return {}
    name_map = {}
    for c in light:
        name_lower = c["name"].lower().strip()
        name_map[name_lower] = c["id"]
    return name_map

def normalize_name(name):
    name = name.lower().strip()
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def find_metadata_id(stream_name, name_map):
    clean = normalize_name(stream_name)
    if clean in name_map:
        return name_map[clean]
    for suffix in [' hd', ' fhd', ' sd', ' 4k', ' uhd', ' 1080p', ' 720p']:
        if clean.endswith(suffix):
            shorter = clean[:-len(suffix)].strip()
            if shorter in name_map:
                return name_map[shorter]
    first_word = clean.split()[0] if clean.split() else ''
    for name, mid in name_map.items():
        if name.startswith(first_word) and len(first_word) > 3:
            return mid
    return None

def parse_m3u(text, name_map):
    streams = {}
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith("#EXTINF"):
            tvg_id = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name = re.search(r'tvg-name="([^"]*)"', line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
            group = re.search(r'group-title="([^"]*)"', line)
            name = line.split(",", 1)[-1].strip() if "," in line else "Unknown"
            metadata_id = None
            if tvg_id and tvg_id.group(1):
                metadata_id = tvg_id.group(1).lower()
            else:
                metadata_id = find_metadata_id(name, name_map)
            if not metadata_id:
                metadata_id = re.sub(r'[^a-z0-9-]', '-', name.lower())
                metadata_id = re.sub(r'-+', '-', metadata_id).strip('-')
            current = {
                "name": name,
                "tvg_id": metadata_id,
                "tvg_name": tvg_name.group(1) if tvg_name else name,
                "logo": tvg_logo.group(1) if tvg_logo else "",
                "group": group.group(1) if group else "Undefined"
            }
        elif line.startswith("http") and current:
            channel_id = current["tvg_id"]
            if channel_id not in streams:
                streams[channel_id] = []
            quality = "SD"
            name_lower = current["name"].lower()
            if "4k" in name_lower or "uhd" in name_lower:
                quality = "4K"
            elif "1080" in name_lower or "fhd" in name_lower:
                quality = "1080p"
            elif "720" in name_lower or "hd" in name_lower:
                quality = "720p"
            if not any(s["url"] == line for s in streams[channel_id]):
                streams[channel_id].append({
                    "url": line,
                    "name": current["name"],
                    "logo": current["logo"],
                    "group": current["group"],
                    "quality": quality,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                })
    return streams

def main():
    print("=" * 60)
    print(f"🔄 Syncing streams with metadata matching")
    print(f"   {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    print("\n📚 Loading metadata index...")
    name_map = load_channel_index()
    print(f"  ✓ {len(name_map)} names indexed")
    
    all_streams = {}
    for url in PUBLIC_SOURCES:
        print(f"\n📥 {url.split('/')[-1]}")
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "TV-API/1.0"})
            if resp.status_code == 200:
                streams = parse_m3u(resp.text, name_map)
                print(f"  Found {len(streams)} channels")
                for ch_id, urls in streams.items():
                    if ch_id not in all_streams:
                        all_streams[ch_id] = []
                    all_streams[ch_id].extend(urls)
            else:
                print(f"  HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"\n📤 Uploading {len(all_streams)} channels to KV (rate-limited)...")
    count = 0
    for channel_id, urls in all_streams.items():
        kv_put(f"streams:{channel_id}", urls[:5])
        count += 1
        if count % 100 == 0:
            print(f"  {count}/{len(all_streams)} (~{int(count/3)}s elapsed)")
    
    total_urls = sum(len(v) for v in all_streams.values())
    kv_put("streams:index", {
        "total_channels": len(all_streams),
        "total_urls": total_urls,
        "updated": datetime.now(timezone.utc).isoformat()
    })
    
    print(f"\n✅ Done: {len(all_streams)} channels, {total_urls} URLs")

if __name__ == "__main__":
    main()
