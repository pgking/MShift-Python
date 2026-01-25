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
    
    def save_app_state(self, main_window):
        path = self.get_app_state_path()

        data = {
            "preferences": main_window.preferences.to_dict(),
            "people": [p.to_dict() for p in main_window.people],
            "services": [s.to_dict() for s in main_window.services],
            "rows": main_window.rows,
            "last_year": int(main_window.year_combo.currentText()),
            "last_month": main_window.month_combo.currentIndex() + 1,
            "recent_files": main_window.recent_files
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
