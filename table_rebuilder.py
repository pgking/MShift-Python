import calendar
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor, QBrush


class TableRebuilder:
    def __init__(self, main_window):
            self.mw = main_window
            self.table = main_window.table

    def finalize(self):
        # 1️⃣ Freeze painting while we rebuild
        self.table.setUpdatesEnabled(False)

        self.rebuild_structure_and_rows()
        # Ensure section rows have no stray items
        for row, row_data in enumerate(self.mw.rows):
            if row_data["type"] == "section":
                for col in range(self.table.columnCount()):
                    self.table.takeItem(row, col)

        self.rebuild_cells()
        self.mw.refresh_row_headers()

        # 6️⃣ One single repaint
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()

    def rebuild_structure(self):
        # CRITICAL, link backend to frontend
        self.mw._load_month()
        
        # Reset the table
        self.table.setRowCount(max(1, len(self.mw.rows)))

        month = self.mw.month_combo.currentIndex() + 1
        year = int(self.mw.year_combo.currentText())

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else  year - 1
        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        days_in_month = calendar.monthrange(year, month)[1]

        total_days = self.mw.n_prev_days + days_in_month
        self.table.setColumnCount(total_days)

        # Create horizontal headers
        for col in range(total_days):
            if col < self.mw.n_prev_days:
                start_day = days_in_prev_month - self.mw.n_prev_days + 1
                day = start_day + col
                display_month = prev_month
                display_year = prev_year

            else :
                day = col - self.mw.n_prev_days + 1
                display_month = month
                display_year = year

            weekday_index = calendar.weekday(display_year, display_month, day)
            weekday_short = self.table.FRENCH_DAYS[weekday_index]
            item = QTableWidgetItem((f"{weekday_short}\n{day}"))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setHorizontalHeaderItem(col, item)

        # Reset scroll to beginning
        self.mw.table.horizontalScrollBar().setValue(0)

    def rebuild_structure_and_rows(self):
        # 1️⃣ Structure: rows, columns, horizontal headers
        self.rebuild_structure()

        # 2️⃣ Vertical headers (sections + people)
        for row_index, row_data in enumerate(self.mw.rows):
            if row_data["type"] == "section":
                self._build_section_row(row_index, row_data["label"])

    def _build_section_row(self, row_index: int, label: str):
        item = QTableWidgetItem(label)
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        font = item.font()
        font.setBold(True)
        item.setFont(font)

        self.table.setVerticalHeaderItem(row_index, item)

    def rebuild_cells(self):
        for row_index, row_data in enumerate(self.mw.rows):
            if row_data["type"] != "person":
                continue

            person = next(p for p in self.mw.people if p.id == row_data["person_id"])
            for col in range(self.table.columnCount()):
                self.table.removeCellWidget(row_index, col)

                month_data, day = self.mw._resolve_day_context(col)
                service_id = month_data.get_service(person.id, day)

                if service_id is None:
                    continue

                combo = self.mw._create_service_combo(
                    row_index,
                    col,
                    preset_service=service_id
                )
                self.table.setCellWidget(row_index, col, combo)



