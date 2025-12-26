import sys
import calendar
import uuid

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
    QColorDialog
)
from PyQt5.QtGui import (
    QColor,
    QBrush
)
from PyQt5.QtCore import Qt


# -------------------------
# DATA CLASSES
# -------------------------

class Service:
    def __init__(self, name, short_name, hours, color_hex):
        self.id = str(uuid.uuid4()) # Unique identifier
        self.name = name
        self.short_name = short_name
        self.hours = hours
        self.color_hex = color_hex

class Person:
    def __init__(self, FullName, ShortName, percentage):
        self.id = str(uuid.uuid4()) # Unique identifier
        self.name = FullName
        self.short_name = ShortName
        self.percentage = percentage

class AddPersonDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Person")
        self.setFixedSize(300, 220)

        layout = QFormLayout(self)

        self.nom_edit = QLineEdit()
        self.prenom_edit = QLineEdit()
        self.display_edit = QLineEdit()
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(0, 100)
        self.percent_spin.setValue(100)
        self.percent_spin.stepBy(10)

        layout.addRow("Nom : ", self.nom_edit)
        layout.addRow("Prénom : ", self.prenom_edit)
        layout.addRow("Affichage : ", self.display_edit)
        layout.addRow("Pourcentage : ", self.percent_spin)

        buttons_layout = QHBoxLayout()
        self.create_btn = QPushButton("Créer")
        self.cancel_btn = QPushButton("Annuler")

        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addRow(buttons_layout)

        self.create_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)

        self.nom_edit.textChanged.connect(self._update_display)
        self.prenom_edit.textChanged.connect(self._update_display)

    def _update_display(self):
        nom = self.nom_edit.text().strip()
        prenom = self.prenom_edit.text().strip()

        if nom and prenom :
            self.display_edit.setText(f"{prenom[0].upper()}. {nom}")

    def _on_create(self):
        if not self.nom_edit.text() or not self.prenom_edit.text():
            return #Warning popup later

        self.person = Person(
            FullName = f"{self.prenom_edit.text()} {self.nom_edit.text()}",
            ShortName = self.display_edit.text(),
            percentage = self.percent_spin.value()
        )

        self.accept()

class AddServiceDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Service")
        self.setFixedSize(300,240)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.short_edit = QLineEdit()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(6, 12)
        self.hours_spin.setValue(12)

        self.color_btn = QPushButton("Choisir couleur")
        self.color = QColor("#FFFFFF")
        self._update_color_button()

        layout.addRow("Nom : ", self.name_edit)
        layout.addRow("Affichage : ", self.short_edit)
        layout.addRow("Heures : ", self.hours_spin)
        layout.addRow("Couleur : ", self.color_btn)

        buttons_layout = QHBoxLayout()
        self.create_btn = QPushButton("Créer")
        self.cancel_btn = QPushButton("Annuler")

        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addRow(buttons_layout)

        self.color_btn.clicked.connect(self._choose_color)
        self.create_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)

    def _choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self._update_color_button()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.color.name()};"
        )

    def _on_create(self):
        if not self.name_edit.text():
            return

        self.service = Service(
            self.name_edit.text(),
            self.short_edit.text(),
            self.hours_spin.value(),
            self.color.name()
        )
        self.accept()

class MonthData:
    def __init__(self, year : int, month : int):
        self.year = year
        self.month = month
        # key : (person.id, day)
        self.assignements = {}

    def get_service(self, person_id, day):
        return self.assignements.get((person_id, day))

    def set_service(self, person_id, day, service_id):
        if service_id is None :
            self.assignements.pop((person_id, day), None)
        
        else :
            self.assignements[(person_id, day)] = service_id



