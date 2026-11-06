"""Área de exibição da página."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QScrollArea

from ..core.render import RenderedPage
from .images import to_qpixmap


class PageView(QScrollArea):
    """Mostra a página renderizada, com rolagem e zoom pela roda + Ctrl."""

    zoom_requested = pyqtSignal(float)  # delta de zoom

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setText("Nenhuma página carregada")
        self.setWidget(self._label)

    def set_page(self, rendered: RenderedPage) -> None:
        self._label.setPixmap(to_qpixmap(rendered))

    def clear(self) -> None:
        self._label.clear()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 0.25 if event.angleDelta().y() > 0 else -0.25
            self.zoom_requested.emit(delta)
            event.accept()
            return
        super().wheelEvent(event)
