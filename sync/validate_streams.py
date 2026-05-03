#!/usr/bin/env python3
"""
Validates known stream URLs and saves working ones to data/streams.json.
Run by GitHub Actions every 30 minutes.
"""

import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Known working free streams (community-maintained)
STREAM_SOURCES = {
    # News
    "France24English.fr": "https://static.france24.com/live/F24_EN_LO_HLS/live_web.m3u8",
    "France24French.fr": "https://static.france24.com/live/F24_FR_LO_HLS/live_web.m3u8",
    "France24Arabic.fr": "https://static.france24.com/live/F24_AR_LO_HLS/live_web.m3u8",
    "France24Spanish.fr": "https://static.france24.com/live/F24_ES_LO_HLS/live_web.m3u8",
    "Bloomberg.us": "https://www.bloomberg.com/media-manifest/streams/us.m3u8",
    "BloombergEurope.us": "https://www.bloomberg.com/media-manifest/streams/eu.m3u8",
    
    # BBC (UK-only, but test anyway)
    "BBCOne.uk": "https://vs-cmaf-pushb-uk-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_one_channel_islands/iptv_mse_v0_hevc.mpd",
    "BBCNews.uk": "https://vs-cmaf-pushb-uk-live.akamaized.net/x=4/i=urn:bbc:pips:service:bbc_news24/iptv_mse_v0_hevc.mpd",
    
    # Free sports
    "beINSportsXtra.fr": "https://d35j504z0x2vu2.cloudfront.net/v1/master/0bc8e8376bd8417a1b6761138aa41c26c7309312/bein-sports-xtra/playlist.m3u8",
    
    # Public IPTV (sample of popular channels)
    "AlJazeera.qa": "https://live-hls-web-aje.getaj.net/AJE/index.m3u8",
}

# Additional URLs from iptv-org validated list
IPTV_ORG_LIST = "https://raw.githubusercontent.com/iptv-org/iptv/master/m3u/iptv.m3u"

TIMEOUT = 10  # seconds per URL validation

def validate_url(name, url):
    """Check if a stream URL is live."""
    try:
        resp = requests.head(url, timeout=TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, allow_redirects=True)
        if resp.status_code == 200:
            return {"name": name, "url": url, "status": "live", "http": 200}
        elif resp.status_code == 403:
            return {"name": name, "url": url, "status": "geo_blocked", "http": 403}
        else:
            return {"name": name, "url": url, "status": "dead", "http": resp.status_code}
    except Exception as e:
        return {"name": name, "url": url, "status": "error", "http": 0, "error": str(e)[:50]}

def fetch_iptv_org():
    """Download and parse iptv-org playlist."""
    try:
        resp = requests.get(IPTV_ORG_LIST, timeout=30, headers={
            "User-Agent": "Mozilla/5.0"
        })
        if resp.status_code != 200:
            return {}
        
        streams = {}
        lines = resp.text.split('\n')
        current_name = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                # Extract channel name
                parts = line.split(',')
                if len(parts) > 1:
                    current_name = parts[-1].strip()
                # Also try tvg-name
                import re
                tvg_match = re.search(r'tvg-name="([^"]*)"', line)
                if tvg_match:
                    current_name = tvg_match.group(1)
            elif line.startswith("http") and current_name:
                # Only keep first 200 to stay manageable
                if len(streams) < 200:
                    streams[current_name] = line
                current_name = ""
        
        return streams
    except:
        return {}

def main():
    print("=" * 60)
    print(f"🔄 Stream Validator: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Collect all URLs to validate
    all_urls = dict(STREAM_SOURCES)
    
    # Add iptv-org streams
    print("\n📥 Fetching iptv-org playlist...")
    iptv_streams = fetch_iptv_org()
    print(f"  Found {len(iptv_streams)} streams")
    all_urls.update(iptv_streams)
    
    print(f"\n🔍 Validating {len(all_urls)} URLs...")
    
    results = []
    live_count = 0
    geo_count = 0
    dead_count = 0
    
    # Validate in parallel (20 threads)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(validate_url, name, url): name for name, url in all_urls.items()}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            results.append(result)
            
            if result["status"] == "live":
                live_count += 1
                print(f"  ✅ {result['name']}: LIVE")
            elif result["status"] == "geo_blocked":
                geo_count += 1
                print(f"  🌍 {result['name']}: GEO-BLOCKED")
            else:
                dead_count += 1
            
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(all_urls)}")
    
    # Save results
    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total": len(results),
            "live": live_count,
            "geo_blocked": geo_count,
            "dead": dead_count
        },
        "streams": {r["name"]: r for r in results}
    }
    
    # Save to data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    with open(data_dir / "streams.json", "w") as f:
        json.dump(output, f, indent=2)
    
    # Also save a lightweight version (just live streams)
    live_streams = {r["name"]: r["url"] for r in results if r["status"] == "live"}
    with open(data_dir / "streams_live.json", "w") as f:
        json.dump({"updated": output["updated"], "count": len(live_streams), "streams": live_streams}, f, indent=2)
    
    print(f"\n" + "=" * 60)
    print(f"✅ Done!")
    print(f"   Live: {live_count}")
    print(f"   Geo-blocked: {geo_count}")
    print(f"   Dead: {dead_count}")
    print(f"   Saved to data/streams.json & data/streams_live.json")
    print("=" * 60)

if __name__ == "__main__":
    main()
