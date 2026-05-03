#!/usr/bin/env python3
"""
Uses yt-dlp to extract direct stream URLs from YouTube live videos.
These URLs CAN be played inline in any video player.
"""

import subprocess
import json
import sys
from pathlib import Path

def extract_direct_url(youtube_url):
    """Use yt-dlp to get the direct m3u8/mp4 URL from a YouTube live stream."""
    try:
        result = subprocess.run(
            ['yt-dlp', '-f', 'best', '-g', youtube_url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        return None
    except Exception as e:
        print(f"    yt-dlp error: {e}")
        return None

def main():
    print("🎬 Extracting direct YouTube URLs with yt-dlp...")
    
    # Load existing YouTube streams
    yt_path = Path("data/youtube_streams.json")
    if not yt_path.exists():
        print("No YouTube streams to process")
        return
    
    with open(yt_path) as f:
        data = json.load(f)
    
    streams = data.get("streams", {})
    total = len(streams)
    converted = 0
    
    for sid, info in streams.items():
        url = info.get("url", "")
        if "youtube.com" not in url:
            continue
        
        print(f"  [{converted+1}/{total}] Extracting: {info['name']}...")
        direct_url = extract_direct_url(url)
        
        if direct_url:
            streams[sid]["url"] = direct_url
            streams[sid]["source"] = "youtube_direct"
            converted += 1
            print(f"    ✅ Got direct URL: {direct_url[:60]}...")
        else:
            print(f"    ❌ Could not extract")
    
    # Save updated
    with open(yt_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Converted {converted}/{total} YouTube streams to direct URLs")

if __name__ == "__main__":
    main()
