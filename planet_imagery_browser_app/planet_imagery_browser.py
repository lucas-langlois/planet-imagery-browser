"""
Planet Imagery Browser - GUI Application
Search and preview Planet satellite imagery with interactive filters
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from tkinter import font as tkfont
import threading
from datetime import datetime, timedelta, timezone
import math
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import base64
import tempfile
import webbrowser

try:
    from cefpython3 import cefpython as cef
    import ctypes
    CEF_AVAILABLE = True
except ImportError:
    cef = None
    CEF_AVAILABLE = False
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
        
        # Try to get API key from multiple sources (in order of priority):
        # 1. Environment variable (most secure for production)
        # 2. config.py file (convenient for local development)
        # 3. Prompt user (fallback)
        
        self.api_key = os.getenv('PLANET_API_KEY', '').strip()
        
        # If not in environment, try loading from config.py
        if not self.api_key:
            try:
                import config
                self.api_key = getattr(config, 'PLANET_API_KEY', '').strip()
                if self.api_key:
                    print("✓ API key loaded from config.py")
            except ImportError:
                pass  # config.py doesn't exist, will prompt user
        
        if not self.api_key:
            self.api_key = self.prompt_for_api_key()
            if self.api_key:
                messagebox.showinfo(
                    "API Key Applied",
                    "Planet API key stored for this session.\n\n"
                    "Set the PLANET_API_KEY environment variable to skip this prompt."
                )
            else:
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
        
        # Tide data storage
        self.tide_data = {}  # Dict mapping datetime to tide_height
        self.tide_file_loaded = None
        
        # Preview mode: 'aoi' or 'full'
        self.preview_mode = 'aoi'
        
        # Store current preview image
        self.current_preview_image = None
        self.current_preview_clean = None
        self.current_leaflet_html = None
        self.current_leaflet_file = None
        self.current_preview_bounds = None
        self.cef_browser = None
        self.map_container = None
        self.cef_initialized = False
        self.aoi_selection_mode = False
        
        # Create main layout
        self.create_ui()
        
    def create_ui(self):
        """Create the main user interface"""
        
        # Create main containers using PanedWindow for better separation
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(main_paned, width=400, bg='#f0f0f0')
        main_paned.add(left_panel, width=400, minsize=350, stretch="never")
        
        # Bind click on left panel to release CEF focus
        left_panel.bind('<Button-1>', self._on_left_panel_click)
        
        right_panel = tk.Frame(main_paned, bg='white')
        main_paned.add(right_panel, stretch="always")
        
        # LEFT PANEL - Search Filters
        self.create_filter_panel(left_panel)
        
        # RIGHT PANEL - Results and Preview
        self.create_results_panel(right_panel)

    def prompt_for_api_key(self):
        """Prompt the user for their Planet API key via dialog."""
        prompt_text = (
            "Enter your Planet API key (starts with PLAK).\n"
            "The key will be used for this session only."
        )
        while True:
            key = simpledialog.askstring(
                "Planet API Key",
                prompt_text,
                parent=self.root,
                show='*'
            )

            if key is None:
                return ""

            key = key.strip()
            if not key:
                retry = messagebox.askretrycancel(
                    "Invalid API Key",
                    "The API key cannot be empty. Would you like to try again?"
                )
                if not retry:
                    return ""
                continue

            os.environ['PLANET_API_KEY'] = key
            return key
        
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
        self.lat_entry.bind('<FocusIn>', self._on_entry_focus)
        
        tk.Label(aoi_frame, text="Center Longitude:", bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=2)
        self.lon_entry = tk.Entry(aoi_frame, width=20)
        self.lon_entry.insert(0, "146.6825115")
        self.lon_entry.grid(row=1, column=1, pady=2)
        self.lon_entry.bind('<FocusIn>', self._on_entry_focus)
        
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
        
        # Button to set AOI from map click
        self.set_aoi_btn = tk.Button(aoi_frame, text="📍 Click Map to Set AOI", 
                                     command=self.enable_aoi_selection,
                                     bg='#FF9800', fg='white', state='disabled')
        self.set_aoi_btn.grid(row=3, column=0, columnspan=2, pady=5, sticky='ew')
        
        # Date Range Section
        date_frame = tk.LabelFrame(scrollable_frame, text="Date Range", bg='#f0f0f0', padx=10, pady=10)
        date_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(date_frame, text="Start Date (YYYY-MM-DD):", bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=2)
        self.start_date_entry = tk.Entry(date_frame, width=20)
        self.start_date_entry.insert(0, "2024-06-01")
        self.start_date_entry.grid(row=0, column=1, pady=2)
        self.start_date_entry.bind('<FocusIn>', self._on_entry_focus)
        
        tk.Label(date_frame, text="End Date (YYYY-MM-DD):", bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=2)
        self.end_date_entry = tk.Entry(date_frame, width=20)
        self.end_date_entry.insert(0, "2025-05-31")
        self.end_date_entry.grid(row=1, column=1, pady=2)
        self.end_date_entry.bind('<FocusIn>', self._on_entry_focus)
        
        # Cloud Cover Section - Removed (no cloud filter)
        
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
        # Search and Reset buttons
        button_frame = tk.Frame(scrollable_frame, bg='#f0f0f0')
        button_frame.pack(pady=20, padx=10, fill=tk.X)
        
        self.search_btn = tk.Button(button_frame, text="🔍 Search", command=self.perform_search,
                                    bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                                    padx=20, pady=10, cursor='hand2')
        self.search_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.reset_btn = tk.Button(button_frame, text="🔄 Reset", command=self.reset_search,
                                   bg='#FF9800', fg='white', font=('Arial', 12, 'bold'),
                                   padx=20, pady=10, cursor='hand2')
        self.reset_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Status Label
        self.status_label = tk.Label(scrollable_frame, text="Ready to search", 
                                     bg='#f0f0f0', fg='#666', wraplength=350)
        self.status_label.pack(pady=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_results_panel(self, parent):
        """Create the results and preview panel"""
        
        # Use PanedWindow for resizable panes
        paned = tk.PanedWindow(parent, orient=tk.VERTICAL, sashwidth=5, bg='#cccccc')
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top section - Results list (smaller)
        results_frame = tk.LabelFrame(paned, text="Search Results", bg='white', padx=5, pady=5)
        paned.add(results_frame, height=250)
        
        # Toolbar for results
        toolbar_frame = tk.Frame(results_frame, bg='white')
        toolbar_frame.pack(fill=tk.X, pady=5)
        
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
        columns = ('ID', 'Date', 'Cloud %', 'Visible %', 'GSD (m)', 'Tide Height (m)')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings', height=5)
        
        self.results_tree.heading('#0', text='#')
        self.results_tree.column('#0', width=50, anchor='center')
        
        column_widths = {'ID': 180, 'Date': 100, 'Cloud %': 80, 'Visible %': 80, 'GSD (m)': 80, 'Tide Height (m)': 110}
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=column_widths.get(col, 100), anchor='center')
        
        # Scrollbar for results
        results_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)
        
        # Bottom section - Image preview (larger)
        preview_frame = tk.LabelFrame(paned, text="Image Preview", bg='white', padx=5, pady=5)
        paned.add(preview_frame, minsize=400)
        
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
        
        self.leaflet_btn = tk.Button(controls_frame, text="🌐 Open Map in Browser",
                                     command=self.open_leaflet_map,
                                     state='disabled', bg='#3F51B5', fg='white')
        self.leaflet_btn.pack(side=tk.LEFT, padx=5)
        
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
        
        
        # Interactive map (no static preview)
        map_tab = tk.Frame(preview_frame, bg='white')
        map_tab.pack(fill=tk.BOTH, expand=True)
        self.map_container = map_tab
        
        if CEF_AVAILABLE:
            # Initialize CEF on first use
            self._initialize_cef()
            # Create frame for CEF browser
            self.cef_frame = tk.Frame(map_tab, bg='white')
            self.cef_frame.pack(fill=tk.BOTH, expand=True)
            
            # Bind click event to manage focus properly
            self.cef_frame.bind('<Button-1>', self._on_map_click)
            
            # Load initial base map showing Queensland coast
            self.root.after(100, self._load_initial_map)
        else:
            self.map_placeholder = tk.Label(
                map_tab,
                text=(
                    "Interactive map preview requires 'cefpython3'.\n\n"
                    "Install with: pip install cefpython3\n\n"
                    "Note: cefpython3 works best on Windows and Linux.\n"
                    "For macOS, use the browser button instead."
                ),
                bg='white', fg='#555', justify='center', font=('Arial', 10)
            )
            self.map_placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
    def _on_entry_focus(self, event):
        """Handle entry field focus - tell CEF to release keyboard focus"""
        if CEF_AVAILABLE and self.cef_browser:
            try:
                # Set focus to false in CEF so keyboard events go to Tkinter
                self.cef_browser.SetFocus(False)
            except:
                pass  # CEF might not be ready yet
        # Make sure the entry field has focus
        event.widget.focus_force()
        # Schedule another focus check to ensure it sticks
        event.widget.after(50, lambda: event.widget.focus_force())
    
    def _on_left_panel_click(self, event):
        """Handle left panel click - release CEF focus"""
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(False)
            except:
                pass
    
    def _on_map_click(self, event):
        """Handle map click - give focus back to CEF"""
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(True)
            except:
                pass
        self.cef_frame.focus_set()
    
    def _load_initial_map(self):
        """Load an initial base map showing Queensland coast for AOI selection"""
        if not CEF_AVAILABLE or not self.cef_initialized:
            return
        
        # Queensland coast bounds (approximate)
        qld_bounds = {
            'south': -28.5,  # Southern QLD
            'north': -10.0,  # Northern QLD (Cape York)
            'west': 142.0,
            'east': 154.0
        }
        
        center_lat = (qld_bounds['south'] + qld_bounds['north']) / 2
        center_lon = (qld_bounds['west'] + qld_bounds['east']) / 2
        
        html_content = self._build_base_map_html(center_lat, center_lon, 6)
        
        if html_content:
            self._render_html_in_cef(html_content)
            self.set_aoi_btn.config(state='normal')
            self.preview_info_label.config(text="Click '📍 Click Map to Set AOI' button, then click on the map to set your location")
            
            # Release CEF focus after map loads so user can edit search filters
            self.root.after(500, self._release_cef_focus)
    
    def _release_cef_focus(self):
        """Helper to release CEF focus"""
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(False)
            except:
                pass
    
    def _build_base_map_html(self, center_lat, center_lon, zoom):
        """Build HTML for the base map without any imagery overlay"""
        try:
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Planet Imagery Browser - Select AOI</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
    <style>
        html, body {{ margin: 0; padding: 0; height: 100%; }}
        #map {{ width: 100%; height: 100%; background: #f0f0f0; }}
        .leaflet-container {{ font: 14px/1.4 'Helvetica Neue', Arial, Helvetica, sans-serif; }}
        .info-box {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 1000;
            max-width: 300px;
        }}
        .info-box h3 {{ margin: 0 0 10px 0; color: #2196F3; }}
        .info-box p {{ margin: 5px 0; font-size: 13px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="info-box">
        <h3>🗺️ Select Your AOI Location</h3>
        <p><strong>Instructions:</strong></p>
        <p>1. Click <strong>"📍 Click Map to Set AOI"</strong> button</p>
        <p>2. Click anywhere on the map</p>
        <p>3. Your AOI center will be updated</p>
        <p>4. Click <strong>"🔍 Search"</strong> to find imagery</p>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});

        // Add OpenStreetMap basemap
        L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }}).addTo(map);

        // Variable to store current AOI marker
        var currentAOIMarker = null;
        
        // Add click handler for AOI selection
        map.on('click', function(e) {{
            var clickedLat = e.latlng.lat;
            var clickedLng = e.latlng.lng;
            
            // Send coordinates back to Python by setting document title
            document.title = 'AOI_CLICK:' + clickedLat + ',' + clickedLng;
            
            // Remove previous marker if it exists
            if (currentAOIMarker) {{
                map.removeLayer(currentAOIMarker);
            }}
            
            // Add new marker
            currentAOIMarker = L.marker([clickedLat, clickedLng], {{
                icon: L.icon({{
                    iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNSIgaGVpZ2h0PSI0MSI+PHBhdGggZmlsbD0iI0ZGOTgwMCIgZD0iTTEyLjUgMEMxOS40IDAgMjUgNS42IDI1IDEyLjVjMCA2LjktMTIuNSAyOC41LTEyLjUgMjguNVMwIDE5LjQgMCAxMi41QzAgNS42IDUuNiAwIDEyLjUgMHoiLz48Y2lyY2xlIGZpbGw9IiNmZmYiIGN4PSIxMi41IiBjeT0iMTIuNSIgcj0iNSIvPjwvc3ZnPg==',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41]
                }})
            }}).addTo(map).bindPopup(
                '<strong>New AOI Center</strong><br/>Lat: ' + clickedLat.toFixed(6) + 
                '<br/>Lng: ' + clickedLng.toFixed(6)
            ).openPopup();
        }});

        L.control.scale().addTo(map);
        
        // Add info about Queensland coast
        L.marker([-19.2577, 146.8177]).addTo(map)
            .bindPopup('<strong>Example: Townsville</strong><br/>Click to set as AOI');
        L.marker([-16.9186, 145.7781]).addTo(map)
            .bindPopup('<strong>Example: Cairns</strong><br/>Click to set as AOI');
        L.marker([-27.4705, 153.0260]).addTo(map)
            .bindPopup('<strong>Example: Brisbane</strong><br/>Click to set as AOI');
    </script>
</body>
</html>
"""
            return html_template
        except Exception as e:
            print(f"Error building base map HTML: {e}")
            return None
    
    def _render_html_in_cef(self, html_content):
        """Render arbitrary HTML content in the CEF browser"""
        if not html_content or not CEF_AVAILABLE or not self.cef_initialized:
            return
        
        try:
            # Save HTML to temporary file
            import tempfile
            import os
            
            # Clean up old temp file if exists
            if hasattr(self, '_temp_html_file'):
                try:
                    self._temp_html_file.close()
                    if os.path.exists(self._temp_html_file.name):
                        os.unlink(self._temp_html_file.name)
                except:
                    pass
            
            self._temp_html_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.html',
                delete=False,
                encoding='utf-8'
            )
            
            # Write HTML to temp file
            self._temp_html_file.write(html_content)
            self._temp_html_file.flush()
            
            # Convert to file:// URL
            file_url = 'file:///' + self._temp_html_file.name.replace('\\', '/')
            
            # Get window handle
            window_info = cef.WindowInfo()
            width = self.cef_frame.winfo_width()
            height = self.cef_frame.winfo_height()
            rect = [0, 0, width, height]
            window_info.SetAsChild(self._get_window_handle(self.cef_frame), rect)
            
            # Create or update browser
            if self.cef_browser:
                self.cef_browser.LoadUrl(file_url)
            else:
                self.cef_browser = cef.CreateBrowserSync(
                    window_info,
                    url=file_url
                )
                
                # Set display handler to monitor title changes
                display_handler = DisplayHandler(self)
                self.cef_browser.SetClientHandler(display_handler)
                
                # Bind resize event
                self.cef_frame.bind("<Configure>", self._on_cef_configure)
        except Exception as e:
            print(f"Error rendering HTML in CEF: {e}")
            import traceback
            traceback.print_exc()
    
    def enable_aoi_selection(self):
        """Enable AOI selection mode - user can click on map to set center point"""
        self.aoi_selection_mode = True
        self.set_aoi_btn.config(text="🎯 Click on Map Now!", bg='#4CAF50')
        self.preview_info_label.config(text="Click anywhere on the map to set new AOI center point")
        
        # Regenerate the map with click handler enabled
        if self.current_leaflet_html and self.current_preview_clean:
            # Rebuild HTML with click enabled
            bounds = self.current_preview_bounds
            if bounds:
                min_lat, max_lat, min_lon, max_lon = bounds
                center_lat = (min_lat + max_lat) / 2
                center_lon = (min_lon + max_lon) / 2
                
                # Get current zoom and grid size from the stored values
                if hasattr(self, '_last_zoom'):
                    zoom = self._last_zoom
                else:
                    zoom = 17
                if hasattr(self, '_last_grid_size'):
                    grid_size = self._last_grid_size
                else:
                    grid_size = 3
                if hasattr(self, '_last_item_id'):
                    item_id = self._last_item_id
                else:
                    item_id = "unknown"
                
                self.current_leaflet_html = self._build_leaflet_html(
                    self.current_preview_clean,
                    bounds,
                    (center_lat, center_lon),
                    zoom,
                    grid_size,
                    item_id
                )
                self._render_leaflet_map()
    
    def update_aoi_from_map(self, lat, lon):
        """Update AOI center from map click"""
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, f"{lat:.7f}")
        self.lon_entry.delete(0, tk.END)
        self.lon_entry.insert(0, f"{lon:.7f}")
        
        # Disable selection mode
        self.aoi_selection_mode = False
        self.set_aoi_btn.config(text="📍 Click Map to Set AOI", bg='#FF9800')
        
        # Release CEF focus so user can interact with controls
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(False)
            except:
                pass
        
        # Recalculate AOI
        self.calculate_aoi()
        
        # Update message
        if self.results:
            self.preview_info_label.config(text=f"AOI updated to: {lat:.6f}, {lon:.6f}. Click 🔄 Reset to clear old results, or 🔍 Search for new imagery.")
        else:
            self.preview_info_label.config(text=f"AOI center set to: {lat:.6f}, {lon:.6f}. Click 🔍 Search to find imagery.")
    
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
            
    def reset_search(self):
        """Reset search and reload initial map"""
        # Release CEF focus so user can interact with controls
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(False)
            except:
                pass
        
        self._reset_search_state(reload_map=True)
        self.status_label.config(text="Ready to search")
        messagebox.showinfo("Reset Complete", "Search cleared. Set your AOI and search again.")
    
    def perform_search(self):
        """Execute the search with current filter settings"""
        
        print("DEBUG: Starting search...")
        
        # Release CEF focus immediately so user can edit fields during search
        if CEF_AVAILABLE and self.cef_browser:
            try:
                self.cef_browser.SetFocus(False)
            except:
                pass
        
        # Clear previous results but don't reload map during search
        if self.results:
            # Only clear results tree, keep map as-is
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.results = []
            self.current_preview_index = 0
        
        # Disable search button
        self.search_btn.config(state='disabled', text='Searching...')
        self.status_label.config(text="Searching for imagery...")
        
        # Run search in separate thread
        thread = threading.Thread(target=self._search_thread)
        thread.daemon = True
        thread.start()
        print("DEBUG: Search thread started")
    
    def _reset_search_state(self, reload_map=True):
        """Reset all state from previous search"""
        # Clear results
        self.results = []
        self.current_preview_index = 0
        
        # Clear results tree
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Clear preview state
        self.current_preview_image = None
        self.current_preview_clean = None
        self.current_leaflet_html = None
        self.current_preview_bounds = None
        
        # Reset preview mode to AOI
        self.preview_mode = 'aoi'
        
        # Disable navigation buttons
        self.prev_btn.config(state='disabled')
        self.next_btn.config(state='disabled')
        self.toggle_preview_btn.config(state='disabled', text='🔍 View Full Scene')
        self.save_preview_btn.config(state='disabled')
        self.leaflet_btn.config(state='disabled')
        self.download_btn.config(state='disabled')
        
        # Reset preview info
        if reload_map:
            self.preview_info_label.config(text="Click '📍 Click Map to Set AOI' to select location, then search")
        else:
            self.preview_info_label.config(text="Searching for imagery...")
        
        # Reload initial base map (only if requested, not during active search)
        if reload_map and CEF_AVAILABLE and self.cef_initialized:
            self.root.after(100, self._load_initial_map)
        
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
            min_coverage = float(self.coverage_entry.get())
            item_type = self.item_type_var.get()
            
            # Build filters (no cloud cover filter)
            date_filter = data_filter.date_range_filter(
                field_name="acquired",
                gte=start_date,
                lte=end_date
            )
            
            coverage_filter = data_filter.range_filter(
                field_name="visible_percent",
                gte=min_coverage
            )
            
            geometry_filter = data_filter.geometry_filter(aoi)
            
            combined_filter = data_filter.and_filter([
                date_filter,
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
        
        # Add new results
        for idx, item in enumerate(self.results, 1):
            props = item['properties']
            item_id = item['id']
            
            # Get tide height if available
            tide_height = self.get_tide_height_for_item(item_id)
            tide_display = f"{tide_height:.2f}" if tide_height is not None else "N/A"
            
            self.results_tree.insert('', 'end', text=str(idx), values=(
                item_id,
                props['acquired'][:10],
                f"{props['cloud_cover']*100:.1f}",
                f"{props.get('visible_percent', 'N/A')}",
                f"{props.get('gsd', 'N/A')}",
                tide_display
            ))
        
        # Update status
        self.status_label.config(text=f"Found {len(self.results)} scenes")
        self.search_btn.config(state='normal', text='🔍 Search')
        
        # Enable AOI selection button when results are available
        if self.results:
            self.set_aoi_btn.config(state='normal')
            messagebox.showinfo("Search Complete", f"Found {len(self.results)} scenes matching your criteria!")
        else:
            self.set_aoi_btn.config(state='disabled')
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
            tile_x_values = []
            tile_y_values = []
            if self.preview_mode == 'full':
                # Full scene: use same zoom (17) but 15x15 grid for wider view
                # Keep zoom at 17 for consistent tile resolution
                
                # Use 15x15 grid for full scene
                tiles_to_fetch = []
                full_grid_size = 15
                offset = full_grid_size // 2
                for dy in range(-offset, offset + 1):
                    for dx in range(-offset, offset + 1):
                        tx = x_tile + dx
                        ty = y_tile + dy
                        tiles_to_fetch.append((tx, ty))
                        tile_x_values.append(tx)
                        tile_y_values.append(ty)
                display_grid_size = full_grid_size
            else:
                # AOI view: use the selected grid size
                tiles_to_fetch = []
                offset = grid_size // 2
                for dy in range(-offset, offset + 1):
                    for dx in range(-offset, offset + 1):
                        tx = x_tile + dx
                        ty = y_tile + dy
                        tiles_to_fetch.append((tx, ty))
                        tile_x_values.append(tx)
                        tile_y_values.append(ty)
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
                
                # Calculate geographic bounds of the mosaic
                min_tile_x = min(tile_x_values)
                max_tile_x = max(tile_x_values)
                min_tile_y = min(tile_y_values)
                max_tile_y = max(tile_y_values)

                min_lon = self._tile_x_to_lon(min_tile_x, zoom)
                max_lon = self._tile_x_to_lon(max_tile_x + 1, zoom)
                max_lat = self._tile_y_to_lat(min_tile_y, zoom)
                min_lat = self._tile_y_to_lat(max_tile_y + 1, zoom)

                bounds = (min_lat, max_lat, min_lon, max_lon)

                # Update UI on main thread - pass both display version and clean version
                self.root.after(0, lambda: self._display_preview(
                    mosaic,
                    mosaic_clean,
                    item_id,
                    index,
                    bounds,
                    zoom,
                    display_grid_size,
                    (center_lat, center_lon)
                ))
            else:
                self.root.after(0, lambda: self._preview_error("Could not load tiles"))
                
        except Exception as e:
            self.root.after(0, lambda: self._preview_error(str(e)))
            
    def _display_preview(self, image, image_clean, item_id, index, bounds, zoom, display_grid_size, center):
        """Display the loaded preview image"""
        
        # Store the clean image (without circle) for saving
        self.current_preview_image = image_clean.copy()
        self.current_preview_clean = image_clean.copy()
        self.current_preview_bounds = bounds

        if self.current_leaflet_file and os.path.exists(self.current_leaflet_file):
            try:
                os.remove(self.current_leaflet_file)
            except OSError:
                pass
            self.current_leaflet_file = None

        self.current_leaflet_html = self._build_leaflet_html(
            image_clean,
            bounds,
            center,
            zoom,
            display_grid_size,
            item_id
        )
        self.leaflet_btn.config(state='normal' if self.current_leaflet_html else 'disabled')
        if self.current_leaflet_html:
            self._render_leaflet_map()
        else:
            self._clear_leaflet_map()
        
        # Update info label
        self.preview_info_label.config(
            text=f"Preview {index + 1} of {len(self.results)}: {item_id}"
        )
        
    def _preview_error(self, error_msg):
        """Handle preview loading error"""
        self.preview_info_label.config(text=f"Error loading preview: {error_msg}")
        self.leaflet_btn.config(state='disabled')
        self.current_leaflet_html = None
        self.current_preview_bounds = None
        self._clear_leaflet_map()
        
    @staticmethod
    def _tile_x_to_lon(x, zoom):
        return x / (2 ** zoom) * 360.0 - 180.0

    @staticmethod
    def _tile_y_to_lat(y, zoom):
        n = math.pi - (2.0 * math.pi * y) / (2 ** zoom)
        return math.degrees(math.atan(math.sinh(n)))

    def _build_leaflet_html(self, image_clean, bounds, center, zoom, display_grid_size, item_id):
        """Create an interactive Leaflet HTML document for the current preview."""
        if not bounds or not center:
            return None

        try:
            # Store values for later use
            self._last_zoom = zoom
            self._last_grid_size = display_grid_size
            self._last_item_id = item_id
            
            buffer = BytesIO()
            image_clean.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            min_lat, max_lat, min_lon, max_lon = bounds
            center_lat, center_lon = center
            overlay_opacity = 0.88
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            grid_label = f"{display_grid_size}x{display_grid_size} tiles"
            mode_label = 'Full Scene' if self.preview_mode == 'full' else 'AOI'

            html_template = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>Planet Preview - {item_id}</title>
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" crossorigin=\"\" />
    <style>
        html, body {{ height: 100%; margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100%; background: #f0f0f0; }}
        .leaflet-container {{ font: 14px/1.4 'Helvetica Neue', Arial, Helvetica, sans-serif; }}
        .leaflet-tile-container {{ z-index: 1 !important; }}
        .leaflet-overlay-pane {{ z-index: 400 !important; }}
    </style>
</head>
<body>
    <div id=\"map\"></div>
    <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" crossorigin=\"\"></script>
    <script>
        var map = L.map('map');
        var imageBounds = [[{min_lat}, {min_lon}], [{max_lat}, {max_lon}]];
        
        // Fit bounds with appropriate zoom based on tile zoom level
        // Add padding to show context around the preview
        map.fitBounds(imageBounds, {{
            padding: [20, 20],
            maxZoom: {zoom}
        }});

        // Add OpenStreetMap basemap
        var osmLayer = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }}).addTo(map);

        // Add satellite image overlay
        var overlay = L.imageOverlay('data:image/png;base64,{image_base64}', imageBounds, {{
            opacity: {overlay_opacity}
        }}).addTo(map);

        L.rectangle(imageBounds, {{color: '#FF5722', weight: 2, fill: false}}).addTo(map);
        L.circle([{center_lat}, {center_lon}], {{radius: 25, weight: 2, color: '#FFFFFF', fillColor: '#FF0000', fillOpacity: 0.6}}).addTo(map);
        L.marker([{center_lat}, {center_lon}]).addTo(map).bindPopup(`
            <strong>Item ID:</strong> {item_id}<br/>
            <strong>Preview:</strong> {mode_label}<br/>
            <strong>Tile Grid:</strong> {grid_label}<br/>
            <strong>Leaflet Zoom:</strong> {zoom}<br/>
            <strong>Generated:</strong> {timestamp}
        `);

        L.control.scale().addTo(map);
        
        // Variable to store current AOI marker
        var currentAOIMarker = null;
        
        // Add click handler for AOI selection
        map.on('click', function(e) {{
            var clickedLat = e.latlng.lat;
            var clickedLng = e.latlng.lng;
            
            // Send coordinates back to Python by setting document title
            document.title = 'AOI_CLICK:' + clickedLat + ',' + clickedLng;
            
            // Remove previous marker if it exists
            if (currentAOIMarker) {{
                map.removeLayer(currentAOIMarker);
            }}
            
            // Add new marker
            currentAOIMarker = L.marker([clickedLat, clickedLng], {{
                icon: L.icon({{
                    iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNSIgaGVpZ2h0PSI0MSI+PHBhdGggZmlsbD0iI0ZGOTgwMCIgZD0iTTEyLjUgMEMxOS40IDAgMjUgNS42IDI1IDEyLjVjMCA2LjktMTIuNSAyOC41LTEyLjUgMjguNVMwIDE5LjQgMCAxMi41QzAgNS42IDUuNiAwIDEyLjUgMHoiLz48Y2lyY2xlIGZpbGw9IiNmZmYiIGN4PSIxMi41IiBjeT0iMTIuNSIgcj0iNSIvPjwvc3ZnPg==',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41]
                }})
            }}).addTo(map);
            
            currentAOIMarker.bindPopup('<strong>New AOI Center</strong><br/>Lat: ' + clickedLat.toFixed(6) + '<br/>Lng: ' + clickedLng.toFixed(6)).openPopup();
        }});
    </script>
</body>
</html>
"""

            return html_template
        except Exception:
            return None

    def _initialize_cef(self):
        """Initialize CEF browser framework."""
        if not CEF_AVAILABLE or self.cef_initialized:
            return
        
        try:
            sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
            settings = {
                "debug": False,
                "log_severity": cef.LOGSEVERITY_INFO,
                "log_file": "",
            }
            
            # Browser switches to allow loading external resources
            switches = {
                "disable-web-security": "",
                "allow-file-access-from-files": "",
                "allow-universal-access-from-files": "",
            }
            
            cef.Initialize(settings, switches)
            self.cef_initialized = True
            
            # Set up message loop timer
            self.root.after(10, self._cef_message_loop)
        except Exception as e:
            print(f"CEF initialization error: {e}")
            self.cef_initialized = False

    def _cef_message_loop(self):
        """Process CEF message loop."""
        if CEF_AVAILABLE and self.cef_initialized:
            cef.MessageLoopWork()
            self.root.after(10, self._cef_message_loop)

    def _render_leaflet_map(self):
        """Render the current Leaflet HTML in the embedded CEF browser."""
        if not self.current_leaflet_html:
            self._clear_leaflet_map()
            return
        
        # Use the generic HTML rendering method
        self._render_html_in_cef(self.current_leaflet_html)

    def _on_cef_configure(self, event):
        """Handle CEF frame resize."""
        if self.cef_browser:
            cef.WindowUtils.OnSize(
                self._get_window_handle(self.cef_frame),
                0, 0, 0
            )

    def _get_window_handle(self, widget):
        """Get native window handle for embedding CEF."""
        if os.name == 'nt':  # Windows
            return widget.winfo_id()
        else:  # Linux
            return widget.winfo_id()

    def _clear_leaflet_map(self):
        """Reset the embedded map view to placeholder."""
        if self.cef_browser:
            placeholder_html = """
                <html><body style='font-family: Arial; text-align: center; padding: 30px; background: white;'>
                    <h3>Interactive Map</h3>
                    <p>Load a preview to view the interactive map.</p>
                </body></html>
            """
            try:
                self.cef_browser.LoadUrl("data:text/html," + placeholder_html)
            except:
                pass

    def open_leaflet_map(self):
        """Open the current preview in the system browser using an interactive Leaflet map."""
        if not self.current_leaflet_html:
            messagebox.showinfo("Leaflet Preview", "No preview available. Please load an image first.")
            return

        try:
            # Clean up previous temp file if present
            if self.current_leaflet_file and os.path.exists(self.current_leaflet_file):
                try:
                    os.remove(self.current_leaflet_file)
                except OSError:
                    pass

            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', prefix='planet_leaflet_') as tmp:
                tmp.write(self.current_leaflet_html)
                self.current_leaflet_file = tmp.name

            webbrowser.open(f"file://{self.current_leaflet_file}")
        except Exception as e:
            messagebox.showerror("Leaflet Preview Error", f"Unable to open Leaflet preview:\n\n{str(e)}")

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
            # Always use zoom 17 for consistent tile resolution
            zoom = 17
            if self.preview_mode == 'full':
                grid_size = 15
            else:
                # Get grid size from the dropdown
                grid_str = self.grid_size_var.get()
                grid_size = int(grid_str.split('x')[0])
            
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
    
    def _refresh_results_display(self):
        """Refresh the results table to show updated tide heights"""
        # Get current scroll position
        current_selection = self.results_tree.selection()
        
        # Update all items
        for item_widget in self.results_tree.get_children():
            item_data = self.results_tree.item(item_widget)
            item_id = item_data['values'][0]
            
            # Get tide height if available
            tide_height = self.get_tide_height_for_item(item_id)
            tide_display = f"{tide_height:.2f}" if tide_height is not None else "N/A"
            
            # Update tide height column
            values = list(item_data['values'])
            values[5] = tide_display  # Tide Height is 6th column (index 5)
            
            self.results_tree.item(item_widget, values=values)
        
        # Restore selection
        if current_selection:
            self.results_tree.selection_set(current_selection)
    
    def export_to_csv(self):
        """Export search results to CSV"""
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
                        props.get('view_angle', ''),
                        props.get('sun_elevation', ''),
                        props.get('sun_azimuth', '')
                    ])
            
            messagebox.showinfo(
                "Export Successful",
                f"Exported {len(self.results)} records to:\n{filename}"
            )
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV:\n\n{str(e)}")
    
    def load_tide_data(self):
        """Load tide data from supported file formats."""
        filename = filedialog.askopenfilename(
            title="Select Tide Data File",
            filetypes=[
                ("Tide data files", "*.csv *.txt"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ],
            initialdir="."
        )
        
        if not filename:
            return  # User cancelled
        
        try:
            self.tide_data = {}
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.txt':
                line_count, tz_info = self._load_tide_from_equispaced_txt(filename)
            else:
                line_count, tz_info = self._load_tide_from_csv(filename)
            
            if line_count == 0:
                raise ValueError("No tide records were detected in the selected file.")
            
            self.tide_file_loaded = filename
            
            # Enable sort button
            self.sort_tide_btn.config(state='normal')
            
            # Refresh display to show tide heights
            if self.results:
                self._refresh_results_display()
            
            messagebox.showinfo(
                "Tide Data Loaded",
                f"Successfully loaded {line_count} tide records from:\n{os.path.basename(filename)}\n\n"
                f"{tz_info}\n\n"
                f"Tide data loaded! You can now:\n"
                f"  • View tide heights in the results table\n"
                f"  • Sort by lowest tide using the sort button\n"
                f"  • Export results with tide heights to CSV"
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("Load Error", f"Failed to load tide data:\n\n{str(e)}\n\nDetails:\n{error_details}")

    def _load_tide_from_csv(self, filename):
        """Parse tide data from CSV formats used previously by the app."""
        import pytz

        line_count = 0
        tz_info = "Parsed tide timestamps"

        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames or []

            def match_field(options):
                for option in options:
                    for original in fieldnames:
                        if not original:
                            continue
                        normalized = original.strip().lstrip('\ufeff').lower()
                        if normalized == option:
                            return original
                return None

            datetime_key = match_field(['datetime'])
            height_key = match_field(['height'])
            tide_height_key = match_field(['tide_height'])

            if datetime_key and height_key:
                branch = 'aest'
                tz_info = "Converted from AEST to UTC timezone"
                aest = pytz.timezone('Australia/Brisbane')
            elif datetime_key and tide_height_key:
                branch = 'utc'
                tz_info = "Parsed native UTC tide timestamps"
            else:
                raise ValueError("Unrecognized CSV format. Expected columns similar to 'DateTime' & 'Height' or 'datetime' & 'tide_height'.")

            for row in reader:
                try:
                    dt_str = (row.get(datetime_key) or '').strip()
                    if not dt_str:
                        continue

                    if branch == 'aest':
                        dt_naive = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                        dt_aest = aest.localize(dt_naive)
                        dt_utc = dt_aest.astimezone(pytz.UTC)
                        tide_height = float(row[height_key])
                    else:
                        dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                        tide_height = float(row[tide_height_key])

                    dt_rounded = dt_utc.replace(second=0, microsecond=0)
                    dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)

                    self.tide_data[dt_rounded] = tide_height
                    line_count += 1

                except Exception as row_error:
                    print(f"Skipping row due to error: {row_error}")
                    continue

        return line_count, tz_info

    def _load_tide_from_equispaced_txt(self, filename):
        """Parse 10-minute equispaced tide predictions from text files."""
        line_count = 0
        header_found = False

        with open(filename, 'r', encoding='utf-8') as txtfile:
            for raw_line in txtfile:
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
                except Exception:
                    continue

                dt_rounded = dt_utc.replace(second=0, microsecond=0)
                dt_rounded = dt_rounded.replace(minute=(dt_rounded.minute // 10) * 10)

                self.tide_data[dt_rounded] = tide_height
                line_count += 1

        if not header_found:
            raise ValueError("Could not locate the 'Date Time Height' header in the text file.")

        return line_count, "Assumed ZULU (UTC) tide timestamps"
    
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


class DisplayHandler:
    """CEF Display Handler to monitor title changes for AOI selection."""
    
    def __init__(self, app):
        self.app = app
    
    def OnTitleChange(self, browser, title):
        """Called when the page title changes."""
        if title and title.startswith('AOI_CLICK:'):
            # Extract coordinates from title
            try:
                coords_str = title.replace('AOI_CLICK:', '')
                lat_str, lon_str = coords_str.split(',')
                lat = float(lat_str)
                lon = float(lon_str)
                
                # Update AOI in the main thread
                self.app.root.after(0, lambda: self.app.update_aoi_from_map(lat, lon))
            except Exception as e:
                print(f"Error parsing AOI coordinates from title: {e}")


def main():
    root = tk.Tk()
    app = PlanetImageryBrowser(root)
    
    def on_closing():
        """Clean up before closing."""
        # Clean up temp HTML file
        if hasattr(app, '_temp_html_file'):
            try:
                import os
                app._temp_html_file.close()
                if os.path.exists(app._temp_html_file.name):
                    os.unlink(app._temp_html_file.name)
            except:
                pass
        
        # Shutdown CEF
        if CEF_AVAILABLE and app.cef_initialized:
            cef.Shutdown()
        
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
