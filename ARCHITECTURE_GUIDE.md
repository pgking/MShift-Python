# MShift Architecture - Quick Reference Guide

## 🎯 Core Principles

### 1. Domain-First Architecture
- **Domain models** (`models.py`) = Pure Python, no UI dependencies
- **UI widgets** = Separate files, import domain models
- **Business logic** = Lives in domain or MainWindow, never in widgets

### 2. Single Source of Truth
- **State ownership:** MainWindow owns all business state
- **Canonical entry point:** `apply_assignment_change()` for ALL mutations
- **No shortcuts:** UI widgets NEVER mutate domain objects directly

### 3. UI Projection-Only
- UI reads from backend
- UI triggers backend methods
- Backend updates state
- Backend triggers UI refresh

---

## ✅ DO's

### ✅ Mutating State
```python
# CORRECT: Use canonical entry point
self.main_window.apply_assignment_change(
    person_id=person.id,
    day=day,
    service_id=service_id,
    reason="user_action"
)
```

### ✅ Adding New Business Logic
```python
# CORRECT: Add to domain model or MainWindow
class MonthData:
    def calculate_workload(self):
        # Business logic here
        pass
```

### ✅ Creating New UI Widgets
```python
# CORRECT: Separate file, imports domain
# my_widget.py
from models import Person, Service
from PyQt5.QtWidgets import QWidget

class MyWidget(QWidget):
    def __init__(self, main_window):
        self.main_window = main_window
```

### ✅ Shared Logic
```python
# CORRECT: Extract to separate module
# cell_authority.py
def resolve_cell_appearance(...):
    # Shared logic used by UI and export
    pass
```

---

## ❌ DON'Ts

### ❌ Direct Mutation
```python
# WRONG: Direct mutation bypasses business logic
month_data.set_service(person_id, day, service_id)  # ❌ NO!

# CORRECT: Use canonical entry point
self.main_window.apply_assignment_change(...)  # ✅ YES!
```

### ❌ UI in Domain Models
```python
# WRONG: models.py
from PyQt5.QtWidgets import QWidget  # ❌ NO!

class Person:
    def show_dialog(self):  # ❌ NO!
        pass
```

### ❌ Duplicated Logic
```python
# WRONG: Same logic in multiple places
# In exporter.py
if service_id is None:
    if is_holiday: ...
    elif is_weekend: ...

# In ui_renderer.py
if service_id is None:
    if is_holiday: ...  # ❌ Duplicated!
    elif is_weekend: ...

# CORRECT: Extract to shared module
from cell_authority import resolve_cell_appearance
appearance = resolve_cell_appearance(...)
```

### ❌ Commented Code
```python
# WRONG: Leaving old code commented
'''
def old_method(self):
    # old implementation
    pass
'''

# CORRECT: Delete it, use git history if needed
```

---

## 📁 File Organization

```
mshift/
├── models.py              # Pure domain models (Person, Service, MonthData)
├── main.py                # MainWindow - owns all state
├── drag_table_widget.py   # UI widget
├── service_cell.py        # UI widget
├── headers.py             # UI widget
├── table_rebuilder.py     # UI helper
├── cell_authority.py      # Shared business logic
├── rules.py               # Business rules (pure functions)
├── workload.py            # Business calculations
├── exporter.py            # Export logic
├── file_io.py             # Schedule persistence
├── app_state.py           # App state persistence
├── preferences.py         # Preferences model
└── dialogs.py             # UI dialogs
```

---

## 🔄 Data Flow Pattern

```
User Action (UI)
    ↓
UI Widget Event Handler
    ↓
MainWindow.apply_assignment_change()  ← Canonical entry point
    ↓
MonthData.set_service()  ← Domain mutation
    ↓
Rules Engine (evaluate_day_service_counts)
    ↓
MainWindow.day_service_violations updated
    ↓
UI Refresh (refresh_row_headers, viewport.update)
    ↓
User sees updated UI
```

---

## 🧪 Testing Strategy

### Domain Models
```python
# Can test without PyQt5
def test_month_data():
    month = MonthData(2024, 1)
    month.set_service("person1", 15, "service1")
    assert month.get_service("person1", 15) == "service1"
```

### Business Rules
```python
# Pure functions, easy to test
def test_rules():
    violations = evaluate_day_service_counts(...)
    assert len(violations) == 2
```

### UI (Manual or Integration)
- Test through MainWindow methods
- Mock domain objects if needed

---

## 🚀 Adding New Features

### Example: Add "Notes" to Days

1. **Domain Model** (`models.py`):
```python
class MonthData:
    def __init__(self, year, month):
        self.notes = {}  # {day: "note text"}
    
    def set_note(self, day, text):
        self.notes[day] = text
```

2. **Canonical Entry Point** (`main.py`):
```python
def apply_note_change(self, day, text):
    month_data = self.schedule[(self.year, self.month)]
    month_data.set_note(day, text)
    self.table.viewport().update()
```

3. **UI Widget** (new file `note_dialog.py`):
```python
class NoteDialog(QDialog):
    def accept(self):
        self.main_window.apply_note_change(
            day=self.day,
            text=self.text_edit.toPlainText()
        )
```

4. **Persistence** (`models.py`):
```python
def to_dict(self):
    return {
        ...
        "notes": self.notes
    }
```

---

## 📝 Code Review Checklist

Before committing, ask yourself:

- [ ] Are domain models pure (no PyQt imports)?
- [ ] Do all mutations go through canonical entry points?
- [ ] Is shared logic extracted to separate modules?
- [ ] Is there any commented-out code to remove?
- [ ] Are all data fields serialized in `to_dict()`?
- [ ] Does the UI only read from backend, never mutate directly?
- [ ] Are business rules in pure functions?

---

## 🎓 Key Takeaways

1. **Separation of Concerns**: Domain ≠ UI ≠ Persistence
2. **Single Entry Point**: One way to mutate state
3. **No Shortcuts**: Direct mutations break the architecture
4. **DRY Principle**: Extract shared logic
5. **Clean Code**: Delete commented code, use git

Your architecture is now solid. Stick to these patterns and your codebase will remain maintainable as it grows! 🚀
