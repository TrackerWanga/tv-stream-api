#!/usr/bin/env python3
"""
Matches validated streams (from validated_all.json) to metadata (channels.json).
"""

import json, re
from pathlib import Path
from datetime import datetime, timezone

def normalize(name):
    n = name.lower().strip()
    n = re.sub(r'\(.*?\)', '', n)
    n = re.sub(r'\[.*?\]', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def main():
    print("🔄 Matching streams to metadata...")
    
    # Load validated streams (6942 entries)
    with open("data/validated_all.json") as f:
        validated = json.load(f)
    
    # Load channel metadata (39457 entries)
    with open("data/channels.json") as f:
        channels = json.load(f)
    
    # Build name → ID lookup
    name_to_id = {}
    for c in channels:
        name_to_id[normalize(c["name"])] = c["id"]
    
    # Match live streams
    matched = {}
    live_count = 0
    
    streams = validated.get("streams", {})
    for sid, info in streams.items():
        if isinstance(info, dict) and info.get("status") != "live":
            continue
        live_count += 1
        
        # Get stream name
        stream_name = normalize(info.get("name", "")) if isinstance(info, dict) else normalize(sid)
        
        # Try match
        meta_id = name_to_id.get(stream_name)
        
        if meta_id:
            url = info.get("url", "") if isinstance(info, dict) else info
            matched[meta_id] = {
                "url": url,
                "name": info.get("name", sid) if isinstance(info, dict) else sid,
                "logo": info.get("logo", "") if isinstance(info, dict) else "",
                "group": info.get("group", "general") if isinstance(info, dict) else "general",
            }
    
    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total_live": live_count,
        "matched": len(matched),
        "streams": matched
    }
    
    with open("data/streams_matched.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"  Total live streams: {live_count}")
    print(f"  Matched to metadata: {len(matched)}")
    print(f"  Saved: data/streams_matched.json")

if __name__ == "__main__":
    main()
