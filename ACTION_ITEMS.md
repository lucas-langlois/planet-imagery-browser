# Planet Imagery Browser - Action Items Checklist

This checklist provides actionable items based on the comprehensive app review.

## 🔴 High Priority (Do First)

### Error Handling
- [ ] Replace bare `except:` with specific exception types
  - [ ] Line 594 in `planet_imagery_browser.py`
  - [ ] Line 853 in `planet_imagery_browser.py`
  - [ ] Add specific exception handling throughout

- [ ] Add structured logging
  ```python
  import logging
  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)
  ```

- [ ] Implement retry logic for API calls
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential
  
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
  def fetch_with_retry(url):
      response = requests.get(url)
      response.raise_for_status()
      return response
  ```

### Input Validation
- [ ] Add CSV file validation before processing
  ```python
  def validate_csv_headers(file):
      required_headers = ['Date', 'Time', 'Height']  # or ['datetime', 'tide_height']
      reader = csv.DictReader(file)
      headers = reader.fieldnames
      return all(h in headers for h in required_headers)
  ```

- [ ] Add coordinate bounds validation
  ```python
  def validate_coordinates(lat, lon):
      if not (-90 <= lat <= 90):
          raise ValueError(f"Invalid latitude: {lat}")
      if not (-180 <= lon <= 180):
          raise ValueError(f"Invalid longitude: {lon}")
  ```

### Code Constants
- [ ] Create constants file or section
  ```python
  # At the top of the file
  TILE_SIZE_PIXELS = 256
  METERS_PER_PIXEL_AT_EQUATOR = 156543.03
  DEFAULT_ZOOM_LEVEL = 17
  METERS_PER_DEG_LAT = 111320
  MAX_CLOUD_COVER = 100
  MIN_COVERAGE = 0
  ```

## 🟡 Medium Priority (Do Soon)

### Testing
- [ ] Create tests directory structure
  ```
  tests/
  ├── __init__.py
  ├── test_aoi_calculation.py
  ├── test_tide_parsing.py
  ├── test_search_filters.py
  └── test_preview_loading.py
  ```

- [ ] Add pytest to requirements
  ```
  # Add to requirements.txt
  pytest>=7.0.0
  pytest-cov>=4.0.0
  ```

- [ ] Write basic unit tests
  ```python
  # tests/test_aoi_calculation.py
  def test_calculate_aoi_valid_inputs():
      result = calculate_aoi(-33.8688, 151.2093, 3)
      assert result['type'] == 'Polygon'
      assert len(result['coordinates'][0]) == 5
  ```

### Code Refactoring
- [ ] Extract shared code to common module
  ```
  planet_browser/
  ├── __init__.py
  ├── core.py          # Shared logic
  ├── gui_tkinter.py   # Tkinter version
  └── gui_streamlit.py # Streamlit version
  ```

- [ ] Refactor long functions
  - [ ] `create_filter_panel()` → Break into smaller methods
  - [ ] `perform_search()` → Extract validation, API call, processing
  - [ ] `load_preview_tiles()` → Separate tile fetching from rendering

- [ ] Add type hints
  ```python
  from typing import Dict, List, Optional, Tuple
  
  def calculate_aoi(
      center_lat: float, 
      center_lon: float, 
      grid_size: int
  ) -> Dict[str, any]:
      ...
  ```

### Documentation
- [ ] Add docstrings to all public functions
  ```python
  def calculate_aoi(center_lat, center_lon, grid_size):
      """
      Calculate Area of Interest bounding box.
      
      Args:
          center_lat (float): Center latitude in decimal degrees
          center_lon (float): Center longitude in decimal degrees
          grid_size (int): Number of tiles per side (1-9)
          
      Returns:
          dict: GeoJSON polygon representing the AOI
          
      Raises:
          ValueError: If coordinates are invalid
      """
  ```

- [ ] Create CONTRIBUTING.md
- [ ] Create CHANGELOG.md

## 🟢 Low Priority (Nice to Have)

### Performance Improvements
- [ ] Implement async HTTP requests
  ```python
  import asyncio
  import aiohttp
  
  async def fetch_tiles_async(urls):
      async with aiohttp.ClientSession() as session:
          tasks = [fetch_one(session, url) for url in urls]
          return await asyncio.gather(*tasks)
  ```

- [ ] Add caching for API responses
  ```python
  from functools import lru_cache
  
  @lru_cache(maxsize=100)
  def get_cached_search_results(aoi_hash, start_date, end_date):
      ...
  ```

- [ ] Implement pagination for large result sets

### CI/CD
- [ ] Create GitHub Actions workflow
  ```yaml
  # .github/workflows/test.yml
  name: Tests
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v2
        - uses: actions/setup-python@v2
          with:
            python-version: '3.9'
        - run: pip install -r requirements.txt
        - run: pip install pytest pytest-cov
        - run: pytest --cov
  ```

### Additional Features
- [ ] Add request rate limiting
  ```python
  from ratelimit import limits, sleep_and_retry
  
  @sleep_and_retry
  @limits(calls=10, period=60)  # 10 calls per minute
  def api_call():
      ...
  ```

- [ ] Add download progress tracking
- [ ] Implement image caching for previews
- [ ] Add export to multiple formats (GeoJSON, KML)

## 🔧 Specific File Fixes

### planet_imagery_browser.py
- [ ] Line 594: Fix bare except
- [ ] Line 853: Add GDAL import error handling
- [ ] Lines 320-443: Add input validation in search function
- [ ] Lines 539-633: Improve error handling in tile loading

### planet_imagery_browser_streamlit.py
- [ ] Line 317: Don't modify os.environ, pass API key directly
- [ ] Lines 115-156: Add pagination to search results
- [ ] Lines 222-245: Add validation for tide data parsing
- [ ] Line 309: Reduce API key visibility (show less chars)

## 📊 Progress Tracking

Track your progress:
```
High Priority:   [ ] 0/10 complete
Medium Priority: [ ] 0/15 complete  
Low Priority:    [ ] 0/8 complete

Overall:         [ ] 0/33 complete (0%)
```

## 🎯 Quick Wins (Start Here!)

These are the easiest and most impactful changes:

1. ✅ Add constants for magic numbers (15 minutes)
2. ✅ Fix bare except clauses (30 minutes)
3. ✅ Add basic logging (20 minutes)
4. ✅ Add docstrings to main functions (1 hour)
5. ✅ Create requirements.lock (5 minutes)

**Total time for quick wins: ~2 hours**

---

**Next Steps:**
1. Choose one item from High Priority
2. Make the change
3. Test it
4. Commit
5. Check it off this list
6. Repeat!

**For detailed explanations, see [APP_REVIEW.md](./APP_REVIEW.md)**
