"""O documento PDF — leitura, índice, busca e rasterização.

Sem Qt, sem banco, sem rede. Só PyMuPDF.
"""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass

from .pymupdf_compat import pymupdf
from .render import RenderedPage, RenderOptions


@dataclass(frozen=True)
class TocEntry:
    """Uma linha do índice original do PDF. `page` é zero-based."""

    level: int
    title: str
    page: int


@dataclass(frozen=True)
class TextLine:
    """Uma linha de texto com a tipografia dominante — serve para achar títulos.

    `size` é o maior corpo de fonte da linha; `bold` é verdadeiro quando todos os
    trechos da linha estão em negrito. `bbox` é (x0, y0, x1, y1) em pontos.
    """

    page: int
    text: str
    size: float
    bold: bool
    font: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class SearchHit:
    """Uma página que contém o termo buscado."""

    page: int
    occurrences: int


class _LruCache:
    """Cache LRU simples e limitado.

    O leitor antigo guardava toda página renderizada para sempre; num livro de
    400 páginas com zoom alto isso engole memória sem teto. Aqui o cache tem
    tamanho máximo e descarta o item usado há mais tempo.
    """

    def __init__(self, maxsize: int):
        self._maxsize = max(1, maxsize)
        self._data: OrderedDict = OrderedDict()

    def get(self, key):
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


