# Build script for MShift
# Run with: .\build.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       MShift Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if build_env exists
if (-not (Test-Path "build_env\Scripts\Activate.ps1")) {
    Write-Host "[X] build_env not found!" -ForegroundColor Red
    Write-Host "Please create it first with: python -m venv build_env" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Step 1: Run tests (using current Python)
Write-Host "[1/5] Running tests..." -ForegroundColor Yellow
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
Write-Host "[2/5] Cleaning old builds..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Write-Host "[OK] Cleanup complete" -ForegroundColor Green
Write-Host ""

# Step 3: Activate build environment
Write-Host "[3/5] Activating build_env..." -ForegroundColor Yellow
& "build_env\Scripts\Activate.ps1"
Write-Host "[OK] Build environment activated" -ForegroundColor Green
Write-Host ""

# Step 4: Build executable with PyInstaller
Write-Host "[4/5] Building executable with PyInstaller..." -ForegroundColor Yellow
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

# Deactivate environment
deactivate

# Step 5: Summary
Write-Host "[5/5] Build Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "Executable location: dist\mshift\mshift.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Test the executable: cd dist\mshift; .\mshift.exe" -ForegroundColor Gray
Write-Host "  2. Create zip: Compress-Archive -Path dist\mshift -DestinationPath MShift-vX.X.X.zip" -ForegroundColor Gray
Write-Host "  3. Upload to GitHub Releases" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
