"""
Undo/Redo system for MShift.

Provides a command pattern implementation for undoable actions.
"""

from typing import List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import copy


@dataclass
class UndoableAction:
    """
    Represents a single undoable action.
    
    Attributes:
        name: Human-readable description of the action
        undo_data: Data needed to undo the action
        redo_data: Data needed to redo the action
        timestamp: When the action was performed
        action_type: Type of action (for filtering/grouping)
    """
    name: str
    undo_data: Any
    redo_data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    action_type: str = "generic"


class UndoManager:
    """
    Manages undo/redo history for the application.
    
    Uses the Command pattern to store reversible actions.
    """
    
    def __init__(self, max_history: int = 20):
        """
        Initialize the undo manager.
        
        Args:
            max_history: Maximum number of actions to keep in history
        """
        self.max_history = max_history
        self.undo_stack: List[UndoableAction] = []
        self.redo_stack: List[UndoableAction] = []
        self._enabled = True
    
    def push(self, action: UndoableAction):
        """
        Add a new action to the undo stack.
        
        Args:
            action: The action to add
        """
        if not self._enabled:
            return
        
        # Add to undo stack
        self.undo_stack.append(action)
        
        # Clear redo stack (new action invalidates redo history)
        self.redo_stack.clear()
        
        # Trim history if needed
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0
    
    def undo(self) -> Optional[UndoableAction]:
        """
        Undo the last action.
        
        Returns:
            The action that was undone, or None if nothing to undo
        """
        if not self.can_undo():
            return None
        
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        
        return action
    
    def redo(self) -> Optional[UndoableAction]:
        """
        Redo the last undone action.
        
        Returns:
            The action that was redone, or None if nothing to redo
        """
        if not self.can_redo():
            return None
        
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        
        return action
    
    def clear(self):
        """Clear all undo/redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of the next undo action."""
        if self.can_undo():
            return self.undo_stack[-1].name
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of the next redo action."""
        if self.can_redo():
            return self.redo_stack[-1].name
        return None
    
    def disable(self):
        """Temporarily disable undo recording."""
        self._enabled = False
    
    def enable(self):
        """Re-enable undo recording."""
        self._enabled = True
    
    def get_history_size(self) -> int:
        """Get current size of undo history."""
        return len(self.undo_stack)
    
    def get_redo_size(self) -> int:
        """Get current size of redo history."""
        return len(self.redo_stack)


class ScheduleUndoManager(UndoManager):
    """
    Specialized undo manager for schedule operations.
    
    Handles common schedule actions like:
    - Service assignments
    - Person additions/deletions
    - Section modifications
    """
    
    def record_service_change(self, year: int, month: int, day: int, 
                             person_id: str, old_service_id: Optional[str], 
                             new_service_id: Optional[str]):
        """
        Record a service assignment change.
        
        Args:
            year, month, day: Date of the change
            person_id: ID of the person
            old_service_id: Previous service ID (None if empty)
            new_service_id: New service ID (None if cleared)
        """
        action = UndoableAction(
            name=f"Change service on {year}-{month:02d}-{day:02d}",
            undo_data={
                "year": year,
                "month": month,
                "day": day,
                "person_id": person_id,
                "service_id": old_service_id
            },
            redo_data={
                "year": year,
                "month": month,
                "day": day,
                "person_id": person_id,
                "service_id": new_service_id
            },
            action_type="service_change"
        )
        self.push(action)
    
    def record_person_add(self, person_data: dict):
        """
        Record adding a person.
        
        Args:
            person_data: Dictionary containing person data
        """
        action = UndoableAction(
            name=f"Add person: {person_data.get('prenom')} {person_data.get('nom')}",
            undo_data={"person_id": person_data.get("id")},
            redo_data={"person_data": copy.deepcopy(person_data)},
            action_type="person_add"
        )
        self.push(action)
    
    def record_person_delete(self, person_data: dict):
        """
        Record deleting a person.
        
        Args:
            person_data: Dictionary containing person data
        """
        action = UndoableAction(
            name=f"Delete person: {person_data.get('prenom')} {person_data.get('nom')}",
            undo_data={"person_data": copy.deepcopy(person_data)},
            redo_data={"person_id": person_data.get("id")},
            action_type="person_delete"
        )
        self.push(action)
    
    def record_person_update(self, person_id: str, old_data: dict, new_data: dict):
        """
        Record updating a person's details.
        
        Args:
            person_id: ID of the person
            old_data: Dictionary containing old person data
            new_data: Dictionary containing new person data
        """
        action = UndoableAction(
            name=f"Update person: {new_data.get('prenom')} {new_data.get('nom')}",
            undo_data={"person_id": person_id, "data": old_data},
            redo_data={"person_id": person_id, "data": new_data},
            action_type="person_update"
        )
        self.push(action)
    
    def record_section_sort(self, section_id: str, section_label: str, 
                           old_order: List[str], new_order: List[str]):
        """
        Record sorting a section.
        
        Args:
            section_id: ID of the section
            section_label: Label of the section
            old_order: Previous order of person IDs
            new_order: New order of person IDs
        """
        action = UndoableAction(
            name=f"Sort section: {section_label}",
            undo_data={
                "section_id": section_id,
                "people_ids": old_order.copy()
            },
            redo_data={
                "section_id": section_id,
                "people_ids": new_order.copy()
            },
            action_type="section_sort"
        )
        self.push(action)
    
    def record_section_rename(self, section_id: str, old_label: str, new_label: str):
        """
        Record renaming a section.
        
        Args:
            section_id: ID of the section
            old_label: Previous label
            new_label: New label
        """
        action = UndoableAction(
            name=f"Rename section: {old_label} → {new_label}",
            undo_data={
                "section_id": section_id,
                "label": old_label
            },
            redo_data={
                "section_id": section_id,
                "label": new_label
            },
            action_type="section_rename"
        )
        self.push(action)
    
    def record_person_move(self, person_id: str, person_name: str,
                          old_section_id: str, new_section_id: str,
                          old_index: int, new_index: int):
        """
        Record moving a person to a different section.
        
        Args:
            person_id: ID of the person
            person_name: Name of the person (for display)
            old_section_id: Previous section ID
            new_section_id: New section ID
            old_index: Previous index in old section
            new_index: New index in new section
        """
        action = UndoableAction(
            name=f"Move person: {person_name}",
            undo_data={
                "person_id": person_id,
                "section_id": old_section_id,
                "index": old_index
            },
            redo_data={
                "person_id": person_id,
                "section_id": new_section_id,
                "index": new_index
            },
            action_type="person_move"
        )
        self.push(action)
    
    def record_bulk_service_change(self, description: str, changes: List[dict]):
        """
        Record a bulk service assignment change (e.g., clear month).
        
        Args:
            description: Human-readable description
            changes: List of dicts, each containing:
                     {year, month, day, person_id, old_service_id, new_service_id}
        """
        if not changes:
            return
            
        undo_changes = []
        redo_changes = []
        
        for change in changes:
            undo_changes.append({
                "year": change["year"],
                "month": change["month"],
                "day": change["day"],
                "person_id": change["person_id"],
                "service_id": change["old_service_id"]
            })
            redo_changes.append({
                "year": change["year"],
                "month": change["month"],
                "day": change["day"],
                "person_id": change["person_id"],
                "service_id": change["new_service_id"]
            })
            
        action = UndoableAction(
            name=description,
            undo_data={"changes": undo_changes},
            redo_data={"changes": redo_changes},
            action_type="bulk_service_change"
        )
        self.push(action)
    
    def record_schema_assignment_change(self, description: str, 
                                      old_assignments: List[dict], 
                                      new_assignments: List[dict]):
        """
        Record changes to schema assignments.
        
        Args:
            description: Description of the change
            old_assignments: List of assignment dicts (state before)
            new_assignments: List of assignment dicts (state after)
        """
        action = UndoableAction(
            name=description,
            undo_data={"assignments": old_assignments},
            redo_data={"assignments": new_assignments},
            action_type="schema_assignment_change"
        )
        self.push(action)
