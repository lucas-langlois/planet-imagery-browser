# Planet API Key Setup Script for Windows PowerShell
# This script helps you set up your Planet API key as a permanent environment variable

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Planet API Key Setup Assistant" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   This script should be run as Administrator to set permanent environment variables.`n" -ForegroundColor Yellow
    Write-Host "   Right-click PowerShell and select 'Run as Administrator'`n" -ForegroundColor Yellow
    
    $continue = Read-Host "Do you want to continue anyway? (y/n)"
    if ($continue -ne 'y') {
        Write-Host "`nExiting. Please run as Administrator." -ForegroundColor Red
        exit
    }
}

# Check if API key is already set
$existingKey = [System.Environment]::GetEnvironmentVariable('PLANET_API_KEY', 'User')

if ($existingKey) {
    Write-Host "✅ API key is already set in your environment!" -ForegroundColor Green
    Write-Host "   Current value (first 10 chars): $($existingKey.Substring(0, [Math]::Min(10, $existingKey.Length)))...`n" -ForegroundColor Gray
    
    $replace = Read-Host "Do you want to replace it with a new key? (y/n)"
    if ($replace -ne 'y') {
        Write-Host "`nKeeping existing API key. Exiting." -ForegroundColor Green
        exit
    }
}

# Prompt for API key
Write-Host "`nPlease enter your Planet API key:" -ForegroundColor Cyan
Write-Host "(It starts with 'PLAK' and you can find it at https://www.planet.com/account/)" -ForegroundColor Gray
$apiKey = Read-Host "API Key"

# Validate input
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "`n❌ Error: API key cannot be empty!" -ForegroundColor Red
    exit
}

if (-not $apiKey.StartsWith("PLAK")) {
    Write-Host "`n⚠️  WARNING: API key doesn't start with 'PLAK'. Are you sure this is correct?" -ForegroundColor Yellow
    $confirm = Read-Host "Continue anyway? (y/n)"
    if ($confirm -ne 'y') {
        Write-Host "`nExiting. Please check your API key." -ForegroundColor Red
        exit
    }
}

# Set the environment variable
try {
    Write-Host "`nSetting environment variable..." -ForegroundColor Cyan
    [System.Environment]::SetEnvironmentVariable('PLANET_API_KEY', $apiKey, 'User')
    
    # Also set for current session
    $env:PLANET_API_KEY = $apiKey
    
    Write-Host "✅ Success! API key has been set." -ForegroundColor Green
    Write-Host "`nThe API key is now stored as a permanent user environment variable." -ForegroundColor Gray
    Write-Host "It will be available in all future PowerShell and application sessions.`n" -ForegroundColor Gray
    
    # Verify
    Write-Host "Verifying..." -ForegroundColor Cyan
    $verifyKey = [System.Environment]::GetEnvironmentVariable('PLANET_API_KEY', 'User')
    
    if ($verifyKey -eq $apiKey) {
        Write-Host "✅ Verification successful!" -ForegroundColor Green
        Write-Host "   Stored key (first 10 chars): $($verifyKey.Substring(0, [Math]::Min(10, $verifyKey.Length)))...`n" -ForegroundColor Gray
    } else {
        Write-Host "⚠️  Verification failed. The key might not have been set correctly." -ForegroundColor Yellow
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  Next Steps:" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "1. Close this PowerShell window" -ForegroundColor White
    Write-Host "2. Open a NEW PowerShell window" -ForegroundColor White
    Write-Host "3. Activate your conda environment: conda activate planet" -ForegroundColor White
    Write-Host "4. Run the application: python planet_imagery_browser.py`n" -ForegroundColor White
    
} catch {
    Write-Host "`n❌ Error setting environment variable:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nPlease make sure you're running as Administrator.`n" -ForegroundColor Yellow
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

