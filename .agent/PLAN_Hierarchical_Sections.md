# Implementation Plan: Hierarchical Sections Feature

**Feature:** Make sections actual containers that hold people, with optional alphabetical sorting while maintaining drag-and-drop flexibility.

**Version:** 1.0.7 (next release)  
**Created:** 2026-01-28  
**Status:** Planning

---

## 📋 Current State Analysis

### Current Implementation
- Sections are defined in `main.py` as a list of dictionaries
- People are stored separately in `controller.people`
- `controller.rows` contains both section markers and person references
- Sections are visual separators, not actual containers
- No relationship between sections and people in the data model

### Current Data Structure
```python
# In main.py
self.sections = [
    {"id": "PMSI", "label": "PMSI"},
    {"id": "Suites", "label": "Suites de couches"},
    # ... etc
]

# In controller
self.people = [Person(...), Person(...), ...]
self.rows = [
    {"type": "section", "id": "PMSI", "label": "PMSI"},
    {"type": "person", "person_id": "uuid-123"},
    {"type": "person", "person_id": "uuid-456"},
    {"type": "section", "id": "Suites", "label": "Suites de couches"},
    # ... etc
]
```

---

## 🎯 Desired State

### New Data Model
People should belong to sections, with sections being first-class containers:

```python
# New Section model
class Section:
    def __init__(self, id, label, people_ids=None):
        self.id = id
        self.label = label
        self.people_ids = people_ids or []  # Ordered list of person IDs
        self.is_collapsed = False  # For future collapsible sections
    
    def add_person(self, person_id, index=None):
        """Add person at specific index or end"""
        
    def remove_person(self, person_id):
        """Remove person from section"""
        
    def reorder_people(self, from_index, to_index):
        """Reorder people within section"""
        
    def sort_people_alphabetically(self, people_list):
        """Sort people in this section alphabetically"""

# In Person model - add section reference
class Person:
    def __init__(self, ..., section_id=None):
        # ... existing fields
        self.section_id = section_id  # Which section this person belongs to
```

---

## 🔧 Implementation Steps

### Phase 1: Data Model Changes (Foundation)

#### Step 1.1: Create Section Model
**File:** `models.py`
- [ ] Create `Section` class with:
  - `id`, `label`, `people_ids` (ordered list)
  - `is_collapsed` (for future feature)
  - `add_person()`, `remove_person()`, `reorder_people()`
  - `sort_alphabetically()` method
  - `to_dict()` and `from_dict()` for serialization

#### Step 1.2: Update Person Model
**File:** `models.py`
- [ ] Add `section_id` field to `Person.__init__()`
- [ ] Update `Person.to_dict()` to include `section_id`
- [ ] Update `Person` deserialization to handle `section_id`

#### Step 1.3: Update Controller
**File:** `controller.py`
- [ ] Add `self.sections = []` (list of Section objects)
- [ ] Update `to_dict()` to serialize sections
- [ ] Update `from_dict()` to deserialize sections
- [ ] Add methods:
  - `get_section_by_id(section_id)`
  - `get_people_in_section(section_id)` - returns ordered list
  - `move_person_to_section(person_id, new_section_id, index=None)`
  - `reorder_person_in_section(person_id, new_index)`

---

### Phase 2: Migration & Backward Compatibility

#### Step 2.1: Data Migration
**File:** `file_io.py` or new `migration.py`
- [ ] Create migration function to convert old format to new:
  - Parse old `rows` structure
  - Create Section objects from section markers
  - Assign people to sections based on their position in rows
  - Set `section_id` on each Person
- [ ] Handle files without sections (assign to default section)
- [ ] Add version field to save format for future migrations

#### Step 2.2: Backward Compatibility
**File:** `file_io.py`
- [ ] Detect old vs new file format
- [ ] Auto-migrate old files on load
- [ ] Show migration notice to user (optional)

---

### Phase 3: UI Changes

