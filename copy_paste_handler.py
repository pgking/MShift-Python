from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPen

class CopyPasteHandler:
    """
    Handles copy and paste logic for the schedule table.
    Shift + Right Click to Copy
    Shift + Left Click to Paste
    """
    def __init__(self, mw):
        self.mw = mw
        self.clipboard_service_id = None
        self.clipboard_cell = None
        self.clipboard_note_text = None
        self.clipboard_split_data = None

    def is_clipboard_valid(self) -> bool:
        """
        Returns True if the copied cell still contains
        the same service as when it was copied.
        """
        if self.clipboard_cell is None:
            return False

        if self.clipboard_service_id is None:
            return False

        row, col = self.clipboard_cell

        resolved = self.mw._resolve_person_cell(row, col)
        if not resolved:
            return False

        person, month_data, day = resolved
        current_service_id = month_data.get_service(person.id, day)

        return current_service_id == self.clipboard_service_id

    def should_show_copy_rect(self) -> bool:
        return (
            self.mw._shift_only_down and
            self.is_clipboard_valid()
        )

    def paint_copy_rectangle(self, painter):
        if self.clipboard_cell is None:
            return

        row, col = self.clipboard_cell

        rect = self.mw.table.visualRect(
            self.mw.table.model().index(row, col)
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

    def handle_events(self, obj, event) -> bool:
        # Only handle viewports interactions
        if obj is not self.mw.table.viewport():
            return False
        
        modifiers = QApplication.keyboardModifiers()
        if not (modifiers & Qt.ShiftModifier):
            return False
        
        # --------------------------------
        # SHIFT + RIGHT CLICK → COPY
        # --------------------------------
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            index = self.mw.table.indexAt(event.pos())
            if not index.isValid():
                return True
            
            resolved = self.mw._resolve_person_cell(index.row(), index.column())
            if not resolved:
                return True
            
            person, month_data, day = resolved
            service_id = month_data.get_service(person.id, day)
            if service_id is None:
                return True
            
            self.clipboard_service_id = service_id
            self.clipboard_cell = (index.row(), index.column())
            
            # Capture Note
            if service_id == "builtin_note":
                self.clipboard_note_text = month_data.get_note(person.id, day)
            else:
                self.clipboard_note_text = None
            
            # Capture Split data
            if service_id == "builtin_split":
                self.clipboard_split_data = month_data.get_split(person.id, day)
            else:
                self.clipboard_split_data = None

            self.mw.table.viewport().update()
            return True
        
        # --------------------------------
        # SHIFT + LEFT CLICK → PASTE
        # --------------------------------
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            # Paste permission based on preference
            if self.mw.preferences.copy_paste_mode == "linked":
                if not self.is_clipboard_valid():
                    return True
                
            else : # Persistent
                if self.clipboard_service_id is None:
                    return True
                
            index = self.mw.table.indexAt(event.pos())
            if not index.isValid():
                return True
            
            resolved = self.mw._resolve_person_cell(index.row(), index.column())
            if not resolved:
                return True
            
            person, month_data, day = resolved
            existing = month_data.get_service(person.id, day)

            if existing is not None and not self.mw.preferences.paste_overwrite_existing:
                return True
            
            # Backend update
            self.mw.apply_assignment_change(
                person_id=person.id,
                day=day,
                service_id=self.clipboard_service_id,
                reason="paste"
            )
            
            # Apply Note if needed
            if self.clipboard_service_id == "builtin_note":
                month_data.set_note(person.id, day, self.clipboard_note_text)
            
            # Apply Split data if needed
            if self.clipboard_service_id == "builtin_split" and self.clipboard_split_data:
                month_data.set_split(person.id, day, self.clipboard_split_data["am"], self.clipboard_split_data["pm"])

            # UI Update
            self.mw.refresh_cell(index.row(), index.column())
            self.mw.refresh_row_headers()
            return True
        
        return False
