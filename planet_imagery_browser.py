"""
Planet Imagery Browser - GUI Application
Search and preview Planet satellite imagery with interactive filters
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from tkinter import font as tkfont
import threading
from datetime import datetime, timedelta
import math
import os
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
from planet import Planet
from planet import data_filter
from planet.order_request import build_request, clip_tool, product
import csv

class PlanetImageryBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("Planet Imagery Browser")
        self.root.geometry("1400x900")
        
        # Initialize Planet client
        self.pl = Planet()
        # Get API key from environment variable for security
        # Set via: export PLANET_API_KEY="your_key_here" (Linux/Mac)
        #      or: $env:PLANET_API_KEY="your_key_here" (Windows PowerShell)
        self.api_key = os.getenv('PLANET_API_KEY', '')
        
        if not self.api_key:
            messagebox.showerror(
                "API Key Missing",
                "Planet API key not found!\n\n"
                "Please set the PLANET_API_KEY environment variable:\n\n"
                "Windows PowerShell:\n"
                "$env:PLANET_API_KEY='your_key_here'\n\n"
                "Linux/Mac:\n"
                "export PLANET_API_KEY='your_key_here'\n\n"
                "Or edit planet_imagery_browser.py and set self.api_key directly."
            )
            # Allow continuing for UI testing, but API calls will fail
        
        # Storage for search results
        self.results = []
        self.current_preview_index = 0
        self.exposure_status = {}  # Dict to store exposure status for each item_id
        
        # Tide data storage
        self.tide_data = {}  # Dict mapping datetime to tide_height
        self.tide_file_loaded = None
        
        # Preview mode: 'aoi' or 'full'
        self.preview_mode = 'aoi'
        
        # Store current preview image
        self.current_preview_image = None
        
        # Create main layout
        self.create_ui()
        
    def create_ui(self):
        """Create the main user interface"""
        
        # Create main containers
        left_panel = tk.Frame(self.root, width=400, bg='#f0f0f0')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        
        right_panel = tk.Frame(self.root, bg='white')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # LEFT PANEL - Search Filters
        self.create_filter_panel(left_panel)
        
        # RIGHT PANEL - Results and Preview
        self.create_results_panel(right_panel)
        
    def create_filter_panel(self, parent):
        """Create the filter panel with search controls"""
        
        # Title
        title = tk.Label(parent, text="Search Filters", font=('Arial', 14, 'bold'), bg='#f0f0f0')
        title.pack(pady=10)
        
        # Scrollable frame for filters
        canvas = tk.Canvas(parent, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # AOI (Area of Interest) Section
        aoi_frame = tk.LabelFrame(scrollable_frame, text="Area of Interest", bg='#f0f0f0', padx=10, pady=10)
        aoi_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(aoi_frame, text="Center Latitude:", bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=2)
        self.lat_entry = tk.Entry(aoi_frame, width=20)
        self.lat_entry.insert(0, "-19.1836382")
        self.lat_entry.grid(row=0, column=1, pady=2)
        
        tk.Label(aoi_frame, text="Center Longitude:", bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=2)
        self.lon_entry = tk.Entry(aoi_frame, width=20)
        self.lon_entry.insert(0, "146.6825115")
        self.lon_entry.grid(row=1, column=1, pady=2)
        
        tk.Label(aoi_frame, text="Grid Size (tiles):", bg='#f0f0f0').grid(row=2, column=0, sticky='w', pady=2)
        self.grid_size_var = tk.StringVar(value="3x3 (~0.59 km²)")
        grid_options = [
            "1x1 (~0.06 km²)",
            "3x3 (~0.59 km²)", 
            "5x5 (~1.64 km²)",
            "7x7 (~3.21 km²)",
            "9x9 (~5.30 km²)"
        ]
        self.grid_size_combo = ttk.Combobox(aoi_frame, textvariable=self.grid_size_var, 
                                           values=grid_options, state='readonly', width=18)
        self.grid_size_combo.grid(row=2, column=1, pady=2)
        
        # Date Range Section
        date_frame = tk.LabelFrame(scrollable_frame, text="Date Range", bg='#f0f0f0', padx=10, pady=10)
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(date_frame, text="Start Date (YYYY-MM-DD):", bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=2)
        self.start_date_entry = tk.Entry(date_frame, width=20)
        self.start_date_entry.insert(0, "2024-06-01")
        self.start_date_entry.grid(row=0, column=1, pady=2)
        
        tk.Label(date_frame, text="End Date (YYYY-MM-DD):", bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=2)
        self.end_date_entry = tk.Entry(date_frame, width=20)
        self.end_date_entry.insert(0, "2025-05-31")
        self.end_date_entry.grid(row=1, column=1, pady=2)
        
        # Cloud Cover Section
        cloud_frame = tk.LabelFrame(scrollable_frame, text="Cloud Cover", bg='#f0f0f0', padx=10, pady=10)
        cloud_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(cloud_frame, text="Max Cloud Cover (%):", bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=2)
        self.cloud_entry = tk.Entry(cloud_frame, width=20)
        self.cloud_entry.insert(0, "5")
        self.cloud_entry.grid(row=0, column=1, pady=2)
        
        # Coverage Section
        coverage_frame = tk.LabelFrame(scrollable_frame, text="Coverage", bg='#f0f0f0', padx=10, pady=10)
        coverage_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(coverage_frame, text="Min Visible (%):", bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=2)
        self.coverage_entry = tk.Entry(coverage_frame, width=20)
        self.coverage_entry.insert(0, "100")
        self.coverage_entry.grid(row=0, column=1, pady=2)
        
        # Item Type Section
        item_frame = tk.LabelFrame(scrollable_frame, text="Item Type", bg='#f0f0f0', padx=10, pady=10)
        item_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.item_type_var = tk.StringVar(value="PSScene")
        tk.Radiobutton(item_frame, text="PlanetScope (PSScene)", variable=self.item_type_var, 
                      value="PSScene", bg='#f0f0f0').pack(anchor='w')
        
        # Download Options Section
        download_frame = tk.LabelFrame(scrollable_frame, text="Download Options", bg='#f0f0f0', padx=10, pady=10)
        download_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.clip_to_aoi_var = tk.BooleanVar(value=True)
        tk.Checkbutton(download_frame, text="Clip to AOI (download only selected area)", 
                      variable=self.clip_to_aoi_var, bg='#f0f0f0',
                      font=('Arial', 9)).pack(anchor='w')
        tk.Label(download_frame, text="Uncheck to download full scene", 
                bg='#f0f0f0', fg='#666', font=('Arial', 8)).pack(anchor='w', padx=20)
        
        # Search Button
        self.search_btn = tk.Button(scrollable_frame, text="🔍 Search", command=self.perform_search,
                                    bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                                    padx=20, pady=10, cursor='hand2')
        self.search_btn.pack(pady=20, fill=tk.X, padx=10)
        
        # Status Label
        self.status_label = tk.Label(scrollable_frame, text="Ready to search", 
                                     bg='#f0f0f0', fg='#666', wraplength=350)
        self.status_label.pack(pady=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_results_panel(self, parent):
        """Create the results and preview panel"""
        
        # Top section - Results list
        results_frame = tk.LabelFrame(parent, text="Search Results", bg='white', padx=5, pady=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Toolbar for results
        toolbar_frame = tk.Frame(results_frame, bg='white')
        toolbar_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(toolbar_frame, text="Bulk Actions:", bg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar_frame, text="✓ Mark Selected as Exposed", 
                 command=lambda: self.mark_exposure(True),
                 bg='#FF9800', fg='white').pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar_frame, text="✗ Mark Selected as Not Exposed", 
                 command=lambda: self.mark_exposure(False),
                 bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar_frame, text="⎯ Clear Status", 
                 command=self.clear_exposure_status,
                 bg='#9E9E9E', fg='white').pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar_frame, text="📊 Export to CSV", 
                 command=self.export_to_csv,
                 bg='#2196F3', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.RIGHT, padx=5)
        
        # Tide data button
        tk.Button(toolbar_frame, text="🌊 Load Tide Data", 
                 command=self.load_tide_data,
                 bg='#00BCD4', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.RIGHT, padx=5)
        
        # Sort by tide button
        self.sort_tide_btn = tk.Button(toolbar_frame, text="↓ Sort by Lowest Tide", 
                 command=self.sort_by_tide,
                 bg='#009688', fg='white', state='disabled')
        self.sort_tide_btn.pack(side=tk.RIGHT, padx=5)
        
        # Results table
        columns = ('ID', 'Date', 'Cloud %', 'Visible %', 'GSD (m)', 'Tide Height (m)', 'Exposure Status')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings', height=8)
        
        self.results_tree.heading('#0', text='#')
        self.results_tree.column('#0', width=50, anchor='center')
        
        column_widths = {'ID': 180, 'Date': 100, 'Cloud %': 80, 'Visible %': 80, 'GSD (m)': 80, 'Tide Height (m)': 110, 'Exposure Status': 120}
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=column_widths.get(col, 100), anchor='center')
        
        # Configure tag colors for exposure status
        self.results_tree.tag_configure('exposed', background='#FFEBEE')
        self.results_tree.tag_configure('not_exposed', background='#E8F5E9')
        
        # Scrollbar for results
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)
        
        # Bottom section - Image preview
        preview_frame = tk.LabelFrame(parent, text="Image Preview", bg='white', padx=5, pady=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Preview controls
        controls_frame = tk.Frame(preview_frame, bg='white')
        controls_frame.pack(fill=tk.X, pady=5)
        
        self.prev_btn = tk.Button(controls_frame, text="◀ Previous", command=self.show_previous,
                                  state='disabled')
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        # Toggle preview mode button
        self.toggle_preview_btn = tk.Button(controls_frame, text="🔍 View Full Scene", 
                                           command=self.toggle_preview_mode,
                                           state='disabled', bg='#9C27B0', fg='white')
        self.toggle_preview_btn.pack(side=tk.LEFT, padx=5)
        
        # Save preview button
        self.save_preview_btn = tk.Button(controls_frame, text="💾 Save Preview", 
                                         command=self.save_preview_image,
                                         state='disabled', bg='#00BCD4', fg='white')
        self.save_preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.preview_info_label = tk.Label(controls_frame, text="Select an item to preview", 
                                          bg='white', font=('Arial', 10))
        self.preview_info_label.pack(side=tk.LEFT, expand=True, padx=10)
        
        self.next_btn = tk.Button(controls_frame, text="Next ▶", command=self.show_next,
                                 state='disabled')
        self.next_btn.pack(side=tk.RIGHT, padx=5)
        
        self.download_btn = tk.Button(controls_frame, text="💾 Download Asset", 
                                     command=self.download_selected,
                                     state='disabled', bg='#2196F3', fg='white')
        self.download_btn.pack(side=tk.RIGHT, padx=5)
        
        # Exposure status buttons
        tk.Label(controls_frame, text="Exposure:", bg='white', font=('Arial', 9)).pack(side=tk.RIGHT, padx=(20, 5))
        
        self.exposed_btn = tk.Button(controls_frame, text="☀ Exposed", 
                                     command=lambda: self.mark_current_exposure(True),
                                     state='disabled', bg='#FF9800', fg='white', width=10)
        self.exposed_btn.pack(side=tk.RIGHT, padx=2)
        
        self.not_exposed_btn = tk.Button(controls_frame, text="🌊 Not Exposed", 
                                         command=lambda: self.mark_current_exposure(False),
                                         state='disabled', bg='#4CAF50', fg='white', width=12)
        self.not_exposed_btn.pack(side=tk.RIGHT, padx=2)
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(preview_frame, bg='#e0e0e0', highlightthickness=1)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Loading label
        self.loading_label = tk.Label(self.preview_canvas, text="", bg='#e0e0e0', 
                                     font=('Arial', 12))
        
    def calculate_aoi(self):
        """Calculate AOI bounding box from center point and grid size"""
        try:
            center_lat = float(self.lat_entry.get())
            center_lon = float(self.lon_entry.get())
            
            # Parse grid size from dropdown (e.g., "3x3 (~0.59 km²)" -> 3)
            grid_str = self.grid_size_var.get()
            grid_size = int(grid_str.split('x')[0])
            
            # Each tile at zoom 17 is approximately 256 pixels * (156543.03 meters/pixel at equator / 2^17)
            # At this latitude (~19°S), tile width is ~192 meters
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
            
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid AOI parameters: {str(e)}")
            return None, None
            
    def perform_search(self):
        """Execute the search with current filter settings"""
        
        # Disable search button
        self.search_btn.config(state='disabled', text='Searching...')
        self.status_label.config(text="Searching for imagery...")
        
        # Run search in separate thread
        thread = threading.Thread(target=self._search_thread)
        thread.daemon = True
        thread.start()
        
    def _search_thread(self):
        """Background thread for search operation"""
        try:
            # Calculate AOI
            aoi, aoi_bounds = self.calculate_aoi()
            if not aoi:
                return
                
            self.aoi_bounds = aoi_bounds
            
            # Parse dates
            start_date = datetime.strptime(self.start_date_entry.get(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_entry.get(), "%Y-%m-%d")
            
            # Get filter values
            max_cloud = float(self.cloud_entry.get()) / 100.0
            min_coverage = float(self.coverage_entry.get())
            item_type = self.item_type_var.get()
            
            # Build filters
            date_filter = data_filter.date_range_filter(
                field_name="acquired",
                gte=start_date,
                lte=end_date
            )
            
            cloud_filter = data_filter.range_filter(
                field_name="cloud_cover",
                lte=max_cloud
            )
            
            coverage_filter = data_filter.range_filter(
                field_name="visible_percent",
                gte=min_coverage
            )
            
            geometry_filter = data_filter.geometry_filter(aoi)
            
            combined_filter = data_filter.and_filter([
                date_filter,
                cloud_filter,
                coverage_filter,
                geometry_filter
            ])
            
            # Perform search
            search_results = self.pl.data.search(
                item_types=[item_type],
                search_filter=combined_filter,
                limit=0  # No limit - fetch all results
            )
            
            # Collect all results (iterate through all pages)
            self.results = []
            count = 0
            for item in search_results:
                self.results.append(item)
                count += 1
                # Update status every 10 items
                if count % 10 == 0:
                    self.root.after(0, lambda c=count: self.status_label.config(text=f"Found {c} scenes..."))
            
            # Update UI on main thread
            self.root.after(0, self._update_results_ui)
            
        except Exception as e:
            self.root.after(0, lambda: self._search_error(str(e)))
            
    def _update_results_ui(self):
        """Update the results table with search results"""
        
        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Reset exposure status for new search
        self.exposure_status = {}
        
        # Add new results
        for idx, item in enumerate(self.results, 1):
            props = item['properties']
            item_id = item['id']
            exposure_status = self.exposure_status.get(item_id, 'Not Marked')
            
            # Get tide height if available
            tide_height = self.get_tide_height_for_item(item_id)
            tide_display = f"{tide_height:.2f}" if tide_height is not None else "N/A"
            
            # Determine tag based on exposure status
            tag = ()
            if exposure_status == 'Exposed':
                tag = ('exposed',)
            elif exposure_status == 'Not Exposed':
                tag = ('not_exposed',)
            
            self.results_tree.insert('', 'end', text=str(idx), values=(
                item_id,
                props['acquired'][:10],
                f"{props['cloud_cover']*100:.1f}",
                f"{props.get('visible_percent', 'N/A')}",
                f"{props.get('gsd', 'N/A')}",
                tide_display,
                exposure_status
            ), tags=tag)
        
        # Update status
        self.status_label.config(text=f"Found {len(self.results)} scenes")
        self.search_btn.config(state='normal', text='🔍 Search')
        
        if self.results:
            messagebox.showinfo("Search Complete", f"Found {len(self.results)} scenes matching your criteria!")
        else:
            messagebox.showwarning("No Results", "No scenes found matching your criteria.")
            
    def _search_error(self, error_msg):
        """Handle search error"""
        self.status_label.config(text=f"Error: {error_msg}")
        self.search_btn.config(state='normal', text='🔍 Search')
        messagebox.showerror("Search Error", f"An error occurred during search:\n\n{error_msg}")
        
    def on_result_select(self, event):
        """Handle selection of a result in the table"""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            index = int(item['text']) - 1
            self.current_preview_index = index
            self.show_preview(index)
            
            # Enable navigation buttons
            self.prev_btn.config(state='normal' if index > 0 else 'disabled')
            self.next_btn.config(state='normal' if index < len(self.results) - 1 else 'disabled')
            self.download_btn.config(state='normal')
            self.exposed_btn.config(state='normal')
            self.not_exposed_btn.config(state='normal')
            self.toggle_preview_btn.config(state='normal')
            self.save_preview_btn.config(state='normal')
            
    def show_preview(self, index):
        """Display high-resolution preview for the selected item"""
        if index < 0 or index >= len(self.results):
            return
            
        item = self.results[index]
        item_id = item['id']
        item_type = item['properties']['item_type']
        
        # Update info label
        self.preview_info_label.config(text=f"Loading preview for {item_id}...")
        
        # Show loading indicator
        self.loading_label.config(text="Loading high-resolution preview...")
        self.loading_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # Load preview in background thread
        thread = threading.Thread(target=self._load_preview_thread, args=(item_id, item_type, index))
        thread.daemon = True
        thread.start()
        
    def _load_preview_thread(self, item_id, item_type, index):
        """Background thread to load tile preview"""
        try:
            # Calculate tile coordinates
            center_lat, center_lon, min_lat, max_lat, min_lon, max_lon = self.aoi_bounds
            
            # Get grid size from dropdown (e.g., "3x3 (~0.59 km²)" -> 3)
            grid_str = self.grid_size_var.get()
            grid_size = int(grid_str.split('x')[0])
            
            # Use zoom 17 for the selected grid size
            zoom = 17
            
            n = 2.0 ** zoom
            x_tile = int((center_lon + 180.0) / 360.0 * n)
            y_tile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                         (1 / math.cos(math.radians(center_lat)))) / math.pi) / 2.0 * n)
            
            # Determine tile fetch pattern based on preview mode
            if self.preview_mode == 'full':
                # Full scene: use zoom 16 for wider view
                zoom = 16
                n = 2.0 ** zoom
                x_tile = int((center_lon + 180.0) / 360.0 * n)
                y_tile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                             (1 / math.cos(math.radians(center_lat)))) / math.pi) / 2.0 * n)
                
                # Use 5x5 grid for full scene
                tiles_to_fetch = []
                full_grid_size = 5
                offset = full_grid_size // 2
                for dy in range(-offset, offset + 1):
                    for dx in range(-offset, offset + 1):
                        tiles_to_fetch.append((x_tile + dx, y_tile + dy))
                display_grid_size = full_grid_size
            else:
                # AOI view: use the selected grid size
                tiles_to_fetch = []
                offset = grid_size // 2
                for dy in range(-offset, offset + 1):
                    for dx in range(-offset, offset + 1):
                        tiles_to_fetch.append((x_tile + dx, y_tile + dy))
                display_grid_size = grid_size
            
            # Fetch tiles
            tile_server = "tiles0"
            auth = HTTPBasicAuth(self.api_key, "")
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
                
                # Save clean version for export (without circle)
                mosaic_clean = mosaic.copy()
                
                # Draw circle at the center coordinates (AOI center) for display only
                draw = ImageDraw.Draw(mosaic)
                
                # Center of mosaic
                center_x = tile_size * display_grid_size / 2
                center_y = tile_size * display_grid_size / 2
                
                # Draw a circle with radius proportional to grid size
                radius = 20 if display_grid_size <= 3 else 30
                circle_bbox = [
                    center_x - radius, center_y - radius,
                    center_x + radius, center_y + radius
                ]
                
                # Draw red circle with white outline for visibility
                draw.ellipse(circle_bbox, outline='white', width=4)
                draw.ellipse(circle_bbox, outline='red', width=3)
                
                # Update UI on main thread - pass both display version and clean version
                self.root.after(0, lambda: self._display_preview(mosaic, mosaic_clean, item_id, index))
            else:
                self.root.after(0, lambda: self._preview_error("Could not load tiles"))
                
        except Exception as e:
            self.root.after(0, lambda: self._preview_error(str(e)))
            
    def _display_preview(self, image, image_clean, item_id, index):
        """Display the loaded preview image"""
        
        # Store the clean image (without circle) for saving
        self.current_preview_image = image_clean.copy()
        
        # Hide loading label
        self.loading_label.place_forget()
        
        # Resize image to fit canvas
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            # Calculate scale
            scale = min(canvas_width / image.width, canvas_height / image.height) * 0.9
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(image)
        
        # Clear canvas and display image
        self.preview_canvas.delete('all')
        self.preview_canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            image=photo, anchor='center'
        )
        
        # Keep reference to prevent garbage collection
        self.preview_canvas.image = photo
        
        # Update info label
        self.preview_info_label.config(
            text=f"Preview {index + 1} of {len(self.results)}: {item_id}"
        )
        
    def _preview_error(self, error_msg):
        """Handle preview loading error"""
        self.loading_label.config(text=f"Error loading preview:\n{error_msg}")
        
    def show_previous(self):
        """Show previous result"""
        if self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.show_preview(self.current_preview_index)
            self.prev_btn.config(state='normal' if self.current_preview_index > 0 else 'disabled')
            self.next_btn.config(state='normal')
            
    def show_next(self):
        """Show next result"""
        if self.current_preview_index < len(self.results) - 1:
            self.current_preview_index += 1
            self.show_preview(self.current_preview_index)
            self.next_btn.config(state='normal' if self.current_preview_index < len(self.results) - 1 else 'disabled')
            self.prev_btn.config(state='normal')
    
    def toggle_preview_mode(self):
        """Toggle between AOI view and full scene view"""
        if self.preview_mode == 'aoi':
            self.preview_mode = 'full'
            self.toggle_preview_btn.config(text="🔍 View AOI", bg='#FF5722')
        else:
            self.preview_mode = 'aoi'
            self.toggle_preview_btn.config(text="🔍 View Full Scene", bg='#9C27B0')
        
        # Reload current preview with new mode
        if self.current_preview_index >= 0 and self.current_preview_index < len(self.results):
            self.show_preview(self.current_preview_index)
    
    def save_preview_image(self):
        """Save the current preview image to file with optional GeoTIFF georeferencing"""
        if self.current_preview_image is None:
            messagebox.showwarning("No Preview", "No preview image to save. Please select an item first.")
            return
        
        if self.current_preview_index < 0 or self.current_preview_index >= len(self.results):
            return
        
        # Get current item info
        item = self.results[self.current_preview_index]
        item_id = item['id']
        
        # Determine default filename based on preview mode
        mode_suffix = "full_scene" if self.preview_mode == 'full' else "aoi"
        default_filename = f"{item_id}_{mode_suffix}.tif"
        
        # Ask user where to save
        filename = filedialog.asksaveasfilename(
            defaultextension=".tif",
            filetypes=[
                ("GeoTIFF files", "*.tif"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*")
            ],
            initialfile=default_filename,
            title="Save Preview Image"
        )
        
        if filename:
            try:
                # Check if saving as GeoTIFF
                is_geotiff = filename.lower().endswith('.tif') or filename.lower().endswith('.tiff')
                
                if is_geotiff:
                    # Save as georeferenced GeoTIFF
                    self._save_as_geotiff(filename, item_id)
                else:
                    # Save as regular image
                    self.current_preview_image.save(filename)
                
                # Get file size
                file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                
                geo_info = "\nGeoreferenced: Yes (EPSG:4326)" if is_geotiff else ""
                
                messagebox.showinfo(
                    "Image Saved",
                    f"Preview saved successfully!\n\n"
                    f"File: {os.path.basename(filename)}\n"
                    f"Size: {file_size_mb:.2f} MB\n"
                    f"Dimensions: {self.current_preview_image.width}x{self.current_preview_image.height} pixels\n"
                    f"Mode: {mode_suffix.replace('_', ' ').title()}{geo_info}"
                )
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image:\n\n{str(e)}")
    
    def _save_as_geotiff(self, filename, item_id):
        """Save preview as georeferenced GeoTIFF"""
        try:
            from osgeo import gdal, osr
            import numpy as np
            
            # Get AOI bounds
            center_lat, center_lon, min_lat, max_lat, min_lon, max_lon = self.aoi_bounds
            
            # Determine zoom level and grid size based on preview mode
            if self.preview_mode == 'full':
                zoom = 16
                grid_size = 5
            else:
                zoom = 17
                grid_size = 3
            
            # Calculate tile coordinates
            n = 2.0 ** zoom
            x_tile = int((center_lon + 180.0) / 360.0 * n)
            y_tile = int((1.0 - math.log(math.tan(math.radians(center_lat)) + 
                         (1 / math.cos(math.radians(center_lat)))) / math.pi) / 2.0 * n)
            
            # Calculate geographic bounds of the mosaic
            offset = grid_size // 2
            
            # Top-left tile
            tile_x_min = x_tile - offset
            tile_y_min = y_tile - offset
            
            # Bottom-right tile
            tile_x_max = x_tile + offset
            tile_y_max = y_tile + offset
            
            # Convert tile coordinates to geographic coordinates
            def tile_to_lon(x, zoom):
                return x / (2.0 ** zoom) * 360.0 - 180.0
            
            def tile_to_lat(y, zoom):
                n = math.pi - 2.0 * math.pi * y / (2.0 ** zoom)
                return math.degrees(math.atan(math.sinh(n)))
            
            # Geographic bounds
            lon_min = tile_to_lon(tile_x_min, zoom)
            lat_max = tile_to_lat(tile_y_min, zoom)
            lon_max = tile_to_lon(tile_x_max + 1, zoom)
            lat_min = tile_to_lat(tile_y_max + 1, zoom)
            
            # Convert PIL Image to numpy array
            img_array = np.array(self.current_preview_image)
            
            # Create GeoTIFF
            driver = gdal.GetDriverByName('GTiff')
            height, width = img_array.shape[:2]
            bands = 3 if len(img_array.shape) == 3 else 1
            
            dataset = driver.Create(filename, width, height, bands, gdal.GDT_Byte,
                                  options=['COMPRESS=LZW', 'TILED=YES'])
            
            # Set geotransform (defines the affine transformation)
            # [top-left x, pixel width, 0, top-left y, 0, pixel height (negative)]
            pixel_width = (lon_max - lon_min) / width
            pixel_height = (lat_min - lat_max) / height
            geotransform = [lon_min, pixel_width, 0, lat_max, 0, pixel_height]
            dataset.SetGeoTransform(geotransform)
            
            # Set projection (WGS84)
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            dataset.SetProjection(srs.ExportToWkt())
            
            # Write image data
            if bands == 3:
                for i in range(3):
                    dataset.GetRasterBand(i + 1).WriteArray(img_array[:, :, i])
            else:
                dataset.GetRasterBand(1).WriteArray(img_array)
            
            # Add metadata
            dataset.SetMetadataItem('PLANET_ITEM_ID', item_id)
            dataset.SetMetadataItem('PREVIEW_MODE', self.preview_mode)
            dataset.SetMetadataItem('ZOOM_LEVEL', str(zoom))
            
            # Close dataset
            dataset.FlushCache()
            dataset = None
            
        except ImportError:
            # GDAL not available, fall back to regular TIFF
            messagebox.showwarning(
                "GDAL Not Available",
                "GDAL library not found. Saving as regular TIFF without georeferencing.\n\n"
                "To save as GeoTIFF, install GDAL:\n"
                "conda install -c conda-forge gdal"
            )
            self.current_preview_image.save(filename)
            
    def download_selected(self):
        """Order and download the currently selected asset"""
        if self.current_preview_index < 0 or self.current_preview_index >= len(self.results):
            return
        
        if not hasattr(self, 'aoi_bounds') or not self.aoi_bounds:
            messagebox.showerror("No AOI", "Please calculate AOI first before downloading.")
            return
            
        item = self.results[self.current_preview_index]
        item_id = item['id']
        
        # Check if clipping is enabled
        clip_enabled = self.clip_to_aoi_var.get()
        
        clip_msg = f"The image will be clipped to your AOI ({self.grid_size_var.get()})" if clip_enabled else "The full scene will be downloaded"
        
        response = messagebox.askyesno(
            "Order Image",
            f"Create order for {item_id}?\n\n"
            f"{clip_msg}\n"
            f"and downloaded to the current directory.\n\n"
            "This may take several minutes."
        )
        
        if response:
            self.download_btn.config(state='disabled', text='Ordering...')
            thread = threading.Thread(target=self._order_and_download_thread, args=(item_id,))
            thread.daemon = True
            thread.start()
            
    def _order_and_download_thread(self, item_id):
        """Background thread for ordering and downloading with optional clip tool"""
        try:
            import time
            
            # Check if clipping is enabled
            clip_enabled = self.clip_to_aoi_var.get()
            
            # Build order request
            if clip_enabled:
                # Get AOI geometry
                center_lat, center_lon, min_lat, max_lat, min_lon, max_lon = self.aoi_bounds
                
                # Create polygon for clip tool (in lon, lat order as required by GeoJSON)
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
                
                # Create clip tool
                clip = clip_tool(aoi_polygon)
                
                # Build order request with clip tool
                order_name = f"AOI_clip_{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                request = build_request(
                    name=order_name,
                    products=[
                        product(
                            item_ids=[item_id],
                            product_bundle="visual",
                            item_type="PSScene",
                        )
                    ],
                    tools=[clip],
                )
            else:
                # Build order request without clip tool (full scene)
                order_name = f"full_scene_{item_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                request = build_request(
                    name=order_name,
                    products=[
                        product(
                            item_ids=[item_id],
                            product_bundle="visual",
                            item_type="PSScene",
                        )
                    ],
                )
            
            # Create order
            self.root.after(0, lambda: self.status_label.config(text="Creating order..."))
            order = self.pl.orders.create_order(request)
            order_id = order['id']
            
            # Wait for order to complete
            self.root.after(0, lambda: self.status_label.config(text=f"Order {order_id} processing..."))
            
            max_wait = 600  # 10 minutes max wait
            elapsed = 0
            check_interval = 10  # Check every 10 seconds
            
            while elapsed < max_wait:
                order_status = self.pl.orders.get_order(order_id)
                state = order_status['state']
                
                self.root.after(0, lambda s=state: self.status_label.config(text=f"Order status: {s}"))
                
                if state == 'success':
                    # Order completed, download the results
                    download_dir = os.path.join("downloads", order_id)
                    os.makedirs(download_dir, exist_ok=True)
                    
                    self.root.after(0, lambda: self.status_label.config(text="Downloading clipped image..."))
                    
                    # Download all results using the Planet SDK
                    downloaded_files = []
                    for result in order_status['results']:
                        result_name = result['name']
                        download_url = result['location']
                        
                        filepath = os.path.join(download_dir, result_name)
                        
                        # Download using requests
                        response = requests.get(download_url, stream=True)
                        if response.status_code == 200:
                            with open(filepath, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            downloaded_files.append(filepath)
                    
                    self.root.after(0, lambda: self._download_complete(download_dir, downloaded_files))
                    return
                    
                elif state == 'failed':
                    error_msg = order_status.get('error', {}).get('message', 'Unknown error')
                    self.root.after(0, lambda: self._download_error(f"Order failed: {error_msg}"))
                    return
                
                elif state in ['cancelled', 'partial']:
                    self.root.after(0, lambda: self._download_error(f"Order {state}"))
                    return
                
                # Wait before checking again
                time.sleep(check_interval)
                elapsed += check_interval
            
            # Timeout
            self.root.after(0, lambda: self._download_error("Order timed out after 10 minutes"))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self._download_error(f"{str(e)}\n\n{error_details}"))
            
    def _download_complete(self, download_dir, files):
        """Handle successful download"""
        self.download_btn.config(state='normal', text='💾 Download Asset')
        self.status_label.config(text=f"Found {len(self.results)} scenes")
        
        files_list = "\n".join([os.path.basename(f) for f in files]) if files else "No files"
        messagebox.showinfo(
            "Download Complete", 
            f"Clipped image downloaded successfully!\n\n"
            f"Location: {download_dir}\n\n"
            f"Files:\n{files_list}"
        )
        
    def _download_error(self, error_msg):
        """Handle download error"""
        self.download_btn.config(state='normal', text='💾 Download Asset')
        messagebox.showerror("Download Error", f"Failed to download asset:\n\n{error_msg}")
    
    def mark_current_exposure(self, is_exposed):
        """Mark the currently previewed item's exposure status"""
        if self.current_preview_index < 0 or self.current_preview_index >= len(self.results):
            return
        
        item = self.results[self.current_preview_index]
        item_id = item['id']
        
        # Update exposure status
        self.exposure_status[item_id] = 'Exposed' if is_exposed else 'Not Exposed'
        
        # Update the table
        self._refresh_results_display()
        
        # Automatically move to next item
        if self.current_preview_index < len(self.results) - 1:
            self.show_next()
    
    def mark_exposure(self, is_exposed):
        """Mark selected items in the table with exposure status"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select one or more items to mark.")
            return
        
        status = 'Exposed' if is_exposed else 'Not Exposed'
        
        for sel in selection:
            item_data = self.results_tree.item(sel)
            item_id = item_data['values'][0]  # First column is ID
            self.exposure_status[item_id] = status
        
        # Refresh display
        self._refresh_results_display()
        
        messagebox.showinfo("Status Updated", 
                          f"Marked {len(selection)} item(s) as '{status}'")
    
    def clear_exposure_status(self):
        """Clear exposure status for selected items"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select one or more items to clear status.")
            return
        
        for sel in selection:
            item_data = self.results_tree.item(sel)
            item_id = item_data['values'][0]
            if item_id in self.exposure_status:
                del self.exposure_status[item_id]
        
        # Refresh display
        self._refresh_results_display()
        
        messagebox.showinfo("Status Cleared", 
                          f"Cleared status for {len(selection)} item(s)")
    
    def _refresh_results_display(self):
        """Refresh the results table to show updated exposure status"""
        # Get current scroll position
        current_selection = self.results_tree.selection()
        
        # Update all items
        for item_widget in self.results_tree.get_children():
            item_data = self.results_tree.item(item_widget)
            item_id = item_data['values'][0]
            exposure_status = self.exposure_status.get(item_id, 'Not Marked')
            
            # Get tide height if available
            tide_height = self.get_tide_height_for_item(item_id)
            tide_display = f"{tide_height:.2f}" if tide_height is not None else "N/A"
            
            # Update exposure status and tide height columns
            values = list(item_data['values'])
            values[5] = tide_display  # Tide Height is 6th column (index 5)
            values[6] = exposure_status  # Exposure Status is 7th column (index 6)
            
            # Determine tag
            tag = ()
            if exposure_status == 'Exposed':
                tag = ('exposed',)
            elif exposure_status == 'Not Exposed':
                tag = ('not_exposed',)
            
            self.results_tree.item(item_widget, values=values, tags=tag)
        
        # Restore selection
        if current_selection:
            self.results_tree.selection_set(current_selection)
    
    def export_to_csv(self):
        """Export search results with exposure status to CSV"""
        if not self.results:
            messagebox.showwarning("No Data", "No search results to export. Please perform a search first.")
            return
        
        # Ask user for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"planet_imagery_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'Item ID',
                    'Acquired Date',
                    'Acquired Time',
                    'Cloud Cover (%)',
                    'Visible Percent (%)',
                    'Clear Percent (%)',
                    'GSD (m)',
                    'Tide Height (m)',
                    'Satellite ID',
                    'Item Type',
                    'Exposure Status',
                    'View Angle',
                    'Sun Elevation',
                    'Sun Azimuth'
                ])
                
                # Write data
                for item in self.results:
                    item_id = item['id']
                    props = item['properties']
                    
                    # Parse datetime
                    acquired_dt = datetime.fromisoformat(props['acquired'].replace('Z', '+00:00'))
                    
                    # Get tide height
                    tide_height = self.get_tide_height_for_item(item_id)
                    tide_display = f"{tide_height:.2f}" if tide_height is not None else ""
                    
                    writer.writerow([
                        item_id,
                        acquired_dt.strftime('%Y-%m-%d'),
                        acquired_dt.strftime('%H:%M:%S'),
                        f"{props['cloud_cover']*100:.2f}",
                        props.get('visible_percent', ''),
                        props.get('clear_percent', ''),
                        props.get('gsd', ''),
                        tide_display,
                        props.get('satellite_id', ''),
                        props.get('item_type', ''),
                        self.exposure_status.get(item_id, 'Not Marked'),
                        props.get('view_angle', ''),
                        props.get('sun_elevation', ''),
                        props.get('sun_azimuth', '')
                    ])
            
            # Count marked items
            exposed_count = sum(1 for status in self.exposure_status.values() if status == 'Exposed')
            not_exposed_count = sum(1 for status in self.exposure_status.values() if status == 'Not Exposed')
            
            messagebox.showinfo(
                "Export Successful",
                f"Exported {len(self.results)} records to:\n{filename}\n\n"
                f"Exposure Status Summary:\n"
                f"  • Exposed: {exposed_count}\n"
                f"  • Not Exposed: {not_exposed_count}\n"
                f"  • Not Marked: {len(self.results) - exposed_count - not_exposed_count}"
            )
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV:\n\n{str(e)}")
    
    def load_tide_data(self):
        """Load tide data from CSV file"""
        filename = filedialog.askopenfilename(
            title="Select Tide Data CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir="data"
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            self.tide_data = {}
            line_count = 0
            
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Parse datetime - expecting ISO format like "2000-12-31T14:00:00Z"
                    dt_str = row['datetime']
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    
                    # Store tide height by datetime (rounded to nearest 10 minutes)
                    # Round to 10-minute intervals to match satellite times
                    dt_rounded = dt.replace(second=0, microsecond=0)
                    dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)
                    
                    tide_height = float(row['tide_height'])
                    self.tide_data[dt_rounded] = tide_height
                    line_count += 1
            
            self.tide_file_loaded = filename
            
            # Enable sort button
            self.sort_tide_btn.config(state='normal')
            
            # Refresh display to show tide heights
            if self.results:
                self._refresh_results_display()
            
            messagebox.showinfo(
                "Tide Data Loaded",
                f"Successfully loaded {line_count} tide records from:\n{filename}\n\n"
                f"Tide data loaded! You can now:\n"
                f"  • View tide heights in the results table\n"
                f"  • Sort by lowest tide using the sort button\n"
                f"  • Export results with tide heights to CSV"
            )
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load tide data:\n\n{str(e)}")
    
    def get_tide_height_for_item(self, item_id):
        """
        Extract datetime from satellite item ID and match with tide data.
        Item ID format: YYYYMMDD_HHMMSS_XX_XXXX or YYYYMMDDHHMMSSXXXXXX
        Example: 20250530_002244_03_24bd or 20240623004021272478
        """
        if not self.tide_data:
            return None
        
        try:
            # Convert to string if it's not already
            item_id_str = str(item_id)
            
            # Check if it has underscores (format: YYYYMMDD_HHMMSS_XX_XXXX)
            if '_' in item_id_str:
                date_time_part = item_id_str.split('_')[:2]  # Get first two parts
                date_str = date_time_part[0]  # YYYYMMDD
                time_str = date_time_part[1]  # HHMMSS
            else:
                # No underscores - format is continuous: YYYYMMDDHHMMSSXXXXXX
                # Extract first 14 characters for YYYYMMDDHHMMSS
                date_str = item_id_str[0:8]   # YYYYMMDD
                time_str = item_id_str[8:14]  # HHMMSS
            
            # Parse into datetime
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            # Create datetime object in UTC (timezone-aware)
            from datetime import timezone
            dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
            
            # Round to nearest 10 minutes to match tide data
            dt_rounded = dt.replace(second=0, microsecond=0)
            dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)
            
            # Look up tide height
            if dt_rounded in self.tide_data:
                return self.tide_data[dt_rounded]
            
            # If exact match not found, try finding closest time within ±10 minutes
            for offset in range(-1, 2):  # Try -10, 0, +10 minutes
                check_dt = dt_rounded + timedelta(minutes=offset * 10)
                if check_dt in self.tide_data:
                    return self.tide_data[check_dt]
            
            return None
            
        except Exception as e:
            print(f"Error parsing datetime from {item_id}: {e}")
            return None
    
    def sort_by_tide(self):
        """Sort results by tide height (lowest first)"""
        if not self.results:
            messagebox.showwarning("No Data", "No search results to sort.")
            return
        
        if not self.tide_data:
            messagebox.showwarning("No Tide Data", "Please load tide data first using the '🌊 Load Tide Data' button.")
            return
        
        # Add tide height to each result for sorting
        results_with_tide = []
        for item in self.results:
            tide_height = self.get_tide_height_for_item(item['id'])
            results_with_tide.append((item, tide_height))
        
        # Sort by tide height (None values go to end)
        results_with_tide.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else float('inf')))
        
        # Update results list
        self.results = [item for item, _ in results_with_tide]
        
        # Refresh display
        self._update_results_ui()
        
        # Count how many have tide data
        with_tide = sum(1 for _, tide in results_with_tide if tide is not None)
        
        messagebox.showinfo(
            "Sorted by Tide",
            f"Results sorted by tide height (lowest first).\n\n"
            f"{with_tide} of {len(self.results)} items matched with tide data."
        )


def main():
    root = tk.Tk()
    app = PlanetImageryBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
