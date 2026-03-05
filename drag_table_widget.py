from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygon, QFont
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
        # Split cell rendering
        # ----------------------
        painter.setRenderHint(QPainter.Antialiasing, True)
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if not item or item.data(Qt.UserRole) != "split":
                    continue
                
                rect = self.visualRect(self.model().index(row, col))
                if not rect.isValid():
                    continue
                
                am_color = QColor(item.data(Qt.UserRole + 1) or "#FFFFFF")
                pm_color = QColor(item.data(Qt.UserRole + 2) or "#FFFFFF")
                am_text = item.data(Qt.UserRole + 3) or ""
                pm_text = item.data(Qt.UserRole + 4) or ""
                
                # Use actual pixel boundaries (QRect.right/bottom are off by 1)
                r_left = rect.x()
                r_top = rect.y()
                r_right = rect.x() + rect.width()
                r_bottom = rect.y() + rect.height()
                
                # Morning triangle (top-left)
                am_poly = QPolygon([
                    QPoint(r_left, r_bottom),
                    QPoint(r_left, r_top),
                    QPoint(r_right, r_top)
                ])
                
                # Afternoon triangle (bottom-right)
                pm_poly = QPolygon([
                    QPoint(r_left, r_bottom),
                    QPoint(r_right, r_top),
                    QPoint(r_right, r_bottom)
                ])
                
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(am_color))
                painter.drawPolygon(am_poly)
                
                painter.setBrush(QBrush(pm_color))
                painter.drawPolygon(pm_poly)
                
                # Diagonal line (bottom-left to top-right)
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.drawLine(QPoint(r_left, r_bottom), QPoint(r_right, r_top))
                
                # Short name labels
                painter.setPen(QPen(QColor(0, 0, 0)))
                font = painter.font()
                base_size = font.pointSizeF()
                small_font = QFont(font)
                small_font.setPointSizeF(max(5, base_size * 0.85))
                # Inherit formatting from item's font
                item_font = item.font()
                small_font.setBold(item_font.bold() if item_font.bold() else True)
                small_font.setItalic(item_font.italic())
                small_font.setUnderline(item_font.underline())
                painter.setFont(small_font)
                
                # AM text: midpoint between top-left corner and cell center
                if am_text:
                    am_cx = rect.left() + rect.width() // 4
                    am_cy = rect.top() + rect.height() // 4
                    tw = rect.width() // 2
                    th = rect.height() // 2
                    am_rect = QRect(am_cx - tw // 2, am_cy - th // 2, tw, th)
                    painter.drawText(am_rect, Qt.AlignCenter, am_text)
                
                # PM text: midpoint between bottom-right corner and cell center
                if pm_text:
                    pm_cx = rect.right() - rect.width() // 4
                    pm_cy = rect.bottom() - rect.height() // 4
                    tw = rect.width() // 2
                    th = rect.height() // 2
                    pm_rect = QRect(pm_cx - tw // 2, pm_cy - th // 2, tw, th)
                    painter.drawText(pm_rect, Qt.AlignCenter, pm_text)
                
                # Restore font
                painter.setFont(font)
        
        painter.setRenderHint(QPainter.Antialiasing, False)

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
