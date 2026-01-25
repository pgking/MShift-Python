from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt
from models import Service


class ServiceCell:
    """
    Binds a QComboBox to a (person, day, MonthData) assignment.
    Owns:
    - service selection logic
    - backend updates
    - combo styling
    """

    def __init__(
        self,
        combo: QComboBox,
        main_window,
        person,
        day: int,
        month_data,
        services: list
    ):
        self.combo = combo
        self.main_window = main_window
        self.person = person
        self.day = day
        self.month_data = month_data
        self.services = services

        self._setup_combo()

    # -------------------------
    # SETUP
    # -------------------------

    def _setup_combo(self):
        self.combo.setContextMenuPolicy(Qt.NoContextMenu)
        self.combo.setEditable(True)
        self.combo.setMaxVisibleItems(len(self.services) + 1)
        self.combo.setFocusPolicy(Qt.NoFocus)
        self.combo.setAutoFillBackground(True)

        line = self.combo.lineEdit()
        line.setReadOnly(True)
        line.setAlignment(Qt.AlignCenter)
        line.setContextMenuPolicy(Qt.NoContextMenu)

        self.combo.clear()
        self.combo.addItem("")  # empty = no service

        for service in self.services:
            if service.is_visible:
                self.combo.addItem(service.name)

        self._apply_style(None)

    def apply_service_by_index(self, index: int):
        # Determine service_id from combo selection
        if index == 0:
            service_id = None
            service = None
        else:
            # We must map back from combo text to correct service object
            current_name = self.combo.itemText(index)
            service = next((s for s in self.services if s.name == current_name), None)
            if service:
                service_id = service.id
            else:
                 # Should not happen unless corrupted
                 return

        # ONLY call canonical entry point - no direct mutation
        self.main_window.apply_assignment_change(
            person_id=self.person.id,
            day=self.day,
            service_id=service_id,
            reason="combo_selection"
        )

        # UI update after backend is updated
        self.combo.setCurrentIndex(index)
        if service:
            self.combo.setCurrentText(service.short_name)
        
        self._apply_style(service)
        
        self.combo.update()
        self.combo.repaint()
        
        self.combo.update()
        self.combo.repaint()
        
        # self.main_window.refresh_row_headers() -> Moved to apply_assignment_change


    # -------------------------
    # BEHAVIOR
    # -------------------------

    def preset_service(self, service):
        """
        Apply an existing service without triggering unwanted side effects.
        """
        self.combo.blockSignals(True)

        if service is None:
            self.combo.setCurrentIndex(0)
            self._apply_style(None)
        else:
            # We need to find the index in the COMBOBOX, not the full list
            # Since combo only contains visible items, hidden items won't have an index > 0
            if service.is_visible:
                # Find index in the filtered list logic (tricky) or just match text
                index = self.combo.findText(service.name)
                if index >= 0:
                    self.combo.setCurrentIndex(index)
                    # Force display of short name
                    self.combo.setCurrentText(service.short_name)
            else:
                # For hidden services, we can't select them in the dropdown
                # But we can set the text manually? QComboBox only shows currentText if editable
                # We set editable=True in setup, so this works.
                self.combo.setCurrentIndex(-1)
                self.combo.setEditText(service.short_name)

            self._apply_style(service)
        
        self.combo.blockSignals(False)


    # -------------------------
    # STYLING
    # -------------------------

    def _apply_style(self, service):
        color = service.color_hex if service else "transparent"
        
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {color};
                border: none;
                padding-left: 4px;
            }}
            QComboBox::drop-down {{
                width: 0px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
       """)
