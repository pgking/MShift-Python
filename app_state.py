from PyQt5.QtCore import QStandardPaths
import os
import json

class AppState:
    """
    Manages application state such as file paths and user preferences.
    """
    '''
    def __init__(self):
        self.config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        self.preferences_file = os.path.join(self.config_dir, "preferences.json")
        self.last_opened_file = os.path.join(self.config_dir, "last_opened.txt")

    def get_last_opened_file(self):
        if os.path.exists(self.last_opened_file):
            with open(self.last_opened_file, 'r') as f:
                return f.read().strip()
        return None

    def set_last_opened_file(self, file_path):
        with open(self.last_opened_file, 'w') as f:
            f.write(file_path)
    '''

    def get_app_state_path(self):
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "app_state.json")
    
    def save_app_state(self, main_window):
        path = self.get_app_state_path()

        data = {
            "preferences": main_window.preferences.to_dict(),
            "people": [p.to_dict() for p in main_window.people],
            "services": [s.to_dict() for s in main_window.services],
            "rows": main_window.rows,
            "last_year": int(main_window.year_combo.currentText()),
            "last_month": main_window.month_combo.currentIndex() + 1
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
