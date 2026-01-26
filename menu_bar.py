import os
from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
from PyQt5.QtGui import QKeySequence


class MenuBar(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent  # MainWindow

        self._create_file_menu()
        self._create_services_menu()
        self._create_preferences_menu()
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

        import_menu = QMenu("Import", self)
        import_menu.addAction("From Excel...", self.parent.import_excel)

        export_menu = QMenu("Export", self)
        export_menu.addAction("Excel", self.parent.export_excel)

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
        file_menu.addMenu(import_menu)
        file_menu.addMenu(export_menu)
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

        check_update_action = QAction("Check for Updates...", self)
        check_update_action.triggered.connect(lambda: self.parent.updater.start_check(silent=False))

        about_menu.addAction(about_action)
        about_menu.addAction(check_update_action)

    def _create_preferences_menu(self):
        prefs_menu = self.addMenu("Preferences")

        prefs_action = QAction("Preferences", self)
        prefs_action.triggered.connect(self.parent.open_preferences)

        prefs_menu.addAction(prefs_action)

    def update_recent_menu(self, paths):
        self.recent_menu.clear()
        
        if not paths:
            no_recent_action = QAction("No recent files", self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)
            return

        for path in paths:
            filename = os.path.basename(path)
            # Create an action for each file
            action = QAction(filename, self)
            action.setToolTip(path)
            action.triggered.connect(lambda checked, p=path: self.parent.load_recent_file(p))
            self.recent_menu.addAction(action)