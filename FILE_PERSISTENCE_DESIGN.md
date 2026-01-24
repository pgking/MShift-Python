# MShift - File Persistence Design

## The Question

**What if there's a disparity between app_state and the schedule file when loading?**

Example scenario:
- Person A has team: [Alice, Bob, Carol] with row order [Alice, Bob, Carol]
- Person B has team: [Alice, Bob, Carol, Dave] with row order [Carol, Dave, Alice, Bob]
- Person A sends `schedule.mshift` to Person B
- What happens when Person B loads it?

## The Answer: Self-Contained Files

### Design Decision

**`.mshift` files are SELF-CONTAINED** - they include everything needed to work on that schedule:
- ✅ People (team roster)
- ✅ Services
- ✅ Row order
- ✅ Schedule data (assignments, holidays)

### What Happens When Loading

```python
def apply_loaded_data(main_window, data):
    # 1. REPLACE current team with file's team
    main_window.people = [Person(**p) for p in data["people"]]
    
    # 2. REPLACE current services with file's services
    main_window.services = [Service(**s) for s in data["services"]]
    
    # 3. REPLACE current row order with file's row order
    main_window.rows = data.get("rows", [])
    
    # 4. Load schedule data
    main_window.schedule = {...}
    
    # 5. ✅ SYNC app_state to match loaded file
    main_window.app_state.save_app_state(main_window)
```

**Result:** Person B's app is now in the exact same state as Person A's was when they saved the file.

### Why This Design?

#### ✅ Pros
1. **Sharing works perfectly** - Critical for your use case (midwives sharing schedules)
2. **No conflicts** - Schedule data always matches the team it was created for
3. **Simple mental model** - One file = complete state
4. **No data loss** - You always know what team the schedule was made for
5. **Reproducible** - Opening a file gives you the exact state it was saved in

#### ❌ Cons
1. **Larger file size** - Includes team roster (but JSON is small, not a real issue)
2. **Overwrites local team** - If you have local changes, they're lost (but this is expected behavior)

### The Alternative (Not Recommended)

**Data-Only Files** - Only save schedule data, keep team in app_state:

```python
def build_save_data(main_window):
    return {
        "schedule": {...}  # Only schedule data
    }
```

**Problems:**
- ❌ Sharing doesn't work - Person B doesn't have Person A's team
- ❌ Need complex conflict resolution - What if schedule references unknown person IDs?
- ❌ Confusing behavior - Opening a file doesn't give you a complete picture

## How It Works in Practice

### Scenario 1: Single User
```
Day 1: Create team [Alice, Bob], save schedule.mshift
Day 2: Close app (app_state.json saved)
Day 3: Open app (loads from app_state.json) → [Alice, Bob] ✅
Day 4: Load schedule.mshift → [Alice, Bob] ✅
```

### Scenario 2: Sharing Between Users
```
Person A:
- Team: [Alice, Bob, Carol]
- Saves schedule_jan.mshift
- Sends to Person B

Person B:
- Team: [Alice, Bob, Carol, Dave]
- Loads schedule_jan.mshift
- Team becomes: [Alice, Bob, Carol] ✅
- app_state.json updated to match
- Next launch: [Alice, Bob, Carol] ✅
```

### Scenario 3: Working on Multiple Schedules
```
User has:
- schedule_jan.mshift (team: [Alice, Bob])
- schedule_feb.mshift (team: [Alice, Bob, Carol])

Load schedule_jan.mshift:
- Team: [Alice, Bob] ✅
- app_state synced

Load schedule_feb.mshift:
- Team: [Alice, Bob, Carol] ✅
- app_state synced

Next launch:
- Loads from app_state: [Alice, Bob, Carol] ✅
- (Last loaded file's state)
```

## Key Implementation Details

### 1. Loading Syncs app_state
```python
# file_io.py
def apply_loaded_data(main_window, data):
    # ... load all data ...
    
    # ✅ CRITICAL: Sync app_state with loaded data
    main_window.app_state.save_app_state(main_window)
```

This prevents conflicts on next launch.

### 2. Closing Syncs app_state
```python
# main.py
def closeEvent(self, event):
    self.app_state.save_app_state(self)
    super().closeEvent(event)
```

This preserves your current state for next launch.

### 3. Two Persistence Systems
```
app_state.json (in AppData):
- Purpose: Remember state between launches
- Updated: On close, after loading file, after preferences change
- Contains: people, services, rows, preferences, last_month

schedule.mshift (user chooses location):
- Purpose: Save/share complete schedule
- Updated: When user clicks "Save"
- Contains: people, services, rows, schedule data
```

## Best Practices

### For Single User
1. Create your team once
2. Save schedule files regularly
3. app_state will remember your last state

### For Sharing
1. Save a `.mshift` file
2. Send to colleague
3. They load it and get your exact state
4. They can modify and send back
5. You load their version and get their changes

### For Multiple Teams
If you work with different teams:
1. Keep separate `.mshift` files for each team
2. Loading a file switches to that team
3. app_state remembers the last team you worked with

## Summary

**The current implementation is correct for your use case.**

✅ Files are self-contained  
✅ Sharing works perfectly  
✅ No conflicts between app_state and loaded files  
✅ app_state syncs after loading  

This design prioritizes **collaboration** and **reproducibility** over keeping a single persistent team roster, which is the right choice for a scheduling application where multiple people need to work on the same schedule.
