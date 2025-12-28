from PyQt5.QtWidgets import (
    QDialog,
    QLineEdit,
    QSpinBox,
    QFormLayout,
    QPushButton,
    QHBoxLayout,
    QColorDialog
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from models import Person, Service

class AddPersonDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Person")
        self.setFixedSize(300, 220)

        layout = QFormLayout(self)

        self.nom_edit = QLineEdit()
        self.prenom_edit = QLineEdit()

        self.short_preview = QLineEdit()
        self.short_preview.setReadOnly(True)
        self.short_preview.setAlignment(Qt.AlignCenter)
        self.short_preview.setStyleSheet(
            "background-color: #f0f0f0; color: #555;"
        )
        self.short_preview.setFrame(False)

        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(0, 100)
        self.percent_spin.setValue(100)
        self.percent_spin.stepBy(10)

        layout.addRow("Nom : ", self.nom_edit)
        layout.addRow("Prénom : ", self.prenom_edit)
        layout.addRow("Affiché :", self.short_preview)
        layout.addRow("Pourcentage : ", self.percent_spin)

        buttons_layout = QHBoxLayout()
        self.create_btn = QPushButton("Créer")
        self.cancel_btn = QPushButton("Annuler")

        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addRow(buttons_layout)

        self.create_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)

        self.nom_edit.textChanged.connect(self._update_short_preview)
        self.prenom_edit.textChanged.connect(self._update_short_preview)

    def _update_short_preview(self):
        prenom = self.prenom_edit.text().strip()
        nom = self.nom_edit.text().strip()

        if not nom : 
            self.short_preview.setText("")
            return

        if prenom :
            text = f"{prenom[0].upper()}. {nom.title()}"
        else :
            text = nom.title()

        self.short_preview.setText(text)

    def _on_create(self):
        if not self.nom_edit.text() or not self.prenom_edit.text():
            return #Warning popup later

        self.person = Person(
            prenom = f"{self.prenom_edit.text()}",
            nom = f"{self.nom_edit.text()}",
            percentage = self.percent_spin.value()
        )

        self.accept()

class AddServiceDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Service")
        self.setFixedSize(300,240)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.short_edit = QLineEdit()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(6, 12)
        self.hours_spin.setValue(12)

        self.color_btn = QPushButton("Choisir couleur")
        self.color = QColor("#FFFFFF")
        self._update_color_button()

        layout.addRow("Nom : ", self.name_edit)
        layout.addRow("Affichage : ", self.short_edit)
        layout.addRow("Heures : ", self.hours_spin)
        layout.addRow("Couleur : ", self.color_btn)

        buttons_layout = QHBoxLayout()
        self.create_btn = QPushButton("Créer")
        self.cancel_btn = QPushButton("Annuler")

        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.cancel_btn)
        layout.addRow(buttons_layout)

        self.color_btn.clicked.connect(self._choose_color)
        self.create_btn.clicked.connect(self._on_create)
        self.cancel_btn.clicked.connect(self.reject)

    def _choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self._update_color_button()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.color.name()};"
        )

    def _on_create(self):
        if not self.name_edit.text():
            return

        self.service = Service(
            self.name_edit.text(),
            self.short_edit.text(),
            self.hours_spin.value(),
            self.color.name()
        )
        self.accept()
