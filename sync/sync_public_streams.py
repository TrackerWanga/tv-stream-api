#!/usr/bin/env python3
"""
Downloads public IPTV playlists and syncs them to KV.
No crawling needed — just fetches and parses.
"""

import os
import re
import json
import requests
from datetime import datetime, timezone

# Public IPTV playlists (free, community-maintained)
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
    resp = requests.put(f"{KV_API}/values/{key}", headers=HEADERS, data=value.encode('utf-8'))
    if resp.status_code == 200:
        print(f"  ✓ {key}")
    else:
        print(f"  ✗ {key} - {resp.status_code}")
    return resp.status_code == 200

def parse_m3u(text):
    """Parse M3U text into structured stream data."""
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
            
            current = {
                "name": name,
                "tvg_id": tvg_id.group(1) if tvg_id else name.lower().replace(' ', '-'),
                "tvg_name": tvg_name.group(1) if tvg_name else name,
                "logo": tvg_logo.group(1) if tvg_logo else "",
                "group": group.group(1) if group else "Undefined"
            }
        
        elif line.startswith("http") and current:
            channel_id = (current["tvg_id"] or current["name"]).lower()
            channel_id = re.sub(r'[^a-z0-9-]', '-', channel_id)
            
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
            
            # Avoid duplicates
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
    print(f"🔄 Syncing public IPTV streams: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    all_streams = {}
    
    for url in PUBLIC_SOURCES:
        print(f"\n📥 Downloading: {url}")
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "TV-API/1.0"})
            if resp.status_code == 200:
                streams = parse_m3u(resp.text)
                print(f"  Found {len(streams)} channels")
                for ch_id, urls in streams.items():
                    if ch_id not in all_streams:
                        all_streams[ch_id] = []
                    all_streams[ch_id].extend(urls)
            else:
                print(f"  Failed: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"\n📤 Uploading {len(all_streams)} channels to KV...")
    
    count = 0
    for channel_id, urls in all_streams.items():
        kv_put(f"streams:{channel_id}", urls[:5])  # Max 5 URLs per channel
        count += 1
        if count % 200 == 0:
            print(f"  Progress: {count}/{len(all_streams)}")
    
    # Store index
    total_urls = sum(len(v) for v in all_streams.values())
    kv_put("streams:index", {
        "total_channels": len(all_streams),
        "total_urls": total_urls,
        "updated": datetime.now(timezone.utc).isoformat()
    })
    
    print(f"\n✅ Synced {len(all_streams)} channels with {total_urls} URLs")

if __name__ == "__main__":
    main()
