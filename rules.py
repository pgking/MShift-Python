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
        
def evaluate_day_service_counts(
        month_data,
        people,
        services_by_id,
        year: int,
        month: int
    ):
    """
    Returns a list of DayServiceViolation for the given month.
    """
    violations = []

    # Build lookup : service_id -> service name
    services_name_by_id = {
        service.id: service.name
        for service in services_by_id.values()
    }

    # Determine number of days in the month from assignments
    _, num_days = calendar.monthrange(year, month)
    days = range(1, num_days + 1)

    for day in sorted(days):
        jour_count = 0
        nuit_count = 0

        for person in people:
            service_id = month_data.get_service(person.id, day)
            if service_id is None:
                continue
            
            service_name = services_name_by_id.get(service_id)
            if service_name == "Jour":
                jour_count += 1
            elif service_name == "Nuit":
                nuit_count += 1

        # Jour rule
        if jour_count != 3 :
            severity = Severity.MISSING if jour_count < 3 else Severity.EXCESS
            violations.append(
                DayServiceViolation(
                    year=year,
                    month=month,
                    day=day,
                    service_kind=ServiceKind.JOUR,
                    severity=severity,
                    count=jour_count
                )
            )
        
        # Nuit rule
        if nuit_count != 3:
            severity = Severity.MISSING if nuit_count < 3 else Severity.EXCESS
            violations.append(
                DayServiceViolation(
                    year=year,
                    month=month,
                    day=day,
                    service_kind=ServiceKind.NUIT,
                    severity=severity,
                    count=nuit_count
                )
            )

    return violations
                
