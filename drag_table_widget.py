from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QTableWidget

class DragTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_rect = None
        self._hover_row = -1
        self._hover_col = -1
        self.FRENCH_DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def set_drag_rect(self, rect: QRect | None):
        self._drag_rect = rect
        self.viewport().update()

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        new_row = index.row() if index.isValid() else -1
        new_col = index.column() if index.isValid() else -1

        if new_row != self._hover_row or new_col != self._hover_col:
            self._hover_row = new_row
            self._hover_col = new_col
            self.viewport().update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_row = -1
        self._hover_col = -1
        self.viewport().update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)  # draw table normally (headers + cells)

        painter = QPainter(self.viewport())

        # ----------------------
        # Section merge
        # ----------------------
        painter.setRenderHint(QPainter.Antialiasing, False)

        for row in range(self.rowCount()):
            if not self.main_window.is_section_row(row):
                continue

            rect = self.visualRect(self.model().index(row, 0))
            if not rect.isValid():
                continue

            # Expand rect to full table width
            rect.setLeft(0)
            rect.setRight(self.viewport().width())

            painter.fillRect(
                rect,
                QColor(245, 245, 245)
            )

        # ----------------------
        # Column shading (Weekends)
        # ----------------------
        color = QColor(200, 200, 200, 120)
        for col in range(self.columnCount()):
            if self._is_shaded_column(col):
                for row in range(self.rowCount()):
                    # Skip shading overlay if the cell has a service (text or background color)
                    # or if it's a section specialized row (handled above)
                    item = self.item(row, col)
                    if item and (item.text() or item.background().style() != Qt.NoBrush):
                        continue
                    if self.main_window.is_section_row(row):
                        continue

                    rect = self.visualRect(self.model().index(row, col))
                    if rect.isValid():
                        painter.fillRect(rect, color)

        # ----------------------
        # Drag rectangle
        # ----------------------
        if self._drag_rect:
            pen = QPen(Qt.black)
            pen.setStyle(Qt.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._drag_rect)

        # ----------------------
        # Copy rectangle
        # ----------------------
        mw = getattr(self, "main_window", None)
        if mw and hasattr(mw, "copy_paste_handler") and mw.copy_paste_handler.should_show_copy_rect():
            mw.copy_paste_handler.paint_copy_rectangle(painter)

        # ----------------------
        # Crosshair highlight
        # ----------------------
        if self._hover_row >= 0 and self._hover_col >= 0:
            pen = QPen(QColor(80, 80, 80, 100))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            vp = self.viewport()

            # Highlight entire row
            first_col_rect = self.visualRect(self.model().index(self._hover_row, 0))
            if first_col_rect.isValid():
                row_rect = QRect(0, first_col_rect.top(), vp.width(), first_col_rect.height())
                painter.drawRect(row_rect)

            # Highlight entire column
            first_row_rect = self.visualRect(self.model().index(0, self._hover_col))
            if first_row_rect.isValid():
                col_rect = QRect(first_row_rect.left(), 0, first_row_rect.width(), vp.height())
                painter.drawRect(col_rect)

        painter.end()

    def _is_shaded_column(self, col: int) -> bool:
        mw = getattr(self, "main_window", None)
        if not mw:
            return False
        
        return mw.is_shaded_day(col)