class PdfDocument:
    """Um PDF aberto, com caches de página, miniatura e texto.

    Diferente da versão anterior, o texto **não** é extraído inteiro na abertura:
    um livro grande abria com vários segundos de espera. A extração é feita por
    página, sob demanda, e memorizada.
    """

    def __init__(
        self,
        path: str | os.PathLike,
        *,
        doc_id: str | None = None,
        page_cache_size: int = 12,
        thumb_cache_size: int = 96,
    ):
        self.path = os.fspath(path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(self.path)

        self.doc_id = doc_id or self.path
        self._doc = pymupdf.open(self.path)
        self._page_cache = _LruCache(page_cache_size)
        self._thumb_cache = _LruCache(thumb_cache_size)
        self._text_cache: dict[int, str] = {}
        self._raw_cache: dict[int, str] = {}
        self._toc: list[TocEntry] | None = None
        self._closed = False

    # ------------------------------------------------------------------ infos

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def title(self) -> str:
        meta = (self._doc.metadata or {}).get("title") or ""
        return meta.strip() or os.path.splitext(os.path.basename(self.path))[0]

    @property
    def toc(self) -> list[TocEntry]:
        """Índice original do PDF, com páginas convertidas para zero-based."""
        if self._toc is None:
            bruto = self._doc.get_toc() or []
            self._toc = [
                TocEntry(level=int(lvl), title=str(titulo), page=max(0, int(pagina) - 1))
                for lvl, titulo, pagina in bruto
            ]
        return self._toc

    def _validar_pagina(self, page: int) -> int:
        if not 0 <= page < self.page_count:
            raise IndexError(f"página {page} fora do intervalo 0..{self.page_count - 1}")
        return page

    # ------------------------------------------------------------------ texto

    def page_text(self, page: int) -> str:
        """Texto da página em minúsculas, extraído sob demanda e memorizado."""
        self._validar_pagina(page)
        if page not in self._text_cache:
            self._text_cache[page] = self._doc.load_page(page).get_text("text").lower()
        return self._text_cache[page]

    def page_text_raw(self, page: int) -> str:
        """Texto da página como está no PDF (maiúsculas preservadas), em ordem de leitura.

        `page_text` é minúsculo porque existe para a busca; para extrair conteúdo
        (nomes de magias, títulos) use este.
        """
        self._validar_pagina(page)
        if page not in self._raw_cache:
            self._raw_cache[page] = self._doc.load_page(page).get_text("text", sort=True)
        return self._raw_cache[page]

    def page_lines(self, page: int) -> list[TextLine]:
        """Linhas da página com tamanho de fonte e negrito, em ordem de leitura."""
        self._validar_pagina(page)
        bruto = self._doc.load_page(page).get_text("dict", sort=True)
        linhas: list[TextLine] = []
        for bloco in bruto.get("blocks", []):
            for linha in bloco.get("lines", []):
                spans = [sp for sp in linha.get("spans", []) if sp.get("text", "").strip()]
                if not spans:
                    continue
                texto = "".join(sp["text"] for sp in linha["spans"]).strip()
                maior = max(spans, key=lambda sp: sp.get("size", 0))
                negrito = all(
                    (sp.get("flags", 0) & 16) or "bold" in sp.get("font", "").lower() for sp in spans
                )
                linhas.append(
                    TextLine(
                        page=page,
                        text=texto,
                        size=round(float(maior.get("size", 0)), 1),
                        bold=bool(negrito),
                        font=str(maior.get("font", "")),
                        bbox=tuple(float(v) for v in linha.get("bbox", (0, 0, 0, 0))),
                    )
                )
        return linhas

    def search(self, query: str) -> list[SearchHit]:
        """Páginas que contêm o termo, com a contagem de ocorrências."""
        termo = (query or "").strip().lower()
        if not termo:
            return []

        achados: list[SearchHit] = []
        for page in range(self.page_count):
            texto = self.page_text(page)
            n = texto.count(termo)
            if n:
                achados.append(SearchHit(page=page, occurrences=n))
        return achados

    # ------------------------------------------------------------- renderização

    def _rasterizar(self, page: int, zoom: float, highlight: str | None) -> RenderedPage:
        pagina = self._doc.load_page(page)

        # Os grifos entram como anotações temporárias e saem logo depois. A versão
        # anterior adicionava a anotação e nunca removia, então os grifos de buscas
        # antigas iam se acumulando na página.
        anotacoes = []
        if highlight:
            for rect in pagina.search_for(highlight):
                annot = pagina.add_highlight_annot(rect)
                annot.set_colors(stroke=(1, 1, 0))
                annot.update()
                anotacoes.append(annot)

        try:
            pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        finally:
            for annot in anotacoes:
                pagina.delete_annot(annot)

        return RenderedPage(
            page=page,
            width=pix.width,
            height=pix.height,
            stride=pix.stride,
            samples=bytes(pix.samples),
        )

    def render_page(self, page: int, options: RenderOptions | None = None) -> RenderedPage:
        """Rasteriza a página (RGB888), usando cache."""
        self._validar_pagina(page)
        opts = options or RenderOptions()
        chave = (page, *opts.cache_key)

        em_cache = self._page_cache.get(chave)
        if em_cache is not None:
            return em_cache

        rendered = self._rasterizar(page, opts.zoom, opts.highlight)
        self._page_cache.put(chave, rendered)
        return rendered

    def render_page_png(self, page: int, options: RenderOptions | None = None) -> bytes:
        """A mesma página em PNG.

        Não é usado pela interface Qt — existe para que um servidor (o backend
        Django, mais adiante) possa servir páginas sem tocar em nada de UI.
        """
        self._validar_pagina(page)
        opts = options or RenderOptions()
        pagina = self._doc.load_page(page)
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(opts.zoom, opts.zoom), alpha=False)
        return pix.tobytes("png")

    def render_thumbnail(self, page: int, scale: float = 0.2) -> RenderedPage:
        """Miniatura leve para a barra lateral."""
        self._validar_pagina(page)
        chave = (page, round(scale, 3))

        em_cache = self._thumb_cache.get(chave)
        if em_cache is not None:
            return em_cache

        rendered = self._rasterizar(page, scale, None)
        self._thumb_cache.put(chave, rendered)
        return rendered

    # ---------------------------------------------------------------- ciclo de vida

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        self._page_cache.clear()
        self._thumb_cache.clear()
        self._text_cache.clear()
        self._raw_cache.clear()
        self._doc.close()
        self._closed = True

    def __enter__(self) -> "PdfDocument":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<PdfDocument {os.path.basename(self.path)!r} páginas={self.page_count}>"
