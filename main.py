import sys
import calendar
import json
import os

from datetime import datetime

from models import Person, Service, MonthData, DragTableWidget
from dialogs import AddPersonDialog, AddServiceDialog, ManageServicesDialog, PreferencesDialog
from menu_bar import MenuBar
from headers import ColoredVerticalHeader, ClickableHorizontalHeader
from exporter import export_to_excel
from file_io import save_schedule, load_schedule
from service_cell import ServiceCell
from table_rebuilder import TableRebuilder
from workload import WorkloadCalculator
from preferences import Preferences
from rules import evaluate_day_service_counts
from app_state import AppState

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLabel,
    QDialog,
    QPushButton,
    QFileDialog,
    QHeaderView,
    QMenu
)
from PyQt5.QtCore import (
    Qt,
    QEvent
)
from PyQt5.QtGui import (
    QPen,
    QColor,
    QPainter
)


# -------------------------
# MAIN WINDOW
# -------------------------

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
        # 2. INPUT / INTERACTION STATE (ephemeral, never saved)
        # =====================================================
        # Dragging cells
        self._mouse_pressed_index = None
        self._mouse_press_pos = None
        self._dragging = False
        self._drag_rect = None
        self._drag_source = None

        # Dragging person rows
        self._row_dragging = False
        self._row_drag_source = None
        self._row_drag_target = None

        # Copy / Paste
        self._clipboard_service_id = None
        self._clipboard_cell = None
        self._shift_only_down = False

        '''self.people = []
        self.services = [
            Service("Jour", "J", 12, "#A3D5FF"),
            Service("Nuit", "N", 12, "#FFD6A3"),
            Service("Planning Familial", "GP", 8, "#C3B1E1"),
        ]'''

        # =====================================================
        # 3. STATIC DOMAIN (never user-editable)
        # =====================================================
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

        # =====================================================
        # 4. CORE STATE CONTAINERS (will be filled by AppState)
        # =====================================================
        self.schedule = {}          # key : (year, month) -> MonthData
        self.current_month = None
        self.rows = []              # Ordered list of rows (sections + people)
        self.people = []
        self.services = []
        self.preferences = None
        self.n_prev_days = 0

        self.day_service_violations = []

        # =====================================================
        # 5. APP STATE MANAGER
        # =====================================================
        self.app_state = AppState()

        # =====================================================
        # 6. CENTRAL WIDGET & LAYOUT (still no data)
        # =====================================================
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._setup_save_load_buttons()
        self._setup_action_buttons()
        self._setup_controls()
        self._setup_table()

        # =====================================================
        # 7. HELPERS THAT DEPEND ON TABLE EXISTING
        # =====================================================
        self.table_rebuilder = TableRebuilder(self)
        self.workload = WorkloadCalculator(schedule= self.schedule, services= self.services)

        # =====================================================
        # 8. LOAD APP STATE OR FALL BACK TO DEFAULTS
        # =====================================================
        loaded = self.load_app_state()
        if not loaded :
            # ---- First launch defaults ----
            self.preferences = Preferences()
            self.n_prev_days = self.preferences.previous_days_shown

            self.services = [
                Service("Jour", "J", 12, "#A3D5FF"),
                Service("Nuit", "N", 12, "#FFD6A3"),
                Service("Planning Familial", "GP", 8, "#C3B1E1"),
            ]

            self.people = []

            self.rows = []
            self._populate_initial_rows()

            # Optional dev seed
            #self._add_person_to_table(Person("Tiphaine",  "Angibaud", 100))

        # =====================================================
        # 9. EVENT FILTERS & FINAL UI BUILD
        # =====================================================
        self.installEventFilter(self)
        self.finalize_table_setup()

    def _load_month(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        key = (year, month)

        if key not in self.schedule :
            self.schedule[key] = MonthData(year, month)

    def _populate_initial_rows(self):
        """Populate the ordered rows list with static sections.
        People will be appended after this in self.rows."""
        for section in self.sections:
            self.rows.append({
                "type": "section",
                "id": section["id"],
                "label": section["label"]
            })


    def _setup_action_buttons(self):
        buttons_layout = QHBoxLayout()

        self.add_person_btn = QLabel("➕ Add Person")
        self.add_service_btn = QLabel("➕ Add Service")

        # Make them look clickable
        self.add_person_btn.setStyleSheet(
            "padding: 6px; border: 1px solid #888; border-radius: 4px;"
        )
        self.add_service_btn.setStyleSheet(
            "padding: 6px; border: 1px solid #888; border-radius: 4px;"
        )

        self.add_person_btn.setAlignment(Qt.AlignCenter)
        self.add_service_btn.setAlignment(Qt.AlignCenter)

        self.add_person_btn.mousePressEvent = self._open_add_person
        self.add_service_btn.mousePressEvent = self._open_add_service

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_person_btn)
        buttons_layout.addWidget(self.add_service_btn)
        buttons_layout.addStretch()

        self.main_layout.addLayout(buttons_layout)


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
            QTableWidgetItem(person.short_name)
        )

        self.finalize_table_setup()


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

    def eventFilter(self, obj, event):

        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            modifiers = event.modifiers()

            self._shift_only_down = (
                (modifiers & Qt.ShiftModifier)
                and not (modifiers & Qt.ControlModifier)
            )

            self.table.viewport().update()

        # -----------------
        # HANDLE VIEWPORT EVENTS
        # -----------------
        if obj is self.table.viewport():
            # -----------------
            # MOUSEWHELL WITH SHIFT FOR HORIZONTAL SCROLL
            # -----------------
            if obj is self.table.viewport():
                if event.type() == event.Type.Wheel:
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers & Qt.ShiftModifier:
                        delta = event.angleDelta().y()  # vertical wheel movement
                        scroll_amount = int(delta / 32)  # Adjust scroll sensitivity
                        # Scroll horizontally
                        bar = self.table.horizontalScrollBar()
                        bar.setValue(bar.value() - scroll_amount)  # minus to match natural scroll direction
                        return True  # consume event

            # -----------------
            # LEFT BUTTON PRESS
            # -----------------
            if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                index = self.table.indexAt(event.pos())
                if not index.isValid():
                    return True

                self._mouse_pressed_index = index
                self._mouse_press_pos = event.pos()
                self._dragging = False
                return True

            # -------------
            # MOUSE MOVE
            # -------------
            if event.type() == event.MouseMove:
                if self._mouse_pressed_index is None:
                    return False

                if self._dragging:
                    target_index = self.table.indexAt(event.pos())
                    if target_index.isValid():
                        self.table.set_drag_rect(self.table.visualRect(target_index))
                    return True

                distance = (event.pos() - self._mouse_press_pos).manhattanLength()
                if distance > QApplication.startDragDistance():
                    self._dragging = True
                    self._start_drag(self._mouse_pressed_index)
                    return True

            # -----------------
            # LEFT BUTTON RELEASE
            # -----------------
            if event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
                # -----------------
                # SHIFT + LEFT CLICK → PASTE SERVICE
                # -----------------
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.ShiftModifier:
                    # Decide whether paste is allowed based on preference
                    if self.preferences.copy_paste_mode == "linked":
                        if not self._clipboard_is_still_valid():
                            return True
                        
                    elif self.preferences.copy_paste_mode == "persistent":
                        if self._clipboard_service_id is None:
                            return True

                    index = self.table.indexAt(event.pos())
                    if not index.isValid():
                        return True

                    row = index.row()
                    col = index.column()

                    resolved = self._resolve_person_cell(row, col)
                    if not resolved:
                        return True
                    
                    person, month_data, day = resolved

                    existing = month_data.get_service(person.id, day)

                    if existing is not None and not self.preferences.paste_overwrite_existing:
                        return True # Silently refuse
                    
                    # Backend write (single source of truth) if allowed
                    self.apply_assignment_change(
                        person_id=person.id,
                        day=day,
                        service_id=self._clipboard_service_id,
                        reason="paste"
                    )

                    # UI re-projection
                    self.table.removeCellWidget(row, col)

                    combo = self._create_service_combo(
                        row,
                        col,
                        preset_service=self._clipboard_service_id
                    )
                    self.table.setCellWidget(row, col, combo)

                    self.refresh_row_headers()
                    return True

                if self._mouse_pressed_index is None:
                    return False

                index = self._mouse_pressed_index

                if self._dragging:
                    self._handle_drop(index, event.pos())
                else:
                    self._open_cell_dropdown(index.row(), index.column())

                self._mouse_pressed_index = None
                self._mouse_press_pos = None
                self._dragging = False
                self._drag_source = None
                self.table.set_drag_rect(None)
                self.table.viewport().update()
                return True

            # -----------------
            # RIGHT CLICK
            # -----------------
            if event.type() == event.MouseButtonPress and event.button() == Qt.RightButton:
                # -----------------
                # SHIFT + RIGHT CLICK → COPY SERVICE
                # -----------------
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.ShiftModifier:
                    index = self.table.indexAt(event.pos())
                    if not index.isValid():
                        return True

                    row = index.row()
                    col = index.column()

                    resolved = self._resolve_person_cell(row, col)
                    if not resolved:
                        return True
                    
                    person, month_data, day = resolved
                    service_id = month_data.get_service(person.id, day)

                    if service_id is None:
                        return True  # nothing to copy

                    self._clipboard_service_id = service_id
                    self._clipboard_cell = (row, col)
                    print("[COPY] service_id =", service_id)

                    self.table.viewport().update()

                    return True  # ⛔ consume event

                # -----------------
                # RIGHT CLICK TO DELETE
                # -----------------
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
                if service_id is not None:
                    # Backend removal
                    self.apply_assignment_change(
                        person_id=person.id,
                        day=day,
                        service_id=None,
                        reason="delete"
                    )

                    # UI update
                    self.table.removeCellWidget(row, column)
                    self.refresh_row_headers()

                return True  # ⛔ consume the event

        return super().eventFilter(obj, event)

    def _start_drag(self, index):
        print("Drag start:", index.row(), index.column())
        row = index.row()
        col = index.column()

        resolved = self._resolve_person_cell(row, col)
        if not resolved:
            print("Drag aborted : invalid cell")
            return True
        
        person, month_data, day = resolved
        service_id = month_data.get_service(person.id, day)

        if service_id is None :
            print("Drag aborted : empty cell")
            return
        
        self._drag_source = (person.id, col, service_id)

    def _handle_drop(self, source_index, pos):
        if not hasattr(self, "_drag_source") or self._drag_source is None:
            return
        
        target = self.table.indexAt(pos)
        if not target.isValid():
            return

        print("Drop:", source_index.row(), source_index.column(), "->", target.row(), target.column())
        
        tgt_row = target.row()
        tgt_col = target.column()

        resolved_target = self._resolve_person_cell(tgt_row, tgt_col)
        if not resolved_target:
            return True
        
        tgt_person, tgt_month_data, tgt_day = resolved_target

        src_person_id, src_col, service_id = self._drag_source
        src_row = next(
            i for i, r in enumerate(self.rows)
            if r.get("person_id") == src_person_id
        )

        resolved_source = self._resolve_person_cell(src_row, src_col)
        if not resolved_source:
            return

        src_person, src_month_data, src_day = resolved_source

        target_service_id = tgt_month_data.get_service(
            tgt_person.id,
            tgt_day
        )

        mode = self.preferences.drag_drop_mode
        if target_service_id is None:
            # Empty target → always replace
            self._replace_service(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "swap":
            self._swap_services(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "replace":
            self._replace_service(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "ask":
            choice = self._ask_drag_drop_action(pos)
            if choice is None:
                return  # Cancelled
            
            if choice == "swap":
                self._swap_services(
                    src_person, src_day, src_month_data,
                    tgt_person, tgt_day, tgt_month_data
                )

            elif choice == "replace":
                self._replace_service(
                    src_person, src_day, src_month_data,
                    tgt_person, tgt_day, tgt_month_data
                )


        # UI update
        # Clear both cells
        src_row = next(i for i, r in enumerate(self.rows) if r.get("person_id") == src_person_id)
        self.table.removeCellWidget(src_row, src_col)
        self.table.removeCellWidget(tgt_row, tgt_col)

        # Source cell
        src_service_now = src_month_data.get_service(src_person.id, src_day)
        if src_service_now is not None:
            src_combo = self._create_service_combo(
                src_row,
                src_col,
                preset_service=src_service_now
            )
            self.table.setCellWidget(src_row, src_col, src_combo)

        # Target cell
        tgt_service_now = tgt_month_data.get_service(tgt_person.id, tgt_day)
        if tgt_service_now is not None:
            tgt_combo = self._create_service_combo(
                tgt_row,
                tgt_col,
                preset_service=tgt_service_now
            )
            self.table.setCellWidget(tgt_row, tgt_col, tgt_combo)

        del self._drag_source
        self.refresh_row_headers()

    def _handle_row_drop(self):
        if not self._row_dragging:
            return
        
        source = self._row_drag_source
        target = self._row_drag_target

        if source is None or target is None or target == source:
            self._reset_row_drag()
            return
        
        # Remove old widgets from the source row
        for col in range(self.table.columnCount()):
            self.table.removeCellWidget(source, col)

        # Get person rows only
        person_row = self.rows.pop(source)

        insert_index = target
        if target > source:
            insert_index -= 1

        self.rows.insert(insert_index, person_row)

        # Reset dragging flags
        self._reset_row_drag()

        # Clear vertical header colors
        self.table.verticalHeader()._row_colors.clear()

        self.finalize_table_setup()


    def _reset_row_drag(self):
        self._row_dragging = False
        self._row_drag_source = None
        self._row_drag_target = None



    def _open_cell_dropdown(self, row, column):
        print(f"[OPEN DROPDOWN] row = {row}, column = {column}")
        combo = self._ensure_combo(row, column)
        if combo is None:
            print("[OPEN DROPDOWN] combo is None")
            return
        
        try:
            combo.activated.disconnect()
        except TypeError:
            pass

        combo.activated.connect(
            lambda index, c=combo: c._service_cell.apply_service_by_index(index)
        )

        combo.showPopup()



    # -------------------------
    # UI SETUP
    # -------------------------

    def _setup_save_load_buttons(self):
        save_load_layout = QHBoxLayout()

        self.save_btn = QLabel("💾 Save")
        self.load_btn = QLabel("📂 Load")

        for btn in [self.save_btn, self.load_btn]:
            btn.setStyleSheet("padding: 6px; border: 1px solid #888; border-radius: 4px;")
            btn.setAlignment(Qt.AlignCenter)

        self.save_btn.mousePressEvent = lambda e: self.save_file()
        self.load_btn.mousePressEvent = lambda e: self.load_file()

        save_load_layout.addStretch()
        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.load_btn)
        save_load_layout.addStretch()

        self.main_layout.addLayout(save_load_layout)
        

    def _setup_controls(self):
        controls_layout = QHBoxLayout()

        real_life_month = datetime.now().month
        real_life_year = datetime.now().year

        self.month_combo = QComboBox()
        self.month_combo.addItems(calendar.month_name[1:])
        self.month_combo.setCurrentIndex(real_life_month - 1)
        self.month_combo.currentIndexChanged.connect(self.finalize_table_setup)

        # Previous month button
        prev_btn = QPushButton("◀")
        prev_btn.setFixedWidth(32)
        prev_btn.clicked.connect(self._go_to_previous_month)

        # Next month button
        next_btn = QPushButton("▶")
        next_btn.setFixedWidth(32)
        next_btn.clicked.connect(self._go_to_next_month)

        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in range(2025, 2031)])
        self.year_combo.setCurrentText(f"{real_life_year}")
        self.year_combo.currentIndexChanged.connect(self.finalize_table_setup)

        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Month:"))
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(prev_btn)
        controls_layout.addWidget(next_btn)
        controls_layout.addWidget(QLabel("Year:"))
        controls_layout.addWidget(self.year_combo)
        controls_layout.addStretch()

        self.main_layout.addLayout(controls_layout)


    def _setup_table(self):
        self.table = DragTableWidget(1, 31)
        self.table.main_window = self
        self.table.setShowGrid(True)

        # Disable cell selection highlight
        self.table.setSelectionMode(QTableWidget.NoSelection)

        self.table.viewport().installEventFilter(self)
        self.table.horizontalHeader().installEventFilter(self)

        # Keep headers interactive
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)

        header = ClickableHorizontalHeader(self, self.table)
        self.table.setHorizontalHeader(header)
        header.setSectionsClickable(True)


        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-bottom: 5px solid #888;  /* line thickness and color */
                padding: 4px;                   /* optional, for spacing */
                background-color : #f0f0f0;
            }
        """)

        # Optional: make sure the header uses full height for the border
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        header = ColoredVerticalHeader(main_window=self, parent=self.table)
        self.table.setVerticalHeader(header)
        header.setMinimumWidth(80)
        header.setStyleSheet("QHeaderView::section { background: transparent; }")

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.main_layout.addWidget(self.table)

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
    
    def _ensure_combo(self, row, column) :
        combo = self.table.cellWidget(row, column)
        if combo is None :
            combo = self._create_service_combo(row, column)
            if combo :
                self.table.setCellWidget(row, column, combo)

        return combo

    def quick_save(self):
        print("Quick save triggered (not implemented yet)")
        self.save_file()

    def save_and_exit(self):
        print("Save and exit triggered")
        self.quick_save()
        QApplication.quit()

    def open_services_dialog(self):
        dialog = ManageServicesDialog(self.services)

        if dialog.exec_() == QDialog.Accepted:
            self.table_rebuilder.rebuild_cells()
            self.refresh_row_headers()

    def open_preferences(self):
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec():
            old_prev_days = self.preferences.previous_days_shown
            self.preferences = dialog.preferences

            if self.preferences.previous_days_shown != old_prev_days:
                self.n_prev_days = self.preferences.previous_days_shown
                self.finalize_table_setup()


    def open_about_dialog(self):
        print("Open about dialog (not implemented yet)")

    def new_file(self):
        print("New file")

        # Reset scheduling data only
        self.schedule = {}
        self.current_month = None

        # Reflect UI
        self.table_clear()
        self.finalize_table_setup()




    # -------------------------
    # LOGIC
    # -------------------------

    def table_clear(self):
        """Clears all table content but keeps the table widget itself."""
        self.table.clearContents()  # Clears all items
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Schedule", "", "MShift File (*.mshift)")
        if not path:
            return
        save_schedule(self, path)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Schedule", "", "MShift File (*.mshift)")
        if not path:
            return
        load_schedule(self, path)

        # Update workload calculator
        self.workload.schedule = self.schedule
        self.workload.services = self.services

        # UI refresh
        self.table_clear()
        self.finalize_table_setup()

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

    def export_excel(self):
        export_to_excel(self)

    def finalize_table_setup(self):
        self.table_rebuilder.finalize()
        self.table_rebuilder.refresh_column_shading()
        
        self.recompute_current_month_violations()

        self.table.horizontalHeader().viewport().update()


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

            text = f"{person.short_name} ({int(summary.worked)}h / {int(summary.expected)}h)"
            self.table.setVerticalHeaderItem(row_index, QTableWidgetItem(text))

            color = self.workload.status_color(summary.ratio)
            header.set_row_color(row_index, color)

    def _swap_services(self, src_person, src_day, src_month_data,
                   tgt_person, tgt_day, tgt_month_data):
        
        src_service_id = src_month_data.get_service(src_person.id, src_day)
        tgt_service_id = tgt_month_data.get_service(tgt_person.id, tgt_day)

        if src_service_id is None and tgt_service_id is None:
            return
        
        self.apply_assignment_change(
            person_id=src_person.id,
            day=src_day,
            service_id=tgt_service_id,
            reason="drag_swap_source"
        )

        self.apply_assignment_change(
            person_id=tgt_person.id,
            day=tgt_day,
            service_id=src_service_id,
            reason="drag_swap_target"
        )

    def _replace_service(self, src_person, src_day, src_month_data,
                     tgt_person, tgt_day, tgt_month_data):
        
        src_service_id = src_month_data.get_service(src_person.id, src_day)
        if src_service_id is None:
            return

        self.apply_assignment_change(
            person_id=src_person.id,
            day=src_day,
            service_id=None,
            reason="drag_replace_source_clear"
        )

        self.apply_assignment_change(
            person_id=tgt_person.id,
            day=tgt_day,
            service_id=src_service_id,
            reason="drag_replace_target_set"
        )

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
    
    def _paint_copy_rectangle(self, painter):
        if self._clipboard_cell is None:
            return

        row, col = self._clipboard_cell

        rect = self.table.visualRect(
            self.table.model().index(row, col)
        )
        if not rect.isValid():
            return
        
        rect = rect.adjusted(-1, -1, 1, 1)  # Slightly bigger than cell

        pen = QPen(Qt.black)
        pen.setStyle(Qt.DotLine)
        pen.setWidth(2)

        painter.setClipping(False)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)

    
    def _should_show_copy_rect(self):
        return (
            self._shift_only_down and
            self._clipboard_is_still_valid()
        )
    
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

        month_data = self.schedule[(year, month)]
        month_data.set_service(person_id, day, service_id)

        # Recompute violations
        self._recompute_day_service_violations()
        
        # Minimal UI refresh
        self.table.horizontalHeader().viewport().update()

    def _recompute_day_service_violations(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1

        month_data = self.schedule.get((year, month))
        if month_data is None:
            self.day_service_violations = []
            return

        self.day_service_violations = evaluate_day_service_counts(
            month_data=month_data,
            people=self.people,
            services_by_id={s.id: s for s in self.services},
            year=year,
            month=month
        )

    def recompute_current_month_violations(self):
        self._recompute_day_service_violations()

    def get_day_service_violations_for_column(self, column: int):
        """
        Returns a list of DayServiceViolation for the given table column.
        Only for the current month view.
        """
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
    
    def _clipboard_is_still_valid(self) -> bool:
        """
        Returns True if the copied cell still contains
        the same service as when it was copied.
        """
        if self._clipboard_cell is None:
            return False

        if self._clipboard_service_id is None:
            return False

        row, col = self._clipboard_cell

        resolved = self._resolve_person_cell(row, col)
        if not resolved:
            return False

        person, month_data, day = resolved
        current_service_id = month_data.get_service(person.id, day)

        return current_service_id == self._clipboard_service_id
    
    def load_app_state(self):
        path = self.app_state.get_app_state_path()
        if not os.path.exists(path):
            return False

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Preferences
        self.preferences = Preferences.from_dict(
            data.get("preferences", {})
        )
        self.n_prev_days = self.preferences.previous_days_shown

        # People
        self.people = [
            Person(**p) for p in data.get("people", [])
        ]

        # Services
        self.services = [
            Service(**s) for s in data.get("services", [])
        ]

        # Rows
        self.rows = data.get("rows", [])
        
        # Restore last viewed month
        if "last_year" in data and "last_month" in data:
            self.year_combo.setCurrentText(str(data["last_year"]))
            self.month_combo.setCurrentIndex(data["last_month"] - 1)

        return True





# -------------------------
# APP ENTRY POINT
# -------------------------

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
