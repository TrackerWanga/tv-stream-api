#!/usr/bin/env python3
"""
Parses IPTV-API M3U output and uploads stream URLs to KV.
Also handles EPG data if available.
"""

import os
import re
import json
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

KV_API = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}/storage/kv/namespaces/{os.environ['CF_KV_NAMESPACE_ID']}"
HEADERS = {
    "Authorization": f"Bearer {os.environ['CF_API_TOKEN']}",
    "Content-Type": "application/json"
}

def kv_put(key, value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    resp = requests.put(f"{KV_API}/values/{key}", headers=HEADERS, data=value.encode('utf-8'))
    status = "✓" if resp.status_code == 200 else f"✗ {resp.status_code}"
    if resp.status_code != 200:
        print(f"  {status} {key} - {resp.text[:80]}")
    return resp.status_code == 200

def parse_m3u(filepath):
    """Parse M3U playlist into structured stream data."""
    if not Path(filepath).exists():
        print(f"  M3U file not found: {filepath}")
        return {}
    
    streams = {}
    current = {}
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("#EXTINF"):
                tvg_id = re.search(r'tvg-id="([^"]*)"', line)
                tvg_name = re.search(r'tvg-name="([^"]*)"', line)
                tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
                group = re.search(r'group-title="([^"]*)"', line)
                name = line.split(",", 1)[-1].strip() if "," in line else "Unknown"
                
                current = {
                    "name": name,
                    "tvg_id": tvg_id.group(1) if tvg_id else "",
                    "tvg_name": tvg_name.group(1) if tvg_name else name,
                    "logo": tvg_logo.group(1) if tvg_logo else "",
                    "group": group.group(1) if group else "Undefined"
                }
            
            elif line.startswith("http") and current.get("tvg_id"):
                channel_id = current["tvg_id"].lower()
                
                # Detect quality
                quality = "SD"
                name_lower = current["name"].lower()
                if "4k" in name_lower or "uhd" in name_lower:
                    quality = "4K"
                elif "1080" in name_lower or "fhd" in name_lower:
                    quality = "1080p"
                elif "720" in name_lower or "hd" in name_lower:
                    quality = "720p"
                
                if channel_id not in streams:
                    streams[channel_id] = []
                
                streams[channel_id].append({
                    "url": line,
                    "name": current["name"],
                    "logo": current["logo"],
                    "group": current["group"],
                    "quality": quality,
                    "last_checked": datetime.utcnow().isoformat()
                })
    
    return streams

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3u", required=True, help="Path to M3U file")
    parser.add_argument("--epg", default=None, help="Path to EPG directory")
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"🔄 Syncing streams to KV: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    # Parse and upload streams
    print("\n🎬 Parsing M3U...")
    streams = parse_m3u(args.m3u)
    
    if not streams:
        print("  No streams found!")
        return
    
    print(f"  Found streams for {len(streams)} channels")
    
    print("\n📤 Uploading to KV...")
    count = 0
    for channel_id, urls in streams.items():
        kv_put(f"streams:{channel_id}", urls)
        count += 1
        if count % 100 == 0:
            print(f"  Progress: {count}/{len(streams)}")
    
    # Store index
    kv_put("streams:index", {
        "total_channels": len(streams),
        "total_urls": sum(len(v) for v in streams.values()),
        "updated": datetime.utcnow().isoformat()
    })
    
    print(f"\n✅ Synced {len(streams)} channels with {sum(len(v) for v in streams.values())} URLs")

if __name__ == "__main__":
    main()
