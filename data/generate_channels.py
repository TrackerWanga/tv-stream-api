#!/usr/bin/env python3
"""
Generates channels.json from iptv-org CSV files.
Handles the actual iptv-org column structure.
"""

import csv
import json
import os
import urllib.request
from pathlib import Path

CSV_URL = "https://raw.githubusercontent.com/iptv-org/database/master/data/channels.csv"

def download_csv():
    if not Path('channels_raw.csv').exists():
        print("Downloading channels.csv from iptv-org...")
        urllib.request.urlretrieve(CSV_URL, 'channels_raw.csv')
        print("✓ Downloaded")
    else:
        print("✓ Using existing channels_raw.csv")

def parse_list(value):
    """Parse semicolon-separated list like 'English;French'"""
    if not value:
        return []
    return [v.strip() for v in value.split(';') if v.strip()]

def generate_channels():
    channels = []
    seen_ids = set()
    
    with open('channels_raw.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Print actual column names for debugging
        print(f"CSV Columns: {reader.fieldnames}\n")
        
        total = sum(1 for _ in open('channels_raw.csv')) - 1
        
        for i, row in enumerate(reader):
            channel_id = (row.get('id', '') or '').strip()
            name = (row.get('name', '') or '').strip()
            
            if not channel_id or channel_id in seen_ids:
                continue
            seen_ids.add(channel_id)
            
            # Parse languages and categories (semicolon-separated)
            languages = parse_list(row.get('languages', ''))
            categories = parse_list(row.get('categories', ''))
            
            channel = {
                "id": channel_id,
                "name": name or channel_id,
                "slug": channel_id.lower().replace(' ', '-'),
                "country": (row.get('country', '') or '').strip() or 'XX',
                "languages": languages if languages else ['en'],
                "categories": categories if categories else ['general'],
                "logo": f"https://raw.githubusercontent.com/iptv-org/database/master/logos/{channel_id.lower()}.png",
                "website": (row.get('website', '') or '').strip() or '',
                "is_nsfw": (row.get('is_nsfw', '') or '').strip().upper() == 'TRUE',
                "launched": (row.get('launched', '') or '').strip() or None,
                "closed": (row.get('closed', '') or '').strip() or None,
                "tvg_id": channel_id,
                "epg_id": channel_id
            }
            
            # Remove empty optional fields
            if not channel['website']:
                del channel['website']
            if not channel['launched']:
                del channel['launched']
            if not channel['closed']:
                del channel['closed']
            
            channels.append(channel)
            
            if i % 5000 == 0 and i > 0:
                print(f"  Processed {i}/{total} channels...")
    
    # Save
    output_path = 'channels.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(channels, f, indent=2, ensure_ascii=False)
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n✓ Generated {len(channels)} channels ({size_mb:.1f} MB)")
    
    # Build indexes
    print("\nBuilding indexes...")
    countries = {}
    categories = {}
    languages = {}
    
    for c in channels:
        country = c['country']
        countries.setdefault(country, []).append(c['id'])
        
        for cat in c['categories']:
            categories.setdefault(cat.lower(), []).append(c['id'])
        
        for lang in c['languages']:
            languages.setdefault(lang.lower(), []).append(c['id'])
    
    with open('countries_index.json', 'w') as f:
        json.dump(countries, f, indent=2)
    print(f"  ✓ {len(countries)} countries")
    
    with open('categories_index.json', 'w') as f:
        json.dump(categories, f, indent=2)
    print(f"  ✓ {len(categories)} categories")
    
    with open('languages_index.json', 'w') as f:
        json.dump(languages, f, indent=2)
    print(f"  ✓ {len(languages)} languages")

if __name__ == '__main__':
    download_csv()
    generate_channels()
    print("\n✅ Done!")
