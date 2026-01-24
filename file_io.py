import json

from models import Person, Service, MonthData

def save_schedule(main_window, path):
    data = build_save_data(main_window)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent = 2)

def build_save_data(main_window):
    """
    Build complete schedule file data.
    
    Design Decision: .mshift files are SELF-CONTAINED
    - Includes: people, services, rows, schedule data
    - Rationale: Enables sharing schedules between users
    - When loaded, replaces current app state completely
    
    This ensures that opening a .mshift file gives you the exact
    state it was saved in, with the correct team and row order.
    """
    return {
        "people": [p.to_dict() for p in main_window.people],
        "services": [s.to_dict() for s in main_window.services],
        "rows": main_window.rows,
        "schedule": {
            f"{year}_{month}": main_window.schedule[(year, month)].to_dict()
            for year, month in main_window.schedule
        }
    }

def load_schedule(main_window, path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    apply_loaded_data(main_window, data)


def apply_loaded_data(main_window, data):
    """
    Apply loaded schedule data to MainWindow.
    
    IMPORTANT: This REPLACES the current team, services, and row order
    with what's in the file. This ensures the schedule data matches
    the team it was created for.
    
    After loading, we sync app_state so the next launch uses the
    loaded team instead of the old app_state.
    """
    # Rebuild people and services
    main_window.people = [Person(**p) for p in data["people"]]
    main_window.services = [Service(**s) for s in data ["services"]]

    # Rebuild row (sections and ordering)
    main_window.rows = data.get("rows", [])

    # Rebuild Schedule
    main_window.schedule = {}
    for key, month_dict in data["schedule"].items():
        main_window.schedule[tuple(map(int, key.split("_")))] = MonthData.from_dict(month_dict)
    
    # ✅ CRITICAL: Sync app_state with loaded data
    # This prevents conflicts when the app is relaunched
    main_window.app_state.save_app_state(main_window)
