# MShift-Python Code Review

**Review Date:** January 27, 2026  
**Version Reviewed:** 1.0.5  
**Reviewer:** Antigravity AI

---

## Executive Summary

MShift is a **midwife scheduling application** built with PyQt5. The application manages staff schedules, workload calculations, and service assignments with rule-based validation. Overall, the codebase demonstrates **solid engineering practices** with good separation of concerns, but there are opportunities for improvement in architecture, scalability, and maintainability.

**Overall Rating: 7/10** ⭐⭐⭐⭐⭐⭐⭐

---

## 1. Architecture Review

### ✅ **Strengths**

#### 1.1 **Separation of Concerns**
The application follows a **modular architecture** with clear separation:

- **Models** (`models.py`): Domain entities (Person, Service, Schema, MonthData)
- **Controller** (`controller.py`): Business logic and state management
- **UI Layer** (`main.py`, dialogs, headers): Presentation logic
- **Utilities**: Specialized handlers (drag_drop, copy_paste, workload)

This is **excellent** and follows MVC-like patterns.

#### 1.2 **Single Responsibility Principle**
Most modules have focused responsibilities:
- `rules.py`: Validation logic
- `workload.py`: Hour calculations
- `exporter.py`/`importer.py`: File I/O
- `updater.py`: Auto-update functionality

#### 1.3 **Data Modeling**
The domain models are well-designed:
- **Service**: Represents shift types with hours, colors, and metadata
- **Person**: Staff members with percentage-based workload
- **Schema**: Repeating patterns for scheduling
- **MonthData**: Encapsulates monthly schedule state

#### 1.4 **Rule-Based Validation**
The `rules.py` module uses an **extensible rule system** with:
- Abstract `Rule` base class
- Concrete implementations (`StaffingRule`)
- Violation tracking with severity levels

This is **architecturally sound** and allows easy addition of new rules.

---

### ⚠️ **Weaknesses & Concerns**

#### 1.1 **God Object Anti-Pattern**
**Issue:** `MainWindow` (1156 lines) is doing too much:
- UI rendering
- Event handling
- Business logic coordination
- State management
- File I/O coordination

**Impact:** 
- Hard to test
- Difficult to maintain
- Violates Single Responsibility Principle

**Recommendation:**
```python
# Split into:
class ScheduleView:      # Pure UI rendering
class EventCoordinator:  # Event handling
class ApplicationFacade: # Coordinates controller + view
```

#### 1.2 **Tight Coupling Between UI and Business Logic**
**Issue:** Despite having a `ScheduleController`, the `MainWindow` still:
- Directly accesses `self.schedule`, `self.people`, `self.services`
- Has proxy properties that delegate to controller (lines 176-214)
- Mixes UI state with domain state

**Example:**
```python
# Lines 176-214: Proxy properties indicate architectural smell
@property
def people(self): return self.controller.people
@people.setter
def people(self, v): self.controller.people = v
```

**Recommendation:**
- Remove proxy properties
- Always access state through `self.controller`
- Move more logic into controller methods

#### 1.3 **Inconsistent State Management**
**Issue:** State is scattered across multiple places:
- `ScheduleController`: Core data (people, services, schedule)
- `MainWindow`: UI state (current_file_path, last_file_mtime)
- `AppState`: Persistence logic

**Recommendation:**
- Consolidate all application state in `ScheduleController`
- Make `AppState` a pure serialization utility
- Move file tracking to controller

#### 1.4 **Missing Dependency Injection**
**Issue:** Hard dependencies make testing difficult:
```python
# workload.py line 18
def __init__(self, main_window):
    self.main_window = main_window  # Tight coupling to UI
```

**Recommendation:**
```python
# Better approach
def __init__(self, schedule_provider, services_provider):
    self.schedule_provider = schedule_provider
    self.services_provider = services_provider
```

---

## 2. Scalability Review

### ✅ **Current Strengths**

#### 2.1 **Data Structure Efficiency**
- Uses dictionaries for O(1) lookups: `schedule[(year, month)]`
- Efficient person/service lookups by ID
- Minimal redundant data storage

#### 2.2 **Lazy Loading**
- Month data created on-demand (line 832-833 in `main.py`)
- Services loaded only when needed

---

### ⚠️ **Scalability Concerns**

#### 2.1 **In-Memory Data Model**
**Issue:** All data held in memory:
- `self.schedule` dictionary grows unbounded
- No pagination or data pruning
- Could become problematic with years of historical data

**Current Capacity Estimate:**
- 50 people × 12 months × 31 days = ~18,600 assignments/year
- With metadata: ~2-5 MB/year (acceptable for desktop app)

**Recommendation:**
- Implement data archiving for old months
- Add lazy loading for historical data
- Consider SQLite for large datasets (100+ people, 5+ years)

#### 2.2 **UI Performance**
**Issue:** Full table rebuild on every change:
```python
# table_rebuilder.py - rebuilds entire table
def finalize(self):
    # Rebuilds all cells
```

