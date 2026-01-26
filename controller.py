from typing import Dict, List, Optional, Tuple
from models import MonthData, Person, Service
from rules import evaluate_rules, DayServiceViolation, Rule, DEFAULT_RULES
from preferences import Preferences

class ScheduleController:
    """
    Central controller for application logic and state management.
    Decouples business logic from the UI (MainWindow).
    """
    def __init__(self):
        # Core data
        self.schedule: Dict[Tuple[int, int], MonthData] = {}
        self.people: List[Person] = []
        self.services: List[Service] = []
        self.preferences: Preferences = Preferences()
        self.rules: List[Rule] = DEFAULT_RULES
        
        # UI state that needs to be persisted or shared
        self.rows: List[dict] = []
        self.recent_files: List[str] = []
        self.day_service_violations: List[DayServiceViolation] = []
        self.current_file_path: Optional[str] = None
        
        # Persistence state
        self.last_year: Optional[int] = None
        self.last_month: Optional[int] = None

        # Derived or temporary state
        self.n_prev_days: int = 0
        
    def to_dict(self) -> dict:
        """Serializes current app state for persistence."""
        return {
            "preferences": self.preferences.to_dict(),
            "people": [p.to_dict() for p in self.people],
            "services": [s.to_dict() for s in self.services],
            "rows": self.rows,
            "last_year": self.last_year,
            "last_month": self.last_month,
            "recent_files": self.recent_files
        }

    def from_dict(self, data: dict):
        """Restores state from a dictionary."""
        self.preferences = Preferences.from_dict(data.get("preferences", {}))
        self.n_prev_days = self.preferences.previous_days_shown
        self.people = [Person(**p) for p in data.get("people", [])]
        self.services = [Service(**s) for s in data.get("services", [])]
        self.rows = data.get("rows", [])
        self.last_year = data.get("last_year")
        self.last_month = data.get("last_month")
        self.recent_files = data.get("recent_files", [])

    def get_month_data(self, year: int, month: int) -> MonthData:
        if (year, month) not in self.schedule:
            self.schedule[(year, month)] = MonthData(year, month)
        return self.schedule[(year, month)]

    def apply_assignment_change(self, person_id: str, day: int, service_id: Optional[str], year: int, month: int):
        """
        Mutates assignment state and recomputes violations.
        """
        month_data = self.get_month_data(year, month)
        month_data.set_service(person_id, day, service_id)
        self.recompute_violations(year, month)

    def apply_comment_change(self, person_id: str, text: str, year: int, month: int):
        """
        Mutates comment state.
        """
        month_data = self.get_month_data(year, month)
        month_data.set_comment(person_id, text)

    def recompute_violations(self, year: int, month: int):
        """
        Recalculates scheduling violations for the given month.
        """
        month_data = self.schedule.get((year, month))
        if month_data is None:
            self.day_service_violations = []
            return

        self.day_service_violations = evaluate_rules(
            rules=self.rules,
            month_data=month_data,
            people=self.people,
            services_by_id={s.id: s for s in self.services},
            year=year,
            month=month
        )

    def get_person_by_id(self, person_id: str) -> Optional[Person]:
        return next((p for p in self.people if p.id == person_id), None)

    def get_service_by_id(self, service_id: str) -> Optional[Service]:
        return next((s for s in self.services if s.id == service_id), None)
