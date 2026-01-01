import openpyxl
import calendar
from openpyxl.styles import PatternFill, Alignment
from PyQt5.QtWidgets import QFileDialog


def export_to_excel(self):
        month = self.month_combo.currentIndex() + 1
        year = int(self.year_combo.currentText())

        key = (year, month)
        if key not in self.schedule:
            print("No data to export for this month")
            return

        month_data = self.schedule[key]

        path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{calendar.month_name[month].upper()} {year}"

        weekend_fill = PatternFill(
            start_color="DDDDDD",
            end_color="DDDDDD",
            fill_type="solid"
        )

        holiday_fill = PatternFill(
            start_color="CCCCCC",
            end_color="CCCCCC",
            fill_type="solid"
        )


        # First cell = MONTH year
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=2)
        ws.cell(row=1, column=1, value=f"{calendar.month_name[month].upper()} {year}")
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
        
        days_in_month = calendar.monthrange(year, month)[1]
        total_days = days_in_month + self.n_prev_days
        start_col = self.n_prev_days

        # Row 1 days' short names
        for col in range(start_col, total_days):
            month_data, day = self._resolve_day_context(col)

            # Compute weekday short names
            weekday_index = calendar.weekday(month_data.year, month_data.month, day)
            weekday_short = self.table.FRENCH_DAYS[weekday_index]

            cell = ws.cell(row = 1, column = col - start_col + 3)
            cell.value = weekday_short
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Row 2 days numbers
        for col in range(start_col, total_days):
            month_data, day = self._resolve_day_context(col)

            cell = ws.cell(row = 2, column = col - start_col + 3)
            cell.value = day
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Shade weekends and holidays
        first_data_row = 3
        last_data_row = first_data_row + len(self.people) - 1
        max_row = ws.max_row

        for col in range(start_col, total_days):
            month_data, day = self._resolve_day_context(col)

            excel_col = col - start_col + 3  # C = first day column

            is_weekend = calendar.weekday(
                month_data.year,
                month_data.month,
                day
            ) >= 5

            is_holiday = day in month_data.holidays

            if not is_weekend and not is_holiday:
                continue

            fill = holiday_fill if is_holiday else weekend_fill

            for row in range(1, last_data_row + 1):
                ws.cell(row=row, column=excel_col).fill = fill


        max_ratio_length = 0
        ws.freeze_panes = "C3"

        # Fill rows with services
        for row_idx, person in enumerate(self.people, start=2):
            # Column A: short_name
            short_name = f"{person.short_name}  {person.percentage if person.percentage != 100 else ''}%"
            ws.cell(row=row_idx + 1, column=1, value=short_name)

            # Column B : worked hours ratio
            worked_hours = self._worked_hours_for_person(person, year, month)
            total_hours = self._expected_hours_for_month(person, year, month)

            ratio_float = 0 if total_hours == 0 else worked_hours / total_hours
            ratio_str = f"{int(worked_hours)}h / {int(total_hours)}h"

            cell_b = ws.cell(row=row_idx + 1, column=2, value=ratio_str)
            cell_b.alignment = Alignment(horizontal="center", vertical="center")

            # ----- CONDITIONAL FORMATTING -----
            if ratio_float < 0.9:
                fill_color = "ADD8FF"  # Light Blue
            elif ratio_float > 1.1:
                fill_color = "FFB4B4"  # Light Red
            else:
                fill_color = "B4E6B4"  # Light Green


            ws.cell(row=row_idx + 1, column=1).fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid"
            )
            cell_b.fill = PatternFill(
                start_color=fill_color,
                end_color=fill_color,
                fill_type="solid"
            )

            max_ratio_length = max(max_ratio_length, len(ratio_str))

            for col_offset, col in enumerate(range(start_col, total_days)):
                month_data, day = self._resolve_day_context(col)
                service_id = month_data.get_service(person.id, day)
                cell = ws.cell(row=row_idx + 1, column=col_offset + 3)

                if service_id is None:
                    cell.value = ""
                    continue

                service = next((s for s in self.services if s.id == service_id), None)
                if service:
                    cell.value = service.short_name
                    cell.fill = PatternFill(start_color=service.color_hex.strip("#"),
                                            end_color=service.color_hex.strip("#"),
                                            fill_type="solid")
                    cell.alignment = Alignment(horizontal="center", vertical="center")

        # Compute max length of names
        max_name_length = max(len(person.short_name) for person in self.people)

        # set column widths
        ws.column_dimensions['A'].width = max_name_length
        ws.column_dimensions['B'].width = max_ratio_length

        wb.save(path)
        print(f"Exported schedule to {path}")
