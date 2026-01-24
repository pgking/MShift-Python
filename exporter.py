import openpyxl
import calendar
from openpyxl.styles import PatternFill, Alignment
from PyQt5.QtWidgets import QFileDialog

from cell_authority import resolve_cell_appearance


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
            start_color="DDDDDD",
            end_color="DDDDDD",
            fill_type="solid"
        )


        # First cell = MONTH year
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=2)
        ws.cell(row=1, column=1, value=f"{calendar.month_name[month].upper()} {year}")
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
        
        days_in_month = calendar.monthrange(year, month)[1]
        total_days = days_in_month + self.n_prev_days
        start_col = self.n_prev_days
        last_col = total_days - 1

        # Row 1 days' short names
        for col in range(start_col, total_days):
            m_data, day = self._resolve_day_context(col)
            weekday_index = calendar.weekday(m_data.year, m_data.month, day)
            weekday_short = self.table.FRENCH_DAYS[weekday_index]

            cell = ws.cell(row=1, column=col - start_col + 3)
            cell.value = weekday_short
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Row 2 days numbers
        for col in range(start_col, total_days):
            _, day = self._resolve_day_context(col)
            cell = ws.cell(row=2, column=col - start_col + 3)
            cell.value = day
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Row 1-2 Header for Notes
        notes_header_col = total_days - start_col + 3
        notes_header_cell = ws.cell(row=1, column=notes_header_col, value="NOTES")
        notes_header_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells(start_row=1, start_column=notes_header_col, end_row=2, end_column=notes_header_col)

        max_ratio_length = 0
        ws.freeze_panes = "C3"

        excel_row = 3

        # Fill rows with services
        for row_desc in self.rows:
            # Section row
            if row_desc["type"] == "section":
                # Write label in first column
                cell = ws.cell(row=excel_row, column=1, value=row_desc["label"])

                # Merge two first cells
                ws.merge_cells(
                    start_row=excel_row,
                    start_column=1,
                    end_row=excel_row,
                    end_column=2
                )
                # Merge across all day columns
                ws.merge_cells(
                    start_row=excel_row,
                    start_column=3,
                    end_row=excel_row,
                    end_column=last_col
                )

                # Center the label
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )
                excel_row += 1
                continue
            
            # Person row
            if row_desc["type"] == "person":
                person_id = row_desc["person_id"]
                person = next(p for p in self.people if p.id == person_id)

                # Column A: display_name with percentage (only if not 100%)
                if person.percentage != 100:
                    name_display = f"{person.display_name}  {person.percentage}%"
                else:
                    name_display = person.display_name
                ws.cell(row=excel_row, column=1, value=name_display)

                # Column B : worked hours ratio
                summary = self.workload.monthly_summary(person, year, month)
                worked_hours = summary.worked
                total_hours = summary.expected

                ratio_float = 0 if total_hours == 0 else worked_hours / total_hours
                ratio_str = f"{int(worked_hours)}h / {int(total_hours)}h"

                cell_b = ws.cell(row=excel_row, column=2, value=ratio_str)
                cell_b.alignment = Alignment(horizontal="center", vertical="center")

                # ----- CONDITIONAL FORMATTING -----
                if ratio_float < 0.9:
                    fill_color = "ADD8FF"  # Light Blue
                elif ratio_float > 1.1:
                    fill_color = "FFB4B4"  # Light Red
                else:
                    fill_color = "B4E6B4"  # Light Green


                ws.cell(row=excel_row, column=1).fill = PatternFill(
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
                    cell = ws.cell(row=excel_row, column=col_offset + 3)

                    service_id = month_data.get_service(person.id, day)

                    is_weekend = calendar.weekday(
                        month_data.year,
                        month_data.month,
                        day
                    ) >= 5

                    is_holiday = day in month_data.holidays

                    # --------------------------------------------------
                    # Cell authority decision (single source of truth)
                    # --------------------------------------------------
                    appearance = resolve_cell_appearance(
                        service_id, 
                        is_holiday, 
                        is_weekend, 
                        self.services
                    )

                    if appearance.type == "service" and appearance.service:
                        cell.value = appearance.service.short_name
                        cell.fill = PatternFill(
                            start_color=appearance.service.color_hex.strip("#"),
                            end_color=appearance.service.color_hex.strip("#"),
                            fill_type="solid"
                        )
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif appearance.type == "holiday":
                        cell.value = ""
                        cell.fill = holiday_fill
                    elif appearance.type == "weekend":
                        cell.value = ""
                        cell.fill = weekend_fill
                    else:  # empty
                        cell.value = ""
                    
                # Notes content
                comment = month_data.get_comment(person.id)
                ws.cell(row=excel_row, column=notes_header_col, value=comment)

                excel_row += 1

        # Compute max length of names
        max_name_length = max(len(person.short_name) for person in self.people) + 5

        # set column widths
        ws.column_dimensions['A'].width = max_name_length
        ws.column_dimensions['B'].width = max_ratio_length

        wb.save(path)
        print(f"Exported schedule to {path}")
