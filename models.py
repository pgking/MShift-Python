import uuid
import calendar

class Service:
    def __init__(self, name, short_name, hours, color_hex, id=None, is_visible=True):
        self.id = id or str(uuid.uuid4()) # Unique identifier
        self.name = name
        self.short_name = short_name
        self.hours = hours
        self.color_hex = color_hex
        self.is_visible = is_visible

    def get_duration(self, year, month, day, holidays):
        """
        Returns the duration of the service for a specific date.
        Handles special logic for services like 'CA' (Congés Annuels).
        """
        if self.short_name == "CA":
            # Congés Annuels Logic:
            # 7h per day, except weekends and holidays.
            weekday = calendar.weekday(year, month, day)
            if weekday >= 5: # Saturday=5, Sunday=6
                return 0.0
            if day in holidays:
                return 0.0
            return 7.0
            
        return float(self.hours)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "hours": self.hours,
            "color_hex": self.color_hex,
            "is_visible": self.is_visible
        }

class Person:
    def __init__(self, prenom: str, nom: str, percentage: int, short_name: str | None = None, id=None):
        self.id = id or str(uuid.uuid4()) # Unique identifier
        self.prenom = prenom.strip()
        self.nom = nom.strip()
        self.percentage = percentage
        if short_name and short_name.strip() :
            self.short_name = short_name.strip()
        
        else :
            self.short_name = self._default_short_name()

    def _default_short_name(self) -> str :
        if not self.prenom :
            return self.nom.title()
        
        return f"{self.prenom[0].upper()}. {self.nom.title()}"
    
    @property
    def display_name(self) -> str:
        """
        Returns formatted name: 'Prénom NOM'
        - Prénom: First letter capitalized, rest lowercase
        - NOM: Fully uppercase
        """
        prenom_formatted = self.prenom.capitalize() if self.prenom else ""
        nom_formatted = self.nom.upper()
        
        if prenom_formatted:
            return f"{prenom_formatted} {nom_formatted}"
        return nom_formatted

    def to_dict(self):
        return {
            "id": self.id,
            "prenom": self.prenom,
            "nom": self.nom,
            "percentage": self.percentage,
            "short_name": self.short_name
        }

class Schema:
    """
    Represents a repeating pattern of services.
    
    Attributes:
        id: Unique identifier
        name: User-defined name for the schema
        start_weekday: Starting day of the week (0=Monday, 6=Sunday)
        span_days: Number of days the pattern spans
        pattern: Dict mapping day_offset (0 to span_days-1) to service_id
    """
    def __init__(self, name: str, start_weekday: int, span_days: int, pattern: dict = None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name.strip()
        self.start_weekday = start_weekday  # 0=Monday, 6=Sunday
        self.span_days = span_days
        self.pattern = pattern or {}  # {day_offset: service_id}
    
    def get_service(self, day_offset: int):
        """Get service_id for a specific day offset in the pattern."""
        return self.pattern.get(day_offset)
    
    def set_service(self, day_offset: int, service_id: str):
        """Set service_id for a specific day offset in the pattern."""
        if service_id is None:
            self.pattern.pop(day_offset, None)
        else:
            self.pattern[day_offset] = service_id
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_weekday": self.start_weekday,
            "span_days": self.span_days,
            "pattern": self.pattern
        }
    
    @staticmethod
    def from_dict(data):
        raw_pattern = data.get("pattern", {})
        # Convert keys back to integers (JSON mandates string keys)
        pattern = {int(k): v for k, v in raw_pattern.items() if str(k).isdigit()}
        
        return Schema(
            name=data["name"],
            start_weekday=data["start_weekday"],
            span_days=data["span_days"],
            pattern=pattern,
            id=data.get("id")
        )

