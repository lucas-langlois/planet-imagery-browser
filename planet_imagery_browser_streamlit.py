"""
Planet Imagery Browser - Streamlit Web Application
Search and preview Planet satellite imagery with interactive filters
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import os
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageDraw
from io import BytesIO
from planet import Planet
from planet import data_filter
from planet.order_request import build_request, clip_tool, product
import time

# Page configuration
st.set_page_config(
    page_title="Planet Imagery Browser",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .exposed-row {
        background-color: #FFEBEE;
    }
    .not-exposed-row {
        background-color: #E8F5E9;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = []
if 'exposure_status' not in st.session_state:
    st.session_state.exposure_status = {}
if 'tide_data' not in st.session_state:
    st.session_state.tide_data = {}
if 'current_preview_index' not in st.session_state:
    st.session_state.current_preview_index = 0
if 'preview_mode' not in st.session_state:
    st.session_state.preview_mode = 'aoi'
if 'aoi_bounds' not in st.session_state:
    st.session_state.aoi_bounds = None

# Initialize Planet client
@st.cache_resource
def get_planet_client(api_key):
    """Initialize Planet client with provided API key"""
    return Planet(api_key=api_key)

def check_api_key():
    """Check if API key is valid by making a simple request"""
    try:
        pl = get_planet_client(st.session_state.api_key)
        # Simple validation - just try to create a client
        return True
    except Exception as e:
        return False

def calculate_aoi(center_lat, center_lon, grid_size):
    """Calculate AOI bounding box from center point and grid size"""
    # Each tile at zoom 17 is approximately 256 pixels * (156543.03 meters/pixel at equator / 2^17)
    tile_size_m = 256 * 156543.03 * math.cos(math.radians(abs(center_lat))) / (2 ** 17)
    
    # Calculate total side length based on grid size
    side_length_m = grid_size * tile_size_m
    half_side_m = side_length_m / 2
    
    # Convert to degrees
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(math.radians(center_lat))
    
    half_side_deg_lat = half_side_m / meters_per_deg_lat
    half_side_deg_lon = half_side_m / meters_per_deg_lon
    
    # Create bounding box
    min_lon = center_lon - half_side_deg_lon
    max_lon = center_lon + half_side_deg_lon
    min_lat = center_lat - half_side_deg_lat
    max_lat = center_lat + half_side_deg_lat
    
    aoi = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat]
        ]]
    }
    
    return aoi, (center_lat, center_lon, min_lat, max_lat, min_lon, max_lon)

def perform_search(aoi, start_date, end_date, max_cloud, min_coverage, item_type):
    """Execute the search with current filter settings"""
    # Build filters
    date_filter_obj = data_filter.date_range_filter(
        field_name="acquired",
        gte=start_date,
        lte=end_date
    )
    
    cloud_filter_obj = data_filter.range_filter(
        field_name="cloud_cover",
        lte=max_cloud / 100.0
    )
    
    coverage_filter_obj = data_filter.range_filter(
        field_name="visible_percent",
        gte=min_coverage
    )
    
    geometry_filter_obj = data_filter.geometry_filter(aoi)
    
    combined_filter = data_filter.and_filter([
        date_filter_obj,
        cloud_filter_obj,
        coverage_filter_obj,
        geometry_filter_obj
    ])
    
    # Perform search
    search_results = pl.data.search(
        item_types=[item_type],
        search_filter=combined_filter,
        limit=0
    )
    
    # Collect results
    results = []
    for item in search_results:
        results.append(item)
    
    return results

def load_preview_tiles(item_id, item_type, center_lat, center_lon, grid_size, preview_mode):
    """Load and mosaic preview tiles"""
    # Determine zoom level and grid size based on preview mode
    if preview_mode == 'full':
        zoom = 16
        display_grid_size = 5
    else:
        zoom = 17
        display_grid_size = grid_size
    
    # Calculate tile coordinates
    n = 2.0 ** zoom
    x_tile = int((center_lon + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                 (1 / math.cos(math.radians(center_lat)))) / math.pi) / 2.0 * n)
    
    # Determine tiles to fetch
    tiles_to_fetch = []
    offset = display_grid_size // 2
    for dy in range(-offset, offset + 1):
        for dx in range(-offset, offset + 1):
            tiles_to_fetch.append((x_tile + dx, y_tile + dy))
    
    # Fetch tiles
    tile_server = "tiles0"
    auth = HTTPBasicAuth(api_key, "")
    tile_images = []
    
    for tx, ty in tiles_to_fetch:
        tile_url = f"https://{tile_server}.planet.com/data/v1/{item_type}/{item_id}/{zoom}/{tx}/{ty}.png"
        try:
            r = requests.get(tile_url, auth=auth, timeout=10)
            if r.status_code == 200:
                tile_images.append(Image.open(BytesIO(r.content)))
            else:
                tile_images.append(None)
        except:
            tile_images.append(None)
    
    # Create mosaic
    if any(tile_images):
        tile_size = 256
        mosaic = Image.new('RGB', (tile_size * display_grid_size, tile_size * display_grid_size), (200, 200, 200))
        for i, tile_img in enumerate(tile_images):
            if tile_img:
                x_pos = (i % display_grid_size) * tile_size
                y_pos = (i // display_grid_size) * tile_size
                mosaic.paste(tile_img, (x_pos, y_pos))
        
        # Draw center marker
        draw = ImageDraw.Draw(mosaic)
        center_x = tile_size * display_grid_size / 2
        center_y = tile_size * display_grid_size / 2
        radius = 20 if display_grid_size <= 3 else 30
        circle_bbox = [
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius
        ]
        draw.ellipse(circle_bbox, outline='white', width=4)
        draw.ellipse(circle_bbox, outline='red', width=3)
        
        return mosaic
    
    return None

def get_tide_height_for_item(item_id, tide_data):
    """Extract datetime from satellite item ID and match with tide data"""
    if not tide_data:
        return None
    
    try:
        from datetime import timezone
        
        item_id_str = str(item_id)
        
        # Check if it has underscores (format: YYYYMMDD_HHMMSS_XX_XXXX)
        if '_' in item_id_str:
            date_time_part = item_id_str.split('_')[:2]
            date_str = date_time_part[0]  # YYYYMMDD
            time_str = date_time_part[1]  # HHMMSS
        else:
            # No underscores - format is continuous
            date_str = item_id_str[0:8]   # YYYYMMDD
            time_str = item_id_str[8:14]  # HHMMSS
        
        # Parse into datetime
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        
        # Round to nearest 10 minutes
        dt_rounded = dt.replace(second=0, microsecond=0)
        dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)
        
        # Look up tide height
        if dt_rounded in tide_data:
            return tide_data[dt_rounded]
        
        # Try ±10 minutes
        for offset in range(-1, 2):
            check_dt = dt_rounded + timedelta(minutes=offset * 10)
            if check_dt in tide_data:
                return tide_data[check_dt]
        
        return None
    except Exception as e:
        return None

# Title and description
st.title("🛰️ Planet Imagery Browser")
st.markdown("Search and preview Planet satellite imagery with interactive filters")

# API Key Input Section
if 'api_key' not in st.session_state or not st.session_state.get('api_key'):
    st.warning("⚠️ **Planet API Key Required**")
    st.markdown("""
    To use this application, you need a Planet API key.
    
    **Don't have one?** [Sign up for free at Planet.com](https://www.planet.com/explorer/)
    
    Your API key will be stored securely in your browser session and will not be saved permanently.
    """)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        api_key_input = st.text_input(
            "Enter your Planet API Key:",
            type="password",
            placeholder="PLAK...",
            help="Your API key starts with 'PLAK' and can be found in your Planet account settings"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if st.button("🔓 Connect", type="primary"):
            if api_key_input:
                st.session_state.api_key = api_key_input
                st.success("✅ API Key saved! Refreshing...")
                st.rerun()
            else:
                st.error("Please enter an API key")
    
    st.info("💡 **Tip:** Keep your API key secure and never share it publicly!")
    st.stop()  # Stop execution until API key is provided
else:
    # Show API key status in a collapsible section
    with st.expander("🔑 API Key Status", expanded=False):
        st.success("✅ API Key Connected")
        masked_key = st.session_state.api_key[:8] + "..." + st.session_state.api_key[-4:]
        st.code(masked_key)
        if st.button("🔄 Change API Key"):
            del st.session_state.api_key
            st.rerun()

# Initialize Planet client with the provided API key
pl = get_planet_client(st.session_state.api_key)
api_key = st.session_state.api_key

# Sidebar - Search Filters
with st.sidebar:
    st.header("🔍 Search Filters")
    
    # AOI Section
    st.subheader("Area of Interest")
    center_lat = st.number_input("Center Latitude", value=-19.1836382, format="%.7f")
    center_lon = st.number_input("Center Longitude", value=146.6825115, format="%.7f")
    
    grid_options = {
        "1x1 (~0.06 km²)": 1,
        "3x3 (~0.59 km²)": 3,
        "5x5 (~1.64 km²)": 5,
        "7x7 (~3.21 km²)": 7,
        "9x9 (~5.30 km²)": 9
    }
    grid_size_str = st.selectbox("Grid Size", list(grid_options.keys()), index=1)
    grid_size = grid_options[grid_size_str]
    
    # Date Range
    st.subheader("Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime(2024, 6, 1))
    with col2:
        end_date = st.date_input("End Date", value=datetime(2025, 5, 31))
    
    # Filters
    st.subheader("Filters")
    max_cloud = st.slider("Max Cloud Cover (%)", 0, 100, 5)
    min_coverage = st.slider("Min Visible Coverage (%)", 0, 100, 100)
    
    item_type = st.selectbox("Item Type", ["PSScene"])
    
    # Download Options
    st.subheader("Download Options")
    clip_to_aoi = st.checkbox("Clip to AOI", value=True, help="Download only the selected area")
    
    # Search Button
    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching for imagery..."):
            aoi, aoi_bounds = calculate_aoi(center_lat, center_lon, grid_size)
            st.session_state.aoi_bounds = aoi_bounds
            
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            
            results = perform_search(aoi, start_dt, end_dt, max_cloud, min_coverage, item_type)
            st.session_state.results = results
            st.session_state.exposure_status = {}
            
            st.success(f"✅ Found {len(results)} scenes!")
    
    # Tide Data
    st.subheader("🌊 Tide Data")
    uploaded_tide_file = st.file_uploader("Upload Tide Data CSV", type=['csv'])
    
    if uploaded_tide_file is not None:
        try:
            import pytz
            from datetime import timezone
            
            df = pd.read_csv(uploaded_tide_file)
            tide_data = {}
            
            # Check format
            if 'DateTime' in df.columns and 'Height' in df.columns:
                # AEST format
                for _, row in df.iterrows():
                    dt_str = row['DateTime']
                    dt_naive = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                    aest = pytz.timezone('Australia/Brisbane')
                    dt_aest = aest.localize(dt_naive)
                    dt_utc = dt_aest.astimezone(pytz.UTC)
                    
                    dt_rounded = dt_utc.replace(second=0, microsecond=0)
                    dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)
                    
                    tide_data[dt_rounded] = float(row['Height'])
            elif 'datetime' in df.columns and 'tide_height' in df.columns:
                # ISO format
                for _, row in df.iterrows():
                    dt_str = row['datetime']
                    dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    
                    dt_rounded = dt_utc.replace(second=0, microsecond=0)
                    dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)
                    
                    tide_data[dt_rounded] = float(row['tide_height'])
            
            st.session_state.tide_data = tide_data
            st.success(f"✅ Loaded {len(tide_data)} tide records")
        except Exception as e:
            st.error(f"Error loading tide data: {str(e)}")

# Main content area
if len(st.session_state.results) == 0:
    st.info("👈 Configure search filters in the sidebar and click 'Search' to find imagery")
else:
    # Create tabs for different views
    tab1, tab2 = st.tabs(["📊 Results Table", "🖼️ Image Preview"])
    
    with tab1:
        st.subheader(f"Search Results ({len(st.session_state.results)} scenes)")
        
        # Bulk actions
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            if st.button("☀️ Mark Selected as Exposed"):
                st.info("Select rows in table, then use checkboxes below")
        with col2:
            if st.button("🌊 Mark Selected as Not Exposed"):
                st.info("Select rows in table, then use checkboxes below")
        with col3:
            if st.button("↓ Sort by Lowest Tide"):
                if st.session_state.tide_data:
                    results_with_tide = []
                    for item in st.session_state.results:
                        tide_height = get_tide_height_for_item(item['id'], st.session_state.tide_data)
                        results_with_tide.append((item, tide_height))
                    results_with_tide.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))
                    st.session_state.results = [item for item, _ in results_with_tide]
                    st.success("✅ Sorted by tide height")
                else:
                    st.warning("Please load tide data first")
        with col4:
            if st.button("📊 Export to CSV"):
                # Create DataFrame for export
                export_data = []
                for item in st.session_state.results:
                    item_id = item['id']
                    props = item['properties']
                    acquired_dt = datetime.fromisoformat(props['acquired'].replace('Z', '+00:00'))
                    tide_height = get_tide_height_for_item(item_id, st.session_state.tide_data)
                    
                    export_data.append({
                        'Item ID': item_id,
                        'Acquired Date': acquired_dt.strftime('%Y-%m-%d'),
                        'Acquired Time': acquired_dt.strftime('%H:%M:%S'),
                        'Cloud Cover (%)': f"{props['cloud_cover']*100:.2f}",
                        'Visible Percent (%)': props.get('visible_percent', ''),
                        'GSD (m)': props.get('gsd', ''),
                        'Tide Height (m)': f"{tide_height:.2f}" if tide_height is not None else "",
                        'Exposure Status': st.session_state.exposure_status.get(item_id, 'Not Marked')
                    })
                
                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"planet_imagery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Create results table
        table_data = []
        for idx, item in enumerate(st.session_state.results):
            props = item['properties']
            item_id = item['id']
            tide_height = get_tide_height_for_item(item_id, st.session_state.tide_data)
            
            table_data.append({
                '#': idx + 1,
                'Item ID': item_id,
                'Date': props['acquired'][:10],
                'Cloud %': f"{props['cloud_cover']*100:.1f}",
                'Visible %': f"{props.get('visible_percent', 'N/A')}",
                'GSD (m)': f"{props.get('gsd', 'N/A')}",
                'Tide (m)': f"{tide_height:.2f}" if tide_height is not None else "N/A",
                'Exposure': st.session_state.exposure_status.get(item_id, 'Not Marked')
            })
        
        df = pd.DataFrame(table_data)
        
        # Display table with selection
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Individual row actions
        st.subheader("Mark Individual Items")
        selected_item_num = st.number_input("Select Item #", min_value=1, max_value=len(st.session_state.results), value=1)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("☀️ Mark as Exposed", key="mark_exposed"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                st.session_state.exposure_status[item_id] = 'Exposed'
                st.success(f"Marked item #{selected_item_num} as Exposed")
                st.rerun()
        with col2:
            if st.button("🌊 Mark as Not Exposed", key="mark_not_exposed"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                st.session_state.exposure_status[item_id] = 'Not Exposed'
                st.success(f"Marked item #{selected_item_num} as Not Exposed")
                st.rerun()
        with col3:
            if st.button("⎯ Clear Status", key="clear_status"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                if item_id in st.session_state.exposure_status:
                    del st.session_state.exposure_status[item_id]
                st.success(f"Cleared status for item #{selected_item_num}")
                st.rerun()
    
    with tab2:
        st.subheader("Image Preview")
        
        # Preview controls
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
        
        with col1:
            if st.button("◀ Previous"):
                if st.session_state.current_preview_index > 0:
                    st.session_state.current_preview_index -= 1
                    st.rerun()
        
        with col2:
            preview_num = st.number_input("Go to #", min_value=1, max_value=len(st.session_state.results), 
                                         value=st.session_state.current_preview_index + 1, key="preview_nav")
            if preview_num != st.session_state.current_preview_index + 1:
                st.session_state.current_preview_index = preview_num - 1
                st.rerun()
        
        with col3:
            if st.button("Next ▶"):
                if st.session_state.current_preview_index < len(st.session_state.results) - 1:
                    st.session_state.current_preview_index += 1
                    st.rerun()
        
        with col4:
            if st.button("🔍 Toggle View"):
                st.session_state.preview_mode = 'full' if st.session_state.preview_mode == 'aoi' else 'aoi'
                st.rerun()
        
        with col5:
            st.markdown(f"**Viewing:** Item {st.session_state.current_preview_index + 1} of {len(st.session_state.results)} "
                       f"({'Full Scene' if st.session_state.preview_mode == 'full' else 'AOI'})")
        
        # Load and display preview
        if st.session_state.aoi_bounds and st.session_state.current_preview_index < len(st.session_state.results):
            item = st.session_state.results[st.session_state.current_preview_index]
            item_id = item['id']
            item_type = item['properties']['item_type']
            
            center_lat, center_lon, min_lat, max_lat, min_lon, max_lon = st.session_state.aoi_bounds
            
            with st.spinner("Loading preview..."):
                preview_image = load_preview_tiles(
                    item_id, item_type, center_lat, center_lon, grid_size, 
                    st.session_state.preview_mode
                )
            
            if preview_image:
                st.image(preview_image, caption=f"Preview: {item_id}", use_container_width=True)
                
                # Download preview button
                buf = BytesIO()
                preview_image.save(buf, format='PNG')
                st.download_button(
                    label="💾 Download Preview",
                    data=buf.getvalue(),
                    file_name=f"{item_id}_preview.png",
                    mime="image/png"
                )
            else:
                st.error("Could not load preview image")
            
            # Show metadata
            with st.expander("📋 Image Metadata"):
                props = item['properties']
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Item ID:** {item_id}")
                    st.write(f"**Acquired:** {props['acquired']}")
                    st.write(f"**Cloud Cover:** {props['cloud_cover']*100:.1f}%")
                    st.write(f"**Visible Percent:** {props.get('visible_percent', 'N/A')}%")
                with col2:
                    st.write(f"**GSD:** {props.get('gsd', 'N/A')} m")
                    st.write(f"**Satellite:** {props.get('satellite_id', 'N/A')}")
                    tide_height = get_tide_height_for_item(item_id, st.session_state.tide_data)
                    st.write(f"**Tide Height:** {f'{tide_height:.2f} m' if tide_height is not None else 'N/A'}")
                    st.write(f"**Exposure Status:** {st.session_state.exposure_status.get(item_id, 'Not Marked')}")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using [Streamlit](https://streamlit.io) | Data from [Planet Labs](https://www.planet.com)")