**Impact:**
- Slow with 50+ people
- Unnecessary redraws

**Recommendation:**
- Implement incremental updates
- Use Qt's model/view architecture (QAbstractTableModel)
- Only refresh affected cells

#### 2.3 **Rule Evaluation Performance**
**Issue:** Rules re-evaluated for entire month on every change:
```python
# controller.py line 119-135
def recompute_violations(self, year: int, month: int):
    # Evaluates ALL days for ALL rules
```

**Impact:**
- O(days × people × rules) complexity
- Could be slow with many rules

**Recommendation:**
- Incremental validation (only affected days)
- Cache violation results
- Debounce validation during bulk operations

#### 2.4 **File I/O Bottleneck**
**Issue:** Auto-save writes entire state on every change:
```python
# main.py line 353-355
if self.preferences and self.preferences.auto_save:
    self.quick_save()  # Saves entire file
```

**Recommendation:**
- Debounce auto-save (e.g., 2-second delay)
- Implement incremental saves
- Use background thread for I/O

---

## 3. Code Quality & Best Practices

### ✅ **Strengths**

#### 3.1 **Type Hints**
Good use of type annotations:
```python
def apply_assignment_change(self, person_id: str, day: int, 
                           service_id: Optional[str], year: int, month: int)
```

#### 3.2 **Docstrings**
Many functions have clear docstrings explaining purpose and behavior.

#### 3.3 **Testing**
Comprehensive test suite (`tests.py`) with:
- Unit tests for models
- Controller tests
- Workload calculation tests
- File I/O tests

**Test Coverage:** ~70% (estimated)

#### 3.4 **Error Handling**
Graceful error handling in critical paths:
```python
try:
    mtime = os.path.getmtime(self.current_file_path)
except Exception as e:
    print(f"Error checking file for updates: {e}")
```

---

### ⚠️ **Areas for Improvement**

#### 3.1 **Magic Numbers**
**Issue:** Hard-coded values scattered throughout:
```python
self._watcher_timer.setInterval(5000)  # What is 5000?
QTimer.singleShot(2000, ...)           # Why 2000?
```

**Recommendation:**
```python
# Constants at module level
FILE_WATCH_INTERVAL_MS = 5000
UPDATE_CHECK_DELAY_MS = 2000
```

#### 3.2 **Long Methods**
Several methods exceed 50 lines:
- `MainWindow.__init__`: 115 lines
- `finalize_table_setup`: Complex logic
- `apply_schema_to_month`: 70 lines

**Recommendation:** Extract helper methods

#### 3.3 **Commented-Out Code**
Found in `dialogs_restore.txt` - should be removed or properly archived.

#### 3.4 **Development Mode Flag**
**Critical Issue:**
```python
# main.py line 153
DEV_MODE = True  # ✅ Change to False for production
```

**This is still enabled in production code!**

**Recommendation:**
- Use environment variables
- Remove from source code
- Add build-time configuration

#### 3.5 **Inconsistent Naming**
Mix of naming conventions:
- `n_prev_days` (snake_case with abbreviation)
- `day_service_violations` (clear)
- `_is_saving_to_disk` (good private indicator)

**Recommendation:** Standardize on full words in snake_case

---

## 4. Security & Data Integrity

### ✅ **Strengths**

#### 4.1 **File Watching**
Detects external file modifications and prompts user (lines 740-765).

#### 4.2 **UUID-Based IDs**
Prevents ID collisions:
```python
self.id = id or str(uuid.uuid4())
```

---

### ⚠️ **Concerns**

#### 4.1 **No Data Validation on Load**
**Issue:** `from_dict` methods don't validate data integrity:
```python
# models.py - no validation
def from_dict(data):
    return Schema(
        name=data["name"],  # Could be None or invalid
        ...
    )
```

**Recommendation:**
- Add schema validation (e.g., using `pydantic`)
- Validate data types and ranges
- Handle corrupt files gracefully

#### 4.2 **No Backup Strategy**
**Issue:** Auto-save overwrites file immediately. If corruption occurs, data is lost.

**Recommendation:**
- Keep N previous versions
- Implement backup rotation
- Add "Restore from backup" feature

#### 4.3 **Pickle Alternative**
**Issue:** Using JSON is good, but consider:
- Versioning for backward compatibility
- Migration scripts for schema changes

---

## 5. Maintainability

### ✅ **Strengths**

#### 5.1 **Modular Structure**
24 Python files with clear responsibilities.

#### 5.2 **Build Documentation**
Excellent `BUILD.md` with step-by-step instructions.

#### 5.3 **Version Control**
Proper `.gitignore` excludes build artifacts.

---

### ⚠️ **Concerns**

#### 5.1 **Missing Documentation**
- No `README.md` for users
- No architecture diagram
- No API documentation

