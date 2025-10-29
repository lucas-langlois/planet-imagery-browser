# Planet Imagery Browser

A graphical user interface (GUI) application for searching, previewing, and downloading Planet satellite imagery with interactive filters and exposure status tracking.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🔍 **Interactive Search**: Filter satellite imagery by date range, cloud cover, coverage, and area of interest
- 🗺️ **Flexible AOI Selection**: Define search area using center coordinates with multiple grid size options (1x1 to 9x9 tiles)
- 🖼️ **High-Resolution Preview**: View AOI-specific or full scene previews with tile-based rendering
- 🌊 **Tide Integration**: Load tide data and sort imagery by lowest tide height
- ☀️ **Exposure Tracking**: Mark and track imagery exposure status with color-coded visualization
- 💾 **Smart Downloads**: Download full scenes or clip to AOI with georeferencing support
- 📊 **CSV Export**: Export search results with metadata, tide heights, and exposure status

## Prerequisites

- Python 3.8 or higher
- Planet API account and API key
- Conda (recommended for environment management)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/planet-imagery-browser.git
   cd planet-imagery-browser
   ```

2. **Create and activate conda environment**
   ```bash
   conda create -n planet-browser python=3.9
   conda activate planet-browser
   ```

3. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```

4. **Optional: Install GDAL for GeoTIFF export**
   ```bash
   conda install -c conda-forge gdal
   ```

5. **Set up your Planet API key**
   
   ⚠️ **IMPORTANT**: Never commit your API key to version control!
   
   Edit `planet_imagery_browser.py` and replace the placeholder API key on line 30:
   ```python
   self.api_key = "YOUR_PLANET_API_KEY_HERE"
   ```
   
   Or better yet, use environment variables:
   ```python
   import os
   self.api_key = os.getenv('PLANET_API_KEY')
   ```

## Usage

### Starting the Application

```bash
python planet_imagery_browser.py
```

### Basic Workflow

1. **Define Area of Interest (AOI)**
   - Enter center latitude and longitude coordinates
   - Select grid size (1x1 to 9x9 tiles, ~0.06 to ~5.30 km²)

2. **Set Search Filters**
   - Date range (start and end dates)
   - Maximum cloud cover percentage
   - Minimum visible coverage percentage
   - Item type (PlanetScope)

3. **Search for Imagery**
   - Click "🔍 Search" button
   - Browse results in the table view

4. **Preview Images**
   - Select any result to view high-resolution preview
   - Toggle between AOI view and full scene view
   - Navigate using Previous/Next buttons

5. **Mark Exposure Status** (Optional)
   - Mark individual images as "Exposed" or "Not Exposed"
   - Use bulk actions for multiple selections
   - Color-coded visualization (red for exposed, green for not exposed)

6. **Load Tide Data** (Optional)
   - Click "🌊 Load Tide Data" to import tide CSV
   - View tide heights in the results table
   - Sort by lowest tide height

7. **Download or Export**
   - Download full scene or clipped imagery
   - Export results to CSV with all metadata

## Tide Data Format

The application supports two tide data CSV formats:

### Format 1: AEST Timezone (Australian Format)
```csv
Date,Time,Height,DateTime,port_id
01/01/2025,00:00,1.08,01/01/2025 00:00,58940
01/01/2025,00:10,1.02,01/01/2025 00:10,58940
...
```

- `DateTime`: DD/MM/YYYY HH:MM format
- `Height`: Tide height in meters
- Timezone: AEST/AEDT (automatically converted to UTC)

### Format 2: ISO Format (UTC)
```csv
datetime,tide_height
2024-06-01T00:00:00Z,1.23
2024-06-01T00:10:00Z,1.25
...
```

- `datetime`: ISO format with timezone (UTC)
- `tide_height`: Tide height in meters

The application automatically detects which format you're using and handles timezone conversions appropriately.

## Download Options

- **Clip to AOI**: Downloads only the selected area (faster, smaller files)
- **Full Scene**: Downloads the entire satellite scene

Downloaded images can be saved as:
- **GeoTIFF** (.tif): Georeferenced with EPSG:4326 (requires GDAL)
- **PNG** (.png): Standard image format
- **JPEG** (.jpg): Compressed image format

## File Structure

```
planet-imagery-browser/
├── planet_imagery_browser.py    # Main application
├── requirements.txt              # Python dependencies
├── README.md                     # This file
├── .gitignore                    # Git ignore rules
├── downloads/                    # Downloaded imagery (created automatically)
└── data/                         # Optional tide data location
```

## API Reference

The application uses the [Planet SDK for Python](https://github.com/planetlabs/planet-client-python) to interact with Planet's Data API and Orders API.

Key API features used:
- Data API search with filters
- Tile server for preview imagery
- Orders API for downloading products
- Clip tool for AOI extraction

## Troubleshooting

### Common Issues

1. **"Module not found" error**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Activate your conda environment: `conda activate planet-browser`

2. **"Authentication failed" error**
   - Verify your Planet API key is correct
   - Check that your Planet account has active permissions

3. **Preview not loading**
   - Check internet connection
   - Verify the selected item has available tiles
   - Try reducing grid size

4. **GeoTIFF export not working**
   - Install GDAL: `conda install -c conda-forge gdal`
   - Or save as PNG/JPEG instead

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Planet SDK for Python](https://github.com/planetlabs/planet-client-python)
- Uses Tkinter for the GUI interface
- PIL/Pillow for image processing

## Contact

For questions or issues, please open an issue on GitHub.

## Related Projects

- [Planet Labs API Documentation](https://developers.planet.com/docs/data/)
- [GDAL - Geospatial Data Abstraction Library](https://gdal.org/)

---

**Note**: This tool requires an active Planet account and API key. Visit [Planet.com](https://www.planet.com/) to sign up.

