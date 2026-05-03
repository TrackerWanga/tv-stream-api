#!/usr/bin/env python3
"""
Fetches live sports data from XCASPER API and saves to our repo.
Runs via GitHub Actions every 5 minutes.
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path

SPORTS_API = "https://movieapi.xcasper.space/api/live"

def main():
    print("⚽ Fetching live sports...")
    
    try:
        resp = requests.get(SPORTS_API, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Origin": "https://movieapi.xcasper.space",
            "Referer": "https://movieapi.xcasper.space/"
        })
        
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return
        
        data = resp.json()
        
        # Extract and clean
        match_list = data.get("data", {}).get("matchList", [])
        highlights = data.get("data", {}).get("highlights", [])
        news = data.get("data", {}).get("newsList", [])
        
        # Filter only matches with streams
        live_matches = []
        for m in match_list:
            if m.get("playPath"):
                live_matches.append({
                    "id": m["id"],
                    "league": m["league"],
                    "team1": m["team1"]["name"],
                    "team2": m["team2"]["name"],
                    "score1": m["team1"]["score"],
                    "score2": m["team2"]["score"],
                    "status": m["status"],
                    "timeDesc": m.get("timeDesc", ""),
                    "startTime": m.get("startTime", 0),
                    "streamUrl": m["playPath"],
                    "type": m.get("type", "")
                })
        
        output = {
            "updated": datetime.now(timezone.utc).isoformat(),
            "live": live_matches,
            "upcoming": [
                {
                    "id": m["id"],
                    "league": m["league"],
                    "team1": m["team1"]["name"],
                    "team2": m["team2"]["name"],
                    "startTime": m.get("startTime", 0),
                }
                for m in match_list if m["status"] == "MatchNotStart"
            ],
            "highlights": [
                {
                    "title": h["title"],
                    "url": h["path"],
                    "cover": h["cover"]["url"],
                    "duration": h["duration"],
                    "views": h["stat"]["viewCount"]
                }
                for h in highlights
            ],
            "news": [
                {"title": n["title"], "cover": n.get("cover", "")}
                for n in news
            ]
        }
        
        Path("data").mkdir(exist_ok=True)
        with open("data/sports.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"  ✅ {len(live_matches)} live matches saved")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    main()