#### Step 3.1: Update Row Building Logic
**File:** `main.py` or new `row_builder.py`
- [ ] Rebuild `self.rows` from sections:
  ```python
  def build_rows_from_sections(self):
      rows = []
      for section in self.controller.sections:
          rows.append({"type": "section", "section_id": section.id})
          for person_id in section.people_ids:
              rows.append({"type": "person", "person_id": person_id})
      return rows
  ```
- [ ] Call this whenever sections or people change

#### Step 3.2: Update Drag & Drop
**File:** `headers.py` (vertical header drag logic)
- [ ] When dragging a person:
  - Determine which section they're being dropped into
  - Call `controller.move_person_to_section(person_id, section_id, index)`
  - Rebuild rows and refresh UI
- [ ] Prevent dragging sections (or implement section reordering)
- [ ] Visual feedback showing which section will receive the person

#### Step 3.3: Add Person Dialog
**File:** `dialogs.py` - `AddPersonDialog`
- [ ] Add section dropdown/selector
- [ ] Default to first section or last-used section
- [ ] Pass selected section when creating person

---

### Phase 4: Section Management UI

#### Step 4.1: Manage Sections Dialog
**File:** New `section_dialogs.py`
- [ ] Create `ManageSectionsDialog`:
  - List all sections
  - Add new section
  - Edit section name
  - Delete section (with warning if has people)
  - Reorder sections (drag & drop or up/down buttons)
- [ ] Add menu item: "Gérer..." → "Sections"

#### Step 4.2: Section Context Menu
**File:** `main.py` or `headers.py`
- [ ] Right-click on section header:
  - "Rename Section"
  - "Sort People Alphabetically"
  - "Add Person to Section"
  - "Delete Section" (if empty)
  - "Collapse/Expand" (future feature)

---

### Phase 5: Alphabetical Sorting

#### Step 5.1: Sort Section
**File:** `controller.py`
- [ ] Implement `sort_section_alphabetically(section_id)`:
  ```python
  def sort_section_alphabetically(self, section_id):
      section = self.get_section_by_id(section_id)
      people = self.get_people_in_section(section_id)
      # Sort by display_name
      people.sort(key=lambda p: p.display_name.lower())
      section.people_ids = [p.id for p in people]
  ```

#### Step 5.2: Sort All Sections
**File:** `controller.py`
- [ ] Implement `sort_all_sections_alphabetically()`:
  - Iterate through all sections
  - Sort each section's people
- [ ] Add menu item: "View" → "Sort All Alphabetically"

---

### Phase 6: Testing & Polish

#### Step 6.1: Update Tests
**File:** `tests.py`
- [ ] Test Section model creation and methods
- [ ] Test Person with section_id
- [ ] Test migration from old format
- [ ] Test drag & drop between sections
- [ ] Test alphabetical sorting

#### Step 6.2: Update Documentation
- [ ] Update README.md with section features
- [ ] Update user guide (if exists)
- [ ] Add migration notes

---

## 🗂️ File Changes Summary

### New Files
- `section_dialogs.py` - Section management UI
- `migration.py` (optional) - Data migration utilities

### Modified Files
1. **models.py**
   - Add `Section` class
   - Update `Person` class with `section_id`

2. **controller.py**
   - Add `sections` list
   - Add section management methods
   - Update serialization

3. **file_io.py**
   - Add migration logic
   - Update save/load to handle sections

4. **main.py**
   - Update initialization to create sections
   - Update row building logic
   - Add section context menu

5. **dialogs.py**
   - Update `AddPersonDialog` with section selector

6. **headers.py**
   - Update drag & drop to work with sections

7. **menu_bar.py**
   - Add "Manage Sections" menu item
   - Add "Sort Alphabetically" menu item

8. **tests.py**
   - Add section tests
   - Add migration tests

---

## 🎨 UI/UX Considerations

### Visual Design
- **Section Headers**: Make them visually distinct (bold, different background)
- **Drag Feedback**: Show which section will receive the person
- **Empty Sections**: Show placeholder text "No people in this section"
- **Section Icons**: Consider adding icons for sections

