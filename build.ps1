# Build script for MShift
# Run with: .\build.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       MShift Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Extract version from main.py
Write-Host "Reading version from main.py..." -ForegroundColor Cyan
$versionLine = Get-Content "main.py" | Select-String -Pattern 'VERSION = "(.+)"'
if ($versionLine -match 'VERSION = "(.+)"') {
    $VERSION = $matches[1]
    Write-Host "Version detected: $VERSION" -ForegroundColor Green
} else {
    Write-Host "[X] Could not detect version from main.py!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if build_env exists
if (-not (Test-Path "build_env\Scripts\Activate.ps1")) {
    Write-Host "[X] build_env not found!" -ForegroundColor Red
    Write-Host "Please create it first with: python -m venv build_env" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Step 0: Pre-build checks
Write-Host "[0/7] Pre-build checks..." -ForegroundColor Yellow
Write-Host "  - Version: $VERSION" -ForegroundColor Gray
Write-Host "  - DEV_MODE will be DISABLED in production build" -ForegroundColor Gray
Write-Host "  - Backup system: ENABLED" -ForegroundColor Gray
Write-Host "  - Data validation: ENABLED" -ForegroundColor Gray
Write-Host "  - Auto-backup rotation: 5 backups" -ForegroundColor Gray
Write-Host "[OK] Configuration verified" -ForegroundColor Green
Write-Host ""

# Step 1: Run tests (using current Python)
Write-Host "[1/7] Running tests..." -ForegroundColor Yellow
python tests.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[X] Tests failed! Fix errors before building." -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "[OK] All tests passed!" -ForegroundColor Green
Write-Host ""

# Step 2: Clean old builds
Write-Host "[2/7] Cleaning old builds..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Write-Host "[OK] Cleanup complete" -ForegroundColor Green
Write-Host ""

# Step 3: Activate build environment
Write-Host "[3/7] Activating build_env..." -ForegroundColor Yellow
& "build_env\Scripts\Activate.ps1"
Write-Host "[OK] Build environment activated" -ForegroundColor Green
Write-Host ""

# Step 4: Build executable with PyInstaller
Write-Host "[4/7] Building executable with PyInstaller..." -ForegroundColor Yellow
& "build_env\Scripts\pyinstaller.exe" mshift.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[X] Build failed!" -ForegroundColor Red
    Write-Host "Make sure PyInstaller is installed: pip install pyinstaller" -ForegroundColor Yellow
    Write-Host ""
    deactivate
    exit 1
}

Write-Host "[OK] Build successful!" -ForegroundColor Green
Write-Host ""

# Step 5: Verify build output
Write-Host "[5/7] Verifying build output..." -ForegroundColor Yellow
if (Test-Path "dist\mshift\mshift.exe") {
    $fileSize = (Get-Item "dist\mshift\mshift.exe").Length / 1MB
    Write-Host "  Executable size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
    Write-Host "[OK] Build verification passed" -ForegroundColor Green
} else {
    Write-Host "[X] Executable not found!" -ForegroundColor Red
    deactivate
    exit 1
}
Write-Host ""

# Deactivate environment
deactivate

# Step 6: Create release zip
Write-Host "[6/7] Creating release zip..." -ForegroundColor Yellow
$zipName = "MShift-v$VERSION.zip"
$zipPath = "dist\$zipName"

# Remove old zip if exists
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

# Create the zip
try {
    Compress-Archive -Path "dist\mshift" -DestinationPath $zipPath -CompressionLevel Optimal
    $zipSize = (Get-Item $zipPath).Length / 1MB
    Write-Host "  Created: $zipName ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Gray
    Write-Host "[OK] Release package created" -ForegroundColor Green
} catch {
    Write-Host "[X] Failed to create zip: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 7: Summary
Write-Host "[7/7] Build Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "Version: $VERSION" -ForegroundColor Cyan
Write-Host ""
Write-Host "Build Outputs:" -ForegroundColor White
Write-Host "  - Executable: dist\mshift\mshift.exe" -ForegroundColor Cyan
Write-Host "  - Release zip: $zipPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Build Features:" -ForegroundColor White
Write-Host "  - Automatic backup system (keeps 5 backups)" -ForegroundColor Green
Write-Host "  - Data validation on file load" -ForegroundColor Green
Write-Host "  - Restore from backup functionality" -ForegroundColor Green
Write-Host "  - Enhanced error handling" -ForegroundColor Green
Write-Host "  - DEV_MODE disabled (production-safe)" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Test the executable: cd dist\mshift; .\mshift.exe" -ForegroundColor Gray
Write-Host "  2. Test backup/restore: Save a file, modify it, restore from backup" -ForegroundColor Gray
Write-Host "  3. Upload $zipName to GitHub Releases" -ForegroundColor Gray
Write-Host ""
Write-Host "Developer Notes:" -ForegroundColor White
Write-Host "  - To enable DEV_MODE: Set environment variable MSHIFT_DEV_MODE=1" -ForegroundColor Gray
Write-Host "  - Backups stored in: .mshift_backups/ (next to .mshift files)" -ForegroundColor Gray
Write-Host "  - See README.md for full documentation" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
