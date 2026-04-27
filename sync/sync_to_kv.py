#!/usr/bin/env python3
"""
Syncs channel metadata and streams to Cloudflare KV.

Environment variables:
  CF_API_TOKEN       - Cloudflare API token
  CF_ACCOUNT_ID      - Cloudflare account ID  
  CF_KV_NAMESPACE_ID - KV namespace ID
"""

import os
import json
import sys
import requests
from pathlib import Path
from datetime import datetime

CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
CF_KV_NAMESPACE_ID = os.environ.get("CF_KV_NAMESPACE_ID")
CF_API_TOKEN = os.environ.get("CF_API_TOKEN")

KV_API = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/storage/kv/namespaces/{CF_KV_NAMESPACE_ID}"
HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

DATA_DIR = Path(__file__).parent.parent / "data"

def kv_put(key, value):
    """Upload value to KV. Handles dict (converts to JSON)."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    
    resp = requests.put(
        f"{KV_API}/values/{key}",
        headers=HEADERS,
        data=value.encode('utf-8')
    )
    
    if resp.status_code == 200:
        print(f"  ✓ {key}")
    else:
        print(f"  ✗ {key} - {resp.status_code}: {resp.text[:100]}")
    return resp.status_code == 200

def sync_all():
    print("=" * 60)
    print(f"🔄 Syncing to Cloudflare KV: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    # Load channel data
    with open(DATA_DIR / "channels.json", "r") as f:
        channels = json.load(f)
    
    # Load indexes
    with open(DATA_DIR / "countries_index.json") as f:
        countries = json.load(f)
    with open(DATA_DIR / "categories_index.json") as f:
        categories = json.load(f)
    with open(DATA_DIR / "languages_index.json") as f:
        languages = json.load(f)
    
    # Upload indexes (small, fast)
    print("\n📊 Uploading indexes...")
    kv_put("index:countries", countries)
    kv_put("index:categories", categories)
    kv_put("index:languages", languages)
    
    # Upload channels in chunks
    print(f"\n📡 Uploading {len(channels)} channels...")
    chunk_size = 3000
    total_chunks = (len(channels) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(channels), chunk_size):
        chunk_num = i // chunk_size
        chunk = channels[i:i+chunk_size]
        kv_put(f"channels:chunk:{chunk_num}", chunk)
        
        if chunk_num % 3 == 0:
            print(f"  Progress: {chunk_num+1}/{total_chunks} chunks")
    
    # Store metadata about chunks
    kv_put("channels:meta", {
        "total": len(channels),
        "chunks": total_chunks,
        "chunk_size": chunk_size,
        "updated": datetime.utcnow().isoformat()
    })
    
    # Store lightweight channel list for autocomplete
    light = [{"id": c["id"], "name": c["name"], "country": c["country"], 
              "categories": c["categories"]} for c in channels]
    kv_put("channels:light", light)
    
    print(f"\n✅ Sync complete!")
    print(f"   {len(channels)} channels")
    print(f"   {len(countries)} countries")
    print(f"   {len(categories)} categories")

if __name__ == "__main__":
    if not all([CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID]):
        print("❌ Missing environment variables!")
        print("   Required: CF_API_TOKEN, CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID")
        sys.exit(1)
    sync_all()
