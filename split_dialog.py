from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QDialogButtonBox, QWidget
)
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QPolygon


class SplitPreviewWidget(QWidget):
    """Small preview showing the diagonal split with chosen colors."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.am_color = QColor("#FFFFFF")
        self.pm_color = QColor("#FFFFFF")
        self.am_text = ""
        self.pm_text = ""
        self.setFixedSize(120, 80)
    
    def set_services(self, am_color, pm_color, am_text, pm_text):
        self.am_color = QColor(am_color) if am_color else QColor("#FFFFFF")
        self.pm_color = QColor(pm_color) if pm_color else QColor("#FFFFFF")
        self.am_text = am_text or ""
        self.pm_text = pm_text or ""
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        rect = QRect(2, 2, w - 4, h - 4)
        
        # Morning triangle (top-left): bottom-left -> top-left -> top-right
        am_poly = QPolygon([
            QPoint(rect.left(), rect.bottom()),
            QPoint(rect.left(), rect.top()),
            QPoint(rect.right(), rect.top())
        ])
        
        # Afternoon triangle (bottom-right): bottom-left -> top-right -> bottom-right
        pm_poly = QPolygon([
            QPoint(rect.left(), rect.bottom()),
            QPoint(rect.right(), rect.top()),
            QPoint(rect.right(), rect.bottom())
        ])
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.am_color))
        painter.drawPolygon(am_poly)
        
        painter.setBrush(QBrush(self.pm_color))
        painter.drawPolygon(pm_poly)
        
        # Diagonal line
        painter.setPen(QPen(QColor(80, 80, 80), 1.5))
        painter.drawLine(rect.bottomLeft(), rect.topRight())
        
        # Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawRect(rect)
        
        # Text labels
        painter.setPen(QPen(QColor(0, 0, 0)))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        
        # AM text: midpoint between top-left corner and cell center
        if self.am_text:
            am_cx = rect.left() + rect.width() // 4
            am_cy = rect.top() + rect.height() // 4
            tw = rect.width() // 2
            th = rect.height() // 2
            am_rect = QRect(am_cx - tw // 2, am_cy - th // 2, tw, th)
            painter.drawText(am_rect, Qt.AlignCenter, self.am_text)
        
        # PM text: midpoint between bottom-right corner and cell center
        if self.pm_text:
            pm_cx = rect.right() - rect.width() // 4
            pm_cy = rect.bottom() - rect.height() // 4
            tw = rect.width() // 2
            th = rect.height() // 2
            pm_rect = QRect(pm_cx - tw // 2, pm_cy - th // 2, tw, th)
            painter.drawText(pm_rect, Qt.AlignCenter, self.pm_text)
        
        painter.end()


class SplitServiceDialog(QDialog):
    """Dialog to select morning and afternoon services for a split cell."""
    
    def __init__(self, services, current_am_id=None, current_pm_id=None, parent=None):
        super().__init__(parent)
        self.services = [s for s in services if s.id != "builtin_split" and s.id != "builtin_note"]
        self.am_service_id = current_am_id
        self.pm_service_id = current_pm_id
        
        self.setWindowTitle("Journée coupée")
        self.setMinimumWidth(320)
        self._build_ui()
        self._update_preview()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Preview
        preview_layout = QHBoxLayout()
        preview_layout.addStretch()
        self.preview = SplitPreviewWidget()
        preview_layout.addWidget(self.preview)
        preview_layout.addStretch()
        layout.addLayout(preview_layout)
        
        # Morning combo
        am_layout = QHBoxLayout()
        am_label = QLabel("Matin :")
        am_label.setFixedWidth(80)
        am_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.am_combo = QComboBox()
        self.am_combo.addItem("— Aucun —", None)
        for svc in self.services:
            if svc.is_visible:
                self.am_combo.addItem(f"{svc.short_name} ({svc.name})", svc.id)
        am_layout.addWidget(am_label)
        am_layout.addWidget(self.am_combo, 1)
        layout.addLayout(am_layout)
        
        # Afternoon combo
        pm_layout = QHBoxLayout()
        pm_label = QLabel("Après-midi :")
        pm_label.setFixedWidth(80)
        pm_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pm_combo = QComboBox()
        self.pm_combo.addItem("— Aucun —", None)
        for svc in self.services:
            if svc.is_visible:
                self.pm_combo.addItem(f"{svc.short_name} ({svc.name})", svc.id)
        pm_layout.addWidget(pm_label)
        pm_layout.addWidget(self.pm_combo, 1)
        layout.addLayout(pm_layout)
        
        # Set current selections
        if self.am_service_id:
            idx = self.am_combo.findData(self.am_service_id)
            if idx >= 0:
                self.am_combo.setCurrentIndex(idx)
        
        if self.pm_service_id:
            idx = self.pm_combo.findData(self.pm_service_id)
            if idx >= 0:
                self.pm_combo.setCurrentIndex(idx)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Connect preview updates
        self.am_combo.currentIndexChanged.connect(self._update_preview)
        self.pm_combo.currentIndexChanged.connect(self._update_preview)
    
    def _update_preview(self):
        am_id = self.am_combo.currentData()
        pm_id = self.pm_combo.currentData()
        
        am_svc = next((s for s in self.services if s.id == am_id), None) if am_id else None
        pm_svc = next((s for s in self.services if s.id == pm_id), None) if pm_id else None
        
        self.preview.set_services(
            am_svc.color_hex if am_svc else "#FFFFFF",
            pm_svc.color_hex if pm_svc else "#FFFFFF",
            am_svc.short_name if am_svc else "",
            pm_svc.short_name if pm_svc else ""
        )
    
    def get_selection(self):
        """Returns (am_service_id, pm_service_id)."""
        return self.am_combo.currentData(), self.pm_combo.currentData()
