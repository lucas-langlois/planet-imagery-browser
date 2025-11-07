from planet import Planet
import math
import json
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image
from io import BytesIO
import os

# Automatically detects authentication configured by `planet auth login`
pl = Planet()

print("Authentication successful!")
print(f"Planet client initialized: {pl}")

# Define center point
center_lat = -19.1836382  # South is negative
center_lon = 146.6825115  # East is positive

# Calculate square AOI for 5.5 hectares
# 5.5 hectares = 55,000 m²
# For a square: side_length = sqrt(55,000) ≈ 234.52 meters
area_ha = 5.5
area_m2 = area_ha * 10000
side_length_m = math.sqrt(area_m2)
half_side_m = side_length_m / 2

print(f"\nAOI Details:")
print(f"Area: {area_ha} hectares ({area_m2} m²)")
print(f"Square side length: {side_length_m:.2f} meters")

# Convert meters to degrees (approximate)
# At this latitude, 1 degree latitude ≈ 111,320 meters
# 1 degree longitude ≈ 111,320 * cos(latitude) meters
meters_per_deg_lat = 111320
meters_per_deg_lon = 111320 * math.cos(math.radians(center_lat))

half_side_deg_lat = half_side_m / meters_per_deg_lat
half_side_deg_lon = half_side_m / meters_per_deg_lon

# Create bounding box coordinates (min_lon, min_lat, max_lon, max_lat)
min_lon = center_lon - half_side_deg_lon
max_lon = center_lon + half_side_deg_lon
min_lat = center_lat - half_side_deg_lat
max_lat = center_lat + half_side_deg_lat

# Create GeoJSON polygon for the square AOI
aoi = {
    "type": "Polygon",
    "coordinates": [[
        [min_lon, min_lat],  # Bottom-left
        [max_lon, min_lat],  # Bottom-right
        [max_lon, max_lat],  # Top-right
        [min_lon, max_lat],  # Top-left
        [min_lon, min_lat]   # Close the polygon
    ]]
}

print(f"\nCenter Point: {center_lat}° S, {center_lon}° E")
print(f"Bounding Box:")
print(f"  Min Lon: {min_lon:.7f}°")
print(f"  Max Lon: {max_lon:.7f}°")
print(f"  Min Lat: {min_lat:.7f}°")
print(f"  Max Lat: {max_lat:.7f}°")
print(f"\nGeoJSON AOI:")
print(json.dumps(aoi, indent=2))

# Search for imagery
print("\n" + "="*60)
print("Searching for Planet imagery...")
print("="*60)

from planet import data_filter

# Define search filters using the data_filter module
date_range_filter = data_filter.date_range_filter(
    field_name="acquired",
    gte=datetime(2024, 6, 1),
    lte=datetime(2025, 5, 31, 23, 59, 59)
)

cloud_cover_filter = data_filter.range_filter(
    field_name="cloud_cover",
    lte=0.05  # Less than 5% cloud cover
)

# Filter for visible/clear percent >= 100% (full coverage of AOI)
coverage_filter = data_filter.range_filter(
    field_name="visible_percent",
    gte=100.0  # 100% visible coverage
)

geometry_filter = data_filter.geometry_filter(aoi)

# Combine all filters
combined_filter = data_filter.and_filter([
    date_range_filter,
    cloud_cover_filter,
    coverage_filter,
    geometry_filter
])

# Item types to search (common Planet imagery types)
item_types = ["PSScene"]  # PlanetScope scenes

# Perform the search
print(f"\nSearch Criteria:")
print(f"  Date Range: 2024-06-01 to 2025-05-31")
print(f"  Cloud Cover: < 5%")
print(f"  Visible Coverage: >= 100%")
print(f"  Item Types: {item_types}")
print("\nSearching...\n")

search_results = pl.data.search(
    item_types=item_types,
    search_filter=combined_filter,
    name="MMP_Seagrass_Search"
)

# Collect and display results
results_list = []
result_count = 0

for item in search_results:
    result_count += 1
    results_list.append(item)
    
    # Only display first 20 for readability, but collect all
    if result_count <= 20:
        print(f"\nResult {result_count}:")
        print(f"  ID: {item['id']}")
        print(f"  Acquired: {item['properties']['acquired']}")
        print(f"  Cloud Cover: {item['properties']['cloud_cover']*100:.2f}%")
        print(f"  Item Type: {item['properties']['item_type']}")

if result_count > 20:
    print(f"\n(+ {result_count - 20} more results not displayed...)")

print(f"\n" + "="*60)
print(f"Total scenes found: {result_count}")
print("="*60)

# Display preview of all results
print("\n" + "="*60)
print("Preview of all results with Thumbnails")
print("="*60)

item_type_id = 'PSScene'
asset_type_id = 'ortho_analytic_8b'

print(f"\nAsset Type: {asset_type_id}\n")

# Get API key - prioritize static API key for tile services
api_key = "PLAK57509390d35c44dca6ed46803db9c394"  # Your API key for tile services
print(f"Using API key for tile requests\n")

# Limit thumbnail display to avoid opening too many windows
max_thumbnails_to_show = 1
print(f"Note: Will open thumbnails for first {max_thumbnails_to_show} result(s) only\n")

