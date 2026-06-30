#!/usr/bin/env python3
"""Stream Vantor Open Data imagery to R2 with multipart uploads.

This script is intended for GitHub Actions or another cloud runner with R2
S3-compatible credentials. It does not write COG/TIFF assets to local disk.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Configuration
COLLECTION_URL = "https://vantor-opendata.s3.amazonaws.com/events/Venezuela-Earthquake-Jun-2026/collection.json"
R2_BUCKET = os.environ.get('S3_BUCKET', 'crisis-damage-intelligence')
R2_ENDPOINT = os.environ.get('S3_ENDPOINT_URL', '')
R2_PREFIX = "vantor/venezuela-earthquake-jun-2026"
STRATEGY = os.environ.get('STRATEGY', 'pre')
DRY_RUN = os.environ.get('DRY_RUN', 'false').lower() == 'true'
PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev")
PART_SIZE = 64 * 1024 * 1024

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def get_r2_client():
    """Create S3 client for R2."""
    import boto3

    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name='auto'
    )

def fetch_json(url):
    """Fetch JSON from URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

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

def head_url(url):
    response = requests.head(url, timeout=60, allow_redirects=True)
    response.raise_for_status()
    return {
        "content_length": int(response.headers.get("content-length", 0)),
        "content_type": response.headers.get("content-type") or get_content_type(url),
        "accept_ranges": response.headers.get("accept-ranges", ""),
    }


def r2_object_size(s3_client, r2_key):
    try:
        response = s3_client.head_object(Bucket=R2_BUCKET, Key=r2_key)
    except Exception:
        return None
    return int(response.get("ContentLength") or 0)


def upload_part(s3_client, r2_key, upload_id, part_number, body, uploaded, content_length):
    response = s3_client.upload_part(
        Bucket=R2_BUCKET,
        Key=r2_key,
        UploadId=upload_id,
        PartNumber=part_number,
        Body=body,
    )
    uploaded += len(body)
    if part_number == 1 or part_number % 10 == 0 or uploaded == content_length:
        total = format_size(content_length) if content_length else "unknown"
        log(f"    part {part_number}: {format_size(uploaded)} / {total}")
    return {"PartNumber": part_number, "ETag": response["ETag"]}, uploaded


