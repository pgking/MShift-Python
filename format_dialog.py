from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel
)
from PyQt5.QtCore import Qt


class CellFormatDialog(QDialog):
    """Dialog to set text formatting (bold, italic, underline) for a cell."""
    
    def __init__(self, bold=False, italic=False, underline=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mise en forme")
        self.setMinimumWidth(220)
        self._build_ui(bold, italic, underline)
    
    def _build_ui(self, bold, italic, underline):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        label = QLabel("Options de mise en forme :")
        label.setAlignment(Qt.AlignLeft)
        layout.addWidget(label)
        
        self.bold_cb = QCheckBox("Gras")
        self.bold_cb.setChecked(bold)
        layout.addWidget(self.bold_cb)
        
        self.italic_cb = QCheckBox("Italique")
        self.italic_cb.setChecked(italic)
        layout.addWidget(self.italic_cb)
        
        self.underline_cb = QCheckBox("Souligné")
        self.underline_cb.setChecked(underline)
        layout.addWidget(self.underline_cb)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_format(self):
        """Returns (bold, italic, underline) tuple."""
        return (
            self.bold_cb.isChecked(),
            self.italic_cb.isChecked(),
            self.underline_cb.isChecked()
        )
