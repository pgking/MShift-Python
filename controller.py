from typing import Dict, List, Optional, Tuple
from models import MonthData, Person, Service, Schema, SchemaAssignment
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
        self.schemas: List[Schema] = []
        self.schema_assignments: List[SchemaAssignment] = []
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
            "schemas": [s.to_dict() for s in self.schemas],
            "schema_assignments": [sa.to_dict() for sa in self.schema_assignments],
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
        self.schemas = [Schema.from_dict(s) for s in data.get("schemas", [])]
        self.schema_assignments = [SchemaAssignment.from_dict(sa) for sa in data.get("schema_assignments", [])]
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
    
    def get_schema_by_id(self, schema_id: str) -> Optional[Schema]:
        return next((s for s in self.schemas if s.id == schema_id), None)
    
    def get_assignments_for_person(self, person_id: str) -> List[SchemaAssignment]:
        """Get all schema assignments for a specific person."""
        return [sa for sa in self.schema_assignments if sa.person_id == person_id]
    
    def apply_schema_to_month(self, schema: Schema, person_id: str, year: int, month: int):
        """
        Apply a schema pattern to a person for a specific month.
        The schema repeats on matching weekdays throughout the month.
        """
        import calendar as cal
        
        month_data = self.get_month_data(year, month)
        days_in_month = cal.monthrange(year, month)[1]
        
        # Iterate through all days in the month
        for day in range(1, days_in_month + 1):
            weekday = cal.weekday(year, month, day)  # 0=Monday, 6=Sunday
            
            # Check if this day matches the schema's starting weekday
            if weekday == schema.start_weekday:
                # Calculate which occurrence of this weekday this is
                occurrence = 0
                for d in range(1, day + 1):
                    if cal.weekday(year, month, d) == schema.start_weekday:
                        occurrence += 1
                
                # Calculate the offset in the pattern (cyclically repeating)
                pattern_offset = ((occurrence - 1) * 7) % schema.span_days
                
                # Apply services for the next span_days starting from this day
                for offset in range(schema.span_days):
                    target_day = day + offset
                    if target_day > days_in_month:
                        break
                    
                    service_id = schema.get_service(offset)
                    if service_id:
                        month_data.set_service(person_id, target_day, service_id)
                
                # Move to next week to avoid overlapping applications
                # (we apply the full pattern starting from each matching weekday)
    
    def auto_apply_schemas(self, year: int, month: int):
        """
        Automatically apply schema assignments that should be active for the given month.
        This is called when loading/navigating to a month.
        """
        for assignment in self.schema_assignments:
            # Check if this assignment should apply to this month
            if not assignment.should_apply_to_month(year, month):
                continue
            
            # Get the schema
            schema = self.get_schema_by_id(assignment.schema_id)
            if not schema:
                continue
            
            # Apply the schema to this person
            self.apply_schema_to_month(schema, assignment.person_id, year, month)
