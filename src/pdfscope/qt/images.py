"""Ponte entre o núcleo (bytes) e o Qt (QPixmap).

Este é o único lugar do pacote onde o formato de imagem do núcleo encontra o Qt.
"""

from __future__ import annotations

from PyQt6.QtGui import QImage, QPixmap

from ..core.render import RenderedPage


def to_qimage(rendered: RenderedPage) -> QImage:
    imagem = QImage(
        rendered.samples,
        rendered.width,
        rendered.height,
        rendered.stride,
        QImage.Format.Format_RGB888,
    )
    # copy() desliga a imagem do buffer original — sem isso o Qt pode acabar
    # lendo memória já liberada pelo Python.
    return imagem.copy()


def to_qpixmap(rendered: RenderedPage) -> QPixmap:
    return QPixmap.fromImage(to_qimage(rendered))
