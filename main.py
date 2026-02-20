# ============================================================
# 1. Imports
# ============================================================

# stdlib
import os
import sys
import calendar
import json
import ctypes

# Set App User Model ID for Windows Taskbar Icon
myappid = 'mshift.midwife.scheduler.1.0' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# Qt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidgetItem,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QLabel,
    QMenu,
    QDialog,
    QInputDialog
)
from PyQt5.QtCore import (
    Qt,
    QEvent,
    QTimer
)
from PyQt5.QtGui import (
    QColor,
    QBrush,
    QFont,
    QIcon,
    QPixmap,
    QPainter
)


# App modules
from models import Person, Service, MonthData, Schema, SchemaAssignment
from dialogs import AddPersonDialog, AddServiceDialog, ManageServicesDialog, PreferencesDialog
from person_dialogs import ManagePeopleDialog
from schema_dialogs import CreateSchemaDialog, ManageSchemasDialog
from menu_bar import MenuBar
from exporter import export_to_excel, export_to_image
from importer import import_from_excel
from file_io import save_schedule, load_schedule
from service_cell import ServiceCell
from preferences import Preferences
from controller import ScheduleController
from app_state import AppState
from updater import UpdateManager
from ui_setup import setup_main_window_ui
from drag_drop_handler import DragDropHandler
from copy_paste_handler import CopyPasteHandler
from migration import rebuild_rows_from_sections

VERSION = "1.0.13"

# ============================================================
# Constants
# ============================================================
FILE_WATCH_INTERVAL_MS = 5000  # Check for external file changes every 5 seconds
UPDATE_CHECK_DELAY_MS = 2000   # Delay before checking for updates on startup
FILE_MTIME_TOLERANCE_S = 0.1   # Tolerance for file modification time comparison
MAX_RECENT_FILES = 3           # Maximum number of recent files to track
MAX_BACKUP_FILES = 5           # Maximum number of backup files to keep

# Zoom
ZOOM_STEP = 0.1
ZOOM_MIN = 0.5
ZOOM_MAX = 2.0
ZOOM_DEFAULT = 1.0

