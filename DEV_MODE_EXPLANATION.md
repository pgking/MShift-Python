# DEV_MODE Explanation

## What is DEV_MODE?

**DEV_MODE** is a configuration flag that controls whether MShift loads sample/test data when the application starts for the first time (when there's no saved app state).

## Behavior

### When DEV_MODE is **ENABLED** (Development)
- ✅ Sample people are created (e.g., "Alice", "Bob", "Charlie")
- ✅ Sample services are created (e.g., "Jour", "Nuit", "Planning Familial")
- ✅ Useful for testing and development
- ✅ Saves time when developing new features

### When DEV_MODE is **DISABLED** (Production - Default)
- ❌ No sample data is loaded
- ✅ Application starts with a clean slate
- ✅ User must add their own people and services
- ✅ **This is the correct behavior for end users**

## How It Works

### In Code (main.py, line 153)
```python
# Old (WRONG - hardcoded):
DEV_MODE = True  # ✅ Change to False for production

# New (CORRECT - environment variable):
DEV_MODE = os.getenv("MSHIFT_DEV_MODE", "").lower() in ("1", "true", "yes")
```

### Default Behavior
- **Without environment variable:** DEV_MODE = `False` (production-safe)
- **With environment variable set:** DEV_MODE = `True` (development mode)

## How to Enable DEV_MODE

### For Development/Testing

**Windows PowerShell:**
```powershell
$env:MSHIFT_DEV_MODE="1"
python main.py
```

**Windows CMD:**
```cmd
set MSHIFT_DEV_MODE=1
python main.py
```

**Linux/Mac:**
```bash
export MSHIFT_DEV_MODE=1
python main.py
```

### For Production Builds

**DO NOTHING!** The environment variable is not set by default, so DEV_MODE will be disabled.

## Verification

### To verify DEV_MODE is disabled in a build:

1. Run the executable: `.\dist\mshift\mshift.exe`
2. Check if sample data appears:
   - **If NO sample people/services appear:** ✅ DEV_MODE is correctly disabled
   - **If sample data appears:** ❌ DEV_MODE is incorrectly enabled

### Build Script Verification

The `build.ps1` script shows this during build:

```
[0/6] Pre-build checks...
  - DEV_MODE will be DISABLED in production build
  - Backup system: ENABLED
  - Data validation: ENABLED
  - Auto-backup rotation: 5 backups
[OK] Configuration verified
```

## Why This Change Was Made

### Before (Code Review Issue)
```python
DEV_MODE = True  # ✅ Change to False for production
```

**Problems:**
- ❌ Hardcoded value in source code
- ❌ Easy to forget to change before building
- ❌ Risk of shipping dev mode to users
- ❌ Users would see sample data on first run

### After (Fixed)
```python
DEV_MODE = os.getenv("MSHIFT_DEV_MODE", "").lower() in ("1", "true", "yes")
```

**Benefits:**
- ✅ Defaults to `False` (production-safe)
- ✅ No code changes needed for production builds
- ✅ Developers can easily enable when needed
- ✅ Environment-based configuration (best practice)

## Summary

| Scenario | DEV_MODE Value | Sample Data | Use Case |
|----------|---------------|-------------|----------|
| **Production Build** | `False` (default) | ❌ No | End users |
| **Development** | `True` (via env var) | ✅ Yes | Developers/Testing |
| **Running from source** | `False` (default) | ❌ No | Clean testing |
| **Running with env var** | `True` | ✅ Yes | Quick testing |

## Key Takeaway

**You don't need to do anything for production builds!** DEV_MODE is now production-safe by default. Just run `.\build.ps1` and the executable will have DEV_MODE disabled automatically.
