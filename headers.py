from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QHeaderView, QMenu
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

class ColoredVerticalHeader(QHeaderView):
    def __init__(self, main_window, parent=None):
        super().__init__(Qt.Vertical, parent)
        self._row_colors = {}
        self.main_window = main_window
        self.setMouseTracking(True)
        self._drop_indicator_row = None

    def set_row_color(self, row, color):
        self._row_colors[row] = color
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        color = self._row_colors.get(logicalIndex)

        if color:
            painter.save()
            painter.fillRect(rect, color)
            painter.restore()
        
        painter.save()
        painter.setBrush(Qt.NoBrush)
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._drop_indicator_row is None:
            return

        painter = QPainter(self.viewport())
        pen = QPen(QColor(50, 50, 50))
        pen.setWidth(2)
        painter.setPen(pen)

        # Clamp index to valid range
        index = min(self._drop_indicator_row, self.count() - 1)

        y = self.sectionViewportPosition(index)

        # If indicator is *after* last row, draw below it
        if self._drop_indicator_row >= self.count():
            y += self.sectionSize(index)

        painter.drawLine(0, y, self.width(), y)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.logicalIndexAt(event.pos())
            # Check if this is a person row
            if index >= 0 and self.main_window.rows[index]["type"] == "person":
                self.main_window._row_dragging = True
                self.main_window._row_drag_source = index
                self.main_window._row_drag_target = index
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.main_window._row_dragging:
            super().mouseMoveEvent(event)
            return
        
        pos = event.pos()
        index = self.logicalIndexAt(event.pos())
        if index < 0:
            self._drop_indicator_row = None
            self.viewport().update()
            return
        
        y = self.sectionViewportPosition(index)
        h = self.sectionSize(index)
        rect = QRect(0, y, self.width(), h)

        # Decide if we are above or below the row
        if pos.y() < rect.center().y():
            self._drop_indicator_row = index
            self.main_window._row_drag_target = index

        else :
            self._drop_indicator_row = index + 1
            self.main_window._row_drag_target = index + 1
        self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.main_window._row_dragging:
            self.main_window._handle_row_drop()

        self._drop_indicator_row = None
        self.viewport().update()
        super().mouseReleaseEvent(event)

class ClickableHorizontalHeader(QHeaderView):
    def __init__(self, main_window, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.main_window = main_window
        self.setSectionsClickable(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            col = self.logicalIndexAt(event.pos())
            if col < 0:
                return

            month_data, day = self.main_window._resolve_day_context(col)

            menu = QMenu()
            if day in month_data.holidays:
                menu.addAction("Enlever férié", lambda: self.toggle_holiday(col, month_data))
            else:
                menu.addAction("Rendre férié", lambda: self.toggle_holiday(col, month_data))

            menu.exec_(self.mapToGlobal(event.pos()))
        else:
            super().mousePressEvent(event)

    def toggle_holiday(self, col, month_data):
        _, day = self.main_window._resolve_day_context(col)
        month_data.toggle_holiday(day)

        self.main_window.table_rebuilder.refresh_column_shading()
        self.main_window.refresh_row_headers()
