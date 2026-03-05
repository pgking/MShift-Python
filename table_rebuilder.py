import calendar
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from PyQt5.QtGui import QColor, QBrush, QFont


class TableRebuilder:
    def __init__(self, main_window):
            self.mw = main_window
            self.table = main_window.table

    def finalize(self):
        # 1️⃣ Freeze painting while we rebuild
        self.table.setUpdatesEnabled(False)
        
        # Clear header stats
        if hasattr(self.table.verticalHeader(), "clear_stats"):
             self.table.verticalHeader().clear_stats()

        self.rebuild_structure_and_rows()

        # Zoom factor
        zoom = getattr(self.mw, '_zoom_factor', 1.0)

        # Row Height (zoomed)
        base_row_h = self.mw.preferences.row_height
        self.table.verticalHeader().setDefaultSectionSize(int(base_row_h * zoom))

        # Column width (zoomed)
        base_col_w = self.mw.preferences.column_width
        scaled_col_w = int(base_col_w * zoom)
        for col in range(self.table.columnCount()):
            if col == self.table.columnCount() - 1:
                # Notes Column - Dynamic Width
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            else:
                self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                self.table.setColumnWidth(col, scaled_col_w)

        # Font (zoomed)
        if hasattr(self.mw, '_base_font'):
            scaled_font = QFont(self.mw._base_font)
            scaled_font.setPointSizeF(self.mw._base_font.pointSizeF() * zoom)
            self.table.setFont(scaled_font)
            self.table.horizontalHeader().setFont(scaled_font)
            self.table.verticalHeader().setFont(scaled_font)

        # Vertical header width (zoomed)
        base_header_w = 80
        self.table.verticalHeader().setMinimumWidth(int(base_header_w * zoom))

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
        self.table.setColumnCount(total_days + 1) # +1 for Notes column

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

        # Last column header for Notes
        notes_item = QTableWidgetItem("Notes")
        notes_item.setTextAlignment(Qt.AlignCenter)
        self.table.setHorizontalHeaderItem(total_days, notes_item)

        # Reset scroll to beginning
        self.mw.table.horizontalScrollBar().setValue(0)

    def rebuild_structure_and_rows(self):
        # 1️⃣ Structure: rows, columns, horizontal headers
        self.rebuild_structure()

        year = int(self.mw.year_combo.currentText())
        month = self.mw.month_combo.currentIndex() + 1

        # 2️⃣ Vertical headers (sections + people)
        for row_index, row_data in enumerate(self.mw.rows):
            if row_data["type"] == "section":
                self._build_section_row(row_index, row_data["label"])
            elif row_data["type"] == "person":
                # Populate Header Stats
                person_id = row_data["person_id"]
                stats = self.mw.controller.calculate_stats_for_month(person_id, year, month)
                if hasattr(self.table.verticalHeader(), "set_person_stats"):
                     self.table.verticalHeader().set_person_stats(row_index, stats)

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
                # ALWAYS clear previous widgets to regain performance
                self.table.removeCellWidget(row_index, col)

                # 1. Notes Column (Item with text)
                if col == self.table.columnCount() - 1:
                    year = int(self.mw.year_combo.currentText())
                    month = self.mw.month_combo.currentIndex() + 1
                    month_data = self.mw.schedule.get((year, month))
                    
                    comment = month_data.get_comment(person.id) if month_data else ""
                    item = QTableWidgetItem(comment)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                    self.table.setItem(row_index, col, item)
                    continue

                # 2. Service Cells (Item with color and short name)
                month_data, day = self.mw._resolve_day_context(col)
                service_id = month_data.get_service(person.id, day)

                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setTextAlignment(Qt.AlignCenter)

                if service_id:
                    service = next((s for s in self.mw.services if s.id == service_id), None)
                    if service:
                        if service.id == "builtin_note":
                            # Custom Note Logic
                            note_text = month_data.get_note(person.id, day)
                            if note_text:
                                item.setText(note_text)
                                item.setToolTip(note_text)
                            else:
                                item.setText(service.short_name) # "📝"
                            item.setBackground(QBrush(QColor(service.color_hex)))
                        elif service.id == "builtin_split":
                            # Split cell - store rendering data
                            split_info = month_data.get_split(person.id, day)
                            if split_info:
                                am_svc = next((s for s in self.mw.services if s.id == split_info["am"]), None) if split_info.get("am") else None
                                pm_svc = next((s for s in self.mw.services if s.id == split_info["pm"]), None) if split_info.get("pm") else None
                                
                                item.setData(Qt.UserRole, "split")
                                item.setData(Qt.UserRole + 1, am_svc.color_hex if am_svc else "#FFFFFF")
                                item.setData(Qt.UserRole + 2, pm_svc.color_hex if pm_svc else "#FFFFFF")
                                item.setData(Qt.UserRole + 3, am_svc.short_name if am_svc else "")
                                item.setData(Qt.UserRole + 4, pm_svc.short_name if pm_svc else "")
                                
                                am_name = am_svc.name if am_svc else "—"
                                pm_name = pm_svc.name if pm_svc else "—"
                                item.setToolTip(f"Matin : {am_name}\nAprès-midi : {pm_name}")
                            else:
                                item.setData(Qt.UserRole, "split")
                                item.setData(Qt.UserRole + 1, "#FFFFFF")
                                item.setData(Qt.UserRole + 2, "#FFFFFF")
                                item.setData(Qt.UserRole + 3, "")
                                item.setData(Qt.UserRole + 4, "")
                            
                            item.setText("")
                            item.setBackground(QBrush(QColor("#FFFFFF")))
                        else:
                            # Standard service
                            item.setText(service.short_name)
                            item.setBackground(QBrush(QColor(service.color_hex)))
                
                # Apply cell text formatting (bold/italic/underline)
                fmt = month_data.get_cell_format(person.id, day)
                if fmt:
                    font = item.font()
                    font.setBold(fmt.get("bold", False))
                    font.setItalic(fmt.get("italic", False))
                    font.setUnderline(fmt.get("underline", False))
                    item.setFont(font)
                
                self.table.setItem(row_index, col, item)



