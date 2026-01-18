from dataclasses import dataclass

@dataclass
class Preferences:
    previous_days_shown: int = 3

    paste_overwrite_existing: bool = True

    # Copy and paste behavior
    copy_paste_mode:str = "linked" # Linked | Persistent

    # Drag and drop behavior
    # Swap | Replace | Ask
    drag_drop_mode: str = "swap"

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)