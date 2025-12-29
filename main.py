import sys
import calendar
import uuid
import json
from datetime import datetime

from models import Person, Service, MonthData, DragTableWidget
from dialogs import AddPersonDialog, AddServiceDialog
from menu_bar import MenuBar

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
    QLineEdit,
    QPushButton,
    QSpinBox,
    QFormLayout,
    QColorDialog,
    QFileDialog
)
from PyQt5.QtGui import (
    QColor,
    QBrush,
    QPainter,
    QPen
)
from PyQt5.QtCore import Qt

# -------------------------
# MAIN WINDOW
# -------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.setWindowTitle("mshift – Midwife Scheduler")
        self.resize(1100, 600)

        self._mouse_pressed_index = None
        self._mouse_press_pos = None
        self._dragging = False
        self._drag_rect = None
        self._drag_source = None

        self.n_prev_days = 3

        self.people = []
        self.services = [
            Service("Jour", "J", 12, "#A3D5FF"),
            Service("Nuit", "N", 12, "#FFD6A3"),
            Service("Planning Familial", "GP", 8, "#C3B1E1"),
        ]

        self.schedule = {} # key : (year, month) -> MonthData
        self.current_month = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._setup_save_load_buttons()
        self._setup_action_buttons()
        self._setup_controls()
        self._setup_table()
        self._update_headers()

        self._add_person_to_table(Person("Tiphaine",  "Angibaud", 100))


    def _populate_table_from_month(self):
        for row, person in enumerate(self.people):
            for col in range(self.table.columnCount()):
                self.table.removeCellWidget(row, col)
                month_data, day = self._resolve_day_context(col)
                service_id = month_data.get_service(person.id, day)

                if service_id is None:
                    continue

                combo = self._create_service_combo(row, col, service_id)
                self.table.setCellWidget(row, col, combo)


    def _load_month(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        key = (year, month)

        if key not in self.schedule :
            self.schedule[key] = MonthData(year, month)

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

        buttons_layout.addWidget(self.add_person_btn)
        buttons_layout.addWidget(self.add_service_btn)
        buttons_layout.addStretch()

        self.main_layout.addLayout(buttons_layout)

    def _add_person_to_table(self, person: Person):
        self.people.append(person)

        if self.table.rowCount() == 1 and self.table.verticalHeaderItem(0) is None:
            row = 0
        else:
            row = self.table.rowCount()
            self.table.insertRow(row)

        self.table.setVerticalHeaderItem(
            row,
            QTableWidgetItem(person.short_name)
        )

        self._update_headers()


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

    def _clear_cell(self, row, column):
        print("Clearing cell")
        person = self.people[row]
        month_data, day = self._resolve_day_context(column)

        # Backend
        month_data.set_service(person.id, day, None)

        # UI
        self.table.removeCellWidget(row, column)

    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
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
            # RIGHT CLICK (DELETE)
            # -----------------
            if event.type() == event.MouseButtonPress and event.button() == Qt.RightButton:
                index = self.table.indexAt(event.pos())
                if not index.isValid():
                    return True

                row = index.row()
                column = index.column()

                # Ignore placeholder row
                if row == 0 and self.table.verticalHeaderItem(row) is None:
                    return True

                person = self.people[row]
                month_data, day = self._resolve_day_context(column)

                service_id = month_data.get_service(person.id, day)
                if service_id is not None:
                    self._clear_cell(row, column)

                return True  # ⛔ consume the event

        return super().eventFilter(obj, event)

    def _start_drag(self, index):
        print("Drag start:", index.row(), index.column())
        row = index.row()
        col = index.column()

        person = self.people[row]
        month_data, day = self._resolve_day_context(col)

        service_id = month_data.get_service(person.id, day)

        if service_id is None :
            return
        
        self._drag_source = (row, col, service_id)

    def _handle_drop(self, source_index, pos):
        if not hasattr(self, "_drag_source"):
            return
        
        target = self.table.indexAt(pos)
        if not target.isValid():
            return

        print("Drop:", source_index.row(), source_index.column(), "->", target.row(), target.column())
        src_row, src_col, service_id = self._drag_source
        tgt_row = target.row()
        tgt_col = target.column()

        # Same cell --> Do nothing
        if src_row == tgt_row and src_col == tgt_col:
            return

        # Backend update
        src_person = self.people[src_row]
        tgt_person = self.people[tgt_row]

        src_month_data, src_day = self._resolve_day_context(src_col)
        tgt_month_data, tgt_day = self._resolve_day_context(tgt_col)

        target_service_id = tgt_month_data.get_service(
            tgt_person.id,
            tgt_day
        )

        # Backend swap
        src_month_data.set_service(src_person.id, src_day, target_service_id)
        tgt_month_data.set_service(tgt_person.id, tgt_day, service_id)

        # UI update
        # Clear both cells
        self.table.removeCellWidget(src_row, src_col)
        self.table.removeCellWidget(tgt_row, tgt_col)

        # Restore source cell if needed
        if target_service_id is not None:
            src_combo = self._create_service_combo(
                src_row,
                src_col,
                preset_service=target_service_id
            )
            self.table.setCellWidget(src_row, src_col, src_combo)

        # Set target cell
        tgt_combo = self._create_service_combo(
            tgt_row,
            tgt_col,
            preset_service=service_id
        )
        self.table.setCellWidget(tgt_row, tgt_col, tgt_combo)

        del self._drag_source

    def _open_cell_dropdown(self, row, column):
        combo = self._ensure_combo(row, column)
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

        save_load_layout.addWidget(self.save_btn)
        save_load_layout.addWidget(self.load_btn)

        self.main_layout.addLayout(save_load_layout)
        

    def _setup_controls(self):
        controls_layout = QHBoxLayout()

        real_life_month = datetime.now().month

        self.month_combo = QComboBox()
        self.month_combo.addItems(calendar.month_name[1:])
        self.month_combo.setCurrentIndex(real_life_month - 1)
        self.month_combo.currentIndexChanged.connect(self._update_headers)

        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in range(2025, 2031)])
        self.year_combo.setCurrentText("2025")
        self.year_combo.currentIndexChanged.connect(self._update_headers)

        controls_layout.addWidget(QLabel("Month:"))
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(QLabel("Year:"))
        controls_layout.addWidget(self.year_combo)
        controls_layout.addStretch()

        self.main_layout.addLayout(controls_layout)


    def _setup_table(self):
        self.table = DragTableWidget(1, 31)
        self.table.setShowGrid(False)

        # Disable cell selection highlight
        self.table.setSelectionMode(QTableWidget.NoSelection)

        self.table.viewport().installEventFilter(self)

        # Keep headers interactive
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)

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

        self.table.verticalHeader().setMinimumWidth(80)

        self.main_layout.addWidget(self.table)

    def _create_service_combo(self, row, column, preset_service = None):
        combo = QComboBox()
        combo.setContextMenuPolicy(Qt.NoContextMenu)
        combo.setEditable(True)
        combo.setAttribute(Qt.WA_TransparentForMouseEvents)

        line = combo.lineEdit()
        line.setReadOnly(True)
        line.setAlignment(Qt.AlignCenter)
        line.setContextMenuPolicy(Qt.NoContextMenu)

        combo.addItem("")

        person = self.people[row]
        month_data, day = self._resolve_day_context(column)

        for service in self.services:
            combo.addItem(service.name)

        def update_combo_style(service=None):
            color = service.color_hex if service else "transparent"
            combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {color};
                    border: none;
                    padding-left: 4px;
                }}
                QComboBox::drop-down {{
                    width: 0px;
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: none;
                }}
            """)

        update_combo_style()

        def on_service_selected(index):
            if index == 0:
                month_data.set_service(person.id, day, None)
                update_combo_style()
                return

            service = self.services[index - 1]

            month_data.set_service(
                person.id,
                day,
                service.id
            )

            combo.setItemText(index, service.short_name)
            combo.setCurrentIndex(index)

            update_combo_style(service)

        combo.currentIndexChanged.connect(on_service_selected)

        if preset_service :
            for i, service in enumerate(self.services) :
                if service.id == preset_service :
                   combo.setCurrentIndex(i + 1)
                   break

        return combo


    def _ensure_combo(self, row, column) :
        combo = self.table.cellWidget(row, column)
        if combo is None :
            combo = self._create_service_combo(row, column)
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
        print("Open services dialog (not implemented yet)")

    def open_about_dialog(self):
        print("Open about dialog (not implemented yet)")

    def new_file(self):
        print("New file")

        # Reset scheduling data only
        self.schedule = {}
        self.current_month = None

        # Reflect UI
        self.table_clear()
        self._refresh_table()




    # -------------------------
    # LOGIC
    # -------------------------
    
    def _update_headers(self):
        # CRITICAL, link backend to frontend
        self._load_month()

        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else  year - 1
        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        days_in_month = calendar.monthrange(year, month)[1]

        total_days = self.n_prev_days + days_in_month
        self.table.setColumnCount(total_days)

        self._clear_cell_backgrounds()

        # Create headers
        for col in range(total_days):
            if col < self.n_prev_days:
                start_day = days_in_prev_month - self.n_prev_days + 1
                day = start_day + col
                display_month = prev_month
                display_year = prev_year

            else :
                day = col - self.n_prev_days + 1
                display_month = month
                display_year = year

            weekday_index = calendar.weekday(display_year, display_month, day)
            weekday_short = self.table.FRENCH_DAYS[weekday_index]
            item = QTableWidgetItem((f"{weekday_short}\n{day}"))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(col, item)
            if weekday_index >= 5:
                self._shade_weekend_column(col)

        self._populate_table_from_month()

        # Reset scroll to beginning
        self.table.horizontalScrollBar().setValue(0)

    def _shade_weekend_column(self, column):
        color = QColor(200, 200, 200, 120)

        for row in range(self.table.rowCount()):
            item = self.table.item(row, column)

            if item is None :
                item = QTableWidgetItem()
                self.table.setItem(row, column, item)

            item.setBackground(color)

    def _clear_cell_backgrounds(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item is not None:
                    item.setBackground(QBrush())

    def _refresh_table(self):
        # Reset the table
        self.table.setRowCount(max(1, len(self.people)))

        # Set vertical headers
        for row, person in enumerate(self.people):
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(person.short_name))

        # Reload the current month
        self._update_headers()

    def table_clear(self):
        """Clears all table content but keeps the table widget itself."""
        self.table.clear()  # Clears all items and headers
        self.table.setRowCount(0)
        self.table.setColumnCount(0)


    def save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Schedule", "", "MShift File (*.mshift)")
        if not path:
            return

        data = {
            "people": [p.to_dict() for p in self.people],
            "services": [s.to_dict() for s in self.services],
            "schedule": {
                f"{year}_{month}": self.schedule[(year, month)].to_dict()
                for year, month in self.schedule
            }
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent = 2)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Schedule", "", "MShift Files (*.mshift)")
        if not path:
            return

        with open (path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Rebuild people and services
        self.people = [Person(**p) for p in data["people"]]
        self.services = [Service(**s) for s in data ["services"]]

        # Rebuild Schedule
        self.schedule = {}
        for key, month_dict in data["schedule"].items():
            self.schedule[tuple(map(int, key.split("_")))] = MonthData.from_dict(month_dict)

        # Refresh UI
        self.table_clear()
        self._refresh_table()

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
