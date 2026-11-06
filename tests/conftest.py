import pytest
from pdfscope.core.pymupdf_compat import pymupdf


@pytest.fixture
def pdf_simples(tmp_path):
    """Um PDF de 3 páginas com índice, para os testes."""
    caminho = tmp_path / "livro.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text((50, 50), "Introducao ao Sistema. Bem vindos jogadores!", fontsize=14)

    p2 = doc.new_page()
    p2.insert_text((50, 50), "Capitulo 1: Combate e Magia. O Dragao ataca o Dragao.", fontsize=14)

    p3 = doc.new_page()
    p3.insert_text((50, 50), "Apendice: tabelas de iniciativa.", fontsize=14)

    doc.set_toc([[1, "Introducao", 1], [1, "Capitulo 1", 2], [2, "Combate", 2]])
    doc.save(caminho)
    doc.close()
    return str(caminho)
