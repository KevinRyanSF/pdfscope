"""O widget de leitura completo — é isto que outros aplicativos embutem."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.bookmarks import BookmarkStore
from ..core.document import PdfDocument
from ..storage.memory import InMemoryBookmarkStore
from .book_tab import BookTab
from .outline_tree import OutlineTree


class PdfReaderWidget(QWidget):
    """Leitor com abas, miniaturas, busca, índice e marcadores.

    Não sabe nada sobre RPG, campanhas ou banco de dados: recebe um
    `BookmarkStore` de fora e pronto. É o que permite o mesmo widget servir o
    aplicativo autônomo e o RPG Master Suite.
    """

    page_changed = pyqtSignal(str, int)  # doc_id, página (zero-based)
    document_opened = pyqtSignal(str)
    document_closed = pyqtSignal(str)

    def __init__(self, bookmark_store: BookmarkStore | None = None, parent=None):
        super().__init__(parent)
        self.bookmark_store: BookmarkStore = bookmark_store or InMemoryBookmarkStore()
        self._abas: dict[str, BookTab] = {}
        self._busca_atual: str = ""

        self._montar_ui()
        self._montar_atalhos()
        self._atualizar_controles()

    # ------------------------------------------------------------------- UI

    def _montar_ui(self) -> None:
        layout = QVBoxLayout(self)

        barra = QHBoxLayout()
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText("Buscar no livro ativo…  (Ctrl+F)")
        self.input_busca.returnPressed.connect(self.buscar)

        self.btn_busca = QPushButton("🔍 Buscar")
        self.btn_busca.clicked.connect(self.buscar)

        self.btn_marcador = QPushButton("⭐ Salvar marcador")
        self.btn_marcador.setToolTip("Cria um marcador na página atual (Ctrl+D)")
        self.btn_marcador.clicked.connect(self.salvar_marcador)

        self.btn_zoom_menos = QPushButton("🔍➖")
        self.btn_zoom_menos.clicked.connect(lambda: self._com_aba(lambda a: a.zoom_by(-0.25)))
        self.btn_zoom_reset = QPushButton("Ajustar")
        self.btn_zoom_reset.clicked.connect(lambda: self._com_aba(lambda a: a.reset_zoom()))
        self.btn_zoom_mais = QPushButton("🔍➕")
        self.btn_zoom_mais.clicked.connect(lambda: self._com_aba(lambda a: a.zoom_by(0.25)))

        self.btn_anterior = QPushButton("◀")
        self.btn_anterior.clicked.connect(lambda: self._com_aba(lambda a: a.step(-1)))
        self.spin_pagina = QSpinBox()
        self.spin_pagina.setMinimum(1)
        self.spin_pagina.setMaximum(1)
        self.spin_pagina.valueChanged.connect(self._ir_para_pagina_do_spin)
        self.label_total = QLabel("/ 0")
        self.btn_proxima = QPushButton("▶")
        self.btn_proxima.clicked.connect(lambda: self._com_aba(lambda a: a.step(1)))

        for widget in (self.input_busca, self.btn_busca, self.btn_marcador):
            barra.addWidget(widget)
        barra.addStretch()
        for widget in (
            self.btn_zoom_menos,
            self.btn_zoom_reset,
            self.btn_zoom_mais,
            self.btn_anterior,
            self.spin_pagina,
            self.label_total,
            self.btn_proxima,
        ):
            barra.addWidget(widget)
        layout.addLayout(barra)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.outline = OutlineTree()
        self.outline.page_requested.connect(self._ao_pedir_pagina)
        self.outline.bookmark_removal_requested.connect(self.remover_marcador)
        splitter.addWidget(self.outline)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._fechar_aba_por_indice)
        self.tabs.currentChanged.connect(self._ao_trocar_aba)
        splitter.addWidget(self.tabs)

        splitter.setSizes([280, 820])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _montar_atalhos(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.input_busca.setFocus)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.salvar_marcador)
        QShortcut(
            QKeySequence(QKeySequence.StandardKey.MoveToNextPage),
            self,
            activated=lambda: self._com_aba(lambda a: a.step(1)),
        )
        QShortcut(
            QKeySequence(QKeySequence.StandardKey.MoveToPreviousPage),
            self,
            activated=lambda: self._com_aba(lambda a: a.step(-1)),
        )

    # ------------------------------------------------------------- documentos

    def open_document(
        self,
        path: str | os.PathLike,
        *,
        doc_id: str | None = None,
        title: str | None = None,
        start_page: int = 0,
    ) -> BookTab:
        """Abre um PDF numa nova aba (ou foca a aba já aberta) e devolve a aba."""
        identificador = str(doc_id) if doc_id is not None else os.fspath(path)

        if identificador in self._abas:
            aba = self._abas[identificador]
            self.tabs.setCurrentWidget(aba)
            return aba

        documento = PdfDocument(path, doc_id=identificador)
        aba = BookTab(documento, title=title or documento.title)
        aba.page_changed.connect(lambda pagina, ident=identificador: self._ao_mudar_pagina(ident, pagina))

        self._abas[identificador] = aba
        indice = self.tabs.addTab(aba, f"📖 {aba.title}")
        self.tabs.setCurrentIndex(indice)

        aba.goto(max(0, min(int(start_page or 0), documento.page_count - 1)), notify=False)
        self._atualizar_controles()
        self._atualizar_outline()
        self.document_opened.emit(identificador)
        return aba

    def close_document(self, doc_id: str) -> None:
        aba = self._abas.get(str(doc_id))
        if aba is not None:
            self._fechar_aba_por_indice(self.tabs.indexOf(aba))

    def current_tab(self) -> BookTab | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, BookTab) else None

    def _com_aba(self, acao) -> None:
        aba = self.current_tab()
        if aba is not None:
            acao(aba)

    def _fechar_aba_por_indice(self, indice: int) -> None:
        if indice < 0:
            return
        aba = self.tabs.widget(indice)
        if not isinstance(aba, BookTab):
            return

        identificador = aba.doc_id
        self.tabs.removeTab(indice)
        self._abas.pop(identificador, None)
        aba.close_document()
        aba.deleteLater()

        self._atualizar_controles()
        self._atualizar_outline()
        self.document_closed.emit(identificador)

    # ------------------------------------------------------------- navegação

    def _ao_mudar_pagina(self, doc_id: str, pagina: int) -> None:
        aba = self.current_tab()
        if aba is not None and aba.doc_id == doc_id:
            self.spin_pagina.blockSignals(True)
            self.spin_pagina.setValue(pagina + 1)
            self.spin_pagina.blockSignals(False)
        self.page_changed.emit(doc_id, pagina)

    def _ir_para_pagina_do_spin(self, valor: int) -> None:
        self._com_aba(lambda aba: aba.goto(valor - 1))

    def _ao_pedir_pagina(self, pagina: int, termo_grifo: str) -> None:
        # Passa a string mesmo vazia: clicar no índice ou num marcador limpa o
        # grifo da busca anterior, em vez de arrastá-lo para a página nova.
        self._com_aba(lambda aba: aba.goto(pagina, highlight=termo_grifo))

    def _ao_trocar_aba(self, _indice: int) -> None:
        self._atualizar_controles()
        self._atualizar_outline()

    def _atualizar_controles(self) -> None:
        aba = self.current_tab()
        tem_aba = aba is not None

        for widget in (
            self.btn_busca,
            self.btn_marcador,
            self.btn_zoom_menos,
            self.btn_zoom_reset,
            self.btn_zoom_mais,
            self.btn_anterior,
            self.btn_proxima,
            self.spin_pagina,
            self.input_busca,
        ):
            widget.setEnabled(tem_aba)

        self.spin_pagina.blockSignals(True)
        if tem_aba:
            self.spin_pagina.setMaximum(aba.document.page_count)
            self.spin_pagina.setValue(aba.current_page + 1)
            self.label_total.setText(f"/ {aba.document.page_count}")
        else:
            self.spin_pagina.setMaximum(1)
            self.spin_pagina.setValue(1)
            self.label_total.setText("/ 0")
        self.spin_pagina.blockSignals(False)

    # ------------------------------------------------------------- marcadores

    def _atualizar_outline(self, resultados=None) -> None:
        aba = self.current_tab()
        if aba is None:
            self.outline.clear()
            return

        self.outline.populate(
            bookmarks=self.bookmark_store.list(aba.doc_id),
            toc=aba.document.toc,
            search_results=resultados,
            query=self._busca_atual,
        )

    def perguntar_titulo_do_marcador(self, sugestao: str) -> str | None:
        """Pergunta o nome do marcador ao usuário.

        Isolado num método para que quem embute o leitor possa trocar o diálogo —
        e para que os testes não precisem de janela modal.
        """
        titulo, ok = QInputDialog.getText(
            self, "Novo marcador", "Nome deste marcador:", text=sugestao
        )
        return titulo.strip() if ok and titulo.strip() else None

    def salvar_marcador(self) -> None:
        aba = self.current_tab()
        if aba is None:
            return

        sugestao = self._busca_atual or f"Página {aba.current_page + 1}"
        titulo = self.perguntar_titulo_do_marcador(sugestao)
        if titulo:
            self.bookmark_store.add(aba.doc_id, aba.current_page, titulo)
            self._atualizar_outline()

    def remover_marcador(self, bookmark_id: str) -> None:
        self.bookmark_store.remove(bookmark_id)
        self._atualizar_outline()

    # ------------------------------------------------------------------ busca

    def buscar(self) -> None:
        aba = self.current_tab()
        if aba is None:
            return

        self._busca_atual = self.input_busca.text().strip()
        if not self._busca_atual:
            aba.clear_highlight()
            self._atualizar_outline()
            return

        self._atualizar_outline(aba.document.search(self._busca_atual))
