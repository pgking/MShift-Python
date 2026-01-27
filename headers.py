from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtWidgets import QHeaderView, QMenu, QToolTip
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygon, QBrush

from rules import Severity

class ColoredVerticalHeader(QHeaderView):
    def __init__(self, main_window, parent=None):
        super().__init__(Qt.Vertical, parent)
        self._row_colors = {}
        self._person_stats = {} # {row_index: stats_dict}
        self.main_window = main_window
        self.setMouseTracking(True)
        self._drop_indicator_row = None

    def set_row_color(self, row, color):
        self._row_colors[row] = color
        self.viewport().update()

    def set_person_stats(self, row, stats):
        self._person_stats[row] = stats
        # Trigger update of this section?
        # self.headerDataChanged(Qt.Vertical, row, row) usually works but viewport update is safer
        self.viewport().update()

    def clear_stats(self):
        self._person_stats.clear()

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

        # Draw Stats if available
        stats = self._person_stats.get(logicalIndex)
        if stats:
            self._paint_stats_circles(painter, rect, stats)

    def _get_stats_geometry(self, rect):
        """Returns (night_rect, weekend_rect) relative to rect."""
        circle_size = 10
        margin_right = 6
        spacing = 4
        
        # Right aligned
        x = rect.right() - margin_right - circle_size
        
        # Centered vertically
        total_h = (2 * circle_size) + spacing
        start_y = rect.center().y() - (total_h / 2) + (circle_size / 2)
        
        night_rect = QRect(x, int(start_y - circle_size/2), circle_size, circle_size)
        weekend_rect = QRect(x, int(start_y + circle_size/2 + spacing), circle_size, circle_size)
        
        return night_rect, weekend_rect

    def _paint_stats_circles(self, painter, rect, stats):
        night_rect, weekend_rect = self._get_stats_geometry(rect)
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        
        # Night Circle
        if stats["night_count"] is not None:
             col_hex = stats.get("night_color", "#000000")
             painter.setBrush(QBrush(QColor(col_hex)))
             painter.drawEllipse(night_rect)

        # Weekend Circle
        if stats["weekend_stats"] is not None:
             col_hex = stats.get("weekend_color", "#C8C8C8")
             painter.setBrush(QBrush(QColor(col_hex)))
             painter.drawEllipse(weekend_rect)

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
        # 1. Handle Stats Tooltips
        index = self.logicalIndexAt(event.pos())
        tooltip_shown = False
        
        if index >= 0:
            stats = self._person_stats.get(index)
            if stats:
                y = self.sectionViewportPosition(index)
                h = self.sectionSize(index)
                # Reconstruct absolute rect for hit testing geometry logic
                # (Geometry logic expects rect based on section position?)
                # _get_stats_geometry uses rect.right(), rect.center().
                # so we need visual rect relative to viewport.
                rect = QRect(0, y, self.width(), h)
                
                night_rect, weekend_rect = self._get_stats_geometry(rect)
                
                pos = event.pos()
                if night_rect.contains(pos) and stats["night_count"] is not None:
                    QToolTip.showText(event.globalPos(), f"Nuits : {stats['night_count']}", self)
                    tooltip_shown = True
                elif weekend_rect.contains(pos) and stats["weekend_stats"] is not None:
                    sat, sun = stats["weekend_stats"]
                    QToolTip.showText(event.globalPos(), f"Samedi : {sat}, Dimanche : {sun}", self)
                    tooltip_shown = True

        if not tooltip_shown:
             # Hide tooltip if we moved out of circle but still in header?
             # QToolTip.hideText() # This might flicker if moving fast?
             # But we must allow super behavior?
             pass

        # 2. Handle Row Dragging
        if not self.main_window._row_dragging:
            super().mouseMoveEvent(event)
            return
        
        pos = event.pos()
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
    ICON_SIZE = 13
    ICON_SPACING = 4
    ICON_MARGIN = 4

    def __init__(self, main_window, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.main_window = main_window
        self.setMouseTracking(True)
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
        
        # Recompute violations after state change
        self.main_window.recompute_current_month_violations()
        self.main_window.refresh_row_headers()
        
        self.main_window.table.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        if self.main_window.is_shaded_day(logicalIndex):
            painter.save()
            painter.fillRect(rect, QColor(200, 200, 200))
            painter.restore()
        
        super().paintSection(painter, rect, logicalIndex)

        violations = self.main_window.get_day_service_violations_for_column(logicalIndex)
        if not violations:
            return

        painter.save()
        painter.setClipping(False)

        inner = rect.adjusted(
            self.ICON_MARGIN,
            self.ICON_MARGIN,
            -self.ICON_MARGIN,
            -self.ICON_MARGIN
        )

        icon_size = self.ICON_SIZE
        spacing = self.ICON_SPACING

        x = inner.right() - icon_size
        y = inner.top()

        for violation in violations:
            if violation.severity == Severity.MISSING:
                # 🔺 Triangle (pointing up)
                half = icon_size // 2
                triangle = QPolygon([
                    QPoint(x, y + icon_size),
                    QPoint(x + icon_size, y + icon_size),
                    QPoint(x + half, y)
                ])
                color = self.main_window.get_service_color_for_kind(violation.service_kind)
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawPolygon(triangle)

            elif violation.severity == Severity.EXCESS:
                # ❓ Question mark
                color = self.main_window.get_service_color_for_kind(violation.service_kind)
                painter.setPen(color)
                font = painter.font()
                font.setBold(True)
                font.setPointSize(9)
                painter.setFont(font)
                painter.drawText(
                    x,
                    y,
                    icon_size,
                    icon_size,
                    Qt.AlignCenter,
                    "?"
                )

            # Move down next symbol (vertical stacking)
            y += icon_size + spacing

        painter.restore()

    def _violation_icon_rects(self, rect, violations):
        """
        Returns a list of (violation, QRect) for hit-testing.
        Must mirror paintSection geometry exactly.
        """
        icon_size = self.ICON_SIZE
        spacing = self.ICON_SPACING

        inner = rect.adjusted(
            self.ICON_MARGIN,
            self.ICON_MARGIN,
            -self.ICON_MARGIN,
            -self.ICON_MARGIN
        )
        x = inner.right() - icon_size
        y = inner.top()

        result = []

        for violation in violations:
            icon_rect = QRect(x, y, icon_size, icon_size)
            result.append((violation, icon_rect))
            y += icon_size + spacing

        return result
    
    def mouseMoveEvent(self, event):
        logical = self.logicalIndexAt(event.pos())
        if logical < 0:
            QToolTip.hideText()
            return super().mouseMoveEvent(event)

        x = self.sectionViewportPosition(logical)
        w = self.sectionSize(logical)
        rect = QRect(x, 0, w, self.height())
        violations = self.main_window.get_day_service_violations_for_column(logical)

        for violation, icon_rect in self._violation_icon_rects(rect, violations):
            if icon_rect.contains(event.pos()):
                QToolTip.showText(
                    self.mapToGlobal(event.pos()),
                    violation.tooltip(),
                    self
                )
                return

        QToolTip.hideText()
        super().mouseMoveEvent(event)



