"""Marcadores e o contrato de armazenamento.

Este módulo é o ponto de inversão de dependência do pdfscope: o leitor sabe
*que* existe um lugar para guardar marcadores, mas nunca sabe qual. Quem embute
o leitor decide — um arquivo JSON, um banco SQL, uma API.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


def novo_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True)
class Bookmark:
    """Um marcador de página criado pelo usuário.

    doc_id é uma string opaca escolhida por quem embute o leitor. Para um app
    de linha de comando costuma ser o caminho do arquivo; para um app com banco,
    a chave primária do registro correspondente.
    """

    doc_id: str
    page: int
    title: str
    id: str = field(default_factory=novo_id)


@runtime_checkable
class BookmarkStore(Protocol):
    """Contrato mínimo de persistência de marcadores."""

    def list(self, doc_id: str) -> list[Bookmark]:
        """Marcadores do documento, ordenados por página."""
        ...

    def add(self, doc_id: str, page: int, title: str) -> Bookmark:
        """Cria e devolve o marcador já persistido."""
        ...

    def remove(self, bookmark_id: str) -> None:
        """Remove pelo id. Silencioso se o marcador já não existir."""
        ...