**Recommendation:**
```markdown
# Add:
- README.md: User guide
- ARCHITECTURE.md: System design
- CONTRIBUTING.md: Developer guide
```

#### 5.2 **No Logging Framework**
**Issue:** Using `print()` statements:
```python
print("Add Person clicked")
print(f"Auto-loading last file: {last_file}")
```

**Recommendation:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Auto-loading last file: %s", last_file)
```

#### 5.3 **Hard-Coded UI Strings**
**Issue:** No internationalization support. French strings hard-coded:
```python
{"id": "Suites", "label": "Suites de couches"}
```

**Recommendation:**
- Extract strings to resource files
- Use Qt's translation system (`tr()`)

---

## 6. Additional Observations

### 6.1 **Positive Patterns**

#### ✅ **Canonical Entry Points**
Excellent pattern for state mutations:
```python
def apply_assignment_change(self, *, person_id, day, service_id, ...):
    """
    Canonical entry point for ALL assignment mutations.
    UI code MUST NOT call MonthData.set_service directly.
    """
```

This prevents inconsistent state!

#### ✅ **Auto-Update Mechanism**
Built-in updater (`updater.py`) is a professional touch.

#### ✅ **Schema System**
Repeating pattern support is sophisticated and well-designed.

---

### 6.2 **Potential Bugs**

#### ⚠️ **Race Condition**
```python
# main.py line 679-685
def quick_save(self):
    if self.current_file_path:
        self._is_saving_to_disk = True
        try:
            save_schedule(...)
            self.last_file_mtime = os.path.getmtime(...)
        finally:
            self._is_saving_to_disk = False
```

**Issue:** If file watcher checks between save and mtime update, could trigger false reload.

**Fix:** Update mtime **before** writing file.

#### ⚠️ **Memory Leak Risk**
```python
# main.py line 583-588
if hasattr(existing, "_service_cell"):
    existing._service_cell = None  # Manual cleanup
```

**Issue:** Circular references between widgets. Qt should handle this, but manual cleanup suggests potential leak.

**Recommendation:** Use weak references or proper Qt parent-child relationships.

---

## 7. Recommendations Summary

### 🔴 **Critical (Do Now)**

1. **Set `DEV_MODE = False`** in production builds
2. **Add data validation** on file load
3. **Implement backup rotation** for auto-save
4. **Fix potential race condition** in file watcher

### 🟡 **High Priority (Next Sprint)**

5. **Refactor `MainWindow`** - split into smaller classes
6. **Add logging framework** - replace print statements
7. **Implement incremental UI updates** - improve performance
8. **Debounce auto-save** - reduce I/O overhead
9. **Add README.md** - user documentation

### 🟢 **Medium Priority (Future)**

10. **Extract constants** - remove magic numbers
11. **Add architecture documentation**
12. **Implement data archiving** - for old months
13. **Add internationalization support**
14. **Improve test coverage** to 85%+

### 🔵 **Low Priority (Nice to Have)**

15. **Consider SQLite** for large datasets
16. **Add telemetry/analytics** (opt-in)
17. **Implement undo/redo** functionality
18. **Add keyboard shortcuts** reference

---

## 8. Scalability Roadmap

### Current Capacity
- **Users:** 1-50 people
- **Data:** 1-3 years of history
- **Performance:** Acceptable

### Growth Path

#### Phase 1: 50-100 people
- ✅ Current architecture sufficient
- Add incremental updates
- Optimize rule evaluation

#### Phase 2: 100-500 people
- Consider database backend (SQLite)
- Implement pagination
- Add data archiving

#### Phase 3: 500+ people (Enterprise)
- Client-server architecture
- PostgreSQL/MySQL backend
- Web-based interface
- Multi-user support with permissions

---

## 9. Final Verdict

### **Overall Assessment: GOOD** 👍

MShift is a **well-engineered desktop application** with:
- ✅ Solid architecture foundation
- ✅ Good separation of concerns
- ✅ Comprehensive testing
- ✅ Professional features (auto-update, file watching)

### **Main Concerns:**
- ⚠️ `MainWindow` is too large (god object)
- ⚠️ Performance could degrade with scale
- ⚠️ Missing production safeguards (DEV_MODE flag)

### **Recommended Next Steps:**

1. **Immediate:** Fix DEV_MODE and add data validation
2. **Short-term:** Refactor MainWindow, add logging
3. **Long-term:** Optimize performance, add documentation

---

## 10. Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Lines of Code** | ~10,000 | - | - |
| **Test Coverage** | ~70% | 85% | ⚠️ |
| **Largest File** | 1,156 lines | <500 | ⚠️ |
| **Cyclomatic Complexity** | Medium | Low | ⚠️ |
| **Documentation** | Partial | Complete | ⚠️ |
| **Type Hints** | Good | Excellent | ✅ |
| **Modularity** | Good | Excellent | ✅ |

---

**End of Review**

*Generated by Antigravity AI - January 27, 2026*
