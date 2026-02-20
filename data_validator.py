"""
Data validation utilities for MShift.

Provides validation for loaded data to ensure integrity and prevent corruption.
"""
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


def validate_person_data(person_dict: Dict[str, Any]) -> None:
    """
    Validate person data structure.
    
    Args:
        person_dict: Dictionary containing person data
    
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["id", "prenom", "nom", "percentage"]
    
    for field in required_fields:
        if field not in person_dict:
            raise ValidationError(f"Person missing required field: {field}")
    
    # Validate types
    if not isinstance(person_dict["id"], str) or not person_dict["id"]:
        raise ValidationError("Person id must be a non-empty string")
    
    if not isinstance(person_dict["prenom"], str):
        raise ValidationError("Person prenom must be a string")
    
    if not isinstance(person_dict["nom"], str) or not person_dict["nom"]:
        raise ValidationError("Person nom must be a non-empty string")
    
    if not isinstance(person_dict["percentage"], (int, float)):
        raise ValidationError("Person percentage must be a number")
    
    if not (0 <= person_dict["percentage"] <= 100):
        raise ValidationError(f"Person percentage must be between 0 and 100, got {person_dict['percentage']}")


def validate_service_data(service_dict: Dict[str, Any]) -> None:
    """
    Validate service data structure.
    
    Args:
        service_dict: Dictionary containing service data
    
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["id", "name", "short_name", "hours", "color_hex"]
    
    for field in required_fields:
        if field not in service_dict:
            raise ValidationError(f"Service missing required field: {field}")
    
    # Validate types
    if not isinstance(service_dict["id"], str) or not service_dict["id"]:
        raise ValidationError("Service id must be a non-empty string")
    
    if not isinstance(service_dict["name"], str) or not service_dict["name"]:
        raise ValidationError("Service name must be a non-empty string")
    
    if not isinstance(service_dict["short_name"], str):
        raise ValidationError("Service short_name must be a string")
    
    if not isinstance(service_dict["hours"], (int, float)):
        raise ValidationError("Service hours must be a number")
    
    if service_dict["hours"] < 0:
        raise ValidationError(f"Service hours must be non-negative, got {service_dict['hours']}")
    
    if not isinstance(service_dict["color_hex"], str):
        raise ValidationError("Service color_hex must be a string")
    
    # Validate color format (basic check)
    color = service_dict["color_hex"]
    if not (color.startswith("#") and len(color) in (4, 7)):
        raise ValidationError(f"Service color_hex must be in format #RGB or #RRGGBB, got {color}")


def validate_month_data(month_dict: Dict[str, Any]) -> None:
    """
    Validate month data structure.
    
    Args:
        month_dict: Dictionary containing month data
    
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["year", "month", "assignments", "holidays"]
    
    for field in required_fields:
        if field not in month_dict:
            raise ValidationError(f"MonthData missing required field: {field}")
    
    # Validate year and month
    if not isinstance(month_dict["year"], int):
        raise ValidationError("MonthData year must be an integer")
    
    if not (1900 <= month_dict["year"] <= 2100):
        raise ValidationError(f"MonthData year must be between 1900 and 2100, got {month_dict['year']}")
    
    if not isinstance(month_dict["month"], int):
        raise ValidationError("MonthData month must be an integer")
    
    if not (1 <= month_dict["month"] <= 12):
        raise ValidationError(f"MonthData month must be between 1 and 12, got {month_dict['month']}")
    
    # Validate assignments
    if not isinstance(month_dict["assignments"], dict):
        raise ValidationError("MonthData assignments must be a dictionary")
    
    # Validate holidays
    if not isinstance(month_dict["holidays"], list):
        raise ValidationError("MonthData holidays must be a list")
    
    for holiday in month_dict["holidays"]:
        if not isinstance(holiday, int):
            raise ValidationError(f"Holiday must be an integer day number, got {holiday}")
        if not (1 <= holiday <= 31):
            raise ValidationError(f"Holiday day must be between 1 and 31, got {holiday}")


def validate_schedule_file(data: Dict[str, Any]) -> None:
    """
    Validate complete schedule file data.
    
    Args:
        data: Dictionary containing complete schedule data
    
    Raises:
        ValidationError: If validation fails
    """
    required_fields = ["people", "services", "schedule"]
    
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Schedule file missing required field: {field}")
    
    # Validate people
    if not isinstance(data["people"], list):
        raise ValidationError("Schedule 'people' must be a list")
    
    for i, person in enumerate(data["people"]):
        try:
            validate_person_data(person)
        except ValidationError as e:
            raise ValidationError(f"Invalid person at index {i}: {e}")
    
    # Validate services
    if not isinstance(data["services"], list):
        raise ValidationError("Schedule 'services' must be a list")
    
    for i, service in enumerate(data["services"]):
        try:
            validate_service_data(service)
        except ValidationError as e:
            raise ValidationError(f"Invalid service at index {i}: {e}")
    
    # Validate schedule
    if not isinstance(data["schedule"], dict):
        raise ValidationError("Schedule 'schedule' must be a dictionary")
    
    for key, month_data in data["schedule"].items():
        try:
            # Validate key format
            if not isinstance(key, str) or "_" not in key:
                raise ValidationError(f"Invalid schedule key format: {key}")
            
            validate_month_data(month_data)
        except ValidationError as e:
            raise ValidationError(f"Invalid month data for key '{key}': {e}")
    
    # Validate rows if present
    if "rows" in data:
        if not isinstance(data["rows"], list):
            raise ValidationError("Schedule 'rows' must be a list")


def validate_and_sanitize(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize loaded data.
    
    This function validates the data structure and applies any necessary
    sanitization or migration for backward compatibility.
    
    Args:
        data: Dictionary containing schedule data
    
    Returns:
        Sanitized data dictionary
    
    Raises:
        ValidationError: If validation fails
    """
    # Apply sanitization / migrations for backward compatibility BEFORE validation
    if "schedule" in data and isinstance(data["schedule"], dict):
        for key, month_data in data["schedule"].items():
            if isinstance(month_data, dict):
                # Migration: add missing 'holidays' field (added after initial release)
                if "holidays" not in month_data:
                    month_data["holidays"] = []

    # Validate the structure
    validate_schedule_file(data)
    
    # Return the validated data
    return data
