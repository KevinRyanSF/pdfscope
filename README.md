# pdfscope

Leitor de PDF embutível: abas, miniaturas com carregamento preguiçoso, busca
com contagem de ocorrências, índice hierárquico e marcadores.

Funciona sozinho como aplicativo e também como um widget dentro de outro
programa PyQt6.

## Instalação

```bash
pip install -e ".[qt]"
```

## Uso como aplicativo

```bash
pdfscope manual.pdf
pdfscope --bookmarks ./meus_marcadores.json livro1.pdf livro2.pdf
```

Sem argumentos ele abre vazio; `Ctrl+O` escolhe os arquivos. Os marcadores vão,
por padrão, para `~/.pdfscope/bookmarks.json`.

## Uso como biblioteca (sem interface)

O núcleo não importa nada de Qt, então serve para scripts, CLIs e servidores:

```python
from pdfscope import PdfDocument, RenderOptions

with PdfDocument("manual.pdf") as doc:
    print(doc.page_count, doc.title)

    for entrada in doc.toc:
        print("  " * entrada.level, entrada.title, "->", entrada.page)

    for hit in doc.search("iniciativa"):
        print(f"página {hit.page + 1}: {hit.occurrences} ocorrência(s)")

    # texto para busca (minúsculo) x texto original (para extrair conteúdo)
    doc.page_text(10)        # "bola de fogo ..."
    doc.page_text_raw(10)    # "Bola de Fogo ..."

    # linhas com tipografia — útil para achar títulos (nome de magia, seção)
    for linha in doc.page_lines(10):
        if linha.bold and linha.size >= 12:
            print("título?", linha.text)

    png = doc.render_page_png(0, RenderOptions(zoom=2.0))
    open("capa.png", "wb").write(png)
```

## Uso como widget PyQt6

```python
from pdfscope.qt import PdfReaderWidget

leitor = PdfReaderWidget()          # marcadores em memória
leitor.open_document("manual.pdf")
leitor.page_changed.connect(lambda doc_id, pagina: print(doc_id, pagina))
```

## Guardando marcadores onde você quiser

`PdfReaderWidget` aceita qualquer objeto que siga o protocolo `BookmarkStore`.
Vêm prontos o `JsonBookmarkStore` (arquivo) e o `InMemoryBookmarkStore`
(descartável). Para gravar em outro lugar — um banco, uma API — basta
implementar três métodos:

```python
class MeuStore:
    def list(self, doc_id: str) -> list[Bookmark]: ...
    def add(self, doc_id: str, page: int, title: str) -> Bookmark: ...
    def remove(self, bookmark_id: str) -> None: ...

leitor = PdfReaderWidget(bookmark_store=MeuStore())
```

`doc_id` é uma string opaca escolhida por você: o caminho do arquivo, o id de um
registro no seu banco, o que fizer sentido no seu aplicativo.

## Estrutura

```
pdfscope/
├─ core/      # sem Qt: documento, renderização, busca, contrato de marcadores
├─ storage/   # implementações prontas de BookmarkStore
├─ qt/        # widgets PyQt6
└─ app.py     # aplicativo autônomo
```

## Licença

MIT.
