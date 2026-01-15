from dataclasses import dataclass

@dataclass
class Preferences:
    previous_days_shown: int = 3

    paste_overwrite_existing: bool = True

    # Drag and drop behavior
    # Swap | Replace | Ask
    drag_drop_mode: str = "swap"