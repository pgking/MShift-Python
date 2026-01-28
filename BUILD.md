# Building and Releasing MShift

This document explains how to build MShift into an executable and create GitHub releases.

## 📋 Prerequisites

Before building, ensure you have:
- Python 3.13+ installed
- PyInstaller installed (`pip install pyinstaller`)
- All dependencies installed (`pip install -r requirements.txt` if you have one)
- A virtual environment for building: `python -m venv build_env`

## 🧪 Pre-Build Testing

**ALWAYS run tests before building a release:**

```bash
python tests.py
```

Ensure all tests pass before proceeding. If any tests fail, fix them first!

## 🏗️ Building the Executable

### Option 1: Automated Build Script (Recommended)

Use the provided build script for a streamlined build process:

```powershell
.\build.ps1
```

This script will:
1. ✅ Verify pre-build configuration
2. ✅ Run all tests
3. ✅ Clean old builds
4. ✅ Activate build environment
5. ✅ Build with PyInstaller
6. ✅ Verify build output
7. ✅ Display summary with next steps

### Option 2: Manual Build

#### Step 1: Clean Previous Builds

```bash
# Remove old build artifacts
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

#### Step 2: Build with PyInstaller

```bash
pyinstaller mshift.spec
```

This will:
- ✅ Build the executable in `dist/mshift/mshift.exe`
- ✅ Automatically exclude test files (`tests.py`)
- ✅ Exclude development dependencies
- ✅ Include all necessary runtime dependencies

#### Step 3: Test the Executable

Before releasing, **test the built executable**:

```bash
cd dist\mshift
.\mshift.exe
```

Verify:
- Application launches correctly
- All features work as expected
- No import errors or missing dependencies
- **DEV_MODE is disabled** (no sample data loads automatically)
- Backup system works (save a file, check for `.mshift_backups/` folder)
- Restore from backup works

## 🔧 Production Build Configuration

### DEV_MODE Behavior

**Important:** DEV_MODE is controlled by environment variable and defaults to **disabled** in production builds.

- **Production (default):** DEV_MODE is OFF - no sample data loads
- **Development:** Set `$env:MSHIFT_DEV_MODE="1"` to enable sample data

**To verify DEV_MODE is disabled:**
1. Run the built executable
2. It should start with a clean slate (no sample people/services)
3. If sample data appears, DEV_MODE is incorrectly enabled

### New Features in v1.0.5

The production build includes:
- ✅ **Automatic Backup System**: Creates timestamped backups on every save
- ✅ **Backup Rotation**: Keeps 5 most recent backups automatically
- ✅ **Data Validation**: Validates all loaded files to prevent corruption
- ✅ **Restore from Backup**: UI dialog to restore from previous backups
- ✅ **Enhanced Error Handling**: User-friendly error messages
- ✅ **Production-Safe Configuration**: DEV_MODE disabled by default

## 📦 Creating a GitHub Release

### Step 1: Prepare the Release Package

```bash
# Navigate to dist folder
cd dist

# Create a zip file (use 7-Zip, Windows Explorer, or PowerShell)
Compress-Archive -Path mshift -DestinationPath MShift-v<VERSION>.zip
```

Replace `<VERSION>` with your version number (e.g., `1.0.5`).

### Step 2: Create GitHub Release

1. Go to your GitHub repository
2. Click "Releases" → "Create a new release"
3. **Tag version:** `v<VERSION>` (e.g., `v1.0.5`)
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

### Example Release Notes for v1.0.5

```markdown
## MShift v1.0.5

### ✨ New Features
- **Automatic Backup System**: Every save now creates a timestamped backup
- **Restore from Backup**: New menu option to restore from previous backups
- **Data Validation**: Files are validated on load to prevent corruption

### 🔧 Improvements
- Enhanced error handling with user-friendly error messages
- Backup rotation keeps 5 most recent backups automatically
- Production-safe configuration (DEV_MODE disabled by default)
- Fixed file watcher race condition

### 📝 Notes
- Backups are stored in `.mshift_backups/` folder next to your files
- Access restore via **File → Restore from Backup...**
- See README.md for full documentation

**Download:** MShift-v1.0.5.zip
```

## 🔒 What Gets Excluded

The build process automatically excludes:

### Development Files:
- `tests.py` - Test suite
- `test_output.txt` - Test results
- `*.spec` files (via .gitignore)
- `build/` directory
- `dist/` directory
- `.mshift_backups/` - Backup directories

### Test Modules:
- `unittest` module
- `pytest` module
- Any `test` imports

### Protected by .gitignore:
- `/Test` folder - Your test data
- `/build` - Build artifacts
- `/dist` - Distribution files
- `*.spec` - PyInstaller specs
- `.mshift_backups/` - Backup folders

## ✅ Pre-Release Checklist

Before publishing a release:

- [ ] Run `python tests.py` - all tests pass
- [ ] Update version number in `main.py` (VERSION constant)
- [ ] Update CHANGELOG or release notes
- [ ] Clean build: `Remove-Item -Recurse -Force build, dist`
- [ ] Build: `.\build.ps1` or `pyinstaller mshift.spec`
- [ ] Test executable: `dist\mshift\mshift.exe`
- [ ] Verify UI works correctly
- [ ] Test file save/load
- [ ] **Test backup creation** (save file, check `.mshift_backups/`)
- [ ] **Test restore from backup** (File → Restore from Backup)
- [ ] **Verify DEV_MODE is disabled** (no sample data on first run)
- [ ] Test schema management
- [ ] Create zip file
- [ ] Upload to GitHub releases
- [ ] Tag release with version number

## 🚀 Build Script Details

The `build.ps1` script provides:

### Pre-Build Checks
- Verifies DEV_MODE will be disabled
- Confirms backup system is enabled
- Shows data validation status

### Build Process
1. Runs all tests
2. Cleans old builds
3. Activates build environment
4. Builds with PyInstaller
5. Verifies executable exists and shows size

### Post-Build Summary
- Lists all new features included
- Provides testing instructions
- Shows developer notes for DEV_MODE

### Usage

```powershell
# Standard build
.\build.ps1

# If build_env doesn't exist, create it first:
python -m venv build_env
.\build_env\Scripts\Activate.ps1
pip install pyinstaller
deactivate

# Then run build
.\build.ps1
```

## 📚 Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [GitHub Releases Guide](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [README.md](README.md) - User documentation
- [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) - Recent improvements

## 🆘 Troubleshooting

### "Module not found" errors
- Ensure all imports are in `hiddenimports` in `mshift.spec`
- Check that PyQt5 is properly installed
- Verify `backup_manager.py` and `data_validator.py` are included

### Executable won't run
- Test with `--debug` flag: `pyinstaller --debug all mshift.spec`
- Check `dist/mshift/` for error logs

### Large file size
- Consider using UPX compression (already enabled)
- Remove unnecessary dependencies

### DEV_MODE enabled in production
- **Issue:** Sample data loads in built executable
- **Cause:** Environment variable set during build
- **Solution:** Ensure `MSHIFT_DEV_MODE` is not set when building
- **Verify:** Check build script output shows "DEV_MODE will be DISABLED"

### Backup system not working
- **Issue:** No `.mshift_backups/` folder created
- **Cause:** File hasn't been saved yet
- **Solution:** Save a file at least once to create backups

---

**Remember:** Never commit `dist/` or `build/` folders to git - they're already in `.gitignore`!

