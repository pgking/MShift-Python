import uuid
import json
from typing import Optional, Dict

from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect

class Service:
    def __init__(self, name, short_name, hours, color_hex, id=None):
        self.id = id or str(uuid.uuid4()) # Unique identifier
        self.name = name
        self.short_name = short_name
        self.hours = hours
        self.color_hex = color_hex

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "hours": self.hours,
            "color_hex": self.color_hex
        }

class Person:
    def __init__(self, prenom: str, nom: str, percentage: int, short_name: str | None = None, id=None):
        self.id = id or str(uuid.uuid4()) # Unique identifier
        self.prenom = prenom.strip()
        self.nom = nom.strip()
        self.percentage = percentage
        if short_name and short_name.strip() :
            self.short_name = short_name.strip()
        
        else :
            self.short_name = self._default_short_name()

    def _default_short_name(self) -> str :
        if not self.prenom :
            return self.nom.title()
        
        return f"{self.prenom[0].upper()}. {self.nom.title()}"

    def to_dict(self):
        return {
            "id": self.id,
            "prenom": self.prenom,
            "nom": self.nom,
            "percentage": self.percentage,
            "short_name": self.short_name
        }

class MonthData:
    def __init__(self, year : int, month : int):
        self.year = year
        self.month = month
        # key : (person.id, day)
        self.assignments = {}

    def get_service(self, person_id, day):
        return self.assignments.get((person_id, day))

    def set_service(self, person_id, day, service_id):
        if service_id is None :
            self.assignments.pop((person_id, day), None)
        
        else :
            self.assignments[(person_id, day)] = service_id

    def to_dict(self):
        return{
            "year": self.year,
            "month": self.month,
            "assignments": {
                f"{person_id}_{day}": service_id
                for (person_id, day), service_id in self.assignments.items()
            }
        }

    @staticmethod
    def from_dict(data):
        month = MonthData(data["year"], data["month"])
        month.assignments = {
            (pid, int(day)): service_id
            for k, service_id in data["assignments"].items()
            for pid, day in [k.split("_")]
        }
        return month

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
        # Weekend shading
        # ----------------------
        color = QColor(200, 200, 200, 120)
        for col in range(self.columnCount()):
            if self._is_weekend_column(col):
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
        
        painter.end()

    def _is_weekend_column(self, col):
        if self.columnCount() == 0:
            return False

        header_item = self.horizontalHeaderItem(col)
        if header_item:
            day_name = header_item.text().split("\n")[0]
            return day_name in ["Sam", "Dim"]
        return False
