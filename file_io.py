import json

from models import Person, Service, MonthData, Section
from data_validator import validate_and_sanitize, ValidationError
from backup_manager import create_backup
from migration import needs_migration, migrate_to_sections, validate_section_integrity

# Maximum number of backup files to keep
MAX_BACKUP_FILES = 5


def save_schedule(controller, path):
    """
    Save schedule to file with automatic backup creation.
    
    Args:
        controller: ScheduleController instance
        path: Path to save the schedule file
    
    Returns:
        Path to the created backup file, or None if no backup was created
    """
    # Create backup before saving (if file exists)
    backup_path = create_backup(path, MAX_BACKUP_FILES)
    
    data = build_save_data(controller)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent = 2)
    
    return backup_path


def build_save_data(controller):
    """
    Build complete schedule file data.
    """
    return {
        "people": [p.to_dict() for p in controller.people],
        "services": [s.to_dict() for s in controller.services],
        "sections": [s.to_dict() for s in controller.sections],
        "rows": controller.rows,
        "schedule": {
            f"{year}_{month}": controller.schedule[(year, month)].to_dict()
            for year, month in controller.schedule
        }
    }

def load_schedule(controller, path):
    """
    Load schedule from file with data validation and automatic migration.
    
    Args:
        controller: ScheduleController instance
        path: Path to the schedule file to load
    
    Raises:
        ValidationError: If the loaded data is invalid
        json.JSONDecodeError: If the file is not valid JSON
        FileNotFoundError: If the file doesn't exist
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Check if migration is needed
    if needs_migration(data):
        data = migrate_to_sections(data)
        
        # Validate section integrity after migration
        warnings = validate_section_integrity(data)
        if warnings:
            print("⚠️  Section validation warnings:")
            for warning in warnings:
                print(f"   - {warning}")
    
    # Validate data before applying
    validated_data = validate_and_sanitize(data)
    
    apply_loaded_data(controller, validated_data)



def apply_loaded_data(controller, data):
    """
    Apply loaded schedule data to Controller.
    """
    # Rebuild people and services
    controller.people = [Person(**p) for p in data["people"]]
    controller.services = [Service(**s) for s in data ["services"]]
    
    # Ensure hidden "Unknown" service exists (for backward compatibility or new saves)
    if not any(s.id == "unknown" for s in controller.services):
        controller.services.append(
            Service("Inconnu", "?", 0, "#FF5555", id="unknown", is_visible=False)
        )
    
    # Ensure builtin services (Notes)
    controller.ensure_builtin_services()
    
    # Load sections
    controller.sections = [Section.from_dict(s) for s in data.get("sections", [])]

    # Rebuild row (sections and ordering)
    controller.rows = data.get("rows", [])

    # Rebuild Schedule
    controller.schedule = {}
    for key, month_dict in data["schedule"].items():
        controller.schedule[tuple(map(int, key.split("_")))] = MonthData.from_dict(month_dict)

