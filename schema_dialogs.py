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
    QRadioButton,
    QApplication,
    QCheckBox
)
from PyQt5.QtGui import QColor, QBrush, QPainter, QPen
from PyQt5.QtCore import Qt, QEvent, QPoint

from models import Schema


class SchemaPatternTable(QTableWidget):
    """Custom table widget for schema pattern editing with drag/drop and copy/paste support."""
    
    def __init__(self, services, parent=None):
        super().__init__(parent)
        self.services = services
        self.parent_dialog = parent
        
        # Copy/paste state
        self.clipboard_service_id = None
        self.clipboard_cell = None
        
        # Drag/drop state
        self.drag_source = None
        self.drag_rect = None
        
        # Mouse state
        self._shift_only_down = False
        
        # Disable cell selection (no blue highlight)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        
        # Install event filter
        self.viewport().installEventFilter(self)
        
    def eventFilter(self, obj, event):
        """Handle copy/paste and drag/drop events."""
        if obj != self.viewport():
            return super().eventFilter(obj, event)
        
        # Only handle mouse events to avoid interfering with dialog keyboard handling
        if event.type() not in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, 
                                QEvent.MouseMove, QEvent.KeyPress, QEvent.KeyRelease):
            return super().eventFilter(obj, event)
        
        try:
            # Handle modifier key changes for visual feedback
            if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
                modifiers = QApplication.keyboardModifiers()
                new_shift = (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier)
                if new_shift != self._shift_only_down:
                    self._shift_only_down = new_shift
                    self.viewport().update()
                return False  # Don't consume keyboard events
            
            # Copy/Paste handling (mouse only)
            if self._handle_copy_paste(event):
                return True
            
            # Drag/Drop handling (mouse only)
            if self._handle_drag_drop(event):
                return True
        except Exception as e:
            print(f"Error in event filter: {e}")
            return False
        
        return super().eventFilter(obj, event)
    
    def _handle_copy_paste(self, event):
        """Handle copy and paste operations."""
        modifiers = QApplication.keyboardModifiers()
        if not (modifiers & Qt.ShiftModifier):
            return False
        
        # SHIFT + RIGHT CLICK = COPY
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if not index.isValid() or index.row() != 0:
                return True
            
            item = self.item(0, index.column())
            if item and item.data(Qt.UserRole):
                self.clipboard_service_id = item.data(Qt.UserRole)
                self.clipboard_cell = (0, index.column())
                self.viewport().update()
            return True
        
        # SHIFT + LEFT CLICK = PASTE
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self.clipboard_service_id is None:
                return True
            
            index = self.indexAt(event.pos())
            if not index.isValid() or index.row() != 0:
                return True
            
            # Apply the service
            service = next((s for s in self.services if s.id == self.clipboard_service_id), None)
            if service:
                item = self.item(0, index.column())
                if not item:
                    item = QTableWidgetItem()
                    self.setItem(0, index.column(), item)
                item.setText(service.short_name)
                item.setBackground(QBrush(QColor(service.color_hex)))
                item.setTextAlignment(Qt.AlignCenter)
                item.setData(Qt.UserRole, service.id)
            
            return True
        
        return False
    
    def _handle_drag_drop(self, event):
        """Handle drag and drop operations."""
        # Start drag
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            if modifiers & Qt.ShiftModifier:
                return False  # Shift+Click is for paste
            
            index = self.indexAt(event.pos())
            if index.isValid() and index.row() == 0:
                item = self.item(0, index.column())
                if item and item.data(Qt.UserRole):
                    self.drag_source = index.column()
                    self.drag_rect = self.visualRect(index)
                    self.viewport().update()
            return False
        
        # Update drag visual
        if event.type() == QEvent.MouseMove and self.drag_source is not None:
            self.viewport().update()
            return False
        
        # Drop
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self.drag_source is not None:
                index = self.indexAt(event.pos())
                if index.isValid() and index.row() == 0:
                    target_col = index.column()
                    
                    # Swap services
                    if target_col != self.drag_source:
                        source_item = self.item(0, self.drag_source)
                        target_item = self.item(0, target_col)
                        
                        # Get source data
                        src_text = source_item.text() if source_item else ""
                        src_bg = source_item.background() if source_item else QBrush(Qt.white)
                        src_data = source_item.data(Qt.UserRole) if source_item else None
                        
                        # Get target data
                        tgt_text = target_item.text() if target_item else ""
                        tgt_bg = target_item.background() if target_item else QBrush(Qt.white)
                        tgt_data = target_item.data(Qt.UserRole) if target_item else None
                        
                        # Swap
                        if not source_item:
                            source_item = QTableWidgetItem()
                            self.setItem(0, self.drag_source, source_item)
                        if not target_item:
                            target_item = QTableWidgetItem()
                            self.setItem(0, target_col, target_item)
                        
                        source_item.setText(tgt_text)
                        source_item.setBackground(tgt_bg)
                        source_item.setTextAlignment(Qt.AlignCenter)
                        source_item.setData(Qt.UserRole, tgt_data)
                        
                        target_item.setText(src_text)
                        target_item.setBackground(src_bg)
                        target_item.setTextAlignment(Qt.AlignCenter)
                        target_item.setData(Qt.UserRole, src_data)
                
                # Reset drag state
                self.drag_source = None
                self.drag_rect = None
                self.viewport().update()
            return False
        
        return False
    
    def paintEvent(self, event):
        """Custom paint to show copy rectangle."""
        super().paintEvent(event)
        
        painter = QPainter(self.viewport())
        
        # Draw copy rectangle
        if self._shift_only_down and self._is_clipboard_valid():
            if self.clipboard_cell:
                row, col = self.clipboard_cell
                rect = self.visualRect(self.model().index(row, col))
                if rect.isValid():
                    rect = rect.adjusted(-1, -1, 1, 1)
                    pen = QPen(Qt.black)
                    pen.setStyle(Qt.DotLine)
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRect(rect)
        
        # Draw drag rectangle
        if self.drag_source is not None and self.drag_rect:
            pen = QPen(QColor("#4A90E2"))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.drag_rect.adjusted(1, 1, -1, -1))
    
    def _is_clipboard_valid(self):
        """Check if clipboard is still valid."""
        if self.clipboard_cell is None or self.clipboard_service_id is None:
            return False
        
        row, col = self.clipboard_cell
        item = self.item(row, col)
        if not item:
            return False
        
        return item.data(Qt.UserRole) == self.clipboard_service_id


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
        
        self.pattern_table = SchemaPatternTable(self.services, self)
        self.pattern_table.setRowCount(1)
        self.pattern_table.setVerticalHeaderLabels(["Services"])
        self.pattern_table.verticalHeader().setVisible(False)
        self.pattern_table.setMaximumHeight(120)
        
        # Disable selection highlighting but keep click events
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
            
            # Center text alignment
            item.setTextAlignment(Qt.AlignCenter)
            
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
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, None)
        
        elif action in service_actions:
            # Set service
            service = service_actions[action]
            item = self.pattern_table.item(row, col)
            item.setText(service.short_name)
            item.setBackground(QBrush(QColor(service.color_hex)))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, service.id)
    
    def _on_create(self):
        """Create the schema from the dialog inputs."""
        print("Create button clicked")  # Debug
        name = self.name_edit.text().strip()
        if not name:
            print("Warning: No name provided")  # Debug
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
        
        print(f"Creating schema: name={name}, days={span_days}, pattern={pattern}")  # Debug
        
        self.schema = Schema(
            name=name,
            start_weekday=start_weekday,
            span_days=span_days,
            pattern=pattern
        )
        
        print("Schema created, accepting dialog")  # Debug
        self.accept()


