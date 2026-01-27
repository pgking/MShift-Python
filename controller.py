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
        
        # Ensure built-ins (actually need services list to be populated first if saving, but for new app it's empty)
        # But ensure_builtin_services appends if missing.
        self.ensure_builtin_services()

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

    def ensure_builtin_services(self):
        note_id = "builtin_note"
        existing = next((s for s in self.services if s.id == note_id), None)
        
        if existing:
            # Update labels just in case
            existing.name = "Note (Texte libre)"
            existing.short_name = "..."
            existing.is_visible = True # FORCE VISIBLE
            
            # Move to top if not already
            if self.services.index(existing) != 0:
                self.services.remove(existing)
                self.services.insert(0, existing)
            return

        # Insert at top for visibility
        self.services.insert(0, Service(
            name="Note (Texte libre)",
            short_name="...",
            hours=0,
            color_hex="#E0E0E0",
            id=note_id,
            is_visible=True
        ))

    def from_dict(self, data: dict):
        """Restores state from a dictionary."""
        self.preferences = Preferences.from_dict(data.get("preferences", {}))
        
        self.people = [Person(**p) for p in data.get("people", [])]
        self.services = [Service(**s) for s in data.get("services", [])]
        self.ensure_builtin_services()
        
        self.schemas = [Schema.from_dict(s) for s in data.get("schemas", [])]
        self.schema_assignments = [SchemaAssignment.from_dict(sa) for sa in data.get("schema_assignments", [])]
        
        self.rows = data.get("rows", [])
        self.last_month = data.get("last_month")
        self.recent_files = data.get("recent_files", [])
        
        # Restore derived/temporary state that might have been lost
        self.n_prev_days = self.preferences.previous_days_shown
        self.last_year = data.get("last_year")


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
    
    def apply_schema_to_month(self, schema: Schema, person_id: str, year: int, month: int, 
                             overwrite: bool = True, start_period: tuple = None):
        """
        Apply a schema pattern to a person for a specific month.
        The schema repeats continuously across month boundaries based on the assignment start date.
        
        Args:
            schema: The schema to apply
            person_id: ID of the person
            year: Target year
            month: Target month
            overwrite: If True, overwrite existing services
            start_period: Tuple (start_year, start_month) of when the assignment started.
                          If None, defaults to current month (starts fresh).
        """
        import calendar as cal
        from datetime import date, timedelta
        
        month_data = self.get_month_data(year, month)
        days_in_month = cal.monthrange(year, month)[1]
        
        # Determine the anchor date based on assignment start
        if start_period:
            start_year, start_month = start_period
            # Validate start_month
            if start_month < 1 or start_month > 12:
                start_year, start_month = year, month
        else:
            start_year, start_month = year, month
            
        # 1. Find the very first potential start day in the assignment's start month
        anchor_date = None
        s_days = cal.monthrange(start_year, start_month)[1]
        for d in range(1, s_days + 1):
            if cal.weekday(start_year, start_month, d) == schema.start_weekday:
                anchor_date = date(start_year, start_month, d)
                break
        
        if anchor_date is None:
            # Should not happen as every month has all weekdays
            return

        # 2. Determine Cycle Length (Multiple of 7 days to ensure it always starts on same weekday)
        # If span is 5 days, cycle is 7 days (Mon-Fri work, Sat-Sun gap, Start Mon)
        # If span is 10 days, cycle is 14 days (Mon week 1 to Wed week 2, Gap until Mon week 3)
        import math
        cycle_weeks = math.ceil(max(1, schema.span_days) / 7)
        cycle_length_days = cycle_weeks * 7

        # 3. Apply pattern to the requested month
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            
            # Calculate days since the anchor date
            days_since_anchor = (current_date - anchor_date).days
            
            # Calculate position in the cycle
            # Note: Python's modulo operator handles negative numbers correctly for cyclical patterns
            # e.g. -5 % 7 = 2, which correctly maps 'Wednesday' back from a 'Monday' anchor
            position_in_cycle = days_since_anchor % cycle_length_days
            
            # If we are within the active span of the cycle, apply service
            if position_in_cycle < schema.span_days:
                # Get service for this position
                service_id = schema.get_service(position_in_cycle)
                
                if service_id:
                    existing_service = month_data.get_service(person_id, day)
                    if overwrite or existing_service is None:
                        month_data.set_service(person_id, day, service_id)
    
    def apply_assignment(self, assignment):
        """
        Apply a schema assignment fully across its duration.
        """
        schema = self.get_schema_by_id(assignment.schema_id)
        if not schema:
            return
            
        start_year = assignment.start_year
        start_month = assignment.start_month
        if not start_year or not start_month:
            return

        limit = 0
        if assignment.repeat_mode == "limited":
            limit = assignment.repeat_months
        elif assignment.repeat_mode == "always":
            limit = 24  # Apply for 2 years (reasonable horizon)
            
        overwrite = getattr(assignment, 'overwrite_existing', True)
        start_period = (start_year, start_month)
        
        # Determine start index (months from year 0)
        start_idx = start_year * 12 + (start_month - 1)
        
        for i in range(limit):
            current_idx = start_idx + i
            y = current_idx // 12
            m = (current_idx % 12) + 1
            
            self.apply_schema_to_month(
                schema,
                assignment.person_id,
                y, m,
                overwrite,
                start_period=start_period
            )
    
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
            
            # Apply the schema to this person with the assignment's overwrite setting
            overwrite = getattr(assignment, 'overwrite_existing', True)  # Default to True for old assignments
            start_period = (assignment.start_year, assignment.start_month) if assignment.start_year else None
            
            self.apply_schema_to_month(
                schema, 
                assignment.person_id, 
                year, 
                month, 
                overwrite,
                start_period=start_period
            )
