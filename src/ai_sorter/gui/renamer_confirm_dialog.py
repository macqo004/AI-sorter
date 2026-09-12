from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)


class RenamerConfirmDialog(QDialog):
    def __init__(self, summary: str, preview_lines: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Renamer — zatwierdzenie")
        self.setModal(True)
        self.setMinimumSize(1000, 650)
        self.resize(1250, 800)

        layout = QVBoxLayout(self)
        label = QLabel(summary + "\n\nCzy wykonać te zmiany?")
        label.setWordWrap(True)
        layout.addWidget(label)

        details = QPlainTextEdit(self)
        details.setReadOnly(True)
        details.setLineWrapMode(QPlainTextEdit.NoWrap)
        details.setPlainText("\n".join(preview_lines))
        details.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        details.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(details, 1)

        buttons = QDialogButtonBox(self)
        self.apply_button = buttons.addButton("Wykonaj zmiany", QDialogButtonBox.AcceptRole)
        buttons.addButton("Anuluj", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
