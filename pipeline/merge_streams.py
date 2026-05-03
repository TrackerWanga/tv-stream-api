#!/usr/bin/env python3
"""
Merges IPTV validated streams + YouTube streams into final API-ready JSON.
Matches to metadata for logos, countries, categories.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

def load_json(path):
    if Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return {}

def main():
    print("🔄 Merging all stream sources...")
    
    # Load all sources
    iptv = load_json("data/streams_live.json")
    youtube = load_json("data/youtube_streams.json")
    channels_meta = load_json("data/channels.json")
    
    # Build name→metadata lookup
    meta_by_name = {}
    meta_by_id = {}
    for c in channels_meta:
        meta_by_name[c["name"].lower().strip()] = c
        meta_by_id[c["id"]] = c
    
    # Merge streams
    all_streams = {}
    
    # Add IPTV streams
    for sid, info in iptv.get("streams", {}).items():
        # Try to match metadata
        name_lower = info.get("name", "").lower().strip()
        meta = meta_by_name.get(name_lower) or meta_by_id.get(sid, {})
        
        all_streams[sid] = {
            "id": meta.get("id", sid),
            "name": meta.get("name", info.get("name", "")),
            "url": info["url"],
            "logo": meta.get("logo", info.get("logo", "")),
            "country": meta.get("country", info.get("country", "")),
            "categories": meta.get("categories", info.get("categories", [info.get("group", "general")])),
            "quality": info.get("quality", "HD"),
            "source": info.get("source", "iptv"),
            "status": info.get("status", "live"),
            "validated_at": info.get("validated_at", "")
        }
    
    # Add YouTube streams (no duplicates)
    for sid, info in youtube.get("streams", {}).items():
        if sid not in all_streams:
            all_streams[sid] = {
                "id": sid,
                "name": info["name"],
                "url": info["url"],
                "logo": info.get("logo", ""),
                "country": info.get("country", ""),
                "categories": info.get("categories", []),
                "quality": "HD",
                "source": "youtube",
                "status": "live",
                "validated_at": datetime.now(timezone.utc).isoformat()
            }
    
    # Organize by category
    by_category = {}
    for sid, info in all_streams.items():
        for cat in info.get("categories", ["other"]):
            cat_lower = cat.lower()
            if cat_lower not in by_category:
                by_category[cat_lower] = {}
            by_category[cat_lower][sid] = info
    
    # Organize by country
    by_country = {}
    for sid, info in all_streams.items():
        country = info.get("country", "XX")
        if country not in by_country:
            by_country[country] = {}
        by_country[country][sid] = info
    
    # Generate Top 100 (sorted by category popularity)
    category_order = ["sports", "news", "entertainment", "movies", "music", "kids", "documentary"]
    top_100 = {}
    for cat in category_order:
        if cat in by_category:
            for sid, info in list(by_category[cat].items())[:15]:
                if len(top_100) < 100:
                    top_100[sid] = info
    
    # Save all files
    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total": len(all_streams),
        "categories": {cat: len(chans) for cat, chans in by_category.items()},
        "countries": {c: len(chans) for c, chans in by_country.items()}
    }
    
    with open("data/api_streams.json", "w") as f:
        json.dump({"meta": output, "streams": all_streams}, f, indent=2)
    
    with open("data/api_by_category.json", "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "categories": by_category}, f, indent=2)
    
    with open("data/api_by_country.json", "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "countries": by_country}, f, indent=2)
    
    with open("data/api_top100.json", "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "streams": top_100}, f, indent=2)
    
    print(f"\n✅ Merged: {len(all_streams)} total streams")
    print(f"   Categories: {len(by_category)}")
    print(f"   Countries: {len(by_country)}")
    print(f"   Top 100 saved")
    print(f"   Files: api_streams.json, api_by_category.json, api_by_country.json, api_top100.json")

if __name__ == "__main__":
    main()
