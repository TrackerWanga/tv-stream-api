#!/usr/bin/env python3
"""
Fetch ALL IPTV sources and extract every stream URL.
Sources:
  1. iptv-org index.m3u (10K+ channels)
  2. iptv-org category playlists
  3. Free-TV/IPTV community list
  4. Our curated working streams
  5. Hardcoded reliable URLs
"""

import requests
import re
import json
from pathlib import Path

SOURCES = [
    "https://iptv-org.github.io/iptv/index.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/entertainment.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/education.m3u",
    "https://iptv-org.github.io/iptv/categories/religious.m3u",
    "https://iptv-org.github.io/iptv/categories/business.m3u",
    "https://iptv-org.github.io/iptv/categories/lifestyle.m3u",
    "https://iptv-org.github.io/iptv/categories/travel.m3u",
    "https://iptv-org.github.io/iptv/categories/cooking.m3u",
    "https://iptv-org.github.io/iptv/categories/science.m3u",
    "https://iptv-org.github.io/iptv/categories/culture.m3u",
    "https://iptv-org.github.io/iptv/categories/comedy.m3u",
    "https://iptv-org.github.io/iptv/categories/animation.m3u",
    "https://iptv-org.github.io/iptv/categories/family.m3u",
    "https://iptv-org.github.io/iptv/categories/weather.m3u",
    "https://iptv-org.github.io/iptv/categories/shop.m3u",
    "https://iptv-org.github.io/iptv/categories/auto.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
]

HARDCODED = {
    "France24English.fr": {
        "url": "https://static.france24.com/live/F24_EN_LO_HLS/live_web.m3u8",
        "name": "France 24 English", "country": "FR", "categories": ["news"]
    },
    "France24French.fr": {
        "url": "https://static.france24.com/live/F24_FR_LO_HLS/live_web.m3u8",
        "name": "France 24 French", "country": "FR", "categories": ["news"]
    },
    "France24Arabic.fr": {
        "url": "https://static.france24.com/live/F24_AR_LO_HLS/live_web.m3u8",
        "name": "France 24 Arabic", "country": "FR", "categories": ["news"]
    },
    "France24Spanish.fr": {
        "url": "https://static.france24.com/live/F24_ES_LO_HLS/live_web.m3u8",
        "name": "France 24 Spanish", "country": "FR", "categories": ["news"]
    },
    "Bloomberg.us": {
        "url": "https://www.bloomberg.com/media-manifest/streams/us.m3u8",
        "name": "Bloomberg TV US", "country": "US", "categories": ["news", "business"]
    },
    "BloombergEurope.us": {
        "url": "https://www.bloomberg.com/media-manifest/streams/eu.m3u8",
        "name": "Bloomberg TV Europe", "country": "US", "categories": ["news", "business"]
    },
    "DWEnglish.de": {
        "url": "https://dwamdstream102.akamaized.net/dw/102/102/mp4:dw-101.mp4/playlist.m3u8",
        "name": "DW English", "country": "DE", "categories": ["news"]
    },
    "CGTN.cn": {
        "url": "https://news.cgtn.com/resource/live/english/cgtn-news.m3u8",
        "name": "CGTN News", "country": "CN", "categories": ["news"]
    },
    "NHKWorld.jp": {
        "url": "https://nhkworld.webcdn.stream.ne.jp/www11/nhkworld-tv/global/2003458/live.m3u8",
        "name": "NHK World Japan", "country": "JP", "categories": ["news"]
    },
    "BBCOne.uk": {
        "url": "https://vs-cmaf-pushb-uk-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_one_channel_islands/iptv_mse_v0_hevc.mpd",
        "name": "BBC One", "country": "UK", "categories": ["general", "entertainment"]
    },
    "BBCNews.uk": {
        "url": "https://vs-cmaf-pushb-uk-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_news24/iptv_mse_v0_hevc.mpd",
        "name": "BBC News", "country": "UK", "categories": ["news"]
    },
}

def parse_m3u(text, source_name):
    """Extract all streams from M3U text."""
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
                "tvg_id": tvg_id.group(1) if tvg_id else "",
                "tvg_name": tvg_name.group(1) if tvg_name else name,
                "logo": tvg_logo.group(1) if tvg_logo else "",
                "group": group.group(1) if group else "Undefined",
                "source": source_name
            }
        
        elif line.startswith("http") and current:
            stream_id = current["tvg_id"] or re.sub(r'[^a-zA-Z0-9]', '', current["name"])
            if stream_id not in streams:
                streams[stream_id] = {
                    "id": stream_id,
                    "name": current["tvg_name"] or current["name"],
                    "url": line,
                    "logo": current["logo"],
                    "group": current["group"],
                    "source": source_name
                }
            current = {}
    
    return streams

def main():
    all_streams = {}
    
    # Fetch M3U sources
    for url in SOURCES:
        source_name = url.split('/')[-1].replace('.m3u', '').replace('.m3u8', '')
        print(f"📥 Fetching: {source_name}...")
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                streams = parse_m3u(resp.text, source_name)
                print(f"  ✅ {len(streams)} streams")
                all_streams.update(streams)
            else:
                print(f"  ❌ HTTP {resp.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Add hardcoded reliable streams
    print(f"\n📥 Adding hardcoded streams: {len(HARDCODED)}")
    for sid, info in HARDCODED.items():
        all_streams[sid] = {
            "id": sid,
            "name": info["name"],
            "url": info["url"],
            "logo": "",
            "group": info["categories"][0] if info["categories"] else "general",
            "source": "curated",
            "country": info.get("country", ""),
            "categories": info.get("categories", [])
        }
    
    # Save
    output_path = Path("data/raw_streams.json")
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(all_streams, f, indent=2)
    
    print(f"\n✅ Total streams extracted: {len(all_streams)}")
    print(f"   Saved to data/raw_streams.json")

if __name__ == "__main__":
    main()