class SchemaAssignment:
    """
    Represents the assignment of a schema to a person.
    
    Attributes:
        person_id: ID of the person
        schema_id: ID of the schema
        repeat_mode: "always" or "limited"
        repeat_months: Number of months to repeat (only used if repeat_mode="limited")
        start_year: Year when assignment was created
        start_month: Month when assignment was created
        overwrite_existing: Whether to overwrite existing services when applying
    """
    def __init__(self, person_id: str, schema_id: str, repeat_mode: str = "always", 
                 repeat_months: int = 1, start_year: int = None, start_month: int = None,
                 overwrite_existing: bool = True):
        self.person_id = person_id
        self.schema_id = schema_id
        self.repeat_mode = repeat_mode  # "always" or "limited"
        self.repeat_months = repeat_months
        self.start_year = start_year
        self.start_month = start_month
        self.overwrite_existing = overwrite_existing
    
    def should_apply_to_month(self, year: int, month: int) -> bool:
        """Check if this assignment should apply to the given month."""
        if self.repeat_mode == "always":
            # Only apply to current and future months
            if self.start_year is None or self.start_month is None:
                return True
            
            current_period = year * 12 + month
            start_period = self.start_year * 12 + self.start_month
            return current_period >= start_period
        
        else:  # limited
            if self.start_year is None or self.start_month is None:
                return False
            
            current_period = year * 12 + month
            start_period = self.start_year * 12 + self.start_month
            end_period = start_period + self.repeat_months - 1
            
            return start_period <= current_period <= end_period
    
    def to_dict(self):
        return {
            "person_id": self.person_id,
            "schema_id": self.schema_id,
            "repeat_mode": self.repeat_mode,
            "repeat_months": self.repeat_months,
            "start_year": self.start_year,
            "start_month": self.start_month,
            "overwrite_existing": self.overwrite_existing
        }
    
    @staticmethod
    def from_dict(data):
        return SchemaAssignment(
            person_id=data["person_id"],
            schema_id=data["schema_id"],
            repeat_mode=data.get("repeat_mode", "always"),
            repeat_months=data.get("repeat_months", 1),
            start_year=data.get("start_year"),
            start_month=data.get("start_month"),
            overwrite_existing=data.get("overwrite_existing", True)
        )

class MonthData:
    def __init__(self, year : int, month : int):
        self.year = year
        self.month = month
        # key : (person.id, day)
        self.assignments = {}
        self.holidays = set()
        self.comments = {} # person_id -> str
        self.notes = {} # (person_id, day) -> str

    def get_service(self, person_id, day):
        return self.assignments.get((person_id, day))

    def set_service(self, person_id, day, service_id):
        if service_id is None :
            self.assignments.pop((person_id, day), None)
            # When clearing service, should we clear note? 
            # User said "right click deletes it", implying deleting service deletes note.
            # I will assume yes.
            self.notes.pop((person_id, day), None)
        
        else :
            self.assignments[(person_id, day)] = service_id

    def get_comment(self, person_id):
        return self.comments.get(person_id, "")

    def set_comment(self, person_id, text):
        if not text:
            self.comments.pop(person_id, None)
        else:
            self.comments[person_id] = text

    def get_note(self, person_id, day):
        return self.notes.get((person_id, day))

    def set_note(self, person_id, day, text):
        if not text:
            self.notes.pop((person_id, day), None)
        else:
            self.notes[(person_id, day)] = text

    def toggle_holiday(self, day: int):
        if day in self.holidays:
            self.holidays.remove(day)
        else:
            self.holidays.add(day)

    def to_dict(self):
        return{
            "year": self.year,
            "month": self.month,
            "assignments": {
                f"{person_id}_{day}": service_id
                for (person_id, day), service_id in self.assignments.items()
            },
            "notes": {
                f"{person_id}_{day}": text
                for (person_id, day), text in self.notes.items()
            },
            "holidays": list(self.holidays),
            "comments": self.comments
        }

    @staticmethod
    def from_dict(data):
        month = MonthData(data["year"], data["month"])
        month.assignments = {
            tuple(k.split("_")[0:2] if len(k.split("_")) == 2 else (k.rpartition('_')[0], k.rpartition('_')[2])): v
            for k, v in data["assignments"].items()
        }
        # Handle notes
        raw_notes = data.get("notes", {})
        month.notes = {
             tuple(k.split("_")[0:2] if len(k.split("_")) == 2 else (k.rpartition('_')[0], k.rpartition('_')[2])): v
             for k, v in raw_notes.items()
        }
        
        # Correction for key parsing: person_id can contain underscores? 
        # The key is f"{person_id}_{day}". Day is int.
        # My parsing logic above is a bit duplicated and potentially fragile if person_id has underscores.
        # But let's look at existing logic for assignments.
        # Existing logic was just: 
        # month.assignments = { } ... wait, I need to see the existing parsing logic.
        
        month.holidays = set(data["holidays"])
        month.comments = data.get("comments", {})
        
        # Post-process keys to convert day to int
        # The keys are (person_id, str_day). We need (person_id, int_day).
        month.assignments = {
            (pid, int(d)): val 
            for (pid, d), val in month.assignments.items()
        }
        month.notes = {
            (pid, int(d)): val 
            for (pid, d), val in month.notes.items()
        }

        return month
