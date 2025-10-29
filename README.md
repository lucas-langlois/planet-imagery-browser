# Planet Imagery Browser

A graphical user interface (GUI) application for searching, previewing, and downloading Planet satellite imagery with interactive filters and exposure status tracking.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Streamlit](https://img.shields.io/badge/streamlit-ready-FF4B4B)

## 🌐 Two Versions Available

This application comes in **two versions**:

### 1️⃣ **Desktop Version** (Tkinter)
- Traditional desktop GUI application
- Runs locally on your computer
- Full offline capability
- File: `planet_imagery_browser.py`

### 2️⃣ **Web Version** (Streamlit) ⭐ NEW!
- Modern web-based interface
- Deploy for FREE on Streamlit Cloud
- Access from anywhere via browser
- Share with colleagues via URL
- File: `planet_imagery_browser_streamlit.py`
- **[📖 See Deployment Guide →](DEPLOYMENT.md)**

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
- Planet API account and API key ([Sign up here](https://www.planet.com/))
- Conda (recommended for environment management)

## Installation

### Step 0: Install Conda (If You Don't Have It)

**What is Conda?**  
Conda is a package and environment manager that helps you install Python packages and manage different Python versions without conflicts. It's especially useful for scientific computing and geospatial projects.

**Choose One:**

#### Option A: Miniconda (Recommended - Lightweight, ~400 MB)
1. Download Miniconda:
   - **Windows**: https://docs.conda.io/en/latest/miniconda.html
   - **Mac**: https://docs.conda.io/en/latest/miniconda.html
   - **Linux**: https://docs.conda.io/en/latest/miniconda.html

2. Run the installer and follow the prompts
   - Windows: Double-click the `.exe` file
   - Mac/Linux: Run `bash Miniconda3-latest-*.sh` in terminal

3. **Restart your terminal** after installation

4. Verify conda is installed:
   ```bash
   conda --version
   ```
   You should see something like: `conda 23.x.x`

#### Option B: Anaconda (Full featured, ~3 GB)
Download from: https://www.anaconda.com/products/distribution

---

### Step 1: Clone the Repository

Open your terminal (or Anaconda Prompt on Windows) and run:

```bash
# Navigate to where you want to store the project
cd Documents  # or your preferred location

# Clone the repository
git clone https://github.com/lucas-langlois/planet-imagery-browser.git

# Enter the project directory
cd planet-imagery-browser
```

---

### Step 2: Create a Conda Environment

**What is a conda environment?**  
An isolated space where you can install packages without affecting other projects or your system Python.

```bash
# Create a new environment named 'planet-browser' with Python 3.9
conda create -n planet-browser python=3.9

# You'll see a list of packages to install - type 'y' and press Enter
```

**What this does:**
- `-n planet-browser` → Names your environment "planet-browser"
- `python=3.9` → Installs Python 3.9 in this environment

---

### Step 3: Activate the Environment

**Every time** you want to use this application, you need to activate the environment first:

```bash
conda activate planet-browser
```

**You'll see your prompt change to:**
```
(planet-browser) C:\Users\YourName>  # Windows
(planet-browser) user@computer:~$    # Mac/Linux
```

The `(planet-browser)` prefix means the environment is active! ✅

---

### Step 4: Install Required Packages

With the environment activated, install the Python packages:

```bash
pip install -r requirements.txt
```

**What this installs:**
- `planet` → Planet Labs SDK for API access
- `Pillow` → Image processing library
- `requests` → HTTP library for downloading
- `pytz` → Timezone handling for AEST/UTC conversion

**This will take 1-2 minutes.** ⏱️

---

### Step 5: Optional - Install GDAL for GeoTIFF Export

If you want to save preview images as georeferenced GeoTIFFs:

```bash
conda install -c conda-forge gdal
```

**What is GDAL?**  
Geospatial Data Abstraction Library - allows saving images with geographic coordinates.

**Note:** This is optional. The app works fine without it (saves as regular PNG/JPEG).

---

### Step 6: Set Up Your Planet API Key

**Get your API key:**
1. Sign up at https://www.planet.com/
2. Go to Account Settings → API Keys
3. Copy your API key (starts with `PLAK...`)

**Set it as an environment variable (Recommended - Secure!):**

**Windows (PowerShell):**
```powershell
$env:PLANET_API_KEY="your_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set PLANET_API_KEY=your_api_key_here
```

**Mac/Linux:**
```bash
export PLANET_API_KEY="your_api_key_here"
```

**To set it permanently:**

**Windows:**
```powershell
# Open PowerShell as Administrator
[System.Environment]::SetEnvironmentVariable('PLANET_API_KEY', 'your_api_key_here', 'User')
```

**Mac/Linux:**
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
echo 'export PLANET_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

---

### Step 7: Run the Application! 🚀

```bash
# Make sure your conda environment is activated
conda activate planet-browser

# Run the application
python planet_imagery_browser.py
```

The GUI window should open! 🎉

---

## Conda Quick Reference

### Common Commands You'll Use:

```bash
# Activate environment (do this every time you open a new terminal)
conda activate planet-browser

# Deactivate environment (when you're done)
conda deactivate

# List all your environments
conda env list

# List packages installed in current environment
conda list

# Update a specific package
conda update package_name

# Install a new package
conda install package_name

# Remove the environment (if you want to start over)
conda env remove -n planet-browser
```

### Troubleshooting:

**Problem: `conda: command not found`**
- **Solution**: Restart your terminal after installing conda, or manually add conda to PATH

**Problem: `conda activate` doesn't work**
- **Windows**: Use "Anaconda Prompt" instead of regular Command Prompt
- **Mac/Linux**: Run `conda init bash` or `conda init zsh`, then restart terminal

**Problem: Environment activation doesn't show `(planet-browser)`**
- **Solution**: Run `conda init` and restart your terminal

**Problem: Packages won't install**
- **Solution**: Make sure environment is activated (`conda activate planet-browser`)
- Try: `conda clean --all` then reinstall

---

## Verifying Your Installation

After installation, verify everything works:

```bash
# 1. Check Python version
python --version
# Should show: Python 3.9.x

# 2. Check conda environment
conda env list
# Should show planet-browser with an asterisk (*)

# 3. Check installed packages
pip list
# Should show: planet, Pillow, requests, pytz

# 4. Test the application
python planet_imagery_browser.py
# GUI window should open
```

## Usage

### Option 1: Desktop Version (Tkinter)

```bash
# Make sure your conda environment is activated
conda activate planet-browser

# Run the desktop application
python planet_imagery_browser.py
```

The GUI window should open! 🎉

### Option 2: Web Version (Streamlit) 🌐

**Run Locally:**
```bash
# Make sure your conda environment is activated
conda activate planet-browser

# Run the web application
streamlit run planet_imagery_browser_streamlit.py
```

Your browser will automatically open to `http://localhost:8501` 🌐

**Deploy to the Web (FREE!):**

See the **[📖 Deployment Guide](DEPLOYMENT.md)** for step-by-step instructions to deploy on Streamlit Cloud for free!

---

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

