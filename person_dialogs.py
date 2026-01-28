from PyQt5.QtWidgets import (
    QDialog, QListWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
import copy

class ManagePeopleDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.controller = main_window.controller
        self.setWindowTitle("Manage People")
        self.setFixedSize(700, 400)
        
        self.current_person = None
        self._is_updating = False  # Flag to prevent recursion/loops
        
        # -------------------
        # LAYOUT STRUCTURE
        # -------------------
        # Main vertical layout (wrapper)
        wrapper_layout = QVBoxLayout(self)
        
        # Content layout (horizontal split)
        content_layout = QHBoxLayout()
        
        
        # -------------------
        # LEFT: PERSON LIST
        # -------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.person_list = QListWidget()
        self.person_list.currentRowChanged.connect(self._on_person_selected)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Person")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        
        self.add_btn.clicked.connect(self._on_add)
        self.delete_btn.clicked.connect(self._on_delete)
        
        left_layout.addWidget(self.person_list)
        left_layout.addLayout(btn_layout)
        
        # -------------------
        # RIGHT: DETAILS EDITOR
        # -------------------
        right_widget = QWidget()
        right_layout = QFormLayout(right_widget)
        # right_layout.setContentsMargins(0, 0, 0, 0) # optional
        
        self.nom_edit = QLineEdit()
        self.prenom_edit = QLineEdit()
        self.percent_spin = QSpinBox()
        self.percent_spin.setRange(0, 100)
        self.percent_spin.setSingleStep(5)
        self.percent_spin.setSuffix("%")
        
        self.section_combo = QComboBox()
        self._populate_sections()
        
        right_layout.addRow("Last Name (Nom):", self.nom_edit)
        right_layout.addRow("First Name (Prénom):", self.prenom_edit)
        right_layout.addRow("Percentage:", self.percent_spin)
        right_layout.addRow("Section:", self.section_combo)
        
        # Connect signals
        self.nom_edit.editingFinished.connect(self._on_field_changed)
        self.prenom_edit.editingFinished.connect(self._on_field_changed)
        self.percent_spin.editingFinished.connect(self._on_field_changed)
        self.section_combo.currentIndexChanged.connect(self._on_field_changed)
        
        # Add widgets to content layout
        content_layout.addWidget(left_widget, 1)
        content_layout.addWidget(right_widget, 1)
        
        # -------------------
        # BOTTOM: CLOSE BUTTON
        # -------------------
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        # Assemble
        wrapper_layout.addLayout(content_layout, 1)
        wrapper_layout.addWidget(self.close_btn, 0, Qt.AlignRight)
        
        # Initial populate
        self._refresh_person_list()
        
    def _populate_sections(self):
        self.section_combo.clear()
        self.section_combo.addItem("None", None)
        for section in self.controller.sections:
            self.section_combo.addItem(section.label, section.id)
            
    def _refresh_person_list(self):
        current_row = self.person_list.currentRow()
        self.person_list.clear()
        
        for person in self.controller.people:
            # Use display_name here!
            self.person_list.addItem(person.display_name)
            
        if current_row >= 0 and current_row < self.person_list.count():
            self.person_list.setCurrentRow(current_row)
            
    def _on_person_selected(self, row):
        if row < 0 or row >= len(self.controller.people):
            self.current_person = None
            self._disable_fields(True)
            self._clear_fields()
            return
            
        self.current_person = self.controller.people[row]
        self._enable_fields()
        self._populate_fields()

    def select_person(self, person_id):
        """Select a person by ID."""
        for i, p in enumerate(self.controller.people):
            if p.id == person_id:
                self.person_list.setCurrentRow(i)
                break
        
    def _disable_fields(self, disable):
        self.nom_edit.setEnabled(not disable)
        self.prenom_edit.setEnabled(not disable)
        self.percent_spin.setEnabled(not disable)
        self.section_combo.setEnabled(not disable)
        self.delete_btn.setEnabled(not disable)

    def _enable_fields(self):
        self._disable_fields(False)
        
    def _clear_fields(self):
        self._is_updating = True
        self.nom_edit.clear()
        self.prenom_edit.clear()
        self.percent_spin.setValue(100)
        self.section_combo.setCurrentIndex(0)
        self._is_updating = False

    def _populate_fields(self):
        if not self.current_person:
            return
            
        self._is_updating = True
        p = self.current_person
        self.nom_edit.setText(p.nom)
        self.prenom_edit.setText(p.prenom)
        self.percent_spin.setValue(p.percentage)
        
        # Find section index
        index = 0
        if p.section_id:
            index = self.section_combo.findData(p.section_id)
            if index == -1: 
                index = 0
        self.section_combo.setCurrentIndex(index)
        self._is_updating = False

    def _on_field_changed(self):
        if self._is_updating or not self.current_person:
            return
            
        # Capture old state for undo
        old_data = self.current_person.to_dict()
        
        # Apply changes
        new_nom = self.nom_edit.text().strip()
        new_prenom = self.prenom_edit.text().strip()
        new_percent = self.percent_spin.value()
        new_section_id = self.section_combo.currentData()
        
        if not new_nom or not new_prenom:
            return # Don't update if names are empty?
            
        # Update object
        self.current_person.nom = new_nom
        self.current_person.prenom = new_prenom
        self.current_person.percentage = new_percent
        
        # Handle Section Change logic (update section objects)
        if self.current_person.section_id != new_section_id:
            # Remove from old section
            if self.current_person.section_id:
                old_section = self.controller.get_section_by_id(self.current_person.section_id)
                if old_section:
                    old_section.remove_person(self.current_person.id)
            
            # Add to new section
            if new_section_id:
                new_section = self.controller.get_section_by_id(new_section_id)
                if new_section:
                    new_section.add_person(self.current_person.id)
            
            self.current_person.section_id = new_section_id

        # Update List Item text (use display_name)
        row = self.controller.people.index(self.current_person)
        self.person_list.item(row).setText(self.current_person.display_name)

        # Capture new state
        new_data = self.current_person.to_dict()
        
        if old_data != new_data:
            self.controller.undo_manager.record_person_update(self.current_person.id, old_data, new_data)
            self.main_window.menu_bar.update_undo_redo_actions()

    def _on_add(self):
        # Open the standard Add Person Dialog
        self.main_window.open_add_person_dialog()
        self._refresh_person_list()
        
    def _on_delete(self):
        if not self.current_person:
            return
            
        reply = QMessageBox.question(
            self,
            "Delete Person",
            f"Are you sure you want to delete {self.current_person.display_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            person_data = self.current_person.to_dict()
            
            # 1. Record Undo
            self.controller.undo_manager.record_person_delete(person_data)
            
            # 2. Remove from global list
            self.controller.people.remove(self.current_person)
            
            # 3. Remove from section
            if self.current_person.section_id:
                section = self.controller.get_section_by_id(self.current_person.section_id)
                if section:
                    section.remove_person(self.current_person.id)
            
            # 4. Refresh local list
            self._refresh_person_list()
            self._clear_fields()
            self.current_person = None
            self.delete_btn.setEnabled(False)
            
            # 5. Notify Main Window
            self.main_window.rebuild_rows_from_sections()
            self.main_window.finalize_table_setup()
            self.main_window.menu_bar.update_undo_redo_actions()
