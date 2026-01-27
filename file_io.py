import json

from models import Person, Service, MonthData

def save_schedule(controller, path):
    data = build_save_data(controller)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent = 2)

def build_save_data(controller):
    """
    Build complete schedule file data.
    """
    return {
        "people": [p.to_dict() for p in controller.people],
        "services": [s.to_dict() for s in controller.services],
        "rows": controller.rows,
        "schedule": {
            f"{year}_{month}": controller.schedule[(year, month)].to_dict()
            for year, month in controller.schedule
        }
    }

def load_schedule(controller, path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    apply_loaded_data(controller, data)


def apply_loaded_data(controller, data):
    """
    Apply loaded schedule data to Controller.
    """
    # Rebuild people and services
    controller.people = [Person(**p) for p in data["people"]]
    controller.services = [Service(**s) for s in data ["services"]]
    
    # Ensure hidden "Unknown" service exists (for backward compatibility or new saves)
    if not any(s.id == "unknown" for s in controller.services):
        controller.services.append(
            Service("Inconnu", "?", 0, "#FF5555", id="unknown", is_visible=False)
        )
    
    # Ensure builtin services (Notes)
    controller.ensure_builtin_services()

    # Rebuild row (sections and ordering)
    controller.rows = data.get("rows", [])

    # Rebuild Schedule
    controller.schedule = {}
    for key, month_dict in data["schedule"].items():
        controller.schedule[tuple(map(int, key.split("_")))] = MonthData.from_dict(month_dict)
