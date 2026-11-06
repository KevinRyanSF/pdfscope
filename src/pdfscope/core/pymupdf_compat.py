"""Importa o PyMuPDF pelo nome certo, seja qual for a versão instalada.

Até a versão 1.24.3 a biblioteca só se chamava `fitz`; a partir dela o nome
oficial passou a ser `pymupdf`, com `fitz` mantido como alias legado. Importar
por aqui evita que o projeto quebre nas duas pontas dessa mudança.
"""

from __future__ import annotations

try:  # PyMuPDF >= 1.24.3
    import pymupdf
except ImportError:  # versões antigas, em que só existe o nome fitz
    try:
        import fitz as pymupdf
    except ImportError as erro:  # pragma: no cover - depende do ambiente
        raise ImportError(
            "PyMuPDF não está instalado. Instale com: pip install PyMuPDF"
        ) from erro

__all__ = ["pymupdf"]
