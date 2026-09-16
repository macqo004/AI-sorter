from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout

from ..image_extension_fixer import ExtensionChangeProposal


class ImageExtensionConfirmDialog(QDialog):
    """Explicit preview/confirmation dialog for extension-only changes."""

    def __init__(self, proposals: list[ExtensionChangeProposal], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Image Extension Correction — confirmation")
        self.setModal(True)
        self.setMinimumSize(1000, 650)
        self.resize(1250, 800)

        layout = QVBoxLayout(self)
        label = QLabel(
            f"Proposed extension-only changes: {len(proposals):,}\n\n"
            "No image contents will be changed. Existing destination files are never overwritten.\n\n"
            "Review the complete list before applying."
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        details = QPlainTextEdit(self)
        details.setReadOnly(True)
        details.setLineWrapMode(QPlainTextEdit.NoWrap)
        details.setPlainText(
            "\n".join(
                f"{proposal.source}  ->  {proposal.destination}  [{proposal.detected_format}]"
                for proposal in proposals
            )
        )
        details.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        details.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(details, 1)

        buttons = QDialogButtonBox(self)
        apply_button = buttons.addButton("Apply extension changes", QDialogButtonBox.AcceptRole)
        apply_button.setDefault(False)
        buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
