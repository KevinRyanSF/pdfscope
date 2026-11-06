"""pdfscope — leitor de PDF com abas, miniaturas, busca e marcadores.

O núcleo (`pdfscope.core`) não depende de nenhuma interface gráfica; a camada
`pdfscope.qt` só é importada quando você a pede, para que o pacote possa ser
usado em scripts e servidores sem PyQt instalado.

    from pdfscope import PdfDocument
    doc = PdfDocument("manual.pdf")
    print(doc.page_count, doc.toc[:3])

    from pdfscope.qt import PdfReaderWidget  # precisa de PyQt6
"""

from .core import (
    Bookmark,
    BookmarkStore,
    PdfDocument,
    RenderedPage,
    RenderOptions,
    SearchHit,
    TextLine,
    TocEntry,
)
from .storage import InMemoryBookmarkStore, JsonBookmarkStore

__version__ = "0.4.0"

__all__ = [
    "Bookmark",
    "BookmarkStore",
    "InMemoryBookmarkStore",
    "JsonBookmarkStore",
    "PdfDocument",
    "RenderOptions",
    "RenderedPage",
    "SearchHit",
    "TextLine",
    "TocEntry",
    "__version__",
]