for idx, item in enumerate(results_list, 1):
    item_id = item['id']
    props = item['properties']
    
    print(f"[{idx}/{len(results_list)}] {item_id}")
    print(f"  Acquired: {props['acquired']}")
    print(f"  Cloud Cover: {props['cloud_cover']*100:.2f}%")
    print(f"  Visible Percent: {props.get('visible_percent', 'N/A')}%")
    print(f"  Clear Percent: {props.get('clear_percent', 'N/A')}%")
    print(f"  GSD: {props.get('gsd', 'N/A')} m")
    print(f"  Satellite ID: {props.get('satellite_id', 'N/A')}")
    
    # Get and display thumbnail (only for first few results)
    if idx <= max_thumbnails_to_show:
        try:
            # Calculate the best zoom level for our AOI
            # For 5.5 ha (~235m side), zoom level 17-18 gives good detail
            zoom = 17
            
            # Get tile coordinates for the center of our AOI
            center_lon = (min_lon + max_lon) / 2
            center_lat = (min_lat + max_lat) / 2
            
            # Calculate tile coordinates (Web Mercator)
            n = 2.0 ** zoom
            x_tile = int((center_lon + 180.0) / 360.0 * n)
            y_tile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                         (1 / math.cos(math.radians(center_lat)))) / math.pi) / 2.0 * n)
            
            print(f"  Fetching tile preview (zoom {zoom}, tile {x_tile}/{y_tile})...")
            
            # Build XYZ tile URL (no query parameters needed with HTTPBasicAuth)
            # Format: https://tiles{0-3}.planet.com/data/v1/{item_type}/{item_id}/{z}/{x}/{y}.png
            tile_server = "tiles0"  # Can be tiles0, tiles1, tiles2, or tiles3
            tile_url = f"https://{tile_server}.planet.com/data/v1/{item_type_id}/{item_id}/{zoom}/{x_tile}/{y_tile}.png"
            
            # Use HTTPBasicAuth with API key as username, empty string as password
            auth = HTTPBasicAuth(api_key, "")
            r = requests.get(tile_url, auth=auth)
            
            if r.status_code == 200:
                print(f"  Opening high-resolution tile preview...")
                img = Image.open(BytesIO(r.content))
                
                # Fetch surrounding tiles for a 3x3 mosaic
                print(f"  Fetching surrounding tiles for complete view...")
                tiles_to_fetch = [
                    (x_tile-1, y_tile-1), (x_tile, y_tile-1), (x_tile+1, y_tile-1),
                    (x_tile-1, y_tile),   (x_tile, y_tile),   (x_tile+1, y_tile),
                    (x_tile-1, y_tile+1), (x_tile, y_tile+1), (x_tile+1, y_tile+1),
                ]
                
                tile_images = []
                for tx, ty in tiles_to_fetch:
                    tile_url_temp = f"https://{tile_server}.planet.com/data/v1/{item_type_id}/{item_id}/{zoom}/{tx}/{ty}.png"
                    try:
                        r_temp = requests.get(tile_url_temp, auth=auth, timeout=5)
                        if r_temp.status_code == 200:
                            tile_images.append(Image.open(BytesIO(r_temp.content)))
                        else:
                            tile_images.append(None)
                    except:
                        tile_images.append(None)
                
                # Create 3x3 mosaic
                if any(tile_images):
                    tile_size = 256  # Standard tile size
                    mosaic = Image.new('RGB', (tile_size * 3, tile_size * 3))
                    for i, tile_img in enumerate(tile_images):
                        if tile_img:
                            x_pos = (i % 3) * tile_size
                            y_pos = (i // 3) * tile_size
                            mosaic.paste(tile_img, (x_pos, y_pos))
                    print(f"  Displaying 3x3 tile mosaic...")
                    mosaic.show()
                else:
                    img.show()
                    
            else:
                print(f"  Tile not available (status: {r.status_code}), trying basic thumbnail...")
                # Fallback to basic thumbnail
                thumb_url = f"https://api.planet.com/data/v1/item-types/{item_type_id}/items/{item_id}/thumb"
                headers = {"Authorization": f"Bearer {api_key}"} if api_key and not api_key.startswith("PL") else None
                auth = (api_key, "") if api_key and api_key.startswith("PL") else None
                r = requests.get(thumb_url, auth=auth, headers=headers)
                if r.status_code == 200:
                    print(f"  Opening basic thumbnail (256x256)...")
                    img = Image.open(BytesIO(r.content))
                    img.show()
                    
        except Exception as e:
            print(f"  Preview error: {str(e)}")
    
    # Get asset information
    try:
        asset = pl.data.get_asset(item_type_id, item_id, asset_type_id)
        asset_status = asset.get('status', 'unknown')
        
        # Get file info if available
        if 'location' in asset:
            print(f"  Asset Status: {asset_status} (ready to download)")
        else:
            print(f"  Asset Status: {asset_status}")
            
        # Get asset size if available
        if '_permissions' in asset and asset['_permissions']:
            print(f"  Permissions: {asset['_permissions']}")
            
    except Exception as e:
        print(f"  Asset Status: Error - {str(e)}")
    
    print()

# Summary
print("="*60)
print("Summary")
print("="*60)
print(f"Total scenes: {len(results_list)}")
print(f"Date range: {results_list[-1]['properties']['acquired'][:10]} to {results_list[0]['properties']['acquired'][:10]}")
print(f"Asset type: {asset_type_id}")
print("\nTo download these images, uncomment the download code section.")
