"""Aplicativo autônomo: `pdfscope livro.pdf`.

É o que torna o pdfscope útil para quem nunca ouviu falar de RPG.
"""

from __future__ import annotations

import argparse
import sys

from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from .qt.reader_widget import PdfReaderWidget
from .storage.json_store import JsonBookmarkStore, caminho_padrao


class PdfScopeWindow(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.setWindowTitle("pdfscope")
        self.resize(1200, 800)

        self.reader = PdfReaderWidget(bookmark_store=store or JsonBookmarkStore())
        self.setCentralWidget(self.reader)

        arquivo = self.menuBar().addMenu("&Arquivo")
        acao_abrir = arquivo.addAction("&Abrir PDF…")
        acao_abrir.setShortcut("Ctrl+O")
        acao_abrir.triggered.connect(self.escolher_arquivos)
        arquivo.addSeparator()
        arquivo.addAction("Sai&r", self.close)

    def escolher_arquivos(self) -> None:
        caminhos, _ = QFileDialog.getOpenFileNames(
            self, "Abrir PDF", "", "Arquivos PDF (*.pdf)"
        )
        for caminho in caminhos:
            self.reader.open_document(caminho)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdfscope",
        description="Leitor de PDF com abas, miniaturas, busca e marcadores.",
    )
    parser.add_argument("arquivos", nargs="*", help="PDFs para abrir")
    parser.add_argument(
        "--bookmarks",
        default=None,
        help=f"arquivo JSON de marcadores (padrão: {caminho_padrao()})",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    app = QApplication(sys.argv[:1])
    janela = PdfScopeWindow(store=JsonBookmarkStore(args.bookmarks))
    for caminho in args.arquivos:
        janela.reader.open_document(caminho)
    janela.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
