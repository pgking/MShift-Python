import sys
import calendar

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLabel
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


# -------------------------
# DATA CLASSES
# -------------------------

class Service:
    def __init__(self, name, short_name, hours, color_hex):
        self.name = name
        self.short_name = short_name
        self.hours = hours
        self.color_hex = color_hex


# -------------------------
# MAIN WINDOW
# -------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("mshift – Midwife Scheduler")
        self.resize(1100, 600)

        # Example services (hardcoded for now)
        self.services = [
            Service("Jour", "J", 12, "#A3D5FF"),
            Service("Nuit", "N", 12, "#FFD6A3"),
            Service("Planning Familial", "GP", 8, "#C3B1E1"),
        ]

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self._setup_controls()
        self._setup_table()
        self._update_headers()


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
        # Placeholder: 5 midwives
        self.table = QTableWidget(5, 31)
        self.table.setVerticalHeaderLabels([
            "Alice",
            "Brigitte",
            "Clara",
            "Diane",
            "Eva"
        ])

        self.table.cellClicked.connect(self._on_cell_clicked)

        self.main_layout.addWidget(self.table)


    # -------------------------
    # LOGIC
    # -------------------------

    def _update_headers(self):
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        days_in_month = calendar.monthrange(year, month)[1]
        self.table.setColumnCount(days_in_month)

        headers = []
        for day in range(1, days_in_month + 1):
            weekday_index = calendar.weekday(year, month, day)
            weekday_short = calendar.day_abbr[weekday_index].lower()
            headers.append(f"{weekday_short}\n{day}")

        self.table.setHorizontalHeaderLabels(headers)


    def _on_cell_clicked(self, row, column):
        # Do not recreate if already filled
        if self.table.cellWidget(row, column) is not None:
            return
        if self.table.item(row, column) is not None:
            return

        combo = QComboBox()
        combo.addItem("")  # empty option

        for service in self.services:
            combo.addItem(service.name)

        def on_service_selected(index):
            if index == 0:
                return

            service = self.services[index - 1]
            item = QTableWidgetItem(service.short_name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setBackground(QColor(service.color_hex))

            self.table.setItem(row, column, item)
            self.table.removeCellWidget(row, column)

        combo.currentIndexChanged.connect(on_service_selected)
        self.table.setCellWidget(row, column, combo)


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