### User Experience
- **Default Section**: New people go to "PMSI" or last-used section
- **Undo/Redo**: Consider adding undo for drag operations (future)
- **Keyboard Shortcuts**: Add shortcuts for sorting (future)
- **Collapsible Sections**: Allow hiding section contents (future)

---

## 🔄 Migration Strategy

### For Existing Users
1. **Auto-migration on first load**:
   - Detect old format (no `sections` key in JSON)
   - Create Section objects from current `rows` structure
   - Assign people to sections based on their position
   - Save in new format

2. **Migration Logic**:
   ```python
   def migrate_old_format(data):
       if "sections" in data:
           return data  # Already new format
       
       sections = []
       current_section = None
       
       for row in data.get("rows", []):
           if row["type"] == "section":
               section = Section(
                   id=row["id"],
                   label=row["label"],
                   people_ids=[]
               )
               sections.append(section)
               current_section = section
           elif row["type"] == "person" and current_section:
               current_section.people_ids.append(row["person_id"])
               # Update person's section_id
               person = find_person(data["people"], row["person_id"])
               person["section_id"] = current_section.id
       
       data["sections"] = [s.to_dict() for s in sections]
       return data
   ```

---

## 🚀 Rollout Plan

### Version 1.0.7 - Phase 1 (Core Implementation)
- Section model
- Data migration
- Basic section assignment
- Drag & drop between sections

### Version 1.0.8 - Phase 2 (Management UI)
- Manage Sections dialog
- Section context menu
- Alphabetical sorting

### Version 1.1.0 - Phase 3 (Advanced Features)
- Collapsible sections
- Section icons/colors
- Bulk operations
- Undo/redo

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Breaking Changes
**Problem:** Old files won't work with new format  
**Solution:** Auto-migration on load with backward compatibility

### Issue 2: Performance with Many Sections
**Problem:** Rebuilding rows frequently could be slow  
**Solution:** Cache rows, only rebuild when sections/people change

### Issue 3: Drag & Drop Complexity
**Problem:** Determining target section during drag  
**Solution:** Use visual indicators and clear drop zones

### Issue 4: Empty Sections
**Problem:** What if all people are removed from a section?  
**Solution:** Keep section, show "Empty" placeholder, allow deletion

---

## 📝 Implementation Checklist

### Before Starting
- [x] Create implementation plan
- [ ] Review plan with user
- [ ] Set version to 1.0.7 in main.py

### Phase 1: Models
- [ ] Create Section class
- [ ] Update Person class
- [ ] Update Controller
- [ ] Test models

### Phase 2: Migration
- [ ] Write migration function
- [ ] Test with old files
- [ ] Test with new files

### Phase 3: UI
- [ ] Update row building
- [ ] Update drag & drop
- [ ] Update Add Person dialog
- [ ] Test UI changes

### Phase 4: Management
- [ ] Create Manage Sections dialog
- [ ] Add context menu
- [ ] Add menu items
- [ ] Test management features

### Phase 5: Sorting
- [ ] Implement sort methods
- [ ] Add UI triggers
- [ ] Test sorting

### Phase 6: Polish
- [ ] Update tests
- [ ] Update documentation
- [ ] Final testing
- [ ] Build and release

---

## 🎯 Success Criteria

- [ ] People can be assigned to sections
- [ ] Sections can be managed (add, edit, delete, reorder)
- [ ] Drag & drop works between sections
- [ ] Alphabetical sorting works per section and globally
- [ ] Old files migrate automatically without data loss
- [ ] All existing features still work
- [ ] Tests pass
- [ ] Documentation updated

---

**Estimated Time:** 4-6 hours of development  
**Complexity:** Medium-High  
**Risk Level:** Medium (requires data migration)

---

**Next Steps:**
1. Review this plan
2. Get user approval
3. Start with Phase 1 (Models)
4. Implement incrementally with testing at each phase
