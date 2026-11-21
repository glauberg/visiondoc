"""Transcrição do inteiro teor com PaddleOCR-VL (T027, ADR-011).

A transcrição é dado não confiável: nunca é interpretada como instrução.
Caixas ficam em pixels da imagem normalizada da página.

Os adaptadores de modelos usam o extra `modelos` (paddleocr) e só são
importados quando instanciados. Sua integração com a versão real da biblioteca
ainda não foi verificada neste ambiente, que não tem os modelos instalados.
"""

import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from PIL import Image

from visiondoc.modelos import Caixa
from visiondoc.preprocessamento import PaginaNormalizada

_BLOCOS_SEM_TEXTO = {"image", "chart", "figure", "seal"}  # blocos sem texto transcrito


@dataclass(frozen=True)
class LinhaTranscrita:
    texto: str
    caixa: Caixa
    confianca: float | None


@dataclass(frozen=True)
class Transcricao:
    pagina: int
    linhas: list[LinhaTranscrita]
    modelo: str

    @property
    def inteiro_teor(self) -> str:
        return "\n".join(linha.texto for linha in self.linhas)

    @property
    def confianca_media(self) -> float:
        valores = [linha.confianca for linha in self.linhas if linha.confianca is not None]
        return float(np.mean(valores)) if valores else 0.0


class Transcritor(Protocol):
    nome_modelo: str

    def transcrever(self, imagem: Image.Image, pagina: int) -> Transcricao: ...


def transcrever_pagina(pagina: PaginaNormalizada, transcritor: Transcritor) -> Transcricao:
    with Image.open(pagina.imagem) as imagem:
        return transcritor.transcrever(imagem.convert("RGB"), pagina.numero)


class AvaliadorPorTranscricao:
    """Adapta um transcritor com escore por linha ao avaliador do pré-processamento."""

    def __init__(self, transcritor: Transcritor) -> None:
        self.transcritor = transcritor

    def confianca_media(self, imagem: Image.Image) -> float:
        return self.transcritor.transcrever(imagem, 0).confianca_media


def _caixa(valores) -> Caixa:
    x1, y1, x2, y2 = (float(v) for v in valores[:4])
    return (math.floor(x1), math.floor(y1), math.ceil(x2), math.ceil(y2))


def converter_resultado_paddleocr_vl(resultado: dict, pagina: int, modelo: str) -> Transcricao:
    """Converte o resultado de PaddleOCRVL.predict (lista `parsing_res_list`, em ordem de leitura)."""
    linhas = []
    for bloco in resultado.get("parsing_res_list", []):
        texto = (bloco.get("block_content") or "").strip()
        if not texto or bloco.get("block_label") in _BLOCOS_SEM_TEXTO:
            continue
        linhas.append(LinhaTranscrita(texto, _caixa(bloco["block_bbox"]), None))
    return Transcricao(pagina, linhas, modelo)


class TranscritorPaddleOCRVL:
    """Inteiro teor com PaddleOCR-VL. Não fornece escore por bloco."""

    def __init__(self, versao: str = "1.6", **opcoes) -> None:
        from paddleocr import PaddleOCRVL  # extra `modelos`

        self.nome_modelo = f"paddleocr-vl@{versao}"
        self._pipeline = PaddleOCRVL(**opcoes)

    def transcrever(self, imagem: Image.Image, pagina: int) -> Transcricao:
        resultados = list(self._pipeline.predict(np.asarray(imagem)[:, :, ::-1]))
        bruto = resultados[0].json if resultados else {}
        bruto = bruto.get("res", bruto)
        return converter_resultado_paddleocr_vl(bruto, pagina, self.nome_modelo)


class TranscritorPPOCR:
    """PaddleOCR tradicional (PP-OCR), com escore por linha.

    Usado como avaliador de espelhamento (Q-15) e linha de base de CER.
    """

    def __init__(self, **opcoes) -> None:
        from paddleocr import PaddleOCR  # extra `modelos`

        self.nome_modelo = "pp-ocr"
        self._ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            **opcoes,
        )

    def transcrever(self, imagem: Image.Image, pagina: int) -> Transcricao:
        resultados = list(self._ocr.predict(np.asarray(imagem)[:, :, ::-1]))
        if not resultados:
            return Transcricao(pagina, [], self.nome_modelo)
        r = resultados[0]
        linhas = [
            LinhaTranscrita(texto, _caixa(caixa), float(escore))
            for texto, caixa, escore in zip(r["rec_texts"], r["rec_boxes"], r["rec_scores"])
            if texto.strip()
        ]
        return Transcricao(pagina, linhas, self.nome_modelo)


class ClassificadorOrientacaoPaddle:
    """Classificador de orientação de documento do PaddleOCR (0, 90, 180, 270).

    A convenção do rótulo deve ser confirmada com o modelo real; aqui se assume
    que o rótulo é a rotação anti-horária presente na imagem, corrigida girando
    no sentido oposto.
    """

    def __init__(self, **opcoes) -> None:
        from paddleocr import DocImgOrientationClassification  # extra `modelos`

        self._modelo = DocImgOrientationClassification(**opcoes)

    def angulo(self, imagem: Image.Image) -> int:
        r = next(iter(self._modelo.predict(np.asarray(imagem)[:, :, ::-1])))
        rotulo = int(r["label_names"][0])
        return (360 - rotulo) % 360
