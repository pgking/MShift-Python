# ============================================================
# 1. Imports
# ============================================================

# stdlib
import os
import sys
import calendar

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
    QBrush
)

# App modules
from models import Person, Service, MonthData, Schema, SchemaAssignment
from dialogs import AddPersonDialog, AddServiceDialog, ManageServicesDialog, PreferencesDialog
from schema_dialogs import CreateSchemaDialog, ManageSchemasDialog
from menu_bar import MenuBar
from exporter import export_to_excel
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
from dev_seed import load_dev_data

VERSION = "1.0.4"

# ============================================================
# 2. Main Window
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

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
        self._watcher_timer.setInterval(5000) # Check every 5 seconds
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
        QTimer.singleShot(2000, lambda: self.updater.start_check(silent=True))

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
            # DEV SEED DATA - Set to False for production
            # =====================================================
            DEV_MODE = True  # ✅ Change to False for production
            
            if DEV_MODE:
                load_dev_data(self)

        # =====================================================
        # 8b. AUTO-LOAD LAST FILE
        # =====================================================
        if self.controller.recent_files:
            last_file = self.controller.recent_files[0]
            if os.path.exists(last_file):
                print(f"Auto-loading last file: {last_file}")
                load_schedule(self.controller, last_file)
                self.current_file_path = last_file
                self.last_file_mtime = os.path.getmtime(last_file)

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

    def closeEvent(self, event):
        self.controller.last_year = int(self.year_combo.currentText())
        self.controller.last_month = self.month_combo.currentIndex() + 1
        self.app_state.save_app_state(self.controller.to_dict())
        super().closeEvent(event)

    # =====================================================
    # 5. TABLE STRUCTURE & PROJECTION
    # =====================================================
    def finalize_table_setup(self):
        # Auto-apply schemas for this month
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        self.controller.auto_apply_schemas(year, month)
        
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

        # FORCE visual update of the vertical header
        header.viewport().update()

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
                if modifiers & Qt.ShiftModifier:
                    delta = event.angleDelta().y()
                    bar = self.table.horizontalScrollBar()
                    bar.setValue(bar.value() - (delta // 12))
                    return True
                    
        return super().eventFilter(obj, event)

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
        dialog = AddPersonDialog()
        if dialog.exec():
           self._add_person_to_table(dialog.person)

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
                    overwrite=True,  # Default to overwriting
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
                save_schedule(self.controller, self.current_file_path)
                # Wait a tiny bit for the OS to finalize the write
                self.last_file_mtime = os.path.getmtime(self.current_file_path)
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
            save_schedule(self.controller, path)
            self.current_file_path = os.path.abspath(path)
            self.last_file_mtime = os.path.getmtime(path)
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
        load_schedule(self.controller, path)
        self.current_file_path = os.path.abspath(path)
        self.last_file_mtime = os.path.getmtime(path)
        self._add_to_recent_files(path)

        # UI refresh
        self.table_clear()
        self.finalize_table_setup()
        self._watcher_timer.start()

    def _check_file_for_updates(self):
        if self._is_saving_to_disk:
            return

        if not self.current_file_path or not os.path.exists(self.current_file_path):
            return

        try:
            mtime = os.path.getmtime(self.current_file_path)
            # Add a small tolerance (0.1s) to avoid sub-second timestamp jitter
            if mtime > self.last_file_mtime + 0.1:
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
        
        # Limit to 3
        self.recent_files = self.recent_files[:3]
        
        # Update UI
        self.menu_bar.update_recent_menu(self.recent_files)
        
        # Persist
        self.app_state.save_app_state(self.controller.to_dict())

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

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
