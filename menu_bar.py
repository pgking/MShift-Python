from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
from PyQt5.QtGui import QKeySequence


class MenuBar(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent  # MainWindow

        self._create_file_menu()
        self._create_services_menu()
        self._create_about_menu()

    def _create_file_menu(self):
        file_menu = self.addMenu("File")

        new_action = QAction("New Schedule", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.parent.new_file)

        save_action = QAction("Save…", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.parent.save_file)

        quick_save_action = QAction("Quick Save", self)
        quick_save_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        quick_save_action.triggered.connect(self.parent.quick_save)

        load_action = QAction("Load…", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self.parent.load_file)

        self.recent_menu = QMenu("Load Recent", self)
        # Filled dynamically later

        save_exit_action = QAction("Save and Exit", self)
        save_exit_action.setShortcut(QKeySequence.Quit)
        save_exit_action.triggered.connect(self.parent.save_and_exit)

        file_menu.addAction(new_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(quick_save_action)
        file_menu.addSeparator()
        file_menu.addAction(load_action)
        file_menu.addMenu(self.recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(save_exit_action)

    def _create_services_menu(self):
        services_menu = self.addMenu("Services")

        manage_services_action = QAction("Manage Services", self)
        manage_services_action.triggered.connect(
            self.parent.open_services_dialog
        )

        services_menu.addAction(manage_services_action)

    def _create_about_menu(self):
        about_menu = self.addMenu("About")

        about_action = QAction("About mshift", self)
        about_action.triggered.connect(self.parent.open_about_dialog)

        about_menu.addAction(about_action)
