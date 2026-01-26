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

class MonthData:
    def __init__(self, year : int, month : int):
        self.year = year
        self.month = month
        # key : (person.id, day)
        self.assignments = {}
        self.holidays = set()
        self.comments = {} # person_id -> str

    def get_service(self, person_id, day):
        return self.assignments.get((person_id, day))

    def set_service(self, person_id, day, service_id):
        if service_id is None :
            self.assignments.pop((person_id, day), None)
        
        else :
            self.assignments[(person_id, day)] = service_id

    def get_comment(self, person_id):
        return self.comments.get(person_id, "")

    def set_comment(self, person_id, text):
        if not text:
            self.comments.pop(person_id, None)
        else:
            self.comments[person_id] = text

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
            "holidays": list(self.holidays),
            "comments": self.comments
        }

    @staticmethod
    def from_dict(data):
        month = MonthData(data["year"], data["month"])
        month.assignments = {
            (pid, int(day)): service_id
            for k, service_id in data["assignments"].items()
            for pid, day in [k.split("_")]
        }
        month.holidays = set(data.get("holidays", []))
        month.comments = data.get("comments", {})
        return month
        