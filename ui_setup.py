import calendar
from datetime import datetime
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QComboBox, QPushButton, QHeaderView
from PyQt5.QtCore import Qt

from drag_table_widget import DragTableWidget
from headers import ClickableHorizontalHeader, ColoredVerticalHeader
from table_rebuilder import TableRebuilder
from workload import WorkloadCalculator

def setup_main_window_ui(mw):
    """
    Assembles the UI for the MainWindow.
    """
    # 1. Create the table instance silently so mw.table exists for dependencies
    # We don't add it to layout yet.
    mw.table = DragTableWidget(1, 31)

    # 2. Initialize rebuilder and workload that depend on mw.table
    mw.table_rebuilder = TableRebuilder(mw)
    mw.workload = WorkloadCalculator(mw)

    # 3. Setup header components (added to layout in this order)
    _setup_save_load_buttons(mw)
    _setup_action_buttons(mw)
    _setup_controls(mw)

    # 4. Configure table and add it to layout at the bottom
    _setup_table(mw)

def _setup_save_load_buttons(mw):
    save_load_layout = QHBoxLayout()

    mw.save_btn = QLabel("💾 Save")
    mw.load_btn = QLabel("📂 Load")

    for btn in [mw.save_btn, mw.load_btn]:
        btn.setStyleSheet("padding: 6px; border: 1px solid #888; border-radius: 4px;")
        btn.setAlignment(Qt.AlignCenter)

    mw.save_btn.mousePressEvent = lambda e: mw.save_file()
    mw.load_btn.mousePressEvent = lambda e: mw.load_file()

    save_load_layout.addStretch()
    save_load_layout.addWidget(mw.save_btn)
    save_load_layout.addWidget(mw.load_btn)
    save_load_layout.addStretch()

    mw.main_layout.addLayout(save_load_layout)

def _setup_controls(mw):
    controls_layout = QHBoxLayout()

    real_life_month = datetime.now().month
    real_life_year = datetime.now().year

    mw.month_combo = QComboBox()
    mw.month_combo.addItems(calendar.month_name[1:])
    mw.month_combo.setCurrentIndex(real_life_month - 1)
    mw.month_combo.currentIndexChanged.connect(mw.finalize_table_setup)

    # Previous month button
    prev_btn = QPushButton("◀")
    prev_btn.setFixedWidth(32)
    prev_btn.clicked.connect(mw._go_to_previous_month)

    # Next month button
    next_btn = QPushButton("▶")
    next_btn.setFixedWidth(32)
    next_btn.clicked.connect(mw._go_to_next_month)

    mw.year_combo = QComboBox()
    mw.year_combo.addItems([str(y) for y in range(2025, 2031)])
    mw.year_combo.setCurrentText(f"{real_life_year}")
    mw.year_combo.currentIndexChanged.connect(mw.finalize_table_setup)

    controls_layout.addStretch()
    controls_layout.addWidget(QLabel("Month:"))
    controls_layout.addWidget(mw.month_combo)
    controls_layout.addWidget(prev_btn)
    controls_layout.addWidget(next_btn)
    controls_layout.addWidget(QLabel("Year:"))
    controls_layout.addWidget(mw.year_combo)
    controls_layout.addStretch()

    mw.main_layout.addLayout(controls_layout)

def _setup_table(mw):
    # mw.table is already created in setup_main_window_ui
    mw.table.main_window = mw
    mw.table.setShowGrid(True)
    mw.table.setStyleSheet("""
        QTableWidget {
            gridline-color: #B0B0B0;
        }
    """)

    # Disable cell selection highlight
    mw.table.setSelectionMode(QTableWidget.NoSelection)

    mw.table.viewport().installEventFilter(mw)
    mw.table.horizontalHeader().installEventFilter(mw)

    # Keep headers interactive
    mw.table.horizontalHeader().setSectionsClickable(True)
    mw.table.verticalHeader().setSectionsClickable(True)

    header = ClickableHorizontalHeader(mw, mw.table)
    mw.table.setHorizontalHeader(header)
    header.setSectionsClickable(True)

    # Handle note edits (last column)
    mw.table.itemChanged.connect(mw._on_item_changed)

    mw.table.horizontalHeader().setStyleSheet("""
        QHeaderView::section {
            border-bottom: 5px solid #888;  /* line thickness and color */
            padding: 4px;                   /* optional, for spacing */
            background-color : #f0f0f0;
        }
    """)

    # Optional: make sure the header uses full height for the border
    mw.table.horizontalHeader().setHighlightSections(False)
    mw.table.horizontalHeader().setStretchLastSection(True)

    header = ColoredVerticalHeader(main_window=mw, parent=mw.table)
    mw.table.setVerticalHeader(header)
    header.setMinimumWidth(80)
    header.setStyleSheet("QHeaderView::section { background: transparent; }")

    mw.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
    mw.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

    mw.main_layout.addWidget(mw.table)

def _setup_action_buttons(mw):
    buttons_layout = QHBoxLayout()

    mw.add_person_btn = QLabel("➕ Add Person")
    mw.add_service_btn = QLabel("➕ Add Service")

    # Make them look clickable
    mw.add_person_btn.setStyleSheet(
        "padding: 6px; border: 1px solid #888; border-radius: 4px;"
    )
    mw.add_service_btn.setStyleSheet(
        "padding: 6px; border: 1px solid #888; border-radius: 4px;"
    )

    mw.add_person_btn.setAlignment(Qt.AlignCenter)
    mw.add_service_btn.setAlignment(Qt.AlignCenter)

    mw.add_person_btn.mousePressEvent = mw._open_add_person
    mw.add_service_btn.mousePressEvent = mw._open_add_service

    buttons_layout.addStretch()
    buttons_layout.addWidget(mw.add_person_btn)
    buttons_layout.addWidget(mw.add_service_btn)
    buttons_layout.addStretch()

    mw.main_layout.addLayout(buttons_layout)
