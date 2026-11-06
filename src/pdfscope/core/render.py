"""Estruturas de renderização — deliberadamente sem nenhuma dependência de UI.

O núcleo do pdfscope devolve *bytes* de imagem, nunca um QPixmap. É isso que
permite que o mesmo código sirva uma interface Qt hoje e um endpoint HTTP amanhã.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderOptions:
    """Como uma página deve ser rasterizada.

    zoom:      1.0 = 100% do tamanho original do PDF.
    highlight: termo a ser grifado em amarelo na página renderizada.
    """

    zoom: float = 1.5
    highlight: str | None = None

    MIN_ZOOM = 0.25
    MAX_ZOOM = 6.0

    def with_zoom(self, zoom: float) -> "RenderOptions":
        limitado = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        return RenderOptions(zoom=limitado, highlight=self.highlight)

    def with_highlight(self, termo: str | None) -> "RenderOptions":
        return RenderOptions(zoom=self.zoom, highlight=termo or None)

    @property
    def cache_key(self) -> tuple:
        return (round(self.zoom, 4), self.highlight or "")


@dataclass(frozen=True)
class RenderedPage:
    """Uma página rasterizada em RGB de 8 bits por canal, sem canal alfa."""

    page: int
    width: int
    height: int
    stride: int
    samples: bytes

    @property
    def size_bytes(self) -> int:
        return len(self.samples)