# Splash
SPLASH_DURATION_MS = 2500     # Duration of the splash screen in milliseconds


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ============================================================
# 2. Main Window
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set Window Icon
        icon_path = resource_path("logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # =====================================================
        # 1. WINDOW & MENU (pure UI shell, no state)
        # =====================================================
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.setWindowTitle("mshift – Midwife Scheduler")
        self.resize(1100, 600)

        # =====================================================
        # 2. INPUT / INTERACTION HANDLERS
        # =====================================================
        self.drag_drop_handler = DragDropHandler(self)
        self.copy_paste_handler = CopyPasteHandler(self)
        self._shift_only_down = False
        self._zoom_factor = ZOOM_DEFAULT
        self._base_font = QApplication.font()  # Capture default app font
        
        # Row dragging state (used by headers.py)
        self._row_dragging = False
        self._row_drag_source = None
        self._row_drag_target = None

        # =====================================================
        # 4. CORE CONTROLLER (holds data and logic)
        # =====================================================
        self.controller = ScheduleController()
        
        # Keep some UI-specific shortcuts for convenience if needed, 
        # but try to migrate to controller.
        self.sections = [
            {"id": "PMSI", "label": "PMSI"},
            {"id": "Suites", "label": "Suites de couches"},
            {"id": "Patho", "label": "Grossesses pathologiques"},
            {"id": "Cons", "label": "Consultations"},
            {"id": "DAN", "label": "DAN"},
            {"id": "PMA", "label": "PMA"},
            {"id": "Salle", "label": "Salle de naissance"},
            {"id": "Vac&Cong", "label": "Vacataires et congés"}
        ]

        self.current_month = None
        
        self.current_file_path = None
        self.last_file_mtime = 0
        self._watcher_timer = QTimer(self)
        self._watcher_timer.setInterval(FILE_WATCH_INTERVAL_MS)
        self._watcher_timer.timeout.connect(self._check_file_for_updates)

        # =====================================================
        # 5. APP STATE MANAGER
        # =====================================================
        self.app_state = AppState()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._is_saving_to_disk = False
        setup_main_window_ui(self)

        # =====================================================
        # 6b. UPDATER
        # =====================================================
        self.updater = UpdateManager(VERSION, self)
        # Check for updates silently after 2 seconds to not block startup
        QTimer.singleShot(UPDATE_CHECK_DELAY_MS, lambda: self.updater.start_check(silent=True))

        # =====================================================
        # 8. LOAD APP STATE OR FALL BACK TO DEFAULTS
        # =====================================================
        loaded = self.load_app_state()
        if not loaded :
            # ---- First launch defaults ----
            self.controller.preferences = Preferences()
            self.controller.n_prev_days = self.controller.preferences.previous_days_shown

            self.controller.services = [
                Service("Jour", "J", 12, "#A3D5FF"),
                Service("Nuit", "N", 12, "#FFD6A3"),
                Service("Planning Familial", "GP", 8, "#C3B1E1"),
                Service("Inconnu", "?", 0, "#FF5555", id="unknown", is_visible=False)
            ]

            self.controller.people = []

            self.controller.rows = []
            self._populate_initial_rows()

            # =====================================================
            # DEV SEED DATA - Controlled by environment variable
            # =====================================================
            DEV_MODE = os.getenv("MSHIFT_DEV_MODE", "").lower() in ("1", "true", "yes")
            
            if DEV_MODE:
                from dev_seed import load_dev_data
                load_dev_data(self)

        # =====================================================
        # 8b. AUTO-LOAD LAST FILE  OR  COMMAND LINE ARG
        # =====================================================
        file_to_load = None
        
        # Check command line argument first (e.g. "Open With" or Double Click)
        if len(sys.argv) > 1:
            potential_file = sys.argv[1]
            if os.path.exists(potential_file) and potential_file.endswith(".mshift"):
                 file_to_load = potential_file

        # Fallback to recent files
        if not file_to_load and self.controller.recent_files:
            last_file = self.controller.recent_files[0]
            if os.path.exists(last_file):
                file_to_load = last_file

        if file_to_load:
            print(f"Auto-loading file: {file_to_load}")
            load_schedule(self.controller, file_to_load)
            self.rebuild_rows_from_sections()  # Rebuild rows from loaded sections
            self.current_file_path = file_to_load
            self.last_file_mtime = os.path.getmtime(file_to_load)
            
            # Update menu to move this file to top of recent list
            self.controller.add_recent_file(file_to_load)

        self.installEventFilter(self)
        self.finalize_table_setup()
        
        # Initial refresh of menu
        self.menu_bar.update_recent_menu(self.recent_files)

    # Proxy properties for legacy code compatibility
    @property
    def people(self): return self.controller.people
    @people.setter
    def people(self, v): self.controller.people = v

    @property
    def services(self): return self.controller.services
    @services.setter
    def services(self, v): self.controller.services = v

    @property
    def schedule(self): return self.controller.schedule
    @schedule.setter
    def schedule(self, v): self.controller.schedule = v

    @property
    def rows(self): return self.controller.rows
    @rows.setter
    def rows(self, v): self.controller.rows = v

    @property
    def preferences(self): return self.controller.preferences
    @preferences.setter
    def preferences(self, v): self.controller.preferences = v

    @property
    def n_prev_days(self): return self.controller.n_prev_days
    @n_prev_days.setter
    def n_prev_days(self, v): self.controller.n_prev_days = v

    @property
    def day_service_violations(self): return self.controller.day_service_violations
    @day_service_violations.setter
    def day_service_violations(self, v): self.controller.day_service_violations = v

    @property
    def recent_files(self): return self.controller.recent_files
    @recent_files.setter
    def recent_files(self, v): self.controller.recent_files = v

    # =====================================================
    # 3b. SECTION MANAGEMENT
    # =====================================================
    def rebuild_rows_from_sections(self):
        """
        Rebuild the rows structure from sections.
        
        This is called after sections are modified to update the UI.
        Rows are used by the vertical header to display sections and people.
        """
        self.controller.rows = rebuild_rows_from_sections(self.controller.sections)

    # =====================================================
    # 3c. UNDO/REDO SYSTEM
    # =====================================================
    def undo(self):
        """Undo the last action."""
        action = self.controller.undo_manager.undo()
        if not action:
            return
        
        # Disable undo recording while performing undo
        self.controller.undo_manager.disable()
        
        try:
            # Handle different action types
            if action.action_type == "service_change":
                self._undo_service_change(action.undo_data)
            elif action.action_type == "person_add":
                self._undo_person_add(action.undo_data)
            elif action.action_type == "person_delete":
                self._undo_person_delete(action.undo_data)
            elif action.action_type == "section_sort":
                self._undo_section_sort(action.undo_data)
            elif action.action_type == "section_rename":
                self._undo_section_rename(action.undo_data)
            elif action.action_type == "person_move":
                self._undo_person_move(action.undo_data)
            elif action.action_type == "bulk_service_change":
                self._undo_bulk_service_change(action.undo_data)
            elif action.action_type == "schema_assignment_change":
                self._undo_schema_assignment_change(action.undo_data)
        finally:
            # Re-enable undo recording
            self.controller.undo_manager.enable()
            # Update menu
            self.menu_bar.update_undo_redo_actions()
    
    def redo(self):
        """Redo the last undone action."""
        action = self.controller.undo_manager.redo()
        if not action:
            return
        
        # Disable undo recording while performing redo
        self.controller.undo_manager.disable()
        
        try:
            # Handle different action types
            if action.action_type == "service_change":
                self._undo_service_change(action.redo_data)
            elif action.action_type == "person_add":
                self._undo_person_delete(action.redo_data)  # Redo add = undo delete
            elif action.action_type == "person_delete":
                self._undo_person_add(action.redo_data)  # Redo delete = undo add
            elif action.action_type == "section_sort":
                self._undo_section_sort(action.redo_data)
            elif action.action_type == "section_rename":
                self._undo_section_rename(action.redo_data)
            elif action.action_type == "person_move":
                self._undo_person_move(action.redo_data)
            elif action.action_type == "bulk_service_change":
                self._undo_bulk_service_change(action.redo_data)
            elif action.action_type == "schema_assignment_change":
                self._undo_schema_assignment_change(action.redo_data)
        finally:
            # Re-enable undo recording
            self.controller.undo_manager.enable()
            # Update menu
            self.menu_bar.update_undo_redo_actions()
    
    def _undo_service_change(self, data):
        """Undo a service assignment change."""
        year = data["year"]
        month = data["month"]
        day = data["day"]
        person_id = data["person_id"]
        service_id = data["service_id"]
        
        # Apply the change
        self.apply_assignment_change(
            person_id=person_id,
            day=day, 
            service_id=service_id, 
            year=year,
            month=month,
            reason="undo"
        )
    
    def _undo_bulk_service_change(self, data):
        """Undo a bulk service assignment change."""
        changes = data["changes"]
        for change in changes:
            self._undo_service_change(change)
            
    def _undo_schema_assignment_change(self, data):
        """Undo schema assignment changes."""
        from models import SchemaAssignment
        assignments_data = data["assignments"]
        
        # We need to replace the entire list of assignments?
        # Or just merge?
        # The easiest way is to re-load them.
        # However, the controller holds ALL assignments for EVERYONE.
        # We only want to touch those related to the person(s) involved?
        # But our undo data format "assignments" could imply "all assignments for this person" 
        # or "all assignments in system".
        
        # To be safe and simple: 
        # 1. Identify which person(s) are affected (by looking at the data).
        # 2. Remove all existing assignments for those persons.
        # 3. Add back the assignments from data.
        
        if not assignments_data:
            return

        person_ids = set(a["person_id"] for a in assignments_data)
        
        # Filter out existing assignments for these people
        self.controller.schema_assignments = [
            sa for sa in self.controller.schema_assignments 
            if sa.person_id not in person_ids
        ]
        
        # Add back restored assignments
        for adata in assignments_data:
            sa = SchemaAssignment(
                person_id=adata["person_id"],
                schema_id=adata["schema_id"],
                repeat_mode=adata["repeat_mode"],
                repeat_months=adata["repeat_months"],
                start_year=adata["start_year"],
                start_month=adata["start_month"],
                overwrite_existing=adata["overwrite_existing"]
            )
            self.controller.schema_assignments.append(sa)
            
        # Re-apply schemas immediately?
        # Yes, if we are in a month that is affected, we might want to refresh.
        # For simplicity, we can rely on finalize_table_setup() called by caller?
        # But undo/redo usually needs to trigger UI refresh.
        # Since this affects potentially many months, we should probably just refresh current view.
        self.finalize_table_setup()
    
    def _undo_person_add(self, data):
        """Undo adding a person (remove them)."""
        person_id = data["person_id"]
        person = self.controller.get_person_by_id(person_id)
        if person:
            self.controller.people.remove(person)
            # Remove from section
            if person.section_id:
                section = self.controller.get_section_by_id(person.section_id)
                if section:
                    section.remove_person(person_id)
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()
    
    def _undo_person_delete(self, data):
        """Undo deleting a person (add them back)."""
        person_data = data["person_data"]
        person = Person(**person_data)
        self.controller.people.append(person)
        # Add to section
        if person.section_id:
            section = self.controller.get_section_by_id(person.section_id)
            if section:
                section.add_person(person.id)
        self.rebuild_rows_from_sections()
        self.finalize_table_setup()
    
    def _undo_section_sort(self, data):
        """Undo section sorting."""
        section_id = data["section_id"]
        people_ids = data["people_ids"]
        section = self.controller.get_section_by_id(section_id)
        if section:
            section.people_ids = people_ids.copy()
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()
    
    def _undo_section_rename(self, data):
        """Undo section rename."""
        section_id = data["section_id"]
        label = data["label"]
        section = self.controller.get_section_by_id(section_id)
        if section:
            section.label = label
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()
    
    def _undo_person_move(self, data):
        """Undo moving a person between sections."""
        person_id = data["person_id"]
        section_id = data["section_id"]
        index = data["index"]
        
        person = self.controller.get_person_by_id(person_id)
        if person and person.section_id:
            # Remove from current section
            old_section = self.controller.get_section_by_id(person.section_id)
            if old_section:
                old_section.remove_person(person_id)
        
        # Add to target section
        section = self.controller.get_section_by_id(section_id)
        if section and person:
            section.add_person(person_id, index)
            person.section_id = section_id
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()

    # =====================================================
    # 4. APP LIFECYCLE & PERSISTENCE
    # =====================================================
    def load_app_state(self):
        data = self.app_state.load_app_state()
        if not data:
            return False

        self.controller.from_dict(data)

        # Restore last viewed month
        if self.controller.last_year and self.controller.last_month:
            self.year_combo.setCurrentText(str(self.controller.last_year))
            self.month_combo.setCurrentIndex(self.controller.last_month - 1)

        return True
    
    def open_preferences(self):
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec():
            self.preferences = dialog.preferences
            self.n_prev_days = self.preferences.previous_days_shown
            
            # Rebuild if needed
            self.finalize_table_setup()

            # Persist app state
            self.controller.last_year = int(self.year_combo.currentText())
            self.controller.last_month = self.month_combo.currentIndex() + 1
            self.app_state.save_app_state(self.controller.to_dict())

    def open_people_dialog(self, initial_person_id=None):
        """Open the Manage People dialog."""
        dialog = ManagePeopleDialog(self)
        if initial_person_id:
            dialog.select_person(initial_person_id)
        dialog.exec_()
        # Refresh UI after closing, in case of changes not fully handled dynamically
        self.rebuild_rows_from_sections()
        self.finalize_table_setup()
        
    def open_add_person_dialog(self):
        """Open the Add Person dialog."""
        dialog = AddPersonDialog(self.controller.sections)
        if dialog.exec_() == QDialog.Accepted:
            # Create Person
            p = Person(
                prenom=dialog.prenom_edit.text(),
                nom=dialog.nom_edit.text(),
                percentage=dialog.percent_spin.value(),
                short_name=dialog.short_preview.text(),
                section_id=dialog.section_combo.currentData()
            )
            
            # Undo support
            self.controller.undo_manager.record_person_add(p.to_dict())
            
            self.controller.people.append(p)
            
            # Add to section
            if p.section_id:
                section = self.controller.get_section_by_id(p.section_id)
                if section:
                    section.add_person(p.id)
            
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()
            self.menu_bar.update_undo_redo_actions()

    def closeEvent(self, event):
        self.controller.last_year = int(self.year_combo.currentText())
        self.controller.last_month = self.month_combo.currentIndex() + 1
        self.app_state.save_app_state(self.controller.to_dict())
        super().closeEvent(event)

    # =====================================================
    # 5. TABLE STRUCTURE & PROJECTION
    # =====================================================
    def finalize_table_setup(self):
        self.table_rebuilder.finalize()
        
        self.recompute_current_month_violations()

        self.table.horizontalHeader().viewport().update()

    def _populate_initial_rows(self):
        """Populate the ordered rows list with static sections.
        People will be appended after this in self.rows."""
        for section in self.sections:
            self.rows.append({
                "type": "section",
                "id": section["id"],
                "label": section["label"]
            })

    def refresh_row_headers(self):
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())
        header = self.table.verticalHeader()

        # Set vertical headers
        for row_index, row_data in enumerate(self.rows):
            if row_data["type"] == "section":
                continue

            person = next(p for p in self.people if p.id == row_data["person_id"])
            summary = self.workload.monthly_summary(person, year, month)

            text = f"{person.display_name} ({summary.worked:g}h / {summary.expected:g}h)"
            self.table.setVerticalHeaderItem(row_index, QTableWidgetItem(text))

            color = self.workload.status_color(summary.ratio)
            header.set_row_color(row_index, color)
            
            # Stats
            stats = self.controller.calculate_stats_for_month(person.id, year, month)
            header.set_person_stats(row_index, stats)

    # =====================================================
    # 6. ASSIGNMENT LOGIC
    # =====================================================
    def clear_person_schedule_month(self, person_id, year, month):
        """Clear all assignments for a person in a specific month, and split schemas if needed."""
        
        # =========================================================
        # PART 1: Handle Schema Assignments (Punch a hole)
        # =========================================================
        # Check for active schema assignments for this month
        current_assignments = [
            sa for sa in self.controller.schema_assignments 
            if sa.person_id == person_id and sa.should_apply_to_month(year, month)
        ]

        if current_assignments:
            old_assignments_state = [sa.to_dict() for sa in self.controller.get_assignments_for_person(person_id)]
            new_assignments = [sa for sa in self.controller.schema_assignments if sa.person_id != person_id]
            
            # For each assignment covering this month, modify it
            target_period = year * 12 + month
            
            for sa in current_assignments:
                # Calculate start period index
                start_p = sa.start_year * 12 + sa.start_month
                
                # If it starts THIS month
                if start_p == target_period:
                    # Move start to next month
                    # If repeat was 1, just delete it (don't add back)
                    if sa.repeat_mode == "limited":
                        if sa.repeat_months > 1:
                            sa.repeat_months -= 1
                            if month == 12:
                                sa.start_year += 1
                                sa.start_month = 1
                            else:
                                sa.start_month += 1
                            new_assignments.append(sa)
                    else: # always
                         if month == 12:
                            sa.start_year += 1
                            sa.start_month = 1
                         else:
                            sa.start_month += 1
                         new_assignments.append(sa)
                
                # If it started BEFORE this month
                elif start_p < target_period:
                    # Split into:
                    # 1. First part ending last month
                    # 2. Second part starting next month (if it extends beyond)
                    
                    months_before = target_period - start_p
                    
                    # Part 1 (Pre-split)
                    part1 = SchemaAssignment(**sa.to_dict())
                    part1.repeat_mode = "limited"
                    part1.repeat_months = months_before
                    new_assignments.append(part1)
                    
                    # Part 2 (Post-split)
                    has_future = False
                    if sa.repeat_mode == "always":
                        has_future = True
                    elif sa.repeat_mode == "limited":
                        total_months = sa.repeat_months
                        if total_months > months_before + 1:
                            has_future = True
                            
                    if has_future:
                        part2 = SchemaAssignment(**sa.to_dict())
                        if month == 12:
                            part2.start_year = year + 1
                            part2.start_month = 1
                        else:
                            part2.start_year = year
                            part2.start_month = month + 1
                            
                        if sa.repeat_mode == "limited":
                            part2.repeat_months = sa.repeat_months - (months_before + 1)
                            
                        new_assignments.append(part2)

            # Re-add other unaffected assignments for this person
            unaffected = [
                sa for sa in self.controller.schema_assignments 
                if sa.person_id == person_id and sa not in current_assignments
            ]
            new_assignments.extend(unaffected)
            
            # Apply changes to controller
            self.controller.schema_assignments = new_assignments
            
            # Record Undo for schema change
            person = self.controller.get_person_by_id(person_id)
            name = person.display_name if person else "Person"
            new_assignments_state = [sa.to_dict() for sa in self.controller.get_assignments_for_person(person_id)]
            
            self.controller.undo_manager.record_schema_assignment_change(
                f"Split schema for {name} (clearing {month}/{year})",
                old_assignments_state,
                new_assignments_state
            )

        # =========================================================
        # PART 2: Clear actual cells
        # =========================================================
        month_data = self.controller.get_month_data(year, month)
        days_in_month = calendar.monthrange(year, month)[1]
        
        changes = []
        for day in range(1, days_in_month + 1):
            old_service = month_data.get_service(person_id, day)
            if old_service is not None:
                changes.append({
                    "year": year,
                    "month": month,
                    "day": day,
                    "person_id": person_id,
                    "old_service_id": old_service,
                    "new_service_id": None
                })
        
        if not changes:
            # If we changed schema but no cells changed (cells were already empty?), we still need to refresh?
            # Yes, finalized_table_setup handles reapplying.
            # But we should ensure UI updates.
            if current_assignments:
                self.finalize_table_setup()
            return
            
        # Record undo
        person = self.controller.get_person_by_id(person_id)
        name = person.display_name if person else "Person"
        self.controller.undo_manager.record_bulk_service_change(
            f"Clear {name}'s schedule for {month}/{year}",
            changes
        )
        
        # Apply changes
        for change in changes:
            self.apply_assignment_change(
                person_id=change["person_id"],
                day=change["day"],
                service_id=None,
                year=year,
                month=month,
                reason="bulk_clear"  # Prevent individual undo recording
            )
    
    def clear_person_schedule_future(self, person_id, year, month):
        """Clear assignments for this month and all future months."""
        
        # =========================================================
        # PART 1: Modify Schema Assignments (Stop Future Automation)
        # =========================================================
        person = self.controller.get_person_by_id(person_id)
        current_assignments = [sa for sa in self.controller.schema_assignments if sa.person_id == person_id]
        
        if current_assignments:
            # Capture state BEFORE modification
            old_assignments_state = [sa.to_dict() for sa in current_assignments]
            assignments_changed = False
            
            # Identify assignments to keep (modified or untouched)
            kept_assignments = []
            
            start_clearing_period = year * 12 + month
            
            for sa in current_assignments:
                should_keep = True
                
                if sa.start_year is None or sa.start_month is None:
                    # Invalid assignment, just keep it or ignore
                    kept_assignments.append(sa)
                    continue

                start_period = sa.start_year * 12 + sa.start_month
                
                if start_period >= start_clearing_period:
                    # Starts after clearing begins -> Delete it
                    should_keep = False
                    assignments_changed = True
                else:
                    # Started before. Check if it extends into clearing period.
                    if sa.repeat_mode == "always":
                        # It's infinite, so we must truncate it
                        months_duration = start_clearing_period - start_period
                        if months_duration > 0:
                            sa.repeat_mode = "limited"
                            sa.repeat_months = months_duration
                            assignments_changed = True
                        else:
                            should_keep = False # Ends before it starts?
                            assignments_changed = True
                    else: # limited
                        current_end_period = start_period + sa.repeat_months
                        if current_end_period > start_clearing_period:
                            # It overlaps, truncate it
                            new_duration = start_clearing_period - start_period
                            if new_duration > 0:
                                sa.repeat_months = new_duration
                                assignments_changed = True
                            else:
                                should_keep = False
                                assignments_changed = True
                
                if should_keep:
                    kept_assignments.append(sa)
            
            if assignments_changed:
                # Update controller list
                # Remove all old assignments for this person
                self.controller.schema_assignments = [
                    sa for sa in self.controller.schema_assignments 
                    if sa.person_id != person_id
                ]
                # Add distinct kept assignments
                self.controller.schema_assignments.extend(kept_assignments)
                
                # Capture new state
                new_assignments_state = [sa.to_dict() for sa in kept_assignments]
                
                # Record Undo
                name = person.display_name if person else "Person"
                self.controller.undo_manager.record_schema_assignment_change(
                    f"Stop schemas for {name} from {month}/{year}",
                    old_assignments_state,
                    new_assignments_state
                )

        # =========================================================
        # PART 2: Clear Existing Cells (Materialized Data)
        # =========================================================
        keys_to_process = []
        for (y, m) in self.controller.schedule.keys():
            if y > year or (y == year and m >= month):
                keys_to_process.append((y, m))
        
        changes = []
        for y, m in keys_to_process:
            month_data = self.controller.get_month_data(y, m)
            days_in_month = calendar.monthrange(y, m)[1]
            
            for day in range(1, days_in_month + 1):
                old_service = month_data.get_service(person_id, day)
                if old_service is not None:
                    changes.append({
                        "year": y,
                        "month": m,
                        "day": day,
                        "person_id": person_id,
                        "old_service_id": old_service,
                        "new_service_id": None
                    })
        
        if not changes:
            return

        # Record undo
        name = person.display_name if person else "Person"
        self.controller.undo_manager.record_bulk_service_change(
            f"Clear {name}'s schedule from {month}/{year}",
            changes
        )
        
        # Apply changes (batching UI updates would be better but this is simpler)
        # We can optimize by disabling auto-save and UI updates until end
        self.preferences.auto_save = False # temp disable
        try:
            for change in changes:
                self.apply_assignment_change(
                    person_id=change["person_id"],
                    day=change["day"],
                    service_id=None,
                    year=change["year"],
                    month=change["month"],
                    reason="bulk_clear"
                )
        finally:
            self.preferences.auto_save = True # restore
            self.menu_bar.update_undo_redo_actions()
            self.quick_save()

    # =====================================================
    # 6. ASSIGNMENTS & RULES
    # =====================================================
    def apply_assignment_change(
        self,
        *,
        person_id,
        day,
        service_id,
        year=None,
        month=None,
        reason=None,   # optional, for debugging / logging
    ):
        """
        Canonical entry point for ALL assignment mutations.

        This method is responsible for:
        - mutating backend state
        - recomputing rule violations
        - triggering minimal UI refresh

        UI code MUST NOT call MonthData.set_service directly.
        """
        if year is None:
            year = int(self.year_combo.currentText())
        if month is None:
            month = self.month_combo.currentIndex() + 1

        # Record undo action (unless this is already an undo/redo operation)
        if reason != "undo":
            # Get old service before changing
            month_data = self.controller.get_month_data(year, month)
            old_service_id = month_data.get_service(person_id, day)
            
            # Record the change
            self.controller.undo_manager.record_service_change(
                year, month, day, person_id, old_service_id, service_id
            )

        self.controller.apply_assignment_change(person_id, day, service_id, year, month)
        
        # Minimal UI refresh
        self.table.horizontalHeader().viewport().update()
        
        # Update worked hours in row headers
        self.refresh_row_headers()

        # UI: Refresh specific cell item
        # Find row for this person
        row_idx = next((i for i, r in enumerate(self.rows) if r.get("person_id") == person_id), None)
        if row_idx is not None:
            # Find column for this day
            # If it's the requested year/month
            cur_year = int(self.year_combo.currentText())
            cur_month = self.month_combo.currentIndex() + 1
            if year == cur_year and month == cur_month:
                col_idx = day + self.n_prev_days - 1
                self.refresh_cell(row_idx, col_idx)

        # Update undo/redo menu
        if reason != "undo":
            self.menu_bar.update_undo_redo_actions()

        # Auto-save if enabled
        if self.preferences and self.preferences.auto_save:
            self.quick_save()


    def apply_comment_change(self, person_id, text):
        """
        Canonical entry point for comment mutations.
        """
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        
        self.controller.apply_comment_change(person_id, text, year, month)

        # UI: Refresh Notes cell
        row_idx = next((i for i, r in enumerate(self.rows) if r.get("person_id") == person_id), None)
        if row_idx is not None:
            notes_col = self.table.columnCount() - 1
            self.refresh_cell(row_idx, notes_col)

        if self.preferences.auto_save:
            self.quick_save()

    def _recompute_day_service_violations(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        self.controller.recompute_violations(year, month)

    def recompute_current_month_violations(self):
        self._recompute_day_service_violations()

    def eventFilter(self, obj, event):
        if self._handle_modifier_keys(event):
            return True
        
        if self.copy_paste_handler.handle_events(obj, event):
            return True
        
        if self.drag_drop_handler.handle_events(obj, event):
            return True
        
        if self._handle_delete_event(obj, event):
            return True
            
        if obj is self.table.viewport():
            if event.type() == QEvent.Wheel:
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self._set_zoom(self._zoom_factor + ZOOM_STEP)
                    elif delta < 0:
                        self._set_zoom(self._zoom_factor - ZOOM_STEP)
                    return True
                if modifiers & Qt.ShiftModifier:
                    delta = event.angleDelta().y()
                    bar = self.table.horizontalScrollBar()
                    bar.setValue(bar.value() - (delta // 12))
                    return True
                    
        # Ctrl+Enter: reset zoom to 100%
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier:
                self._reset_zoom()
                return True

        return super().eventFilter(obj, event)

    # =====================================================
    # ZOOM
    # =====================================================
    def _set_zoom(self, factor):
        """Set zoom factor, clamped to [ZOOM_MIN, ZOOM_MAX]."""
        factor = round(max(ZOOM_MIN, min(ZOOM_MAX, factor)), 2)
        if factor == self._zoom_factor:
            return
        self._zoom_factor = factor
        self._apply_zoom()

    def _reset_zoom(self):
        """Reset zoom to 100%."""
        self._set_zoom(ZOOM_DEFAULT)

    def _apply_zoom(self):
        """Apply the current zoom factor to the table."""
        # Scale font
        scaled_font = QFont(self._base_font)
        scaled_font.setPointSizeF(self._base_font.pointSizeF() * self._zoom_factor)
        self.table.setFont(scaled_font)
        self.table.horizontalHeader().setFont(scaled_font)
        self.table.verticalHeader().setFont(scaled_font)

        # Scale column widths
        base_col_w = self.preferences.column_width
        scaled_col_w = int(base_col_w * self._zoom_factor)
        for col in range(self.table.columnCount()):
            if col == self.table.columnCount() - 1:
                continue  # Notes column stays dynamic
            self.table.setColumnWidth(col, scaled_col_w)

        # Scale row heights
        base_row_h = self.preferences.row_height
        scaled_row_h = int(base_row_h * self._zoom_factor)
        self.table.verticalHeader().setDefaultSectionSize(scaled_row_h)

        # Scale vertical header width
        base_header_w = 80
        scaled_header_w = int(base_header_w * self._zoom_factor)
        self.table.verticalHeader().setMinimumWidth(scaled_header_w)

        # Update zoom label
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"🔍 {int(self._zoom_factor * 100)}%")

        self.table.viewport().update()

    def _handle_modifier_keys(self, event) -> bool:
        if event.type() not in (QEvent.KeyPress, QEvent.KeyRelease):
            return False
        
        modifiers = event.modifiers()
        new_shift_only = (
            (modifiers & Qt.ShiftModifier)
            and not (modifiers & Qt.ControlModifier)
        )

        if new_shift_only != self._shift_only_down:
            self._shift_only_down = new_shift_only
            self.table.viewport().update()

        return False
    
    def _handle_delete_event(self, obj, event) -> bool:
        if obj is not self.table.viewport():
            return False
        
        if event.type() != QEvent.MouseButtonPress:
            return False
        
        if event.button() != Qt.RightButton:
            return False
        
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ShiftModifier:
            return False # Shift + right click is copy, not delete
        
        index = self.table.indexAt(event.pos())
        if not index.isValid():
            return True
        
        row = index.row()
        column = index.column()

        resolved = self._resolve_person_cell(row, column)
        if not resolved:
            return True
        
        person, month_data, day = resolved
        service_id = month_data.get_service(person.id, day)
        if service_id is None:
            return True
        
        # Backend removal (handles UI refresh automatically through apply_assignment_change)
        self.apply_assignment_change(
            person_id=person.id,
            day=day,
            service_id=None,
            reason="delete"
        )

        return True

    
    # =====================================================
    # 10. UI HELPERS
    # =====================================================
    def _create_service_combo(self, row, column, preset_service = None):
        # Only allow combo for person rows
        row_data = self.rows[row]
        if row_data["type"] != "person":
            return None # <-- Do nothing for sections

        combo = QComboBox()
        combo.setAttribute(Qt.WA_TransparentForMouseEvents)

        person = next((p for p in self.people if p.id  == row_data["person_id"]), None)
        if person is None:
            return combo # Fallback, should not happen

        month_data, day = self._resolve_day_context(column)
    
        # Hand over control to ServiceCell
        combo._service_cell = ServiceCell(
            combo = combo,
            main_window = self,
            person = person,
            day = day,
            month_data = month_data,
            services = self.services
        )

        # Preset existing service (if any)
        if preset_service:
            service = next(s for s in self.services if s.id == preset_service)
            combo._service_cell.preset_service(service)

        return combo

    def _ensure_combo(self, row, column):
        """If cell is empty, create combo. If already a combo, ignore."""
        combo = self.table.cellWidget(row, column)
        if combo:
            return combo

        combo = self._create_service_combo(row, column)
        if combo:
            self.table.setCellWidget(row, column, combo)

        return combo
    
    # =====================================================
    # 11. USER ACTIONS & DIALOGS
    # =====================================================
    def _add_person_to_table(self, person: Person):
        self.people.append(person)

        self.rows.append({
            "type": "person",
            "person_id": person.id
        })

        if self.table.rowCount() == 1 and self.table.verticalHeaderItem(0) is None:
            row = 0
        else:
            row = self.table.rowCount()
            self.table.insertRow(row)

        self.table.setVerticalHeaderItem(
            row,
            QTableWidgetItem(person.display_name)
        )

        self.finalize_table_setup()
        self.app_state.save_app_state(self)

        if self.preferences.auto_save:
            self.quick_save()

    def _open_add_person(self, event):
        print("Add Person clicked")
        dialog = AddPersonDialog(sections=self.controller.sections)
        if dialog.exec():
            person = dialog.person
            self._add_person_to_table(person)
            
            # Add person to their section
            if person.section_id:
                section = self.controller.get_section_by_id(person.section_id)
                if section:
                    section.add_person(person.id)
                    self.rebuild_rows_from_sections()
                    self.finalize_table_setup()

    def _open_add_service(self, event):
        print("Add Service clicked")
        dialog = AddServiceDialog()
        if dialog.exec():
            self.services.append(dialog.service)
            self.finalize_table_setup()
            self.app_state.save_app_state(self)

            if self.preferences.auto_save:
                self.quick_save()
    
    def _open_add_schema(self, event):
        """Open dialog to create a new schema."""
        print("Add Schema clicked")
        dialog = CreateSchemaDialog(self.services, self)
        if dialog.exec_():
            self.controller.schemas.append(dialog.schema)
            self.app_state.save_app_state(self.controller.to_dict())
            
            if self.preferences.auto_save:
                self.quick_save()

    def open_about_dialog(self):
        print("Open about dialog (not implemented yet)")

    def _open_cell_dropdown(self, row, column):
        # Don't open for Notes col or section rows
        row_data = self.rows[row]
        if row_data["type"] != "person" or column == self.table.columnCount() - 1:
            return

        # Toggle: If already open, close it
        existing = self.table.cellWidget(row, column)
        if existing:
            if hasattr(existing, "hidePopup"):
                existing.hidePopup()
            
            # Break cycle to ensure destruction
            if hasattr(existing, "_service_cell"):
                existing._service_cell = None
            
            self.table.removeCellWidget(row, column)
            existing.deleteLater()
            return

        # Dynamically create the combo
        combo = self._create_service_combo(row, column)
        if combo is None:
            return
        
        # Position it over the cell
        self.table.setCellWidget(row, column, combo)
        
        # Handle selection
        def on_activated(index):
            combo._service_cell.apply_service_by_index(index)
            self.table.removeCellWidget(row, column)
            self.table.viewport().update()

        combo.activated.connect(on_activated)
        
        # Also remove if it loses focus/closes without selection
        # (Using a small delay or event filter might be better, but combo.showPopup()
        # usually takes over focus). 
        # A simpler way: connect to a signal that fires when popup is hidden.
        # But QComboBox doesn't have a 'popupHidden' signal directly.
        # Let's just remove it after it's been used or if row/col changes.

        combo.showPopup()

    def open_services_dialog(self):
        dialog = ManageServicesDialog(self.services)

        if dialog.exec_() == QDialog.Accepted:
            self.table_rebuilder.rebuild_cells()
            self.refresh_row_headers()
    
    def open_schemas_dialog(self):
        """Open the dialog to manage schemas."""
        dialog = ManageSchemasDialog(
            self.controller.schemas, 
            self.services, 
            self.people,
            self.controller.schema_assignments,
            self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # Save app state after schema changes
            self.app_state.save_app_state(self.controller.to_dict())
    
    def open_sections_dialog(self):
        """Open the dialog to manage sections."""
        from section_dialogs import ManageSectionsDialog
        
        dialog = ManageSectionsDialog(self.controller, self)
        
        if dialog.exec_() == QDialog.Accepted:
            # Rebuild rows from updated sections
            self.rebuild_rows_from_sections()
            self.finalize_table_setup()
            
            # Save app state after section changes
            self.app_state.save_app_state(self.controller.to_dict())
            
            if self.preferences.auto_save:
                self.quick_save()
    
    def open_assign_schema_dialog(self):
        """Open the dialog to assign a schema to people."""
        dialog = AssignSchemaDialog(self.controller.schemas, self.people, self)
        
        if dialog.exec_() == QDialog.Accepted:
            # Get current year and month
            year = int(self.year_combo.currentText())
            month = self.month_combo.currentIndex() + 1
            
            # Create schema assignments
            for person in dialog.selected_people:
                assignment = SchemaAssignment(
                    person_id=person.id,
                    schema_id=dialog.selected_schema.id,
                    repeat_mode=dialog.repeat_mode,
                    repeat_months=dialog.repeat_months,
                    start_year=year,
                    start_month=month
                )
                self.controller.schema_assignments.append(assignment)
                
                # Apply the schema to current month
                self.controller.apply_schema_to_month(
                    dialog.selected_schema,
                    person.id,
                    year,
                    month,
                    overwrite=False,  # Never overwrite existing services
                    start_period=(year, month)
                )
            
            # Refresh UI
            self.finalize_table_setup()
            
            # Save changes
            self.app_state.save_app_state(self.controller.to_dict())
            
            if self.preferences.auto_save:
                self.quick_save()

    def quick_save(self):
        if self.current_file_path:
            self._is_saving_to_disk = True
            try:
                # Set expected mtime BEFORE saving to prevent race condition
                # The file watcher checks if mtime > last_file_mtime, so we set it
                # to current time to prevent false positives
                import time
                expected_mtime = time.time()
                self.last_file_mtime = expected_mtime
                
                save_schedule(self.controller, self.current_file_path)
                
                # Update with actual mtime after save
                self.last_file_mtime = os.path.getmtime(self.current_file_path)
            except Exception as e:
                print(f"Error saving file: {e}")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save file:\n{e}"
                )
            finally:
                self._is_saving_to_disk = False
        else:
            self.save_file()

    def save_and_exit(self):
        print("Save and exit triggered")
        self.quick_save()
        QApplication.quit()

    def new_file(self):
        print("New file")

        # Reset scheduling data only
        self.schedule = {}
        self.current_month = None

        # Reflect UI
        self.table_clear()
        self.finalize_table_setup()
    
    # =====================================================
    # 12. FILE I/O (SCHEDULE-LEVEL)
    # =====================================================
    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Schedule", self.current_file_path or "", "MShift File (*.mshift)")
        if not path:
            return
        self._is_saving_to_disk = True
        try:
            import time
            expected_mtime = time.time()
            self.last_file_mtime = expected_mtime
            
            save_schedule(self.controller, path)
            self.current_file_path = os.path.abspath(path)
            self.last_file_mtime = os.path.getmtime(path)
        except Exception as e:
            print(f"Error saving file: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save file:\n{e}"
            )
        finally:
            self._is_saving_to_disk = False
        self._add_to_recent_files(path)
        self._watcher_timer.start()

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Schedule", "", "MShift File (*.mshift)")
        if not path:
            return
        
        self.load_recent_file(path)

    def load_recent_file(self, path):
        try:
            load_schedule(self.controller, path)
            self.rebuild_rows_from_sections()  # Rebuild rows from loaded sections
            self.current_file_path = os.path.abspath(path)
            self.last_file_mtime = os.path.getmtime(path)
            self._add_to_recent_files(path)

            # UI refresh
            self.table_clear()
            self.finalize_table_setup()
            self._watcher_timer.start()
        except FileNotFoundError:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "File Not Found",
                f"The file could not be found:\\n{path}"
            )
        except json.JSONDecodeError as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Invalid File Format",
                f"The file is not a valid MShift file or is corrupted:\\n{e}"
            )
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            # Check if it's a ValidationError
            error_type = type(e).__name__
            if error_type == "ValidationError":
                QMessageBox.critical(
                    self,
                    "Data Validation Error",
                    f"The file contains invalid data:\\n{e}\\n\\nThe file may be corrupted or from an incompatible version."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Load Error",
                    f"Failed to load file:\\n{e}"
                )
            print(f"Error loading file: {e}")

    def _check_file_for_updates(self):
        if self._is_saving_to_disk:
            return

        if not self.current_file_path or not os.path.exists(self.current_file_path):
            return

        try:
            mtime = os.path.getmtime(self.current_file_path)
            # Add a small tolerance to avoid sub-second timestamp jitter
            if mtime > self.last_file_mtime + FILE_MTIME_TOLERANCE_S:
                # File updated externally!
                self.last_file_mtime = mtime # Prevent multiple prompts
                
                choice = QMessageBox.question(
                    self,
                    "File Updated",
                    f"The file '{os.path.basename(self.current_file_path)}' has been modified by another application (e.g., cloud sync).\n\n"
                    "Would you like to reload it now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if choice == QMessageBox.Yes:
                    self.load_recent_file(self.current_file_path)
        except Exception as e:
            print(f"Error checking file for updates: {e}")

    def _add_to_recent_files(self, path):
        # normalize path
        path = os.path.abspath(path)
        
        # remove if already in list to move to top
        if path in self.recent_files:
            self.recent_files.remove(path)
            
        self.recent_files.insert(0, path)
        
        # Limit to MAX_RECENT_FILES
        self.recent_files = self.recent_files[:MAX_RECENT_FILES]
        
        # Update UI
        self.menu_bar.update_recent_menu(self.recent_files)
        
        # Persist
        self.app_state.save_app_state(self.controller.to_dict())
    
    def restore_from_backup(self):
        """Show dialog to restore from a backup file."""
        if not self.current_file_path:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "No File Open",
                "Please open a file first before restoring from backup."
            )
            return
        
        from backup_manager import get_backup_list, restore_from_backup
        
        # Get list of available backups
        backups = get_backup_list(self.current_file_path)
        
        if not backups:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "No Backups Found",
                "No backup files were found for the current file."
            )
            return
        
        # Create a dialog to select backup
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Restore from Backup")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select a backup to restore:")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        for backup_path, backup_time in backups:
            item_text = backup_time.strftime("%Y-%m-%d %H:%M:%S")
            list_widget.addItem(item_text)
        list_widget.setCurrentRow(0)  # Select most recent by default
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        restore_button = QPushButton("Restore")
        cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(restore_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        def on_restore():
            selected_row = list_widget.currentRow()
            if selected_row >= 0:
                backup_path, backup_time = backups[selected_row]
                
                # Confirm restoration
                from PyQt5.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    dialog,
                    "Confirm Restore",
                    f"Are you sure you want to restore from backup dated {backup_time.strftime('%Y-%m-%d %H:%M:%S')}?\n\n"
                    "The current file will be backed up before restoration.",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    if restore_from_backup(backup_path, self.current_file_path):
                        QMessageBox.information(
                            dialog,
                            "Restore Successful",
                            "The backup has been restored successfully."
                        )
                        dialog.accept()
                        # Reload the file
                        self.load_recent_file(self.current_file_path)
                    else:
                        QMessageBox.critical(
                            dialog,
                            "Restore Failed",
                            "Failed to restore from backup. Please check the console for errors."
                        )
        
        restore_button.clicked.connect(on_restore)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec_()


    # =====================================================
    # 13. DOMAIN RESOLUTION HELPERS
    # =====================================================
    def _resolve_person_cell(self, row: int, col: int):
        """
        Resolve a table cell into domain objects.

        Returns:
            (person, month_data, day) if the cell is a valid person cell
            None otherwise
        """
        if row < 0 or col < 0:
            return None

        if row >= len(self.rows):
            return None

        row_data = self.rows[row]
        if row_data["type"] != "person":
            return None

        person = next(
            (p for p in self.people if p.id == row_data["person_id"]),
            None
        )
        if person is None:
            return None

        month_data, day = self._resolve_day_context(col)
        return person, month_data, day
    
    def _resolve_day_context(self, column):
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1

        if column < self.n_prev_days:
            day = calendar.monthrange(prev_year, prev_month)[1] - self.n_prev_days + 1 + column
            key = (prev_year, prev_month)

        else:
            day = column - self.n_prev_days + 1
            key = (year, month)

        if key not in self.schedule:
            self.schedule[key] = MonthData(*key)

        return self.schedule[key], day

    def refresh_cell(self, row, col):
        """Redraws a single cell (service or note) based on latest backend data."""
        resolved = self._resolve_person_cell(row, col)
        if not resolved:
            return
        
        person, month_data, day = resolved
        
        # Remove any cell widget (e.g., combo box) so the item underneath is visible
        if self.table.cellWidget(row, col):
            self.table.removeCellWidget(row, col)
        
        # Block signals to avoid recursive _on_item_changed calls
        self.table.blockSignals(True)
        
        item = self.table.item(row, col)
        if not item:
            item = QTableWidgetItem()
            self.table.setItem(row, col, item)

        # 1. Notes Column
        if col == self.table.columnCount() - 1:
            item.setText(month_data.get_comment(person.id))
        
        # 2. Service Cells
        else:
            service_id = month_data.get_service(person.id, day)
            if service_id:
                service = next((s for s in self.services if s.id == service_id), None)
                if service:
                    if service.id == "builtin_note":
                        # Custom Note Logic
                        note_text = month_data.get_note(person.id, day)
                        if note_text:
                            item.setText(note_text)
                            item.setToolTip(note_text)
                        else:
                            item.setText(service.short_name)
                    else:
                        item.setText(service.short_name)
                        item.setToolTip("")

                    item.setBackground(QBrush(QColor(service.color_hex)))
                else:
                    item.setText("?")
                    item.setBackground(QBrush(QColor("#FF5555")))
            else:
                item.setText("")
                item.setBackground(QBrush(Qt.transparent))

        self.table.blockSignals(False)

    def _on_item_changed(self, item):
        """Handles manual text editing (currently only for the Notes column)."""
        row = item.row()
        col = item.column()
        
        # Only handle last column (Notes)
        if col != self.table.columnCount() - 1:
            return

        resolved = self._resolve_person_cell(row, col)
        if not resolved: return
        
        person, month_data, day = resolved
        new_text = item.text()
        
        if month_data.get_comment(person.id) != new_text:
            self.apply_comment_change(person.id, new_text)

    def _on_item_double_clicked(self, item):
        """Handles double-click to edit Note services."""
        row = item.row()
        col = item.column()
        
        # Skip Notes column (handled by itemChanged)
        if col == self.table.columnCount() - 1:
            return

        resolved = self._resolve_person_cell(row, col)
        if not resolved:
            return

        person, month_data, day = resolved
        service_id = month_data.get_service(person.id, day)
        
        if service_id == "builtin_note":
            # Force close combo and its popup
            combo = self.table.cellWidget(row, col)
            if combo:
                if hasattr(combo, "hidePopup"):
                    combo.hidePopup()
                
                # Break cycle
                if hasattr(combo, "_service_cell"):
                    combo._service_cell = None
                
                self.table.removeCellWidget(row, col)
                combo.deleteLater()
            
            # Force UI update to clear artifacts
            self.table.viewport().repaint()
            
            # Schedule the dialog opening slightly later to allow the event loop
            # to process the combo destruction/popup closing.
            QTimer.singleShot(10, lambda: self._open_note_dialog(month_data, person.id, day, row, col))

    def _open_note_dialog(self, month_data, person_id, day, row, col):
        """Helper to open the note dialog async."""
        current_text = month_data.get_note(person_id, day) or ""
        text, ok = QInputDialog.getMultiLineText(
            self, 
            "Edit Note", 
            "Enter text:", 
            current_text
        )
        
        if ok:
            month_data.set_note(person_id, day, text)
            self.refresh_cell(row, col)
            if self.preferences.auto_save:
                self.quick_save()

    def get_day_service_violations_for_column(self, column: int):
        """
        Returns a list of DayServiceViolation for the given table column.
        Only for the current month view.
        """
        if column >= self.table.columnCount() - 1:
            return []

        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        # Resolve column → (month, day)
        month_data, day = self._resolve_day_context(column)

        # Only care about current visible month
        if month_data.year != year or month_data.month != month:
            return []

        return [
            v for v in self.day_service_violations
            if v.day == day
        ]
    
    def get_service_color_for_kind(self, service_kind):
        """
        Returns QColor for Jour / Nuit service kind.
        """
        for service in self.services:
            if service.name == service_kind.value:
                return QColor(service.color_hex)

        # Fallback (should not happen)
        return QColor(0, 0, 0)
    
    def _is_column_in_current_month(self, column: int) -> bool:
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        month_data, _ = self._resolve_day_context(column)

        return (
            month_data.year == year and
            month_data.month == month
        )

    
    # =====================================================
    # 14. NAVIGATION & CALENDAR
    # =====================================================
    def _go_to_previous_month(self):
        month = self.month_combo.currentIndex()
        year = int(self.year_combo.currentText())

        if month == 0:
            self.month_combo.setCurrentIndex(11)
            self.year_combo.setCurrentText(str(year - 1))
        else:
            self.month_combo.setCurrentIndex(month - 1)

    def _go_to_next_month(self):
        month = self.month_combo.currentIndex()
        year = int(self.year_combo.currentText())

        if month == 11:
            self.month_combo.setCurrentIndex(0)
            self.year_combo.setCurrentText(str(year + 1))
        else:
            self.month_combo.setCurrentIndex(month + 1)

    def _load_month(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        key = (year, month)

        if key not in self.schedule :
            self.schedule[key] = MonthData(year, month)

    # =====================================================
    # 15. UTILITIES
    # =====================================================
    def table_clear(self):
        """Clears all table content but keeps the table widget itself."""
        self.table.clearContents()  # Clears all items
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

    def export_excel(self):
        export_to_excel(self)

    def export_image(self):
        export_to_image(self)

    def import_excel(self):
        import_from_excel(self)

    def _ask_drag_drop_action(self, viewport_pos):
        """
        Ask user what to do when dropping onto an occupied cell.
        Returns: "swap", "replace", or None (cancel)
        """
        menu = QMenu(self)

        swap_action = menu.addAction("Swap services")
        replace_action = menu.addAction("Replace existing service")

        chosen = menu.exec_(self.table.viewport().mapToGlobal(viewport_pos))

        if chosen == swap_action:
            return "swap"
        if chosen == replace_action:
            return "replace"

        return None
    
    def _abort_drag_with_feedback(self):
        # Clear drag visuals
        self.table.set_drag_rect(None)
        self.table.viewport().update()

        # Reset drag state
        self._drag_source = None

        # Show gentle feedback
        self._show_toast(
            "This day belongs to the previous month.\nChange month to edit its schedule."
        )

    def _show_toast(self, text: str, duration_ms: int = 2000):
        label = QLabel(text, self)
        label.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 220);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 11pt;
            }
        """)
        label.setAlignment(Qt.AlignCenter)
        label.adjustSize()

        # Position: bottom center of the window
        x = (self.width() - label.width()) // 2
        y = self.height() - label.height() - 40
        label.move(x, y)
        label.show()

        # Fade + auto-destroy
        QTimer.singleShot(duration_ms, label.deleteLater)

    def is_shaded_day(self, column: int) -> bool:
        if column >= self.table.columnCount() - 1:
            return False

        month_data, day = self._resolve_day_context(column)

        weekday = calendar.weekday(month_data.year, month_data.month, day)
        if weekday >= 5:
            return True

        return day in month_data.holidays
    
    def _handle_row_drop(self):
        """Delegates row drop handling to the drag_drop_handler."""
        # Copy state from MainWindow to handler
        self.drag_drop_handler.row_dragging = self._row_dragging
        self.drag_drop_handler.row_drag_source = self._row_drag_source
        self.drag_drop_handler.row_drag_target = self._row_drag_target
        
        # Execute the drop
        self.drag_drop_handler.handle_row_drop()
        
        # Copy state back from handler to MainWindow
        self._row_dragging = self.drag_drop_handler.row_dragging
        self._row_drag_source = self.drag_drop_handler.row_drag_source
        self._row_drag_target = self.drag_drop_handler.row_drag_target
    
    def is_section_row(self, row: int) -> bool:
        if row < 0 or row >= len(self.rows):
            return False
        
        return self.rows[row]["type"] == "section"





# =====================================================
# 16. APP ENTRY POINT
# =====================================================

def _build_splash_pixmap():
    """
    Build a polished splash screen pixmap with the logo centered
    on a dark background, with app name and version text.
    """
    splash_w, splash_h = 480, 400
    pixmap = QPixmap(splash_w, splash_h)
    pixmap.fill(QColor(30, 30, 40))  # Dark background

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # Load and draw logo (centered, scaled to ~200px)
    logo_path = resource_path("logo.png")
    if os.path.exists(logo_path):
        logo = QPixmap(logo_path)
        logo_size = 200
        scaled = logo.scaled(
            logo_size, logo_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        x = (splash_w - scaled.width()) // 2
        y = 50
        painter.drawPixmap(x, y, scaled)

    # App name
    font = QFont("Segoe UI", 22, QFont.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(0, 280, splash_w, 40, Qt.AlignCenter, "MShift")

    # Subtitle
    font2 = QFont("Segoe UI", 11)
    painter.setFont(font2)
    painter.setPen(QColor(180, 180, 200))
    painter.drawText(0, 320, splash_w, 30, Qt.AlignCenter, "Midwife Scheduler")

    # Version
    font3 = QFont("Segoe UI", 9)
    painter.setFont(font3)
    painter.setPen(QColor(120, 120, 140))
    painter.drawText(0, 360, splash_w, 25, Qt.AlignCenter, f"v{VERSION}")

    painter.end()
    return pixmap


def main():
    app = QApplication(sys.argv)

    # --- Splash Screen ---
    splash_pixmap = _build_splash_pixmap()
    from PyQt5.QtWidgets import QSplashScreen
    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents()

    # Build the main window while the splash is visible
    window = MainWindow()

    # Close splash and show main window after delay
    QTimer.singleShot(SPLASH_DURATION_MS, lambda: (
        splash.finish(window),
        window.show()
    ))

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
