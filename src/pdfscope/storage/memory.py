"""Armazenamento de marcadores em memória (útil em testes e como base)."""

from __future__ import annotations

from ..core.bookmarks import Bookmark


class InMemoryBookmarkStore:
    """Guarda os marcadores num dicionário. Some quando o processo morre."""

    def __init__(self) -> None:
        self._por_doc: dict[str, list[Bookmark]] = {}

    def list(self, doc_id: str) -> list[Bookmark]:
        return sorted(self._por_doc.get(doc_id, []), key=lambda b: (b.page, b.title))

    def add(self, doc_id: str, page: int, title: str) -> Bookmark:
        marcador = Bookmark(doc_id=doc_id, page=int(page), title=title)
        self._por_doc.setdefault(doc_id, []).append(marcador)
        return marcador

    def remove(self, bookmark_id: str) -> None:
        for doc_id, marcadores in self._por_doc.items():
            self._por_doc[doc_id] = [b for b in marcadores if b.id != bookmark_id]
