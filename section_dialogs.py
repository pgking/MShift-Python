"""
Section management dialogs for MShift.

Provides UI for creating, editing, deleting, and reordering sections.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QFormLayout,
    QWidget,
    QLabel,
    QMessageBox,
    QInputDialog
)
from PyQt5.QtCore import Qt
from models import Section


class ManageSectionsDialog(QDialog):
    """
    Dialog for managing sections (add, edit, delete, reorder).
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Manage Sections")
        self.setMinimumSize(600, 400)
        
        # =====================================================
        # LEFT SIDE: Section List
        # =====================================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        list_label = QLabel("Sections:")
        list_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(list_label)
        
        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self._on_section_selected)
        left_layout.addWidget(self.section_list)
        
        # List buttons
        list_btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add")
        self.delete_btn = QPushButton("🗑️ Delete")
        self.move_up_btn = QPushButton("⬆️ Up")
        self.move_down_btn = QPushButton("⬇️ Down")
        
        self.add_btn.clicked.connect(self._on_add_section)
        self.delete_btn.clicked.connect(self._on_delete_section)
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_down_btn.clicked.connect(self._on_move_down)
        
        list_btn_layout.addWidget(self.add_btn)
        list_btn_layout.addWidget(self.delete_btn)
        list_btn_layout.addWidget(self.move_up_btn)
        list_btn_layout.addWidget(self.move_down_btn)
        
        left_layout.addLayout(list_btn_layout)
        
        # =====================================================
        # RIGHT SIDE: Section Editor
        # =====================================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        editor_label = QLabel("Section Details:")
        editor_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(editor_label)
        
        form_layout = QFormLayout()
        
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)
        self.id_edit.setStyleSheet("background-color: #f0f0f0;")
        
        self.label_edit = QLineEdit()
        self.label_edit.textChanged.connect(self._on_label_changed)
        
        form_layout.addRow("ID:", self.id_edit)
        form_layout.addRow("Label:", self.label_edit)
        
        right_layout.addLayout(form_layout)
        
        # People count
        self.people_count_label = QLabel()
        self.people_count_label.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        right_layout.addWidget(self.people_count_label)
        
        # Sort button
        self.sort_btn = QPushButton("🔤 Sort People Alphabetically")
        self.sort_btn.clicked.connect(self._on_sort_section)
        self.sort_btn.setToolTip("Sort people in this section by last name (Nom)")
        right_layout.addWidget(self.sort_btn)
        
        right_layout.addStretch()
        
        # Info label
        info_label = QLabel(
            "💡 Tip: Use the arrow buttons to reorder sections.\n"
            "Deleting a section will move its people to the first section."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 10px; margin-top: 10px;")
        right_layout.addWidget(info_label)
        
        # =====================================================
        # BOTTOM: Action Buttons
        # =====================================================
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.sort_all_btn = QPushButton("🔤 Sort All Sections")
        self.sort_all_btn.clicked.connect(self._on_sort_all)
        self.sort_all_btn.setToolTip("Sort people alphabetically in all sections")
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        bottom_layout.addWidget(self.sort_all_btn)
        bottom_layout.addWidget(self.close_btn)
        
        # =====================================================
        # Assemble Layout
        # =====================================================
        top_layout = QHBoxLayout()
        top_layout.addWidget(left_widget, 1)
        top_layout.addWidget(right_widget, 2)
        
        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)
        
        # Initialize
        self.current_section = None
        self._refresh_section_list()
        self._update_buttons_state()
    
    def _refresh_section_list(self):
        """Refresh the section list widget."""
        current_row = self.section_list.currentRow()
        
        # Block signals to prevent recursion
        self.section_list.blockSignals(True)
        self.section_list.clear()
        
        for section in self.controller.sections:
            people_count = len(section.people_ids)
            self.section_list.addItem(f"{section.label} ({people_count} people)")
        
        # Restore selection
        if 0 <= current_row < len(self.controller.sections):
            self.section_list.setCurrentRow(current_row)
        
        # Re-enable signals
        self.section_list.blockSignals(False)
    
    def _on_section_selected(self, index):
        """Handle section selection."""
        if 0 <= index < len(self.controller.sections):
            self.current_section = self.controller.sections[index]
            self._populate_editor()
        else:
            self.current_section = None
            self._clear_editor()
        
        self._update_buttons_state()
    
    def _populate_editor(self):
        """Populate editor fields with current section data."""
        if not self.current_section:
            return
        
        # Block signals to prevent recursion
        self.label_edit.blockSignals(True)
        
        self.id_edit.setText(self.current_section.id)
        self.label_edit.setText(self.current_section.label)
        
        people_count = len(self.current_section.people_ids)
        self.people_count_label.setText(f"Contains {people_count} people")
        
        # Re-enable signals
        self.label_edit.blockSignals(False)
    
    def _clear_editor(self):
        """Clear editor fields."""
        self.id_edit.clear()
        self.label_edit.clear()
        self.people_count_label.clear()
    
    def _update_buttons_state(self):
        """Update button enabled/disabled state."""
        has_selection = self.current_section is not None
        current_index = self.section_list.currentRow()
        
        self.delete_btn.setEnabled(has_selection and len(self.controller.sections) > 1)
        self.sort_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and current_index > 0)
        self.move_down_btn.setEnabled(has_selection and current_index < len(self.controller.sections) - 1)
    
    def _on_label_changed(self):
        """Handle label text change."""
        if self.current_section:
            self.current_section.label = self.label_edit.text()
            self._refresh_section_list()
    
    def _on_add_section(self):
        """Add a new section."""
        label, ok = QInputDialog.getText(
            self,
            "New Section",
            "Section name:",
            QLineEdit.Normal,
            ""
        )
        
        if ok and label.strip():
            # Generate unique ID from label
            section_id = label.strip().replace(" ", "_").lower()
            
            # Ensure ID is unique
            counter = 1
            original_id = section_id
            while any(s.id == section_id for s in self.controller.sections):
                section_id = f"{original_id}_{counter}"
                counter += 1
            
            # Create new section
            new_section = Section(section_id, label.strip())
            self.controller.sections.append(new_section)
            
            self._refresh_section_list()
            self.section_list.setCurrentRow(len(self.controller.sections) - 1)
    
    def _on_delete_section(self):
        """Delete the selected section."""
        if not self.current_section:
            return
        
        if len(self.controller.sections) <= 1:
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete the last section. At least one section must exist."
            )
            return
        
        people_count = len(self.current_section.people_ids)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Section",
            f"Delete section '{self.current_section.label}'?\n\n"
            f"This section contains {people_count} people.\n"
            f"They will be moved to the first section.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Move people to first section (that's not this one)
            target_section = None
            for section in self.controller.sections:
                if section.id != self.current_section.id:
                    target_section = section
                    break
            
            if target_section:
                for person_id in self.current_section.people_ids:
                    target_section.add_person(person_id)
                    # Update person's section_id
                    person = self.controller.get_person_by_id(person_id)
                    if person:
                        person.section_id = target_section.id
            
            # Remove section
            self.controller.sections.remove(self.current_section)
            self.current_section = None
            
            self._refresh_section_list()
            self._update_buttons_state()
    
    def _on_move_up(self):
        """Move selected section up in the list."""
        if not self.current_section:
            return
        
        index = self.controller.sections.index(self.current_section)
        if index > 0:
            # Swap with previous
            self.controller.sections[index], self.controller.sections[index - 1] = \
                self.controller.sections[index - 1], self.controller.sections[index]
            
            self._refresh_section_list()
            self.section_list.setCurrentRow(index - 1)
    
    def _on_move_down(self):
        """Move selected section down in the list."""
        if not self.current_section:
            return
        
        index = self.controller.sections.index(self.current_section)
        if index < len(self.controller.sections) - 1:
            # Swap with next
            self.controller.sections[index], self.controller.sections[index + 1] = \
                self.controller.sections[index + 1], self.controller.sections[index]
            
            self._refresh_section_list()
            self.section_list.setCurrentRow(index + 1)
    
    def _on_sort_section(self):
        """Sort people in the selected section alphabetically."""
        if not self.current_section:
            return
        
        people_count = len(self.current_section.people_ids)
        if people_count == 0:
            QMessageBox.information(
                self,
                "No People",
                "This section has no people to sort."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Sort Section",
            f"Sort {people_count} people in '{self.current_section.label}' alphabetically by last name (Nom)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.controller.sort_section_alphabetically(self.current_section.id)
            QMessageBox.information(
                self,
                "Sorted",
                f"People in '{self.current_section.label}' have been sorted alphabetically by last name."
            )
    
    def _on_sort_all(self):
        """Sort people in all sections alphabetically."""
        total_people = sum(len(s.people_ids) for s in self.controller.sections)
        
        if total_people == 0:
            QMessageBox.information(
                self,
                "No People",
                "There are no people to sort."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Sort All Sections",
            f"Sort people alphabetically in all {len(self.controller.sections)} sections?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.controller.sort_all_sections_alphabetically()
            QMessageBox.information(
                self,
                "Sorted",
                "All sections have been sorted alphabetically."
            )
