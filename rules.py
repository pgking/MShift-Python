from dataclasses import dataclass
from enum import Enum
import calendar

class ServiceKind(Enum):
    JOUR = "Jour"
    NUIT = "Nuit"


class Severity(Enum):
    MISSING = "missing"
    EXCESS = "excess"


@dataclass(frozen=True)
class DayServiceViolation:
    year: int
    month: int
    day: int

    service_kind: ServiceKind
    severity: Severity

    count: int
    expected: int = 3

    def tooltip(self) -> str:
        if self.severity == Severity.MISSING:
            return (
                f"{self.service_kind.value} missing : "
                f"{self.expected - self.count} "
                f"(expected {self.expected}, got {self.count})"
            )
        else:
            return (
                f"Too many {self.service_kind.value} : "
                f"{self.count - self.expected} "
                f"(expected {self.expected}, got {self.count})"
            )
        
from abc import ABC, abstractmethod
from typing import List

class Rule(ABC):
    """Base class for all scheduling rules."""
    @abstractmethod
    def evaluate(self, month_data, people, services_by_id, year, month) -> List[DayServiceViolation]:
        pass

class StaffingRule(Rule):
    """Rule that checks if a minimum/maximum number of people are assigned to a service."""
    def __init__(self, service_name: str, expected_count: int, service_kind: ServiceKind):
        self.service_name = service_name
        self.expected_count = expected_count
        self.service_kind = service_kind

    def evaluate(self, month_data, people, services_by_id, year, month) -> List[DayServiceViolation]:
        violations = []
        _, num_days = calendar.monthrange(year, month)
        
        for day in range(1, num_days + 1):
            count = 0
            for person in people:
                service_id = month_data.get_service(person.id, day)
                if service_id and services_by_id.get(service_id).name == self.service_name:
                    count += 1
            
            if count != self.expected_count:
                severity = Severity.MISSING if count < self.expected_count else Severity.EXCESS
                violations.append(
                    DayServiceViolation(
                        year=year,
                        month=month,
                        day=day,
                        service_kind=self.service_kind,
                        severity=severity,
                        count=count,
                        expected=self.expected_count
                    )
                )
        return violations

# Default rule set
DEFAULT_RULES = [
    StaffingRule("Jour", 3, ServiceKind.JOUR),
    StaffingRule("Nuit", 3, ServiceKind.NUIT),
]

def evaluate_rules(
        rules: List[Rule],
        month_data,
        people,
        services_by_id,
        year: int,
        month: int
    ) -> List[DayServiceViolation]:
    """
    Evaluates a list of rules and returns all violations.
    """
    all_violations = []
    for rule in rules:
        all_violations.extend(rule.evaluate(month_data, people, services_by_id, year, month))
    return all_violations

# Legacy compatibility
def evaluate_day_service_counts(month_data, people, services_by_id, year, month):
    return evaluate_rules(DEFAULT_RULES, month_data, people, services_by_id, year, month)
                
