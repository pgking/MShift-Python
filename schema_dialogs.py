from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QWidget,
    QListWidget,
    QMenu,
    QRadioButton
)
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt

from models import Schema


class CreateSchemaDialog(QDialog):
    """Dialog for creating a new schema pattern."""
    
    WEEKDAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    def __init__(self, services: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Créer un Schéma")
        self.resize(700, 400)
        
        self.services = services
        self.schema = None
        
        main_layout = QVBoxLayout(self)
        
        # Name input at the top
        name_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom du schéma...")
        name_layout.addRow("Nom:", self.name_edit)
        main_layout.addLayout(name_layout)
        
        # Settings row
        settings_layout = QFormLayout()
        
        self.start_day_combo = QComboBox()
        self.start_day_combo.addItems(self.WEEKDAYS_FR)
        
        self.span_spin = QSpinBox()
        self.span_spin.setRange(1, 14)
        self.span_spin.setValue(7)
        self.span_spin.valueChanged.connect(self._rebuild_table)
        
        settings_layout.addRow("Jour de début:", self.start_day_combo)
        settings_layout.addRow("Nombre de jours:", self.span_spin)
        
        main_layout.addLayout(settings_layout)
        
        # Pattern table
        table_label = QLabel("Motif:")
        table_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(table_label)
        
        self.pattern_table = QTableWidget()
        self.pattern_table.setRowCount(1)
        self.pattern_table.setVerticalHeaderLabels(["Services"])
        self.pattern_table.verticalHeader().setVisible(False)
        self.pattern_table.setMaximumHeight(120)
        self.pattern_table.cellClicked.connect(self._on_cell_clicked)
        
        self._rebuild_table()
        
        main_layout.addWidget(self.pattern_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        create_btn = QPushButton("Créer")
        cancel_btn = QPushButton("Annuler")
        
        create_btn.clicked.connect(self._on_create)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def _rebuild_table(self):
        """Rebuild the pattern table based on span_days."""
        span = self.span_spin.value()
        self.pattern_table.setColumnCount(span)
        
        # Set headers as "Jour 1", "Jour 2", etc.
        headers = [f"Jour {i+1}" for i in range(span)]
        self.pattern_table.setHorizontalHeaderLabels(headers)
        
        # Clear all cells
        for col in range(span):
            item = self.pattern_table.item(0, col)
            if not item:
                item = QTableWidgetItem("")
                self.pattern_table.setItem(0, col, item)
            else:
                item.setText("")
                item.setBackground(QBrush(Qt.white))
            
            # Store service_id in item data
            item.setData(Qt.UserRole, None)
    
    def _on_cell_clicked(self, row, col):
        """Show service selection menu when cell is clicked."""
        if row != 0:
            return
        
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        
        # Add "Clear" option
        clear_action = menu.addAction("Effacer")
        menu.addSeparator()
        
        # Add service options
        service_actions = {}
        for service in self.services:
            if service.is_visible:
                action = menu.addAction(f"{service.short_name} - {service.name}")
                service_actions[action] = service
        
        # Show menu at cursor
        action = menu.exec_(self.pattern_table.viewport().mapToGlobal(
            self.pattern_table.visualItemRect(self.pattern_table.item(row, col)).center()
        ))
        
        if action == clear_action:
            # Clear cell
            item = self.pattern_table.item(row, col)
            item.setText("")
            item.setBackground(QBrush(Qt.white))
            item.setData(Qt.UserRole, None)
        
        elif action in service_actions:
            # Set service
            service = service_actions[action]
            item = self.pattern_table.item(row, col)
            item.setText(service.short_name)
            item.setBackground(QBrush(QColor(service.color_hex)))
            item.setData(Qt.UserRole, service.id)
    
    def _on_create(self):
        """Create the schema from the dialog inputs."""
        name = self.name_edit.text().strip()
        if not name:
            # TODO: Show warning
            return
        
        start_weekday = self.start_day_combo.currentIndex()
        span_days = self.span_spin.value()
        
        # Extract pattern from table
        pattern = {}
        for col in range(span_days):
            item = self.pattern_table.item(0, col)
            if item:
                service_id = item.data(Qt.UserRole)
                if service_id:
                    pattern[col] = service_id
        
        self.schema = Schema(
            name=name,
            start_weekday=start_weekday,
            span_days=span_days,
            pattern=pattern
        )
        
        self.accept()


class ManageSchemasDialog(QDialog):
    """Dialog for managing existing schemas."""
    
    WEEKDAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    def __init__(self, schemas: list, services: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gérer les Schémas")
        self.resize(700, 400)
        
        self.schemas = schemas
        self.services = services
        self.current_schema = None
        
        main_layout = QHBoxLayout(self)
        
        # Left: schema list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.schema_list = QListWidget()
        self._refresh_schema_list()
        self.schema_list.currentRowChanged.connect(self._on_schema_selected)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Créer")
        self.delete_btn = QPushButton("Supprimer")
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.delete_btn)
        
        self.create_btn.clicked.connect(self._on_create)
        self.delete_btn.clicked.connect(self._on_delete)
        
        left_layout.addWidget(QLabel("Schémas:"))
        left_layout.addWidget(self.schema_list)
        left_layout.addLayout(btn_layout)
        
        # Right: schema details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.details_label = QLabel("Sélectionnez un schéma")
        self.details_label.setStyleSheet("font-weight: bold;")
        self.details_label.setAlignment(Qt.AlignCenter)
        
        right_layout.addWidget(self.details_label)
        
        # Pattern preview table
        self.preview_table = QTableWidget()
        self.preview_table.setRowCount(1)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setMaximumHeight(120)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        right_layout.addWidget(self.preview_table)
        right_layout.addStretch()
        
        # Add to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)
        
        # Close button
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        
        bottom_layout = QVBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        main_layout.addLayout(bottom_layout)
    
    def _refresh_schema_list(self):
        """Refresh the schema list."""
        self.schema_list.clear()
        for schema in self.schemas:
            self.schema_list.addItem(schema.name)
    
    def _on_schema_selected(self, index):
        """Handle schema selection."""
        if index < 0 or index >= len(self.schemas):
            self.current_schema = None
            self.details_label.setText("Sélectionnez un schéma")
            self.preview_table.clear()
            self.preview_table.setColumnCount(0)
            return
        
        self.current_schema = self.schemas[index]
        self._show_schema_details()
    
    def _show_schema_details(self):
        """Display details of the current schema."""
        if not self.current_schema:
            return
        
        schema = self.current_schema
        
        # Update details label
        weekday_name = self.WEEKDAYS_FR[schema.start_weekday]
        self.details_label.setText(
            f"{schema.name}\n"
            f"Commence: {weekday_name} | Durée: {schema.span_days} jour(s)"
        )
        
        # Update preview table
        self.preview_table.setColumnCount(schema.span_days)
        headers = [f"J{i+1}" for i in range(schema.span_days)]
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        for col in range(schema.span_days):
            service_id = schema.get_service(col)
            item = QTableWidgetItem("")
            
            if service_id:
                service = next((s for s in self.services if s.id == service_id), None)
                if service:
                    item.setText(service.short_name)
                    item.setBackground(QBrush(QColor(service.color_hex)))
            
            self.preview_table.setItem(0, col, item)
    
    def _on_create(self):
        """Open create schema dialog."""
        dialog = CreateSchemaDialog(self.services, self)
        if dialog.exec():
            new_schema = dialog.schema
            self.schemas.append(new_schema)
            self._refresh_schema_list()
            self.schema_list.setCurrentRow(len(self.schemas) - 1)
    
    def _on_delete(self):
        """Delete the current schema."""
        if not self.current_schema:
            return
        
        idx = self.schemas.index(self.current_schema)
        del self.schemas[idx]
        self.current_schema = None
        self._refresh_schema_list()


class AssignSchemaDialog(QDialog):
    """Dialog for assigning a schema to one or more people."""
    
    def __init__(self, schemas: list, people: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assigner un Schéma")
        self.resize(500, 400)
        
        self.schemas = schemas
        self.people = people
        self.selected_people = []
        self.selected_schema = None
        self.repeat_mode = "always"
        self.repeat_months = 1
        
        main_layout = QVBoxLayout(self)
        
        # Schema selection
        schema_layout = QFormLayout()
        self.schema_combo = QComboBox()
        
        if not schemas:
            self.schema_combo.addItem("Aucun schéma disponible")
            self.schema_combo.setEnabled(False)
        else:
            for schema in schemas:
                self.schema_combo.addItem(schema.name, schema.id)
        
        schema_layout.addRow("Schéma:", self.schema_combo)
        main_layout.addLayout(schema_layout)
        
        # People selection
        people_label = QLabel("Sélectionner les personnes:")
        people_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(people_label)
        
        self.people_list = QListWidget()
        self.people_list.setSelectionMode(QListWidget.MultiSelection)
        
        for person in people:
            self.people_list.addItem(person.display_name)
        
        main_layout.addWidget(self.people_list)
        
        # Repetition settings
        repeat_label = QLabel("Répétition:")
        repeat_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(repeat_label)
        
        self.always_radio = QRadioButton("Toujours répéter (appliqué aux futurs mois)")
        self.limited_radio = QRadioButton("Répéter pour un nombre limité de mois")
        self.always_radio.setChecked(True)
        
        main_layout.addWidget(self.always_radio)
        
        limited_layout = QHBoxLayout()
        limited_layout.addWidget(self.limited_radio)
        
        self.months_spin = QSpinBox()
        self.months_spin.setRange(1, 24)
        self.months_spin.setValue(1)
        self.months_spin.setEnabled(False)
        self.months_spin.setSuffix(" mois")
        
        limited_layout.addWidget(self.months_spin)
        limited_layout.addStretch()
        
        main_layout.addLayout(limited_layout)
        
        # Enable/disable months spinner based on radio selection
        self.limited_radio.toggled.connect(self.months_spin.setEnabled)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        assign_btn = QPushButton("Assigner")
        cancel_btn = QPushButton("Annuler")
        
        assign_btn.clicked.connect(self._on_assign)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(assign_btn)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def _on_assign(self):
        """Validate and prepare assignment data."""
        if not self.schemas:
            return
        
        # Get selected schema
        schema_id = self.schema_combo.currentData()
        if not schema_id:
            return
        
        self.selected_schema = next((s for s in self.schemas if s.id == schema_id), None)
        if not self.selected_schema:
            return
        
        # Get selected people
        selected_items = self.people_list.selectedItems()
        if not selected_items:
            # TODO: Show warning
            return
        
        self.selected_people = []
        for item in selected_items:
            person_name = item.text()
            person = next((p for p in self.people if p.display_name == person_name), None)
            if person:
                self.selected_people.append(person)
        
        # Get repetition settings
        self.repeat_mode = "always" if self.always_radio.isChecked() else "limited"
        self.repeat_months = self.months_spin.value()
        
        self.accept()
