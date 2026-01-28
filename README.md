# MShift - Midwife Scheduler

**Version:** 1.0.5  
**A PyQt5-based scheduling application for midwife staff management**

---

## 🚀 Features

### Core Functionality
- **Staff Management**: Manage midwife staff with customizable workload percentages
- **Service Management**: Define shift types with hours, colors, and metadata
- **Schedule Management**: Create and manage monthly schedules
- **Schema System**: Create repeating patterns for automated scheduling
- **Workload Tracking**: Automatic calculation of worked vs. expected hours
- **Rule-Based Validation**: Automatic detection of scheduling conflicts

### Data Safety Features ✨ NEW
- **Automatic Backups**: Every save creates a timestamped backup
- **Backup Rotation**: Keeps the 5 most recent backups automatically
- **Restore from Backup**: Easy recovery from previous versions
- **Data Validation**: Prevents loading of corrupt or invalid files
- **File Watching**: Detects external changes and prompts for reload

### Import/Export
- **Excel Export**: Export schedules to Excel format
- **Excel Import**: Import schedules from Excel files

### User Experience
- **Auto-Save**: Optional automatic saving on changes
- **Recent Files**: Quick access to recently opened files
- **Auto-Update**: Automatic update checking and installation
- **Drag & Drop**: Intuitive drag-and-drop scheduling
- **Copy & Paste**: Efficient schedule editing

---

## 📦 Installation

### Requirements
- Python 3.8+
- PyQt5
- openpyxl (for Excel import/export)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd MShift-Python

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

---

## 🔧 Configuration

### Environment Variables

#### Development Mode
To enable development mode with sample data:
```bash
# Windows (PowerShell)
$env:MSHIFT_DEV_MODE="1"
python main.py

# Windows (CMD)
set MSHIFT_DEV_MODE=1
python main.py

# Linux/Mac
export MSHIFT_DEV_MODE=1
python main.py
```

**Note:** Development mode is disabled by default for production safety.

---

## 💾 Backup System

### Automatic Backups
MShift automatically creates backups every time you save a file:
- Backups are stored in `.mshift_backups/` directory next to your file
- Each backup is timestamped (e.g., `schedule_backup_20260128_143022.mshift`)
- The 5 most recent backups are kept; older ones are automatically deleted

### Restoring from Backup
1. Open the file you want to restore
2. Go to **File → Restore from Backup...**
3. Select the backup you want to restore from the list
4. Click **Restore**
5. Confirm the restoration

**Note:** The current file is automatically backed up before restoration.

### Backup Location
If your schedule file is at:
```
C:\Documents\my_schedule.mshift
```

Backups will be at:
```
C:\Documents\.mshift_backups\
  ├── my_schedule_backup_20260128_143022.mshift
  ├── my_schedule_backup_20260128_142015.mshift
  ├── my_schedule_backup_20260128_141003.mshift
  └── ...
```

---

## 🛡️ Data Safety

### Data Validation
MShift validates all loaded files to ensure data integrity:
- **Type Checking**: Ensures all fields have correct data types
- **Range Validation**: Validates percentages, dates, and other ranges
- **Format Validation**: Checks color codes and other formatted data
- **Error Messages**: Clear, helpful error messages if validation fails

### File Watching
MShift monitors your open file for external changes:
- Checks every 5 seconds for modifications
- Prompts you to reload if the file was changed externally
- Prevents conflicts with cloud sync services (Dropbox, OneDrive, etc.)

---

## 📁 File Format

MShift uses JSON-based `.mshift` files for easy debugging and version control:
```json
{
  "people": [...],
  "services": [...],
  "rows": [...],
  "schedule": {...}
}
```

**Benefits:**
- Human-readable format
- Easy to version control with Git
- Can be edited manually if needed (with caution)
- Compatible with text-based diff tools

---

## ⚙️ Preferences

Access preferences via **Preferences → Preferences**:
- **Auto-Save**: Enable/disable automatic saving
- **Previous Days Shown**: Number of previous month days to display

---

## 🔄 Updates

MShift includes automatic update checking:
- Checks for updates on startup (after 2 seconds)
- Manual check via **About → Check for Updates...**
- Downloads and installs updates automatically

---

## 🐛 Troubleshooting

### File Won't Load
**Error:** "The file contains invalid data"  
**Solution:** The file may be corrupted. Use **File → Restore from Backup** to recover.

### Missing Backups
**Issue:** No backups appear in restore dialog  
**Cause:** Backups are only created when you save a file  
**Solution:** Save the file at least once to create backups

### DEV_MODE Enabled in Production
**Issue:** Sample data loads automatically  
**Solution:** Ensure `MSHIFT_DEV_MODE` environment variable is not set

### File Modified Externally Prompt
**Issue:** Frequent reload prompts  
**Cause:** Cloud sync service is modifying the file  
**Solution:** This is normal behavior; click "Yes" to reload or "No" to keep current version

---

## 📝 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New Schedule |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Quick Save |
| `Ctrl+O` | Open File |
| `Ctrl+Q` | Save and Exit |
| `Shift+Click` | Copy service (drag & drop) |
| `Right Click` | Delete service |

---

## 🏗️ Building from Source

See [BUILD.md](BUILD.md) for detailed build instructions.

---

## 📄 License

[Add your license information here]

---

## 👥 Contributing

[Add contribution guidelines here]

---

## 📞 Support

For issues or questions:
- Check the troubleshooting section above
- Review the code review document: [CODE_REVIEW.md](CODE_REVIEW.md)
- Check implementation details: [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)

---

## 🎯 Version History

### Version 1.0.5 (Current)
- ✨ Added automatic backup system with rotation
- ✨ Added data validation on file load
- ✨ Added restore from backup functionality
- 🐛 Fixed file watcher race condition
- 🔧 Improved error handling for file operations
- 🔧 Replaced magic numbers with named constants
- 🔒 Changed DEV_MODE to environment variable for production safety

### Previous Versions
- See git history for earlier changes

---

**Made with ❤️ for midwife scheduling**
