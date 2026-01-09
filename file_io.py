import json

from models import Person, Service, MonthData

def save_schedule(main_window, path):
    data = build_save_data(main_window)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent = 2)

def build_save_data(main_window):
    return {
        "people": [p.to_dict() for p in main_window.people],
        "services": [s.to_dict() for s in main_window.services],
        "rows": main_window.rows,
        "schedule": {
            f"{year}_{month}": main_window.schedule[(year, month)].to_dict()
            for year, month in main_window.schedule
        }
    }

'''def to_dict(self):
    return{
        "year": self.year,
        "month": self.month,
        "holidays": list(self.holidays),
        "services": self.services_data
    }'''

def load_schedule(main_window, path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    apply_loaded_data(main_window, data)


def apply_loaded_data(main_window, data):
    # Rebuild people and services
    main_window.people = [Person(**p) for p in data["people"]]
    main_window.services = [Service(**s) for s in data ["services"]]

    # Rebuild row (sections and ordering)
    main_window.rows = data.get("rows", [])

    # Rebuild Schedule
    main_window.schedule = {}
    for key, month_dict in data["schedule"].items():
        main_window.schedule[tuple(map(int, key.split("_")))] = MonthData.from_dict(month_dict)


'''def from_dict(cls, data):
    obj = cls(data["year"], data["month"])
    obj.holidays = set(data.get("holidays", []))
    obj.services_data = data.get("services", {})
    return obj'''
