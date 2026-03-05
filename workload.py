import calendar

from dataclasses import dataclass
from PyQt5.QtGui import QColor

from models import Person

@dataclass
class MonthlyWorkSummary:
    worked: float
    expected: float

    @property
    def ratio(self) -> float:
        return 0 if self.expected == 0 else self.worked / self.expected
    
class WorkloadCalculator:
    def __init__(self, main_window):
        self.main_window = main_window

    @property
    def schedule(self):
        return self.main_window.schedule
    
    @property
    def services(self):
        return self.main_window.services

    def expected_hours_for_month(self, person: Person, year: int, month: int) -> float:
        weekdays = 0
        days_in_month = calendar.monthrange(year, month)[1]

        for day in range(1, days_in_month + 1):
            if calendar.weekday(year, month, day) < 5:
                weekdays += 1

        base_hours = 7 * weekdays * (person.percentage / 100.0)

        key = (year, month)
        holidays = self.schedule.get(key).holidays if key in self.schedule else set()
        holiday_hours = 7 * len(holidays)

        return base_hours - holiday_hours
    
    def worked_hours_for_person(self, person: Person, year: int, month: int) -> float:
        key = (year, month)
        if key not in self.schedule:
            return 0.0
        
        month_data = self.schedule[key]
        total_hours = 0.0

        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            service_id = month_data.get_service(person.id, day)
            if service_id is None:
                continue

            service = next((s for s in self.services if s.id == service_id), None)
            if service:
                if service.id == "builtin_split":
                    # Split cell: half of AM hours + half of PM hours
                    split_info = month_data.get_split(person.id, day)
                    if split_info:
                        am_svc = next((s for s in self.services if s.id == split_info.get("am")), None) if split_info.get("am") else None
                        pm_svc = next((s for s in self.services if s.id == split_info.get("pm")), None) if split_info.get("pm") else None
                        if am_svc:
                            total_hours += am_svc.get_duration(year, month, day, month_data.holidays, person_percentage=person.percentage) / 2
                        if pm_svc:
                            total_hours += pm_svc.get_duration(year, month, day, month_data.holidays, person_percentage=person.percentage) / 2
                else:
                    total_hours += service.get_duration(year, month, day, month_data.holidays, person_percentage=person.percentage)

        return total_hours
    
    def monthly_summary(self, person: Person, year: int, month: int) -> MonthlyWorkSummary:
        return MonthlyWorkSummary(
            worked=self.worked_hours_for_person(person, year, month),
            expected=self.expected_hours_for_month(person, year, month)
        )
    
    def status_color(self, ratio: float) -> QColor:
        if ratio < 0.9:
            return QColor(170, 200, 255)  # Light blue
        
        elif ratio > 1.1:
            return QColor(255, 180, 180)  # Light red
        
        else:
            return QColor(180, 230, 180)  # Light green