"""
Planet Imagery Browser - Streamlit Web Application
Search and preview Planet satellite imagery with interactive filters
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import math
import os
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageDraw
from io import BytesIO
from zipfile import ZipFile
from planet import Planet
from planet import data_filter
from planet.order_request import build_request, clip_tool, product
import pytz
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
    # Planet SDK uses environment variable or session
    # We need to set it temporarily for the session
    os.environ['PL_API_KEY'] = api_key
    return Planet()

def check_api_key(api_key):
    """Check if API key is valid by making a simple request"""
    try:
        # Set environment variable temporarily
        os.environ['PL_API_KEY'] = api_key
        pl = Planet()
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

def perform_search(aoi, start_date, end_date, max_cloud, item_type):
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
    
    geometry_filter_obj = data_filter.geometry_filter(aoi)
    
    combined_filter = data_filter.and_filter([
        date_filter_obj,
        cloud_filter_obj,
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

def parse_tide_csv(df):
    """Parse tide data from CSV formats."""
    tide_data = {}
    normalized = {}
    for col in df.columns:
        if isinstance(col, str):
            normalized[col.strip().lstrip('\ufeff').lower()] = col

    datetime_col = normalized.get('datetime')
    height_col = normalized.get('height')
    tide_height_col = normalized.get('tide_height')

    if not datetime_col:
        raise ValueError("No 'DateTime' or 'datetime' column found in CSV")

    line_count = 0

    if datetime_col and height_col:
        branch = 'aest'
        tz_info = "Converted from AEST to UTC timezone"
        aest = pytz.timezone('Australia/Brisbane')
    elif datetime_col and tide_height_col:
        branch = 'utc'
        tz_info = "Parsed native UTC tide timestamps"
    else:
        raise ValueError("Unrecognized CSV format. Expected columns similar to 'DateTime' & 'Height' or 'datetime' & 'tide_height'.")

    for _, row in df.iterrows():
        dt_raw = row[datetime_col]
        if pd.isna(dt_raw):
            continue
        dt_str = str(dt_raw).strip()
        if not dt_str:
            continue

        try:
            if branch == 'aest':
                dt_naive = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                dt_aest = aest.localize(dt_naive)
                dt_utc = dt_aest.astimezone(pytz.UTC)
                height_value = row[height_col]
            else:
                dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                height_value = row[tide_height_col]

            height_value = float(str(height_value).strip())

            dt_rounded = dt_utc.replace(second=0, microsecond=0)
            dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)

            tide_data[dt_rounded] = height_value
            line_count += 1
        except Exception:
            continue

    return tide_data, line_count, tz_info

def parse_tide_txt(uploaded_file):
    """Parse equispaced tide predictions from text files."""
    content = uploaded_file.getvalue().decode('utf-8', errors='ignore').splitlines()
    tide_data = {}
    line_count = 0
    header_found = False

    for raw_line in content:
        line = raw_line.strip()
        if not line:
            continue

        if not header_found:
            if line.lower().startswith('date') and 'height' in line.lower():
                header_found = True
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        date_str, time_str = parts[0], parts[1]
        height_str = parts[-1]

        try:
            dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            dt_utc = dt_naive.replace(tzinfo=timezone.utc)
            tide_height = float(height_str)

            dt_rounded = dt_utc.replace(second=0, microsecond=0)
            dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)

            tide_data[dt_rounded] = tide_height
            line_count += 1
        except Exception:
            continue

    if not header_found:
        raise ValueError("Could not locate the 'Date Time Height' header in the text file.")

    return tide_data, line_count, "Assumed ZULU (UTC) tide timestamps"

def order_and_download_asset(item, clip_to_aoi, aoi_bounds, status_placeholder, download_placeholder):
    """Create an order for the selected asset and provide a download link."""
    global pl

    status_placeholder.info("Creating order...")
    download_placeholder.empty()
    progress_placeholder = st.empty()

    try:
        item_id = item['id']
        item_type = item['properties'].get('item_type', 'PSScene')

        tools = []
        order_suffix = "full_scene"

        if clip_to_aoi and aoi_bounds:
            center_lat, center_lon, min_lat, max_lat, min_lon, max_lon = aoi_bounds
            aoi_polygon = {
                "type": "Polygon",
                "coordinates": [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat]
                ]]
            }
            tools.append(clip_tool(aoi_polygon))
            order_suffix = "AOI_clip"
        elif clip_to_aoi and not aoi_bounds:
            status_placeholder.error("AOI bounds are not available. Run a search to define an AOI before ordering.")
            return

        order_name = f"{order_suffix}_{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if tools:
            request = build_request(
                name=order_name,
                products=[
                    product(
                        item_ids=[item_id],
                        product_bundle="visual",
                        item_type=item_type,
                    )
                ],
                tools=tools,
            )
        else:
            request = build_request(
                name=order_name,
                products=[
                    product(
                        item_ids=[item_id],
                        product_bundle="visual",
                        item_type=item_type,
                    )
                ],
            )

        order = pl.orders.create_order(request)
        order_id = order.get('id')
        if not order_id:
            status_placeholder.error("Failed to create order. No order ID returned.")
            return

        max_wait = 600
        check_interval = 10
        elapsed = 0

        while elapsed <= max_wait:
            order_status = pl.orders.get_order(order_id)
            state = order_status.get('state', 'unknown')
            progress_placeholder.info(f"Order status: {state}")

            if state == 'success':
                results = order_status.get('results', [])
                if not results:
                    status_placeholder.warning("Order completed but no downloadable assets were returned.")
                    progress_placeholder.empty()
                    return

                files = []
                for result in results:
                    download_url = result.get('location')
                    result_name = result.get('name', f"{item_id}.tif")
                    if not download_url:
                        continue

                    response = requests.get(download_url, timeout=60)
                    if response.status_code == 200:
                        files.append((result_name, response.content))

                if not files:
                    status_placeholder.warning("Order succeeded but no files could be downloaded.")
                    progress_placeholder.empty()
                    return

                zip_buffer = BytesIO()
                with ZipFile(zip_buffer, 'w') as zip_file:
                    for file_name, content in files:
                        zip_file.writestr(file_name, content)
                zip_buffer.seek(0)

                progress_placeholder.empty()
                status_placeholder.success("Order complete! Download your assets below.")
                download_placeholder.download_button(
                    label="⬇️ Download Ordered Assets",
                    data=zip_buffer.getvalue(),
                    file_name=f"{item_id}_assets.zip",
                    mime="application/zip",
                    key=f"download_order_{order_id}"
                )
                return

            if state == 'failed':
                error_msg = order_status.get('error', {}).get('message', 'Unknown error')
                status_placeholder.error(f"Order failed: {error_msg}")
                progress_placeholder.empty()
                return

            if state in ['cancelled', 'partial']:
                status_placeholder.error(f"Order {state}. Please try again.")
                progress_placeholder.empty()
                return

            time.sleep(check_interval)
            elapsed += check_interval

        status_placeholder.error("Order timed out after 10 minutes. Please try again later.")
        progress_placeholder.empty()

    except Exception as exc:
        progress_placeholder.empty()
        status_placeholder.error(f"Failed to order asset: {exc}")

# Title and description
st.title("🛰️ Planet Imagery Browser")
st.markdown("Search and preview Planet satellite imagery with interactive filters")

# API Key Input Section
if 'api_key' not in st.session_state or not st.session_state.get('api_key'):
    st.warning("🔑 **Enter Your Planet API Key**")
    st.caption("Your key stays in your browser session only. It is never stored on disk or sent anywhere else.")

    st.session_state.setdefault('api_key_form_buffer', "")

    with st.form("api_key_capture_form", clear_on_submit=False):
        user_input = st.text_input(
            "Planet API Key",
            value=st.session_state.api_key_form_buffer,
            placeholder="PLAK...",
            help="Paste your API key from Planet.com"
        )
        submitted = st.form_submit_button("🔓 Connect", type="primary", use_container_width=True)

        if submitted:
            cleaned = user_input.strip()
            st.session_state.api_key_form_buffer = cleaned

            if cleaned:
                st.session_state.api_key = cleaned
                st.session_state.api_key_form_buffer = ""
                st.success("✅ API key saved! Loading the app...")
                st.rerun()
            else:
                st.error("❌ No API key detected. Please paste your key above and submit again.")

    st.caption("Tip: Paste your key, then click Connect. No extra keystrokes needed.")

    st.stop()
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
# Set environment variable for the entire session
os.environ['PL_API_KEY'] = st.session_state.api_key
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
    st.subheader("Cloud Cover")
    max_cloud = st.slider("Maximum acceptable cloud cover (%)", 0, 100, 5)
    st.caption("Imagery with cloud cover greater than this value will be excluded from search results.")
    
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
            
            results = perform_search(aoi, start_dt, end_dt, max_cloud, item_type)
            st.session_state.results = results
            st.session_state.exposure_status = {}
            st.session_state.selection_flags = {}
            st.session_state.current_preview_index = 0
            st.session_state.preview_mode = 'aoi'
            
            st.success(f"✅ Found {len(results)} scenes!")
    
    # Tide Data
    st.subheader("🌊 Tide Data")
    uploaded_tide_file = st.file_uploader("Upload Tide Data (CSV or TXT)", type=['csv', 'txt'])
    
    if uploaded_tide_file is not None:
        try:
            line_count = 0
            tz_info = "Parsed tide timestamps"
            tide_data = {}

            filename_lower = uploaded_tide_file.name.lower()
            uploaded_tide_file.seek(0)

            if filename_lower.endswith('.txt'):
                tide_data, line_count, tz_info = parse_tide_txt(uploaded_tide_file)
            else:
                df = pd.read_csv(uploaded_tide_file)
                tide_data, line_count, tz_info = parse_tide_csv(df)

            if line_count == 0:
                st.warning("No tide records detected in the uploaded file.")
            else:
                st.session_state.tide_data = tide_data
                st.success(f"✅ Loaded {line_count} tide records\n\n{tz_info}")
        except Exception as e:
            st.error(f"Error loading tide data: {str(e)}")

# Main content area
if len(st.session_state.results) == 0:
    st.info("👈 Configure search filters in the sidebar and click 'Search' to find imagery")
else:
    if 'selection_flags' not in st.session_state:
        st.session_state.selection_flags = {}
    # Create tabs for different views
    tab1, tab2 = st.tabs(["📊 Results Table", "🖼️ Image Preview"])
    
    with tab1:
        st.subheader(f"Search Results ({len(st.session_state.results)} scenes)")
        
        flash_message = st.session_state.pop('flash_message', None)
        if flash_message:
            st.success(flash_message)

        st.caption("Use the Select column below to choose scenes for bulk actions.")

        table_data = []
        for idx, item in enumerate(st.session_state.results):
            props = item['properties']
            item_id = item['id']
            tide_height = get_tide_height_for_item(item_id, st.session_state.tide_data)

            visible_val = props.get('visible_percent')
            clear_val = props.get('clear_percent')
            gsd_val = props.get('gsd')

            visible_str = f"{visible_val:.1f}" if isinstance(visible_val, (int, float)) else ("N/A" if visible_val is None else str(visible_val))
            clear_str = f"{clear_val:.1f}" if isinstance(clear_val, (int, float)) else ("N/A" if clear_val is None else str(clear_val))
            gsd_str = f"{gsd_val:.2f}" if isinstance(gsd_val, (int, float)) else ("N/A" if gsd_val is None else str(gsd_val))
            tide_str = f"{tide_height:.2f}" if tide_height is not None else "N/A"

            is_selected = st.session_state.selection_flags.get(item_id, False)

            table_data.append({
                '#': idx + 1,
                'Item ID': item_id,
                'Date': props['acquired'][:10],
                'Cloud %': f"{props['cloud_cover']*100:.1f}",
                'Visible %': visible_str,
                'Clear %': clear_str,
                'GSD (m)': gsd_str,
                'Tide (m)': tide_str,
                'Satellite': props.get('satellite_id', 'N/A'),
                'Exposure': st.session_state.exposure_status.get(item_id, 'Not Marked'),
                'Select': is_selected
            })

        df = pd.DataFrame(table_data)

        column_config = {
            'Select': st.column_config.CheckboxColumn('Select', help='Toggle to include item in bulk actions', default=False)
        }
        disabled_cols = [col for col in df.columns if col != 'Select']

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=disabled_cols,
            column_config=column_config
        )

        st.session_state.selection_flags = {
            row['Item ID']: bool(row.get('Select', False))
            for _, row in edited_df.iterrows()
        }
        selected_ids = [item_id for item_id, selected in st.session_state.selection_flags.items() if selected]
        st.caption(f"Selected for bulk actions: {len(selected_ids)} item(s)")

        action_cols = st.columns([2, 2, 2, 2])
        with action_cols[0]:
            if st.button("☀️ Mark Selected as Exposed"):
                if not selected_ids:
                    st.warning("Select items in the table using the 'Select' column.")
                else:
                    for item_id in selected_ids:
                        st.session_state.exposure_status[item_id] = 'Exposed'
                    st.session_state.flash_message = f"Marked {len(selected_ids)} item(s) as Exposed"
                    st.rerun()
        with action_cols[1]:
            if st.button("🌊 Mark Selected as Not Exposed"):
                if not selected_ids:
                    st.warning("Select items in the table using the 'Select' column.")
                else:
                    for item_id in selected_ids:
                        st.session_state.exposure_status[item_id] = 'Not Exposed'
                    st.session_state.flash_message = f"Marked {len(selected_ids)} item(s) as Not Exposed"
                    st.rerun()
        with action_cols[2]:
            if st.button("↓ Sort by Lowest Tide"):
                if st.session_state.tide_data:
                    results_with_tide = []
                    for item in st.session_state.results:
                        tide_height = get_tide_height_for_item(item['id'], st.session_state.tide_data)
                        results_with_tide.append((item, tide_height))
                    results_with_tide.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))
                    st.session_state.results = [item for item, _ in results_with_tide]
                    st.session_state.flash_message = "Results sorted by tide height"
                    st.rerun()
                else:
                    st.warning("Please load tide data first")
        with action_cols[3]:
            if st.button("📊 Export to CSV"):
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
                        'Clear Percent (%)': props.get('clear_percent', ''),
                        'GSD (m)': props.get('gsd', ''),
                        'Tide Height (m)': f"{tide_height:.2f}" if tide_height is not None else "",
                        'Satellite ID': props.get('satellite_id', ''),
                        'Item Type': props.get('item_type', ''),
                        'Exposure Status': st.session_state.exposure_status.get(item_id, 'Not Marked'),
                        'View Angle': props.get('view_angle', ''),
                        'Sun Elevation': props.get('sun_elevation', ''),
                        'Sun Azimuth': props.get('sun_azimuth', '')
                    })

                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"planet_imagery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="export_results"
                )

        st.divider()

        st.subheader("Mark Individual Items")
        selected_item_num = st.number_input("Select Item #", min_value=1, max_value=len(st.session_state.results), value=1)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("☀️ Mark as Exposed", key="mark_exposed"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                st.session_state.exposure_status[item_id] = 'Exposed'
                st.session_state.flash_message = f"Marked item #{selected_item_num} as Exposed"
                st.rerun()
        with col2:
            if st.button("🌊 Mark as Not Exposed", key="mark_not_exposed"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                st.session_state.exposure_status[item_id] = 'Not Exposed'
                st.session_state.flash_message = f"Marked item #{selected_item_num} as Not Exposed"
                st.rerun()
        with col3:
            if st.button("⎯ Clear Status", key="clear_status"):
                item_id = st.session_state.results[selected_item_num - 1]['id']
                if item_id in st.session_state.exposure_status:
                    del st.session_state.exposure_status[item_id]
                st.session_state.flash_message = f"Cleared status for item #{selected_item_num}"
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

                download_status = st.empty()
                download_link_placeholder = st.empty()
                if st.button("💾 Download Asset", key=f"download_asset_{st.session_state.current_preview_index}"):
                    with st.spinner("Ordering asset... This may take several minutes."):
                        order_and_download_asset(
                            item,
                            clip_to_aoi,
                            st.session_state.aoi_bounds,
                            download_status,
                            download_link_placeholder
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

