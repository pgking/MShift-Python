# Building and Releasing MShift

This document explains how to build MShift into an executable and create GitHub releases.

## 📋 Prerequisites

Before building, ensure you have:
- Python 3.13+ installed
- PyInstaller installed (`pip install pyinstaller`)
- All dependencies installed (`pip install -r requirements.txt` if you have one)

## 🧪 Pre-Build Testing

**ALWAYS run tests before building a release:**

```bash
python tests.py
```

Ensure all tests pass before proceeding. If any tests fail, fix them first!

## 🏗️ Building the Executable

### Step 1: Clean Previous Builds

```bash
# Remove old build artifacts
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

### Step 2: Build with PyInstaller

```bash
pyinstaller mshift.spec
```

This will:
- ✅ Build the executable in `dist/mshift/mshift.exe`
- ✅ Automatically exclude test files (`tests.py`)
- ✅ Exclude development dependencies
- ✅ Include all necessary runtime dependencies

### Step 3: Test the Executable

Before releasing, **test the built executable**:

```bash
cd dist\mshift
.\mshift.exe
```

Verify:
- Application launches correctly
- All features work as expected
- No import errors or missing dependencies

## 📦 Creating a GitHub Release

### Step 1: Prepare the Release Package

```bash
# Navigate to dist folder
cd dist

# Create a zip file (use 7-Zip, Windows Explorer, or PowerShell)
Compress-Archive -Path mshift -DestinationPath MShift-v<VERSION>.zip
```

Replace `<VERSION>` with your version number (e.g., `1.2.0`).

### Step 2: Create GitHub Release

1. Go to your GitHub repository
2. Click "Releases" → "Create a new release"
3. **Tag version:** `v<VERSION>` (e.g., `v1.2.0`)
4. **Release title:** `MShift v<VERSION>`
5. **Description:** Add release notes (see template below)
6. **Attach files:** Upload `MShift-v<VERSION>.zip`
7. Click "Publish release"

### Release Notes Template

```markdown
## MShift v<VERSION>

### ✨ New Features
- Feature 1 description
- Feature 2 description

### 🐛 Bug Fixes
- Fix 1 description
- Fix 2 description

### 🔧 Improvements
- Improvement 1 description
- Improvement 2 description

### 📝 Notes
- Any important notes for users
- Migration instructions if needed

**Download:** MShift-v<VERSION>.zip
```

## 🔒 What Gets Excluded

The build process automatically excludes:

### Development Files:
- `tests.py` - Test suite
- `test_output.txt` - Test results
- `*.spec` files (via .gitignore)
- `build/` directory
- `dist/` directory

### Test Modules:
- `unittest` module
- `pytest` module
- Any `test` imports

### Protected by .gitignore:
- `/Test` folder - Your test data
- `/build` - Build artifacts
- `/dist` - Distribution files
- `*.spec` - PyInstaller specs

## ✅ Pre-Release Checklist

Before publishing a release:

- [ ] Run `python tests.py` - all tests pass
- [ ] Update version number in `main.py` (if applicable)
- [ ] Update CHANGELOG or release notes
- [ ] Clean build: `Remove-Item -Recurse -Force build, dist`
- [ ] Build: `pyinstaller mshift.spec`
- [ ] Test executable: `dist\mshift\mshift.exe`
- [ ] Verify UI works correctly
- [ ] Test file save/load
- [ ] Test schema management
- [ ] Create zip file
- [ ] Upload to GitHub releases
- [ ] Tag release with version number

## 🚀 Automated Build Script (Optional)

Create `build.ps1` for automated builds:

```powershell
# Build script for MShift

Write-Host "Running tests..." -ForegroundColor Cyan
python tests.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed! Fix errors before building." -ForegroundColor Red
    exit 1
}

Write-Host "Tests passed! Cleaning old builds..." -ForegroundColor Green
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Building executable..." -ForegroundColor Cyan
pyinstaller mshift.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful! Executable: dist\mshift\mshift.exe" -ForegroundColor Green
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
```

Run with: `.\build.ps1`

## 📚 Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [GitHub Releases Guide](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

## 🆘 Troubleshooting

### "Module not found" errors
- Ensure all imports are in `hiddenimports` in `mshift.spec`
- Check that PyQt5 is properly installed

### Executable won't run
- Test with `--debug` flag: `pyinstaller --debug all mshift.spec`
- Check `dist/mshift/` for error logs

### Large file size
- Consider using UPX compression (already enabled)
- Remove unnecessary dependencies

---

**Remember:** Never commit `dist/` or `build/` folders to git - they're already in `.gitignore`!
