"""Testes da camada Qt do leitor."""

from pdfscope.qt import PdfReaderWidget
from pdfscope.storage import InMemoryBookmarkStore


def test_abre_documento_e_atualiza_controles(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)

    aba = leitor.open_document(pdf_simples, doc_id="livro-1", title="Manual")
    assert aba.document.page_count == 3
    assert leitor.label_total.text() == "/ 3"
    assert leitor.spin_pagina.value() == 1
    assert leitor.tabs.count() == 1


def test_nao_abre_o_mesmo_documento_duas_vezes(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)

    primeira = leitor.open_document(pdf_simples, doc_id="livro-1")
    segunda = leitor.open_document(pdf_simples, doc_id="livro-1")
    assert primeira is segunda
    assert leitor.tabs.count() == 1


def test_comeca_na_pagina_pedida(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)

    aba = leitor.open_document(pdf_simples, doc_id="livro-1", start_page=2)
    assert aba.current_page == 2
    assert leitor.spin_pagina.value() == 3


def test_navegacao_sincroniza_barra_superior(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)
    aba = leitor.open_document(pdf_simples, doc_id="livro-1")

    aba.step(1)
    assert aba.current_page == 1
    assert leitor.spin_pagina.value() == 2

    aba.step(-5)  # não passa do começo
    assert aba.current_page == 1


def test_zoom_tem_limites(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)
    aba = leitor.open_document(pdf_simples, doc_id="livro-1")

    assert aba.zoom == 1.5
    aba.zoom_by(0.25)
    assert aba.zoom == 1.75
    for _ in range(50):
        aba.zoom_by(0.25)
    assert aba.zoom <= 6.0


def test_sinal_de_pagina_carrega_doc_id(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)
    aba = leitor.open_document(pdf_simples, doc_id="livro-42")

    with qtbot.waitSignal(leitor.page_changed, timeout=1000) as sinal:
        aba.step(1)
    assert sinal.args == ["livro-42", 1]


def test_busca_popula_o_painel_lateral(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)
    leitor.open_document(pdf_simples, doc_id="livro-1")

    leitor.input_busca.setText("dragao")
    leitor.buscar()

    # marcadores + índice + resultados
    assert leitor.outline.topLevelItemCount() == 3
    resultados = leitor.outline.topLevelItem(2)
    assert "dragao" in resultados.text(0)
    assert resultados.childCount() == 1
    assert "Página 2" in resultados.child(0).text(0)


def test_marcador_usa_o_store_injetado(qtbot, pdf_simples):
    store = InMemoryBookmarkStore()
    leitor = PdfReaderWidget(bookmark_store=store)
    qtbot.addWidget(leitor)
    aba = leitor.open_document(pdf_simples, doc_id="livro-1")
    aba.goto(2)

    leitor.perguntar_titulo_do_marcador = lambda sugestao: "Tabela de armas"
    leitor.salvar_marcador()

    marcadores = store.list("livro-1")
    assert len(marcadores) == 1
    assert marcadores[0].page == 2

    leitor.remover_marcador(marcadores[0].id)
    assert store.list("livro-1") == []


def test_fechar_aba_libera_o_documento(qtbot, pdf_simples):
    leitor = PdfReaderWidget()
    qtbot.addWidget(leitor)
    aba = leitor.open_document(pdf_simples, doc_id="livro-1")
    documento = aba.document

    with qtbot.waitSignal(leitor.document_closed, timeout=1000):
        leitor.close_document("livro-1")

    assert leitor.tabs.count() == 0
    assert documento.closed
    assert leitor.label_total.text() == "/ 0"
