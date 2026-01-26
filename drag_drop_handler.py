from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QApplication

class DragDropHandler:
    """
    Handles drag and drop logic for both cells and person rows.
    """
    def __init__(self, mw):
        self.mw = mw
        
        # Cell dragging state
        self.mouse_pressed_index = None
        self.mouse_press_pos = None
        self.dragging = False
        self.drag_source = None # (person_id, col, service_id)

        # Row dragging state
        self.row_dragging = False
        self.row_drag_source = None
        self.row_drag_target = None

    def start_drag(self, index):
        row = index.row()
        col = index.column()

        resolved = self.mw._resolve_person_cell(row, col)
        if not resolved:
            return True
        
        person, month_data, day = resolved
        service_id = month_data.get_service(person.id, day)

        if service_id is None :
            return
        
        self.drag_source = (person.id, col, service_id)

    def replace_service(self, src_person, src_day, src_month_data,
                        tgt_person, tgt_day, tgt_month_data):
        
        src_service_id = src_month_data.get_service(src_person.id, src_day)
        if src_service_id is None:
            return
        
        # Clear source
        self.mw.apply_assignment_change(
            person_id=src_person.id,
            day=src_day,
            service_id=None,
            reason="drag_replace_source"
        )

        # Apply target
        self.mw.apply_assignment_change(
            person_id=tgt_person.id,
            day=tgt_day,
            service_id=src_service_id,
            reason="drag_replace_target"
        )

    def swap_services(self, src_person, src_day, src_month_data,
                      tgt_person, tgt_day, tgt_month_data):
        
        src_service_id = src_month_data.get_service(src_person.id, src_day)
        tgt_service_id = tgt_month_data.get_service(tgt_person.id, tgt_day)

        if src_service_id is None and tgt_service_id is None:
            return
        
        self.mw.apply_assignment_change(
            person_id=src_person.id,
            day=src_day,
            service_id=tgt_service_id,
            reason="drag_swap_source"
        )

        self.mw.apply_assignment_change(
            person_id=tgt_person.id,
            day=tgt_day,
            service_id=src_service_id,
            reason="drag_swap_target"
        )

    def handle_drop(self, source_index, pos):
        if self.drag_source is None:
            return
        
        target = self.mw.table.indexAt(pos)
        if not target.isValid():
            return
        
        # Block if in previous month
        if not self.mw._is_column_in_current_month(target.column()):
            self.mw._abort_drag_with_feedback()
            return
        
        tgt_row = target.row()
        tgt_col = target.column()

        resolved_target = self.mw._resolve_person_cell(tgt_row, tgt_col)
        if not resolved_target:
            return True
        
        tgt_person, tgt_month_data, tgt_day = resolved_target

        src_person_id, src_col, service_id = self.drag_source
        src_row = next(
            i for i, r in enumerate(self.mw.rows)
            if r.get("person_id") == src_person_id
        )

        resolved_source = self.mw._resolve_person_cell(src_row, src_col)
        if not resolved_source:
            return

        src_person, src_month_data, src_day = resolved_source

        target_service_id = tgt_month_data.get_service(
            tgt_person.id,
            tgt_day
        )

        mode = self.mw.preferences.drag_drop_mode
        if target_service_id is None:
            # Empty target → always replace
            self.replace_service(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "swap":
            self.swap_services(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "replace":
            self.replace_service(
                src_person, src_day, src_month_data,
                tgt_person, tgt_day, tgt_month_data
            )

        elif mode == "ask":
            choice = self.mw._ask_drag_drop_action(pos)
            if choice is None:
                return  # Cancelled
            
            if choice == "swap":
                self.swap_services(
                    src_person, src_day, src_month_data,
                    tgt_person, tgt_day, tgt_month_data
                )

            elif choice == "replace":
                self.replace_service(
                    src_person, src_day, src_month_data,
                    tgt_person, tgt_day, tgt_month_data
                )


        # UI update
        self.mw.refresh_cell(src_row, src_col)
        self.mw.refresh_cell(tgt_row, tgt_col)

        self.drag_source = None
        self.mw.refresh_row_headers()

    def handle_row_drop(self):
        if not self.row_dragging:
            return
        
        source = self.row_drag_source
        target = self.row_drag_target

        if source is None or target is None or target == source:
            self.reset_row_drag()
            return
        
        # Remove old widgets from the source row
        for col in range(self.mw.table.columnCount()):
            self.mw.table.removeCellWidget(source, col)

        # Get person rows only
        person_row = self.mw.rows.pop(source)

        insert_index = target
        if target > source:
            insert_index -= 1

        self.mw.rows.insert(insert_index, person_row)

        # Reset dragging flags
        self.reset_row_drag()

        # Clear vertical header colors
        self.mw.table.verticalHeader()._row_colors.clear()

        self.mw.finalize_table_setup()
        self.mw.app_state.save_app_state(self.mw.controller.to_dict())

        if self.mw.preferences.auto_save:
            self.mw.quick_save()

    def reset_row_drag(self):
        self.row_dragging = False
        self.row_drag_source = None
        self.row_drag_target = None

    def handle_events(self, obj, event) -> bool:
        # Only viewport events
        if obj is not self.mw.table.viewport():
            return False
        
        # -----------------
        # LEFT BUTTON PRESS
        # -----------------
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            index = self.mw.table.indexAt(event.pos())
            if not index.isValid():
                return False
            
            self.mouse_pressed_index = index
            self.mouse_press_pos = event.pos()
            self.dragging = False
            return False # Allow propagation
        
        # -----------------
        # MOUSE MOVE (DRAG DETECTION)
        # -----------------
        if event.type() == QEvent.MouseMove and self.mouse_pressed_index is not None:
            if self.mouse_press_pos is None:
                return False
            
            distance = (event.pos() - self.mouse_press_pos).manhattanLength()
            if distance > QApplication.startDragDistance():
                if not self.dragging:
                    self.dragging = True
                    self.start_drag(self.mouse_pressed_index)

                if self.drag_source is not None:
                    target_index = self.mw.table.indexAt(event.pos())
                    if target_index.isValid():
                        self.mw.table.set_drag_rect(self.mw.table.visualRect(target_index))

                return True

            return False
        
        # -----------------
        # LEFT BUTTON RELEASE
        # -----------------
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self.mouse_pressed_index is None:
                return False
            
            if self.dragging:  # If you were dragging
                self.handle_drop(self.mouse_pressed_index, event.pos())
            else:               # If you just clicked
                row = self.mouse_pressed_index.row()
                col = self.mouse_pressed_index.column()
                self.mw._open_cell_dropdown(row, col)

            # Reset Drag State
            self.mouse_pressed_index = None
            self.mouse_press_pos = None
            self.dragging = False
            self.drag_source = None

            self.mw.table.set_drag_rect(None)
            self.mw.table.viewport().update()

            return True
        
        return False