# -------------------------
# MAIN WINDOW
# -------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("mshift – Midwife Scheduler")
        self.resize(1100, 600)

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

        self._setup_action_buttons()
        self._setup_controls()
        self._setup_table()
        self._update_headers()

        self._add_person_to_table(Person("Tiphaine Angibaud", "T. Angibaud", 100))

    def _populate_table_from_month(self):
        if not self.current_month:
            return

        for row, person in enumerate(self.people):
            for day in range(1, self.table.columnCount() + 1):
                service_id = self.current_month.get_service(person.id, day)

                if service_id is None:
                    self.table.removeCellWidget(row, day - 1)
                    continue

                service = next(
                    (s for s in self.services if s.id == service_id),
                    None
                )
                if service is None:
                    continue  # service was deleted later

                combo = self._create_service_combo(row, day - 1, service_id)
                self.table.setCellWidget(row, day - 1, combo)


    def _load_month(self):
        year = int(self.year_combo.currentText())
        month = self.month_combo.currentIndex() + 1
        key = (year, month)

        if key not in self.schedule :
            self.schedule[key] = MonthData(year, month)

        self.current_month = self.schedule[key]

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



    # -------------------------
    # UI SETUP
    # -------------------------

    def _setup_controls(self):
        controls_layout = QHBoxLayout()

        self.month_combo = QComboBox()
        self.month_combo.addItems(calendar.month_name[1:])
        self.month_combo.currentIndexChanged.connect(self._update_headers)

        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in range(2024, 2031)])
        self.year_combo.setCurrentText("2025")
        self.year_combo.currentIndexChanged.connect(self._update_headers)

        controls_layout.addWidget(QLabel("Month:"))
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(QLabel("Year:"))
        controls_layout.addWidget(self.year_combo)
        controls_layout.addStretch()

        self.main_layout.addLayout(controls_layout)


    def _setup_table(self):
        self.table = QTableWidget(1, 31)
        self.table.setShowGrid(False)

        # Disable cell selection highlight
        self.table.setSelectionMode(QTableWidget.NoSelection)

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

        self.table.cellClicked.connect(self._on_cell_clicked)

        self.main_layout.addWidget(self.table)

    def _create_service_combo(self, row, column, preset_service = None):
        combo = QComboBox()
        combo.setEditable(True)
        combo.lineEdit().setReadOnly(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)

        combo.addItem("")

        person = self.people[row]
        day = column + 1

        for service in self.services:
            combo.addItem(service.name)

        def on_service_selected(index):
            if index == 0:
                self.current_month.set_service(person.id, day, None)
                combo.setStyleSheet("""
                    QComboBox {
                        border: none;
                        padding-left: 4px;
                    }
                """)
                return

            service = self.services[index - 1]

            self.current_month.set_service(
                person.id,
                day,
                service.id
            )

            combo.setItemText(index, service.short_name)
            combo.setCurrentIndex(index)

            combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {service.color_hex};
                    border: none;
                    padding-left: 4px;
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
            """)

        combo.currentIndexChanged.connect(on_service_selected)

        if preset_service :
            for i, service in enumerate(self.services) :
                if service.id == preset_service :
                   combo.setCurrentIndex(i + 1)
                   break

        return combo



    # -------------------------
    # LOGIC
    # -------------------------

    FRENCH_DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    
    def _update_headers(self):
        # CRITICAL, link backend to frontend
        self._load_month()

        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        days_in_month = calendar.monthrange(year, month)[1]
        self.table.setColumnCount(days_in_month)

        self._clear_cell_backgrounds()

        headers = []
        for day in range(1, days_in_month + 1):
            weekday_index = calendar.weekday(year, month, day)
            weekday_short = self.FRENCH_DAYS[weekday_index]
            item = QTableWidgetItem((f"{weekday_short}\n{day}"))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(day - 1, item)
            if weekday_index >= 5:
                self._shade_weekend_column(day - 1)

        self._populate_table_from_month()

    def _shade_weekend_column(self, column):
        color = QColor(200, 200, 200)

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



    def _on_cell_clicked(self, row, column):
        # Ignore placeholder row
        if row == 0 and self.table.verticalHeaderItem(row) is None:
            return

        combo = self._create_service_combo(row, column)
        self.table.setCellWidget(row, column, combo)
        combo.showPopup()

    

        


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
