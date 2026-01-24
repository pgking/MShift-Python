# Development Mode Guide

## Quick Start

### Enable Dev Mode

In `main.py` line ~166:
```python
DEV_MODE = True  # ✅ Enabled for testing
```

**What happens:**
- App launches with 6 pre-loaded people
- No need to manually add people for testing
- Perfect for testing violations, workload, drag-and-drop, etc.

### Disable Dev Mode (Production)

```python
DEV_MODE = False  # ✅ Disabled for production
```

**What happens:**
- App launches with empty team (first launch only)
- Subsequent launches load from app_state as normal

---

## Dev Seed Features

### 1. Pre-loaded People

When `DEV_MODE = True`, you get:
```
Tiphaine Angibaud (100%)
Marie Dubois (80%)
Sophie Martin (100%)
Claire Bernard (50%)
Julie Petit (100%)
Emma Rousseau (80%)
```

Different percentages help test workload calculations!

### 2. Sample Schedule (Optional)

Want to test violations? Add this to your code:

```python
# In main.py, after load_dev_data(self)
if DEV_MODE:
    from dev_seed import load_dev_data, load_dev_schedule_sample
    load_dev_data(self)
    
    # Add sample schedule for current month
    year = int(self.year_combo.currentText())
    month = self.month_combo.currentIndex() + 1
    load_dev_schedule_sample(self, year, month)
```

**What you get:**
- Day 1: Correct (3 Jour, 3 Nuit) ✅
- Day 2: Violations (2 Jour, 4 Nuit) ⚠️

Perfect for testing violation icons in headers!

---

## Customizing Dev Seed

Edit `dev_seed.py` to add your own test data:

```python
def load_dev_data(main_window):
    test_people = [
        Person("Your", "Name", 100),
        Person("Another", "Person", 80),
        # Add more...
    ]
    
    for person in test_people:
        main_window._add_person_to_table(person)
```

---

## How It Works

### First Launch (No app_state.json)
```
1. Check if app_state exists → No
2. Load defaults (services, empty people)
3. Check DEV_MODE → True
4. Load dev_seed → 6 people added ✅
5. App launches with test data
```

### Subsequent Launches (app_state.json exists)
```
1. Check if app_state exists → Yes
2. Load from app_state → Last team + schedule ✅
3. DEV_MODE is ignored (already have data)
4. App launches with your real data
```

**Key Point:** Dev seed only runs on **first launch**. After that, app_state takes over.

---

## Testing Workflow

### Scenario 1: Fresh Testing
```bash
1. Delete app_state.json (in AppData)
2. Launch app → Dev seed loads
3. Test features
4. Close app → app_state saves dev data
5. Next launch → Dev data persists
```

### Scenario 2: Reset to Dev Seed
```bash
1. Delete app_state.json
2. Launch app → Dev seed loads again
```

### Scenario 3: Production Mode
```bash
1. Set DEV_MODE = False
2. Delete app_state.json
3. Launch app → Empty team
4. Add real team
```

---

## Best Practices

### ✅ DO
- Keep `DEV_MODE = True` during development
- Customize `dev_seed.py` with realistic test data
- Use `load_dev_schedule_sample()` to test violations
- Commit `dev_seed.py` to git (helps other developers)

### ❌ DON'T
- Ship with `DEV_MODE = True` to production
- Commit `app_state.json` to git (it's user-specific)
- Forget to test with `DEV_MODE = False` before release

---

## Finding app_state.json

**Windows:**
```
C:\Users\<YourName>\AppData\Local\<AppName>\app_state.json
```

**Quick way to reset:**
```python
# Add this temporary button to your app
def reset_dev_data(self):
    import os
    path = self.app_state.get_app_state_path()
    if os.path.exists(path):
        os.remove(path)
    print("✅ app_state deleted. Restart app to reload dev seed.")
```

---

## Summary

**For Development:**
```python
DEV_MODE = True  # Get 6 test people on first launch
```

**For Production:**
```python
DEV_MODE = False  # Start with empty team
```

**To Reset:**
Delete `app_state.json` and relaunch.

That's it! Happy testing! 🚀
