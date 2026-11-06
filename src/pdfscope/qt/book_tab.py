"""Uma aba de livro: documento + miniaturas + página."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from ..core.document import PdfDocument
from ..core.render import RenderOptions
from .page_view import PageView
from .thumbnail_bar import ThumbnailBar


class BookTab(QWidget):
    """Estado de leitura de um documento: página atual, zoom e grifo."""

    page_changed = pyqtSignal(int)

    def __init__(self, document: PdfDocument, title: str = "", parent=None):
        super().__init__(parent)
        self.document = document
        self.title = title or document.title
        self._options = RenderOptions()
        self._current_page = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.thumbnails = ThumbnailBar(document)
        self.thumbnails.page_selected.connect(self.goto)
        splitter.addWidget(self.thumbnails)

        self.page_view = PageView()
        self.page_view.zoom_requested.connect(self.zoom_by)
        splitter.addWidget(self.page_view)

        splitter.setSizes([200, 800])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    # ------------------------------------------------------------------ estado

    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def zoom(self) -> float:
        return self._options.zoom

    @property
    def highlight(self) -> str | None:
        return self._options.highlight

    @property
    def doc_id(self) -> str:
        return self.document.doc_id

    # ------------------------------------------------------------- navegação

    def goto(self, page: int, highlight: str | None = None, *, notify: bool = True) -> None:
        if not 0 <= page < self.document.page_count:
            return

        self._current_page = page
        if highlight is not None:
            self._options = self._options.with_highlight(highlight)

        self.page_view.set_page(self.document.render_page(page, self._options))
        self.thumbnails.set_current_page(page)

        if notify:
            self.page_changed.emit(page)

    def step(self, delta: int) -> None:
        self.goto(self._current_page + delta)

    def zoom_by(self, delta: float) -> None:
        novas = self._options.with_zoom(self._options.zoom + delta)
        if novas.zoom != self._options.zoom:
            self._options = novas
            self.goto(self._current_page, notify=False)

    def reset_zoom(self) -> None:
        self._options = self._options.with_zoom(1.5)
        self.goto(self._current_page, notify=False)

    def clear_highlight(self) -> None:
        self._options = self._options.with_highlight(None)
        self.goto(self._current_page, notify=False)

    # ---------------------------------------------------------------- limpeza

    def close_document(self) -> None:
        self.page_view.clear()
        self.document.close()
