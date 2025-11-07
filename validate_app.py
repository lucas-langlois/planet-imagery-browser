#!/usr/bin/env python3
"""
Quick validation script for Planet Imagery Browser
Tests basic functionality without requiring API key
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    errors = []
    
    try:
        import tkinter
        print("  ✓ tkinter")
    except ImportError as e:
        errors.append(f"  ✗ tkinter: {e}")
    
    try:
        from PIL import Image
        print("  ✓ Pillow")
    except ImportError as e:
        errors.append(f"  ✗ Pillow: {e}")
    
    try:
        import requests
        print("  ✓ requests")
    except ImportError as e:
        errors.append(f"  ✗ requests: {e}")
    
    try:
        from planet import Planet
        print("  ✓ planet")
    except ImportError as e:
        errors.append(f"  ✗ planet: {e}")
    
    try:
        import streamlit
        print("  ✓ streamlit")
    except ImportError as e:
        errors.append(f"  ✗ streamlit: {e}")
    
    try:
        import pandas
        print("  ✓ pandas")
    except ImportError as e:
        errors.append(f"  ✗ pandas: {e}")
    
    if errors:
        print("\nErrors found:")
        for error in errors:
            print(error)
        return False
    
    print("\n✓ All imports successful!")
    return True

def test_syntax():
    """Test that Python files have valid syntax"""
    print("\nTesting Python syntax...")
    
    files = [
        'planet_imagery_browser.py',
        'planet_imagery_browser_streamlit.py'
    ]
    
    import py_compile
    errors = []
    
    for filename in files:
        if os.path.exists(filename):
            try:
                py_compile.compile(filename, doraise=True)
                print(f"  ✓ {filename}")
            except py_compile.PyCompileError as e:
                errors.append(f"  ✗ {filename}: {e}")
        else:
            errors.append(f"  ✗ {filename}: File not found")
    
    if errors:
        print("\nSyntax errors found:")
        for error in errors:
            print(error)
        return False
    
    print("\n✓ All syntax checks passed!")
    return True

def test_aoi_calculation():
    """Test AOI calculation without API"""
    print("\nTesting AOI calculation...")
    
    try:
        # Import the function from streamlit version
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from planet_imagery_browser_streamlit import calculate_aoi
        
        # Test with Sydney coordinates
        result = calculate_aoi(-33.8688, 151.2093, 3)
        
        assert 'type' in result, "Result missing 'type' field"
        assert result['type'] == 'Polygon', f"Expected Polygon, got {result['type']}"
        assert 'coordinates' in result, "Result missing 'coordinates' field"
        assert len(result['coordinates']) > 0, "Coordinates array is empty"
        
        print("  ✓ AOI calculation works correctly")
        print(f"    Center: -33.8688, 151.2093")
        print(f"    Grid size: 3x3")
        print(f"    Result type: {result['type']}")
        return True
        
    except Exception as e:
        print(f"  ✗ AOI calculation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=" * 60)
    print("Planet Imagery Browser - Validation Script")
    print("=" * 60)
    
    results = []
    
    results.append(("Import Test", test_imports()))
    results.append(("Syntax Test", test_syntax()))
    results.append(("AOI Calculation", test_aoi_calculation()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All validation tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
