from PyQt5.QtCore import QStandardPaths
import os
import json

class AppState:
    """
    Manages application state such as file paths and user preferences.
    """

    def get_app_state_path(self):
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "app_state.json")
    
    def save_app_state(self, data: dict):
        if not isinstance(data, dict):
            print(f"[AppState] WARNING: save_app_state received {type(data).__name__} instead of dict. Skipping save.")
            return
        
        path = self.get_app_state_path()

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_app_state(self) -> dict | None:
        path = self.get_app_state_path()
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    print(f"[AppState] WARNING: app_state.json contains {type(data).__name__} instead of dict. Ignoring.")
                    return None
                return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AppState] WARNING: app_state.json is corrupted or empty ({e}). Starting fresh.")
            return None

