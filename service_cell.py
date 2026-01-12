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
            self.combo.addItem(service.name)

        self._apply_style(None)

    def apply_service_by_index(self, index: int):
        if index == 0:
            self.month_data.set_service(self.person.id, self.day, None)
            self._apply_style(None)
        else:
            service = self.services[index - 1]
            self.month_data.set_service(self.person.id, self.day, service.id)
            self._apply_style(service)

        self.main_window.refresh_row_headers()


    # -------------------------
    # BEHAVIOR
    # -------------------------

    def _on_service_selected(self, index: int):
        if index == 0:
            self.month_data.set_service(self.person.id, self.day, None)
            self._apply_style(None)
            self.combo.setCurrentIndex(0)
        else:
            service = self.services[index - 1]
            self.month_data.set_service(self.person.id, self.day, service.id)
            self._apply_style(service)

        self.main_window.refresh_row_headers()

    def preset_service(self, service):
        """
        Apply an existing service without triggering unwanted side effects.
        """
        self.combo.blockSignals(True)

        if service is None:
            self.combo.setCurrentIndex(0)
            self._apply_style(None)
        else:
            index = self.services.index(service) + 1
            self.combo.setCurrentIndex(index)
            self.combo.setCurrentText(service.short_name)
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
