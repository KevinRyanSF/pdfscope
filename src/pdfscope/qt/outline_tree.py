"""Painel lateral: marcadores, índice original e resultados de busca."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem

from ..core.bookmarks import Bookmark
from ..core.document import SearchHit, TocEntry

PAPEL_PAGINA = Qt.ItemDataRole.UserRole
PAPEL_GRIFO = Qt.ItemDataRole.UserRole + 1
PAPEL_MARCADOR = Qt.ItemDataRole.UserRole + 2


class OutlineTree(QTreeWidget):
    """Árvore de navegação do livro.

    Emite `page_requested(pagina, termo_grifo)` — o termo vem vazio quando o
    item clicado não é um resultado de busca.
    """

    page_requested = pyqtSignal(int, str)
    bookmark_removal_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Navegação do livro")
        self.itemClicked.connect(self._ao_clicar)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu_de_contexto)

    # ------------------------------------------------------------------ montagem

    def populate(
        self,
        *,
        bookmarks: list[Bookmark],
        toc: list[TocEntry],
        search_results: list[SearchHit] | None = None,
        query: str = "",
    ) -> None:
        self.clear()

        raiz_marcadores = QTreeWidgetItem([f"⭐ Meus marcadores ({len(bookmarks)})"])
        for marcador in bookmarks:
            item = QTreeWidgetItem([f"📌 {marcador.title} (p. {marcador.page + 1})"])
            item.setData(0, PAPEL_PAGINA, marcador.page)
            item.setData(0, PAPEL_MARCADOR, marcador.id)
            raiz_marcadores.addChild(item)
        if not bookmarks:
            raiz_marcadores.addChild(QTreeWidgetItem(["(nenhum marcador ainda)"]))
        self.addTopLevelItem(raiz_marcadores)
        raiz_marcadores.setExpanded(True)

        raiz_toc = QTreeWidgetItem(["📁 Índice original"])
        if toc:
            pilha: list[tuple[int, QTreeWidgetItem]] = [(0, raiz_toc)]
            for entrada in toc:
                item = QTreeWidgetItem([f"{entrada.title} (p. {entrada.page + 1})"])
                item.setData(0, PAPEL_PAGINA, entrada.page)
                # Respeita a hierarquia de níveis do PDF em vez de achatar tudo.
                while len(pilha) > 1 and pilha[-1][0] >= entrada.level:
                    pilha.pop()
                pilha[-1][1].addChild(item)
                pilha.append((entrada.level, item))
        else:
            raiz_toc.addChild(QTreeWidgetItem(["(este PDF não tem índice)"]))
        self.addTopLevelItem(raiz_toc)
        raiz_toc.setExpanded(True)

        if search_results is not None:
            total = sum(hit.occurrences for hit in search_results)
            raiz_busca = QTreeWidgetItem(
                [f"🔍 '{query}' — {total} ocorrência(s) em {len(search_results)} página(s)"]
            )
            for hit in search_results:
                rotulo = f"Página {hit.page + 1} ({hit.occurrences}×)"
                item = QTreeWidgetItem([rotulo])
                item.setData(0, PAPEL_PAGINA, hit.page)
                item.setData(0, PAPEL_GRIFO, query)
                raiz_busca.addChild(item)
            if not search_results:
                raiz_busca.addChild(QTreeWidgetItem(["(nada encontrado)"]))
            self.addTopLevelItem(raiz_busca)
            raiz_busca.setExpanded(True)

    # ------------------------------------------------------------------ eventos

    def _ao_clicar(self, item: QTreeWidgetItem, _coluna: int) -> None:
        pagina = item.data(0, PAPEL_PAGINA)
        if pagina is None:
            return
        self.page_requested.emit(int(pagina), item.data(0, PAPEL_GRIFO) or "")

    def _menu_de_contexto(self, ponto) -> None:
        item = self.itemAt(ponto)
        if item is None:
            return
        marcador_id = item.data(0, PAPEL_MARCADOR)
        if not marcador_id:
            return

        menu = QMenu(self)
        acao = QAction("Remover marcador", menu)
        acao.triggered.connect(lambda: self.bookmark_removal_requested.emit(str(marcador_id)))
        menu.addAction(acao)
        menu.exec(self.viewport().mapToGlobal(ponto))
