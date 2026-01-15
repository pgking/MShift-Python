from PyQt5.QtWidgets import (
    QDialog,
    QLineEdit,
    QSpinBox,
    QFormLayout,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QColorDialog,
    QListWidget,
    QWidget,
    QCheckBox,
    QStackedWidget,
    QLabel
)

from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from models import Person, Service
from preferences import Preferences

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
        self.percent_spin.setSingleStep(5)

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

class ManageServicesDialog(QDialog):
    def __init__(self, services: list):
        super().__init__()
        self.setWindowTitle("Manage Services")
        self.setFixedSize(600, 300)

        self.services = services
        self.current_service = None # Selected service

        # MAIN LAYOUT
        main_layout = QHBoxLayout(self)

        # -------------------
        # LEFT: SERVICE LIST
        # -------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.service_list = QListWidget()
        self._refresh_service_list()
        self.service_list.currentRowChanged.connect(self._on_service_selected)

        # Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Create")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.delete_btn)

        self.create_btn.clicked.connect(self._on_create)
        self.delete_btn.clicked.connect(self._on_delete)

        left_layout.addWidget(self.service_list)
        left_layout.addLayout(btn_layout)

        # -------------------
        # RIGHT: EDITOR
        # -------------------
        right_widget = QWidget()
        right_layout = QFormLayout(right_widget)

        self.name_edit = QLineEdit()
        self.short_edit = QLineEdit()
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(7, 12)
        self.color_btn = QPushButton()
        self.color = QColor("#FFFFFF")
        self._update_color_button()
        self.color_btn.clicked.connect(self._choose_color)

        right_layout.addRow("Name", self.name_edit)
        right_layout.addRow("Short name", self.short_edit)
        right_layout.addRow("Hours", self.hours_spin)
        right_layout.addRow("Color :", self.color_btn)

        # Field focus out signal
        self.name_edit.editingFinished.connect(self._update_service_from_fields)
        self.short_edit.editingFinished.connect(self._update_service_from_fields)
        self.hours_spin.editingFinished.connect(self._update_service_from_fields)

        # -------------------
        # BOTTOM OK BUTTON
        # -------------------
        self.ok_btn = QPushButton("Exit")
        self.ok_btn.clicked.connect(self.accept)

        # Add left layout and right layout to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)
        main_layout.addWidget(self.ok_btn, alignment=Qt.AlignBottom)

    # -------------------
    # METHODS
    # -------------------
    def _refresh_service_list(self):
        self.service_list.clear()
        for service in self.services:
            self.service_list.addItem(service.name)

    def _on_service_selected(self, index):
        if index < 0 or index >= len(self.services):
            self.current_service = None
            self._clear_fields()
            return

        self.current_service = self.services[index]
        self._populate_fields()

    def _populate_fields(self):
        s = self.current_service
        if not s:
            return

        self.name_edit.setText(s.name)
        self.short_edit.setText(s.short_name)
        self.hours_spin.setValue(s.hours)
        self.color = QColor(s.color_hex)
        self._update_color_button()

    def _clear_fields(self):
        self.name_edit.setText("")
        self.short_edit.setText("")
        self.hours_spin.setValue(12)
        self.color = QColor("#FFFFFF")
        self._update_color_button()

    def _update_service_from_fields(self):
        if not self.current_service:
            return
        
        s = self.current_service
        s.name = self.name_edit.text()
        s.short_name = self.short_edit.text()
        s.hours = self.hours_spin.value()
        s.color_hex = self.color.name()

        # Refresh list to show name changes
        self._refresh_service_list()

        # Keep current service selected after refresh
        idx = self.services.index(s)
        self.service_list.setCurrentRow(idx)

    def _choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self._update_color_button()
            self._update_service_from_fields()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.color.name()}; min-height: 30px;"
        )

    def _on_create(self):
        dialog = AddServiceDialog()
        if dialog.exec():
            new_service = dialog.service
            self.services.append(new_service)
            self._refresh_service_list()
            self.service_list.setCurrentRow(len(self.services) - 1)

    def _on_delete(self):
        if not self.current_service:
            return

        idx = self.services.index(self.current_service)
        del self.services[idx]
        self.current_service = None
        self._refresh_service_list()
        self._clear_fields()


class PreferencesDialog(QDialog):
    def __init__(self, preferences: Preferences, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(600, 400)
        
        # Work on COPY
        self.preferences = Preferences(**preferences.__dict__)

        # Main Layout
        main_layout = QVBoxLayout(self)

        # ----------------------
        # CENTER: split view
        # ----------------------
        center_layout = QHBoxLayout()

        # Left : categories
        self.category_list = QListWidget()
        self.category_list.addItems([
            "General",
            "Behavior",
            "Shortcuts",
            "Appearance"
        ])
        self.category_list.setFixedWidth(150)
        self.category_list.setCurrentRow(0)

        # Right : stacked widgets for category settings
        self.pages = QStackedWidget()
        
        # ----------------------
        # PAGES
        # ----------------------
        self._build_general_page()
        self._build_behavior_page()
        self._build_shortcuts_page()
        self._build_appearance_page()

        center_layout.addWidget(self.category_list)
        center_layout.addWidget(self.pages, 1)

        main_layout.addLayout(center_layout)

        # ----------------------
        # BOTTOM BUTTONS
        # ----------------------
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        self.category_list.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )

    def accept(self):
        self.preferences.paste_overwrite_existing = (
            self.paste_overwrite_checkbox.isChecked()
        )

        super().accept()

    def _add_page(self, widget: QWidget):
        self.pages.addWidget(widget)

    def _build_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel(
            "General application settings.\n\n"
            "These options affect overall behavior of the scheduler."
        )
        label.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        layout.addWidget(label)
        layout.addStretch()

        self._add_page(page)

    def _build_behavior_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Behavior Settings")
        title.setStyleSheet("font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)

        self.paste_overwrite_checkbox = QCheckBox("Allow paste to overwrite existing services")
        self.paste_overwrite_checkbox.setChecked(self.preferences.paste_overwrite_existing)

        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(self.paste_overwrite_checkbox)
        layout.addStretch()

        self._add_page(page)

    def _build_shortcuts_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        self._add_page(page)

    def _build_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        self._add_page(page)
