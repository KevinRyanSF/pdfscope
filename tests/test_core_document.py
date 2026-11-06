"""Testes do núcleo — rodam sem nenhuma interface gráfica."""

import pytest

from pdfscope import PdfDocument, RenderOptions
from pdfscope.core.document import _LruCache


def test_abre_e_le_metadados(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        assert doc.page_count == 3
        assert doc.title  # cai no nome do arquivo quando não há título embutido
        assert doc.doc_id == pdf_simples


def test_arquivo_inexistente():
    with pytest.raises(FileNotFoundError):
        PdfDocument("nao_existe_mesmo.pdf")


def test_toc_vira_zero_based_e_preserva_nivel(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        toc = doc.toc
        assert [e.title for e in toc] == ["Introducao", "Capitulo 1", "Combate"]
        assert [e.page for e in toc] == [0, 1, 1]  # o PDF guarda 1-based
        assert toc[2].level == 2


def test_busca_conta_ocorrencias(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        achados = doc.search("dragao")
        assert len(achados) == 1
        assert achados[0].page == 1
        assert achados[0].occurrences == 2  # a palavra aparece duas vezes


def test_busca_vazia_nao_retorna_nada(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        assert doc.search("") == []
        assert doc.search("   ") == []


def test_texto_e_extraido_sob_demanda(pdf_simples):
    """Abrir o documento não deve custar a extração de todas as páginas."""
    with PdfDocument(pdf_simples) as doc:
        assert doc._text_cache == {}
        doc.page_text(0)
        assert list(doc._text_cache) == [0]


def test_render_respeita_zoom(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        pequena = doc.render_page(0, RenderOptions(zoom=1.0))
        grande = doc.render_page(0, RenderOptions(zoom=2.0))
        assert grande.width > pequena.width
        assert grande.height > pequena.height
        assert len(pequena.samples) == pequena.stride * pequena.height


def test_render_usa_cache(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        primeira = doc.render_page(0)
        segunda = doc.render_page(0)
        assert primeira is segunda  # mesmo objeto: veio do cache


def test_grifo_nao_gruda_no_documento(pdf_simples):
    """O grifo é temporário: renderizar sem termo depois deve voltar ao normal."""
    with PdfDocument(pdf_simples) as doc:
        limpa_antes = doc.render_page(1, RenderOptions(zoom=1.0))
        doc.render_page(1, RenderOptions(zoom=1.0, highlight="dragao"))
        doc._page_cache.clear()
        limpa_depois = doc.render_page(1, RenderOptions(zoom=1.0))
        assert limpa_antes.samples == limpa_depois.samples


def test_pagina_invalida(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        with pytest.raises(IndexError):
            doc.render_page(99)
        with pytest.raises(IndexError):
            doc.page_text(-1)


def test_thumbnail_menor_que_pagina(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        thumb = doc.render_thumbnail(0)
        pagina = doc.render_page(0, RenderOptions(zoom=1.0))
        assert thumb.width < pagina.width


def test_png_para_uso_sem_qt(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        dados = doc.render_page_png(0)
        assert dados[:8] == b"\x89PNG\r\n\x1a\n"


def test_close_e_idempotente(pdf_simples):
    doc = PdfDocument(pdf_simples)
    doc.close()
    doc.close()
    assert doc.closed


def test_lru_descarta_o_mais_antigo():
    cache = _LruCache(maxsize=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")          # "a" passa a ser o mais recente
    cache.put("c", 3)       # deve expulsar "b"
    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3


def test_cache_de_paginas_tem_teto(pdf_simples):
    with PdfDocument(pdf_simples, page_cache_size=2) as doc:
        for zoom in (1.0, 1.5, 2.0, 2.5):
            doc.render_page(0, RenderOptions(zoom=zoom))
        assert len(doc._page_cache) == 2


def test_texto_original_preserva_maiusculas(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        assert "Dragao" in doc.page_text_raw(1)
        assert "dragao" in doc.page_text(1)  # a versão de busca continua minúscula


def test_linhas_trazem_tamanho_de_fonte(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        linhas = doc.page_lines(1)
        assert linhas, "a página tem texto"
        assert linhas[0].page == 1
        assert "Combate" in linhas[0].text
        assert linhas[0].size == 14.0


def test_png_com_grifo_nao_deixa_anotacao_na_pagina(pdf_simples):
    with PdfDocument(pdf_simples) as doc:
        com = doc.render_page_png(1, RenderOptions(zoom=1.0, highlight="Dragao"))
        sem = doc.render_page_png(1, RenderOptions(zoom=1.0))
        assert com != sem  # o grifo aparece
        assert doc.render_page_png(1, RenderOptions(zoom=1.0)) == sem  # e não fica para trás
