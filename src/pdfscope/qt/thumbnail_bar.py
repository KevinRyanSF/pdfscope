"""Barra de miniaturas com renderização preguiçosa.

A versão anterior renderizava a miniatura de *todas* as páginas na abertura do
livro. Num manual de 300 páginas isso é uma eternidade antes de aparecer
qualquer coisa na tela. Aqui os itens são criados vazios (barato) e só as
miniaturas visíveis são desenhadas, conforme o usuário rola.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QSlider, QWidget

from ..core.document import PdfDocument
from .images import to_qpixmap

TAMANHO_ICONE = QSize(80, 110)
MARGEM_PRE_RENDER = 3  # quantas páginas além da área visível já vão renderizadas


class ThumbnailBar(QWidget):
    """Lista de miniaturas + slider vertical de navegação rápida."""

    page_selected = pyqtSignal(int)

    def __init__(self, document: PdfDocument, parent=None):
        super().__init__(parent)
        self._document = document
        self._renderizadas: set[int] = set()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.lista = QListWidget()
        self.lista.setIconSize(TAMANHO_ICONE)
        self.lista.setSpacing(6)
        self.lista.setUniformItemSizes(True)
        self.lista.currentRowChanged.connect(self._ao_selecionar_linha)
        self.lista.verticalScrollBar().valueChanged.connect(self._agendar_render)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(0)
        self.slider.setMaximum(max(0, document.page_count - 1))
        # Invertido para que a página 1 fique no topo.
        self.slider.setInvertedAppearance(True)
        self.slider.setInvertedControls(True)
        self.slider.valueChanged.connect(self.page_selected.emit)

        layout.addWidget(self.lista, 1)
        layout.addWidget(self.slider, 0)

        self._preencher()

    # ------------------------------------------------------------------ setup

    def _preencher(self) -> None:
        placeholder = QSize(TAMANHO_ICONE.width() + 16, TAMANHO_ICONE.height() + 20)
        for numero in range(self._document.page_count):
            item = QListWidgetItem(f"Pág. {numero + 1}")
            item.setSizeHint(placeholder)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.lista.addItem(item)

    # ------------------------------------------------------- render preguiçoso

    def showEvent(self, event):
        super().showEvent(event)
        self._agendar_render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._agendar_render()

    def _agendar_render(self, *_args) -> None:
        # Deixa o Qt terminar o layout antes de perguntar o que está visível.
        QTimer.singleShot(0, self._renderizar_visiveis)

    def _intervalo_visivel(self) -> tuple[int, int]:
        viewport = self.lista.viewport().rect()
        topo = self.lista.indexAt(viewport.topLeft()).row()
        base = self.lista.indexAt(viewport.bottomLeft()).row()

        if topo < 0:
            topo = 0
        if base < 0:
            base = min(self._document.page_count - 1, topo + 8)

        return (
            max(0, topo - MARGEM_PRE_RENDER),
            min(self._document.page_count - 1, base + MARGEM_PRE_RENDER),
        )

    def _renderizar_visiveis(self) -> None:
        if self._document.closed or self._document.page_count == 0:
            return

        inicio, fim = self._intervalo_visivel()
        for numero in range(inicio, fim + 1):
            if numero in self._renderizadas:
                continue
            item = self.lista.item(numero)
            if item is None:
                continue
            item.setIcon(QIcon(to_qpixmap(self._document.render_thumbnail(numero))))
            self._renderizadas.add(numero)

    # ------------------------------------------------------------------ estado

    def _ao_selecionar_linha(self, linha: int) -> None:
        if linha >= 0:
            self.page_selected.emit(linha)

    def set_current_page(self, page: int) -> None:
        """Sincroniza lista e slider sem disparar sinais em loop."""
        for widget, setter in ((self.lista, "setCurrentRow"), (self.slider, "setValue")):
            widget.blockSignals(True)
            getattr(widget, setter)(page)
            widget.blockSignals(False)
        self._agendar_render()
