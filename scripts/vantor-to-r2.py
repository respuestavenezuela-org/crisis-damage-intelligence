#!/usr/bin/env python3
"""
Download Vantor Open Data imagery and upload to Cloudflare R2.
Processes STAC collection, downloads all assets, uploads to R2.
"""

import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from datetime import datetime

# Configuration
ROOT = Path(__file__).resolve().parents[1]
COLLECTION_URL = "https://vantor-opendata.s3.amazonaws.com/events/Venezuela-Earthquake-Jun-2026/collection.json"
R2_BUCKET = "crisis-damage-intelligence"
R2_PREFIX = "vantor/venezuela-earthquake-jun-2026"
LOCAL_CACHE = Path("/tmp/vantor-downloads")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def fetch_json(url):
    """Fetch JSON from URL."""
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def get_file_size(url):
    """Get file size via HEAD request."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as response:
            return int(response.headers.get('Content-Length', 0))
    except Exception:
        return 0

def download_file(url, dest):
    """Download file from URL to destination."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with open(dest, 'wb') as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
    return dest.stat().st_size

def upload_to_r2(local_path, r2_key):
    """Upload file to R2 using wrangler."""
    cmd = [
        "npx", "wrangler", "r2", "object", "put",
        f"{R2_BUCKET}/{r2_key}",
        "--file", str(local_path)
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        log(f"  Upload failed: {result.stderr}")
        return False
    return True

def format_size(size_bytes):
    """Format bytes to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f}KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.1f}MB"
    else:
        return f"{size_bytes/1024**3:.1f}GB"

def main():
    log("Fetching STAC collection...")
    collection = fetch_json(COLLECTION_URL)
    
    # Get all item links
    item_links = [link for link in collection['links'] if link['rel'] == 'item']
    log(f"Found {len(item_links)} items in collection")
    
    # Fetch all items
    items = []
    for link in item_links:
        item = fetch_json(link['href'])
        items.append(item)
    
    # Sort by quality (cloud cover) and date
    items.sort(key=lambda x: (x['properties'].get('eo:cloud_cover', 100), x['properties'].get('datetime', '')))
    
    # Create manifest
    manifest = {
        "source": "Vantor Open Data Program",
        "collection_url": COLLECTION_URL,
        "license": "CC-BY-NC-4.0",
        "uploaded_at": datetime.now().isoformat(),
        "total_items": len(items),
        "items": []
    }
    
    # Process each item
    for idx, item in enumerate(items, 1):
        item_id = item['id']
        props = item['properties']
        dt = props.get('datetime', 'unknown')
        phase = props.get('phase', 'unknown')
        vehicle = props.get('vehicle_name', 'unknown')
        cloud = props.get('eo:cloud_cover', 'N/A')
        
        log(f"[{idx}/{len(items)}] Processing {item_id}")
        log(f"  Date: {dt} | Phase: {phase} | Vehicle: {vehicle} | Cloud: {cloud}%")
        
        item_manifest = {
            "id": item_id,
            "datetime": dt,
            "phase": phase,
            "vehicle": vehicle,
            "cloud_cover": cloud,
            "assets": {}
        }
        
        # Process each asset
        for asset_name, asset_info in item['assets'].items():
            url = asset_info['href']
            filename = Path(url).name
            r2_key = f"{R2_PREFIX}/{item_id}/{filename}"
            local_path = LOCAL_CACHE / item_id / filename
            
            # Get file size
            size = get_file_size(url)
            log(f"  Download candidate {asset_name}: {filename} ({format_size(size)})")
            
            # Download
            try:
                downloaded_size = download_file(url, local_path)
                log(f"  Downloaded: {format_size(downloaded_size)}")
            except Exception as e:
                log(f"  Download failed: {e}")
                continue
            
            # Upload to R2
            log("  Uploading to R2...")
            if upload_to_r2(local_path, r2_key):
                log(f"  Uploaded: r2://{R2_BUCKET}/{r2_key}")
                item_manifest['assets'][asset_name] = {
                    "r2_key": r2_key,
                    "r2_url": f"https://{R2_BUCKET}.r2.cloudflarestorage.com/{r2_key}",
                    "size": downloaded_size,
                    "type": asset_info.get('type', 'unknown')
                }
            else:
                log("  Upload failed")
            
            # Clean up local file to save space
            local_path.unlink()
            log("  Cleaned up local file")
        
        manifest['items'].append(item_manifest)
        
        # Save progress manifest
        manifest_path = LOCAL_CACHE / "upload_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        log("  Manifest saved")
        log("")
    
    # Final summary
    log("=" * 60)
    log("UPLOAD COMPLETE")
    log("=" * 60)
    
    total_files = sum(len(item['assets']) for item in manifest['items'])
    total_bytes = sum(
        asset['size'] 
        for item in manifest['items'] 
        for asset in item['assets'].values()
    )
    
    log(f"Total items: {len(items)}")
    log(f"Total files uploaded: {total_files}")
    log(f"Total size: {format_size(total_bytes)}")
    log(f"Manifest saved to: {manifest_path}")
    
    # Print R2 URLs for reference
    log("\nR2 URLs for before imagery (best quality first):")
    for item in manifest['items']:
        if 'visual' in item['assets']:
            cloud = item.get('cloud_cover', 'N/A')
            dt = item.get('datetime', 'unknown')
            url = item['assets']['visual']['r2_url']
            log(f"  {item['id']} | Cloud:{cloud}% | {dt}")
            log(f"    {url}")

if __name__ == "__main__":
    main()