def upload_url_to_r2(s3_client, url, r2_key, content_type, content_length=0):
    """Stream an HTTP response into an explicit R2 multipart upload."""
    upload = s3_client.create_multipart_upload(
        Bucket=R2_BUCKET,
        Key=r2_key,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    upload_id = upload["UploadId"]
    parts = []
    part_number = 1
    uploaded = 0
    buffer = bytearray()

    try:
        with requests.get(url, stream=True, timeout=(30, 3600)) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if not chunk:
                    continue
                buffer.extend(chunk)
                while len(buffer) >= PART_SIZE:
                    body = bytes(buffer[:PART_SIZE])
                    del buffer[:PART_SIZE]
                    part, uploaded = upload_part(
                        s3_client,
                        r2_key,
                        upload_id,
                        part_number,
                        body,
                        uploaded,
                        content_length,
                    )
                    parts.append(part)
                    part_number += 1

            if buffer:
                part, uploaded = upload_part(
                    s3_client,
                    r2_key,
                    upload_id,
                    part_number,
                    bytes(buffer),
                    uploaded,
                    content_length,
                )
                parts.append(part)

            s3_client.complete_multipart_upload(
                Bucket=R2_BUCKET,
                Key=r2_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
    except Exception:
        s3_client.abort_multipart_upload(
            Bucket=R2_BUCKET,
            Key=r2_key,
            UploadId=upload_id,
        )
        raise


def upload_bytes_to_r2(s3_client, body, r2_key, content_type, cache_control="public, max-age=300"):
    s3_client.put_object(
        Bucket=R2_BUCKET,
        Key=r2_key,
        Body=body,
        ContentType=content_type,
        CacheControl=cache_control,
    )

def get_content_type(file_path):
    """Get content type based on extension."""
    ext = Path(str(file_path)).suffix.lower()
    types = {
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.json': 'application/json',
        '.csv': 'text/csv',
        '.geojson': 'application/geo+json',
    }
    return types.get(ext, 'application/octet-stream')

def process_item(s3_client, item):
    """Process a single STAC item."""
    item_id = item['id']
    props = item['properties']
    
    log(f"Processing {item_id}")
    log(f"  Date: {props.get('datetime', 'unknown')}")
    log(f"  Phase: {props.get('phase', 'unknown')}")
    log(f"  Vehicle: {props.get('vehicle_name', 'unknown')}")
    log(f"  Cloud cover: {props.get('eo:cloud_cover', 'N/A')}%")
    
    result = {
        "id": item_id,
        "datetime": props.get('datetime'),
        "phase": props.get('phase'),
        "vehicle": props.get('vehicle_name'),
        "cloud_cover": props.get('eo:cloud_cover'),
        "assets": {}
    }
    
    if not DRY_RUN:
        item_json_key = f"{R2_PREFIX}/{item_id}/{item_id}.json"
        item_json_body = json.dumps(item, indent=2).encode("utf-8")
        upload_bytes_to_r2(
            s3_client,
            item_json_body,
            item_json_key,
            "application/json; charset=utf-8",
        )
        result["assets"]["stac_item"] = {
            "r2_key": item_json_key,
            "public_url": f"{PUBLIC_BASE_URL}/{item_json_key}",
            "size": len(item_json_body),
            "type": "application/json",
        }

    for asset_name, asset_info in item.get('assets', {}).items():
        url = asset_info['href']
        filename = Path(url).name
        r2_key = f"{R2_PREFIX}/{item_id}/{filename}"
        
        # Skip COGs for metadata/thumb-only strategies.
        if STRATEGY == 'thumbs' and asset_name == 'visual':
            log(f"  ⏭️  Skipping COG (thumbs strategy)")
            continue
        
        log(f"  📥 {asset_name}: {filename}")
        
        if DRY_RUN:
            log(f"  📝 DRY RUN - Would upload to r2://{R2_BUCKET}/{r2_key}")
            result['assets'][asset_name] = {
                "r2_key": r2_key,
                "dry_run": True
            }
            continue
        
        try:
            meta = head_url(url)
            existing_size = r2_object_size(s3_client, r2_key)
            if existing_size == meta["content_length"] and existing_size > 0:
                log(f"  ✅ Already present in R2: {format_size(existing_size)}")
                size = existing_size
            else:
                log(f"  ⇄ Streaming to R2 without local file: {format_size(meta['content_length'])}")
                upload_url_to_r2(s3_client, url, r2_key, meta["content_type"], meta["content_length"])
                size = r2_object_size(s3_client, r2_key) or meta["content_length"]
                log(f"  ✅ Uploaded to r2://{R2_BUCKET}/{r2_key}")
            
            result['assets'][asset_name] = {
                "r2_key": r2_key,
                "public_url": f"{PUBLIC_BASE_URL}/{r2_key}",
                "size": size,
                "type": meta.get("content_type") or asset_info.get('type', 'unknown'),
                "source_url": url,
            }
            
        except Exception as e:
            log(f"  ❌ Error: {e}")
            result['assets'][asset_name] = {"error": str(e)}
    
    return result

def main():
    log("=" * 60)
    log("VANTOR → R2 SYNC")
    log(f"Strategy: {STRATEGY}")
    log(f"Dry run: {DRY_RUN}")
    log("=" * 60)
    
    # Initialize R2 client only when we are going to write.
    s3_client = None
    if not DRY_RUN:
        s3_client = get_r2_client()
        log("R2 client initialized")
    
    # Fetch collection
    log("Fetching STAC collection...")
    collection = fetch_json(COLLECTION_URL)
    
    item_links = [link for link in collection['links'] if link['rel'] == 'item']
    log(f"Found {len(item_links)} items")
    
    # Fetch all items
    items = []
    for link in item_links:
        items.append(fetch_json(link['href']))

    unique_items = {}
    duplicate_ids = []
    for item in items:
        item_id = item["id"]
        if item_id in unique_items:
            duplicate_ids.append(item_id)
            continue
        unique_items[item_id] = item
    items = list(unique_items.values())
    if duplicate_ids:
        log(f"Deduplicated {len(duplicate_ids)} duplicate item link(s): {', '.join(sorted(set(duplicate_ids)))}")
    
    # Sort by quality (cloud cover ascending)
    items.sort(key=lambda x: x['properties'].get('eo:cloud_cover', 100))
    
    # Filter based on strategy
    if STRATEGY == 'best':
        # Top 6 by quality
        items = items[:6]
        log(f"Selected top {len(items)} items by quality")
    elif STRATEGY == 'pre':
        items = [item for item in items if item['properties'].get('phase') == 'pre']
        log(f"Selected all {len(items)} pre-event items")
    elif STRATEGY == 'thumbs':
        # All items, but only thumbnails
        log(f"Processing all {len(items)} items, thumbnails only")
    else:
        # All items, all assets
        log(f"Processing all {len(items)} items")

    phase_counts = {}
    for item in items:
        phase = item["properties"].get("phase", "unknown")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    log(f"Phase counts: {phase_counts}")
    
    # Process each item
    manifest = {
        "source": "Vantor Open Data Program",
        "collection_url": COLLECTION_URL,
        "license": "CC-BY-NC-4.0",
        "strategy": STRATEGY,
        "dry_run": DRY_RUN,
        "phase_counts": phase_counts,
        "uploaded_at": datetime.now().isoformat(),
        "items": []
    }
    
    for idx, item in enumerate(items, 1):
        log(f"\n[{idx}/{len(items)}] {'='*50}")
        result = process_item(s3_client, item)
        manifest['items'].append(result)

        # Save progress for the GitHub Actions artifact and R2.
        manifest_path = Path('/tmp/vantor-manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        if not DRY_RUN:
            manifest_body = json.dumps(manifest, indent=2).encode("utf-8")
            upload_bytes_to_r2(
                s3_client,
                manifest_body,
                f"{R2_PREFIX}/manifests/vantor-stream-manifest.json",
                "application/json; charset=utf-8",
            )
            upload_bytes_to_r2(
                s3_client,
                manifest_body,
                f"{R2_PREFIX}/manifests/vantor-{STRATEGY}-manifest.json",
                "application/json; charset=utf-8",
            )
    
    # Final summary
    log("\n" + "=" * 60)
    log("SYNC COMPLETE")
    log("=" * 60)
    
    total_files = sum(len(item['assets']) for item in manifest['items'])
    total_bytes = sum(
        asset.get('size', 0)
        for item in manifest['items']
        for asset in item['assets'].values()
        if 'size' in asset
    )
    
    log(f"Items processed: {len(items)}")
    file_label = "Files planned" if DRY_RUN else "Files uploaded"
    log(f"{file_label}: {total_files}")
    log(f"Total size: {format_size(total_bytes)}")
    
    if DRY_RUN:
        log("\n⚠️  This was a DRY RUN. No files were actually uploaded.")
        log("   Run with dry_run=false to perform the actual upload.")
    
    # Print best images info
    log("\nBest quality images:")
    for item in manifest['items']:
        cloud = item.get('cloud_cover', 'N/A')
        dt = item.get('datetime', 'unknown')
        log(f"  {item['id']} | Cloud:{cloud}% | {dt}")

if __name__ == "__main__":
    main()
