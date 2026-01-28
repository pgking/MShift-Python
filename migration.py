"""
Data migration utilities for MShift.

Handles migration from old data formats to new formats,
ensuring backward compatibility with existing files.
"""

from typing import Dict, Any, List
from models import Section


def needs_migration(data: Dict[str, Any]) -> bool:
    """
    Check if data needs migration to the new section-based format.
    
    Args:
        data: Loaded data dictionary
        
    Returns:
        True if migration is needed, False otherwise
    """
    # If sections key exists and is not empty, already migrated
    if "sections" in data and data["sections"]:
        return False
    
    # If rows exist but no sections, needs migration
    if "rows" in data and data["rows"]:
        return True
    
    # Empty file or new file, no migration needed
    return False


def migrate_to_sections(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old row-based format to new section-based format.
    
    This function:
    1. Extracts sections from the old 'rows' structure
    2. Creates Section objects with ordered people_ids
    3. Assigns section_id to each Person
    4. Preserves the original row order
    
    Args:
        data: Data dictionary in old format
        
    Returns:
        Migrated data dictionary with sections
    """
    if not needs_migration(data):
        return data
    
    print("🔄 Migrating file to new section-based format...")
    
    sections = []
    current_section = None
    people_by_id = {p["id"]: p for p in data.get("people", [])}
    
    # Parse rows to extract sections and assign people
    for row in data.get("rows", []):
        if row.get("type") == "section":
            # Create a new section
            section_data = {
                "id": row.get("id", row.get("label", "unknown")),
                "label": row.get("label", "Unknown Section"),
                "people_ids": [],
                "is_collapsed": False
            }
            current_section = section_data
            sections.append(current_section)
            
        elif row.get("type") == "person" and current_section is not None:
            # Add person to current section
            person_id = row.get("person_id")
            if person_id:
                current_section["people_ids"].append(person_id)
                
                # Update person's section_id
                if person_id in people_by_id:
                    people_by_id[person_id]["section_id"] = current_section["id"]
    
    # Handle people without a section (shouldn't happen, but be safe)
    # Create a default section for orphaned people
    orphaned_people = [
        pid for pid, person in people_by_id.items()
        if person.get("section_id") is None
    ]
    
    if orphaned_people:
        print(f"⚠️  Found {len(orphaned_people)} people without sections, adding to default section")
        default_section = {
            "id": "default",
            "label": "Non classé",
            "people_ids": orphaned_people,
            "is_collapsed": False
        }
        sections.insert(0, default_section)  # Add at the beginning
        
        # Update orphaned people's section_id
        for person_id in orphaned_people:
            people_by_id[person_id]["section_id"] = "default"
    
    # Update data with sections
    data["sections"] = sections
    data["people"] = list(people_by_id.values())
    
    print(f"✅ Migration complete: {len(sections)} sections, {len(people_by_id)} people")
    
    return data


def rebuild_rows_from_sections(sections: List[Section], people_ids_order: List[str] = None) -> List[Dict[str, Any]]:
    """
    Rebuild the rows structure from sections.
    
    This maintains compatibility with the UI which expects rows.
    
    Args:
        sections: List of Section objects
        people_ids_order: Optional custom order for people (for future use)
        
    Returns:
        List of row dictionaries for UI rendering
    """
    rows = []
    
    for section in sections:
        # Add section header row
        rows.append({
            "type": "section",
            "id": section.id,
            "label": section.label
        })
        
        # Add person rows in section order
        for person_id in section.people_ids:
            rows.append({
                "type": "person",
                "person_id": person_id
            })
    
    return rows


def validate_section_integrity(data: Dict[str, Any]) -> List[str]:
    """
    Validate that sections and people are properly linked.
    
    Args:
        data: Data dictionary with sections
        
    Returns:
        List of validation warnings (empty if all OK)
    """
    warnings = []
    
    people_by_id = {p["id"]: p for p in data.get("people", [])}
    sections_by_id = {s["id"]: s for s in data.get("sections", [])}
    
    # Check 1: All people in sections exist
    for section in data.get("sections", []):
        for person_id in section.get("people_ids", []):
            if person_id not in people_by_id:
                warnings.append(f"Section '{section['label']}' references non-existent person: {person_id}")
    
    # Check 2: All people have valid section_id
    for person in data.get("people", []):
        section_id = person.get("section_id")
        if section_id and section_id not in sections_by_id:
            warnings.append(f"Person '{person.get('prenom', '')} {person.get('nom', '')}' has invalid section_id: {section_id}")
    
    # Check 3: People appear in their assigned section
    for person in data.get("people", []):
        person_id = person["id"]
        section_id = person.get("section_id")
        
        if section_id:
            section = sections_by_id.get(section_id)
            if section and person_id not in section.get("people_ids", []):
                warnings.append(f"Person '{person.get('prenom', '')} {person.get('nom', '')}' has section_id '{section_id}' but is not in that section's people_ids")
    
    return warnings
