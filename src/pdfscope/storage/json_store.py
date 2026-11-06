"""Armazenamento padrão: um arquivo JSON.

É o que faz o pdfscope ser útil sozinho — sem banco, sem configuração.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..core.bookmarks import Bookmark


def caminho_padrao() -> Path:
    """~/.pdfscope/bookmarks.json (respeita XDG_DATA_HOME quando definido)."""
    base = os.environ.get("XDG_DATA_HOME")
    raiz = Path(base) / "pdfscope" if base else Path.home() / ".pdfscope"
    return raiz / "bookmarks.json"


class JsonBookmarkStore:
    """Marcadores num único JSON, no formato {doc_id: [ {id, page, title} ]}."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = Path(path) if path is not None else caminho_padrao()
        self._dados: dict[str, list[dict]] = self._carregar()

    def _carregar(self) -> dict[str, list[dict]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as fp:
                dados = json.load(fp)
        except (json.JSONDecodeError, OSError):
            # Arquivo corrompido não pode derrubar o leitor.
            return {}
        return dados if isinstance(dados, dict) else {}

    def _salvar(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.path.with_suffix(".tmp")
        with temporario.open("w", encoding="utf-8") as fp:
            json.dump(self._dados, fp, ensure_ascii=False, indent=2)
        os.replace(temporario, self.path)

    # ------------------------------------------------------------------ API

    def list(self, doc_id: str) -> list[Bookmark]:
        registros = self._dados.get(str(doc_id), [])
        marcadores = [
            Bookmark(
                doc_id=str(doc_id),
                page=int(r["page"]),
                title=str(r["title"]),
                id=str(r["id"]),
            )
            for r in registros
        ]
        return sorted(marcadores, key=lambda b: (b.page, b.title))

    def add(self, doc_id: str, page: int, title: str) -> Bookmark:
        marcador = Bookmark(doc_id=str(doc_id), page=int(page), title=title)
        self._dados.setdefault(str(doc_id), []).append(
            {"id": marcador.id, "page": marcador.page, "title": marcador.title}
        )
        self._salvar()
        return marcador

    def remove(self, bookmark_id: str) -> None:
        mudou = False
        for doc_id, registros in list(self._dados.items()):
            restantes = [r for r in registros if r.get("id") != bookmark_id]
            if len(restantes) != len(registros):
                self._dados[doc_id] = restantes
                mudou = True
        if mudou:
            self._salvar()
