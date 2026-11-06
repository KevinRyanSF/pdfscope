"""Testes dos armazenamentos de marcadores que vêm no pacote."""

import json

import pytest

from pdfscope.core.bookmarks import Bookmark, BookmarkStore
from pdfscope.storage import InMemoryBookmarkStore, JsonBookmarkStore


@pytest.fixture(params=["memoria", "json"])
def store(request, tmp_path):
    if request.param == "memoria":
        return InMemoryBookmarkStore()
    return JsonBookmarkStore(tmp_path / "marcadores.json")


def test_implementa_o_protocolo(store):
    assert isinstance(store, BookmarkStore)


def test_adiciona_e_lista(store):
    criado = store.add("livro-1", 10, "Tabela de armas")
    assert isinstance(criado, Bookmark)

    marcadores = store.list("livro-1")
    assert len(marcadores) == 1
    assert marcadores[0].title == "Tabela de armas"
    assert marcadores[0].page == 10


def test_isola_por_documento(store):
    store.add("livro-1", 1, "A")
    store.add("livro-2", 2, "B")
    assert [b.title for b in store.list("livro-1")] == ["A"]
    assert [b.title for b in store.list("livro-2")] == ["B"]
    assert store.list("livro-3") == []


def test_ordena_por_pagina(store):
    store.add("livro", 30, "Terceiro")
    store.add("livro", 10, "Primeiro")
    store.add("livro", 20, "Segundo")
    assert [b.title for b in store.list("livro")] == ["Primeiro", "Segundo", "Terceiro"]


def test_remove(store):
    marcador = store.add("livro", 5, "Some daqui")
    store.add("livro", 6, "Fica")
    store.remove(marcador.id)
    assert [b.title for b in store.list("livro")] == ["Fica"]


def test_remover_id_inexistente_nao_explode(store):
    store.remove("id-que-nunca-existiu")


def test_json_persiste_entre_instancias(tmp_path):
    caminho = tmp_path / "marcadores.json"
    JsonBookmarkStore(caminho).add("livro", 7, "Regra de queda")

    recarregado = JsonBookmarkStore(caminho)
    marcadores = recarregado.list("livro")
    assert len(marcadores) == 1
    assert marcadores[0].title == "Regra de queda"


def test_json_sobrevive_a_arquivo_corrompido(tmp_path):
    caminho = tmp_path / "marcadores.json"
    caminho.write_text("{isso não é json", encoding="utf-8")

    store = JsonBookmarkStore(caminho)
    assert store.list("qualquer") == []
    store.add("livro", 1, "Recomeço")
    assert json.loads(caminho.read_text(encoding="utf-8"))["livro"][0]["title"] == "Recomeço"
