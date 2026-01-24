from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QTableWidget

class DragTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_rect = None
        self.FRENCH_DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    def set_drag_rect(self, rect: QRect | None):
        self._drag_rect = rect
        self.viewport().update()

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
        # Column shading
        # ----------------------
        color = QColor(200, 200, 200, 120)
        for col in range(self.columnCount()):
            if self._is_shaded_column(col):
                for row in range(self.rowCount()):
                    rect = self.visualRect(self.model().index(row, col))
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
        if mw and mw._should_show_copy_rect():
            mw._paint_copy_rectangle(painter)

        painter.end()

    def _is_shaded_column(self, col: int) -> bool:
        mw = getattr(self, "main_window", None)
        if not mw:
            return False
        
        return mw.is_shaded_day(col)
