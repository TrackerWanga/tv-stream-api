#!/usr/bin/env python3
"""
Validates ALL stream URLs in parallel.
Only keeps HTTP 200 URLs.
Outputs validated_streams.json
"""

import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

TIMEOUT = 8
MAX_WORKERS = 50

def validate(stream_id, stream_info):
    """Check if a stream URL is live."""
    url = stream_info["url"]
    try:
        resp = requests.head(url, timeout=TIMEOUT, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            allow_redirects=True)
        
        status = "live" if resp.status_code == 200 else "dead"
        http = resp.status_code
    except:
        status = "error"
        http = 0
    
    return {**stream_info, "status": status, "http_code": http, "validated_at": datetime.now(timezone.utc).isoformat()}

def main():
    print("=" * 60)
    print(f"🔄 Stream Validator: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Load raw streams
    with open("data/raw_streams.json") as f:
        raw = json.load(f)
    
    total = len(raw)
    print(f"\n🔍 Validating {total} URLs ({MAX_WORKERS} parallel)...")
    
    results = {}
    live = 0
    dead = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(validate, sid, info): sid for sid, info in raw.items()}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            sid = futures[future]
            results[sid] = result
            
            if result["status"] == "live":
                live += 1
            else:
                dead += 1
            
            if (i + 1) % 500 == 0:
                print(f"  Progress: {i+1}/{total} (live: {live}, dead: {dead})")
    
    # Save all results
    with open("data/validated_all.json", "w") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "stats": {"total": total, "live": live, "dead": dead},
            "streams": results
        }, f, indent=2)
    
    # Save live-only (what the API serves)
    live_streams = {sid: info for sid, info in results.items() if info["status"] == "live"}
    with open("data/streams_live.json", "w") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "total": len(live_streams),
            "streams": live_streams
        }, f, indent=2)
    
    # Top channels (most popular categories)
    top_categories = ["sports", "news", "entertainment", "movies", "music", "kids"]
    top_streams = {}
    for sid, info in live_streams.items():
        group = info.get("group", "").lower()
        for cat in top_categories:
            if cat in group:
                if cat not in top_streams:
                    top_streams[cat] = {}
                top_streams[cat][sid] = info
                break
    
    with open("data/top_streams.json", "w") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "streams": top_streams
        }, f, indent=2)
    
    print(f"\n✅ Done!")
    print(f"   Total: {total}")
    print(f"   Live: {live} ({100*live//total if total else 0}%)")
    print(f"   Dead: {dead}")
    print(f"   Saved: data/streams_live.json & data/top_streams.json")

if __name__ == "__main__":
    main()