class ManageSchemasDialog(QDialog):
    """Dialog for managing existing schemas with full editing and assignment capabilities."""
    
    WEEKDAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    def __init__(self, schemas: list, services: list, people: list, schema_assignments: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gérer les Schémas")
        self.resize(900, 600)
        
        self.schemas = schemas
        self.services = services
        self.people = people
        self.schema_assignments = schema_assignments  # List of SchemaAssignment objects
        self.current_schema = None
        
        main_layout = QHBoxLayout(self)
        
        # ====================
        # LEFT: Schema list
        # ====================
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
        
        # ====================
        # RIGHT: Schema editor
        # ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Name field
        name_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nom du schéma...")
        self.name_edit.textChanged.connect(self._on_name_changed)
        name_layout.addRow("Nom:", self.name_edit)
        right_layout.addLayout(name_layout)
        
        # Settings (start day, span)
        settings_layout = QFormLayout()
        
        self.start_day_combo = QComboBox()
        self.start_day_combo.addItems(self.WEEKDAYS_FR)
        self.start_day_combo.currentIndexChanged.connect(self._on_settings_changed)
        
        self.span_spin = QSpinBox()
        self.span_spin.setRange(1, 14)
        self.span_spin.setValue(7)
        self.span_spin.valueChanged.connect(self._on_span_changed)
        
        settings_layout.addRow("Jour de début:", self.start_day_combo)
        settings_layout.addRow("Nombre de jours:", self.span_spin)
        right_layout.addLayout(settings_layout)
        
        # Pattern table (editable)
        table_label = QLabel("Motif:")
        table_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(table_label)
        
        self.pattern_table = SchemaPatternTable(self.services, self)
        self.pattern_table.setRowCount(1)
        self.pattern_table.setVerticalHeaderLabels(["Services"])
        self.pattern_table.verticalHeader().setVisible(False)
        self.pattern_table.setMaximumHeight(120)
        self.pattern_table.cellClicked.connect(self._on_cell_clicked)
        
        right_layout.addWidget(self.pattern_table)
        
        # ====================
        # ASSIGNMENTS section
        # ====================
        assignments_label = QLabel("Assigné à:")
        assignments_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(assignments_label)
        
        # Assignment list container
        assignment_scroll_widget = QWidget()
        self.assignments_layout = QVBoxLayout(assignment_scroll_widget)
        self.assignments_layout.setContentsMargins(0, 0, 0, 0)
        self.assignments_layout.addStretch()
        
        right_layout.addWidget(assignment_scroll_widget)
        
        # Add assignment button
        add_assignment_btn = QPushButton("+ Ajouter une personne")
        add_assignment_btn.clicked.connect(self._add_assignment_slot)
        right_layout.addWidget(add_assignment_btn)
        
        right_layout.addStretch()
        
        # ====================
        # BOTTOM: Close button
        # ====================
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        right_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        # Add to main layout
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 3)
        
        # Disable editing initially
        self._set_editing_enabled(False)
    
    def _set_editing_enabled(self, enabled: bool):
        """Enable/disable editing controls."""
        self.name_edit.setEnabled(enabled)
        self.start_day_combo.setEnabled(enabled)
        self.span_spin.setEnabled(enabled)
        self.pattern_table.setEnabled(enabled)
    
    def _refresh_schema_list(self):
        """Refresh the schema list."""
        self.schema_list.clear()
        for schema in self.schemas:
            self.schema_list.addItem(schema.name)
    
    def _on_schema_selected(self, index):
        """Handle schema selection."""
        if index < 0 or index >= len(self.schemas):
            self.current_schema = None
            self._set_editing_enabled(False)
            self._clear_editor()
            return
        
        self.current_schema = self.schemas[index]
        self._set_editing_enabled(True)
        self._load_schema_into_editor()
    
    def _clear_editor(self):
        """Clear all editor fields."""
        self.name_edit.setText("")
        self.start_day_combo.setCurrentIndex(0)
        self.span_spin.setValue(7)
        self.pattern_table.setColumnCount(0)
        self._clear_assignments()
    
    def _load_schema_into_editor(self):
        """Load the current schema into the editor."""
        if not self.current_schema:
            return
        
        schema = self.current_schema
        
        # Block signals to avoid triggering updates while loading
        self.name_edit.blockSignals(True)
        self.start_day_combo.blockSignals(True)
        self.span_spin.blockSignals(True)
        
        # Load basic fields
        self.name_edit.setText(schema.name)
        self.start_day_combo.setCurrentIndex(schema.start_weekday)
        self.span_spin.setValue(schema.span_days)
        
        # Unblock signals
        self.name_edit.blockSignals(False)
        self.start_day_combo.blockSignals(False)
        self.span_spin.blockSignals(False)
        
        # Load pattern table
        self._rebuild_pattern_table()
        
        # Load assignments
        self._load_assignments()
    
    def _rebuild_pattern_table(self):
        """Rebuild the pattern table based on current schema."""
        if not self.current_schema:
            return
        
        schema = self.current_schema
        span = schema.span_days
        
        self.pattern_table.setColumnCount(span)
        headers = [f"Jour {i+1}" for i in range(span)]
        self.pattern_table.setHorizontalHeaderLabels(headers)
        
        # Populate cells
        for col in range(span):
            service_id = schema.get_service(col)
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            
            if service_id:
                service = next((s for s in self.services if s.id == service_id), None)
                if service:
                    item.setText(service.short_name)
                    item.setBackground(QBrush(QColor(service.color_hex)))
                    item.setData(Qt.UserRole, service.id)
            
            self.pattern_table.setItem(0, col, item)
    
    def _on_name_changed(self):
        """Handle name change."""
        if not self.current_schema:
            return
        
        self.current_schema.name = self.name_edit.text().strip()
        
        # Update list item
        current_row = self.schema_list.currentRow()
        if current_row >= 0:
            self.schema_list.item(current_row).setText(self.current_schema.name)
    
    def _on_settings_changed(self):
        """Handle start day change."""
        if not self.current_schema:
            return
        
        self.current_schema.start_weekday = self.start_day_combo.currentIndex()
    
    def _on_span_changed(self):
        """Handle span days change."""
        if not self.current_schema:
            return
        
        old_span = self.current_schema.span_days
        new_span = self.span_spin.value()
        
        self.current_schema.span_days = new_span
        
        # Rebuild table (preserving existing pattern where possible)
        self._rebuild_pattern_table()
    
    def _on_cell_clicked(self, row, col):
        """Handle cell click to show service menu."""
        if row != 0 or not self.current_schema:
            return
        
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
        
        # Show menu
        action = menu.exec_(self.pattern_table.viewport().mapToGlobal(
            self.pattern_table.visualItemRect(self.pattern_table.item(row, col)).center()
        ))
        
        if action == clear_action:
            # Clear cell
            item = self.pattern_table.item(row, col)
            item.setText("")
            item.setBackground(QBrush(Qt.white))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, None)
            
            # Update schema
            if col in self.current_schema.pattern:
                del self.current_schema.pattern[col]
        
        elif action in service_actions:
            # Set service
            service = service_actions[action]
            item = self.pattern_table.item(row, col)
            item.setText(service.short_name)
            item.setBackground(QBrush(QColor(service.color_hex)))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, service.id)
            
            # Update schema
            self.current_schema.pattern[col] = service.id
    
    def _load_assignments(self):
        """Load assignments for the current schema."""
        self._clear_assignments()
        
        if not self.current_schema:
            return
        
        # Find all assignments for this schema
        for assignment in self.schema_assignments:
            if assignment.schema_id == self.current_schema.id:
                person = next((p for p in self.people if p.id == assignment.person_id), None)
                if person:
                    self._add_assignment_row(person, assignment)
    
    def _clear_assignments(self):
        """Clear all assignment rows."""
        # Remove all widgets except the stretch
        while self.assignments_layout.count() > 1:
            item = self.assignments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _add_assignment_slot(self):
        """Add a new assignment slot."""
        if not self.current_schema:
            return
        
        self._add_assignment_row(None, None)
    
    def _add_assignment_row(self, person=None, assignment=None):
        """Add an assignment row with person selector, repeat options, and overwrite checkbox."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(5)
        
        # Person dropdown
        person_combo = QComboBox()
        person_combo.addItem("-- Sélectionner --", None)
        person_combo.setMinimumWidth(120)
        
        for p in self.people:
            person_combo.addItem(p.display_name, p.id)
        
        if person:
            index = person_combo.findData(person.id)
            if index >= 0:
                person_combo.setCurrentIndex(index)
        
        row_layout.addWidget(person_combo)
        
        # Repeat mode dropdown
        repeat_combo = QComboBox()
        repeat_combo.addItem("Répéter indéfiniment", "always")
        repeat_combo.addItem("Répéter pour", "limited")
        repeat_combo.setMinimumWidth(140)
        
        # Set initial value
        if assignment:
            index = repeat_combo.findData(assignment.repeat_mode)
            if index >= 0:
                repeat_combo.setCurrentIndex(index)
        else:
            repeat_combo.setCurrentIndex(0)  # Default to "always"
        
        row_layout.addWidget(repeat_combo)
        
        # Months spinner (shown only when "limited" is selected)
        months_spin = QSpinBox()
        months_spin.setRange(1, 24)
        months_spin.setValue(assignment.repeat_months if assignment else 1)
        months_spin.setSuffix(" mois")
        months_spin.setMinimumWidth(80)
        months_spin.setVisible(repeat_combo.currentData() == "limited")
        
        row_layout.addWidget(months_spin)
        
        # Overwrite checkbox
        overwrite_check = QCheckBox("Écraser")
        overwrite_check.setChecked(True)  # Checked by default
        overwrite_check.setToolTip("Écraser les services existants lors de l'application du schéma")
        
        row_layout.addWidget(overwrite_check)
        
        # Remove button
        remove_btn = QPushButton("−")
        remove_btn.setFixedWidth(30)
        remove_btn.clicked.connect(lambda: self._remove_assignment_row(row_widget, assignment))
        row_layout.addWidget(remove_btn)
        
        # Connect events
        def on_person_changed():
            self._on_assignment_changed(
                person_combo, repeat_combo, months_spin, overwrite_check, assignment
            )
        
        def on_repeat_mode_changed():
            # Show/hide months spinner
            months_spin.setVisible(repeat_combo.currentData() == "limited")
            if assignment:
                assignment.repeat_mode = repeat_combo.currentData()
        
        def on_months_changed():
            if assignment:
                assignment.repeat_months = months_spin.value()
        
        def on_overwrite_changed():
            if assignment:
                assignment.overwrite_existing = overwrite_check.isChecked()
        
        person_combo.currentIndexChanged.connect(on_person_changed)
        repeat_combo.currentIndexChanged.connect(on_repeat_mode_changed)
        months_spin.valueChanged.connect(on_months_changed)
        overwrite_check.stateChanged.connect(on_overwrite_changed)
        
        # Insert before the stretch
        self.assignments_layout.insertWidget(self.assignments_layout.count() - 1, row_widget)
    
    def _on_assignment_changed(self, person_combo, repeat_combo, months_spin, overwrite_check, existing_assignment):
        """Handle assignment change."""
        if not self.current_schema:
            return
        
        person_id = person_combo.currentData()
        
        if person_id is None:
            # Remove assignment if it exists
            if existing_assignment and existing_assignment in self.schema_assignments:
                self.schema_assignments.remove(existing_assignment)
            return
        
        # Check if assignment already exists
        if existing_assignment:
            # Update existing
            existing_assignment.person_id = person_id
            existing_assignment.repeat_mode = repeat_combo.currentData()
            existing_assignment.repeat_months = months_spin.value()
            existing_assignment.overwrite_existing = overwrite_check.isChecked()
        else:
            # Create new assignment
            from models import SchemaAssignment
            new_assignment = SchemaAssignment(
                person_id=person_id,
                schema_id=self.current_schema.id,
                repeat_mode=repeat_combo.currentData(),
                repeat_months=months_spin.value(),
                start_year=0,  # Will be set when applied
                start_month=0,
                overwrite_existing=overwrite_check.isChecked()
            )
            self.schema_assignments.append(new_assignment)
    
    def _remove_assignment_row(self, row_widget, assignment):
        """Remove an assignment row."""
        # Remove from schema_assignments
        if assignment and assignment in self.schema_assignments:
            self.schema_assignments.remove(assignment)
        
        # Remove widget
        row_widget.deleteLater()
        self.assignments_layout.removeWidget(row_widget)
    
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
