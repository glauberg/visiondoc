"""Pré-processamento: orientação, espelhamento, inclinação e contraste (T026).

Referências: RF-SDD-04, ING-SEC-08 e Q-15. Toda transformação geométrica fica
registrada para converter o bbox de volta à página rasterizada original.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from visiondoc.modelos import Caixa, Pagina

# EXIF: rotação anti-horária necessária para exibir a imagem corretamente.
_EXIF_PARA_ROTACAO = {3: 180, 6: 270, 8: 90}
_INCLINACAO_MIN, _INCLINACAO_MAX = 0.3, 15.0


class ClassificadorOrientacao(Protocol):
    def angulo(self, imagem: Image.Image) -> int:
        """Rotação anti-horária (0, 90, 180 ou 270) que deixa a página na posição de leitura."""


class AvaliadorOCR(Protocol):
    def confianca_media(self, imagem: Image.Image) -> float: ...


@dataclass(frozen=True)
class Transformacao:
    """Afim da página original (pixels) para a imagem normalizada."""

    matriz: tuple[float, ...]  # 9 valores, linha a linha
    tamanho_original: tuple[int, int]
    tamanho_normalizado: tuple[int, int]

    @classmethod
    def identidade(cls, largura: int, altura: int) -> "Transformacao":
        return cls(tuple(np.eye(3).ravel()), (largura, altura), (largura, altura))

    def _compor(self, passo: np.ndarray, tamanho: tuple[int, int]) -> "Transformacao":
        m = passo @ np.array(self.matriz).reshape(3, 3)
        return Transformacao(tuple(m.ravel()), self.tamanho_original, tamanho)

    def girar_90(self, k: int) -> "Transformacao":
        largura, altura = self.tamanho_normalizado
        t = self
        for _ in range(k % 4):
            passo = np.array([[0, 1, 0], [-1, 0, largura], [0, 0, 1]], dtype=float)
            t = t._compor(passo, (altura, largura))
            largura, altura = altura, largura
        return t

    def espelhar(self) -> "Transformacao":
        largura, _ = self.tamanho_normalizado
        passo = np.array([[-1, 0, largura], [0, 1, 0], [0, 0, 1]], dtype=float)
        return self._compor(passo, self.tamanho_normalizado)

    def girar(self, graus: float) -> "Transformacao":
        """Rotação anti-horária arbitrária com expansão da tela."""
        largura, altura = self.tamanho_normalizado
        passo, tamanho = _matriz_rotacao(largura, altura, graus)
        return self._compor(np.vstack([passo, [0, 0, 1]]), tamanho)

    def _aplicar(self, m: np.ndarray, caixa: Caixa, limite: tuple[int, int]) -> Caixa:
        x1, y1, x2, y2 = caixa
        cantos = np.array([[x1, y1, 1], [x2, y1, 1], [x1, y2, 1], [x2, y2, 1]], dtype=float)
        pontos = cantos @ m.T
        xs, ys = pontos[:, 0], pontos[:, 1]
        return (
            max(0, math.floor(xs.min() + 1e-6)),
            max(0, math.floor(ys.min() + 1e-6)),
            min(limite[0], math.ceil(xs.max() - 1e-6)),
            min(limite[1], math.ceil(ys.max() - 1e-6)),
        )

    def para_normalizada(self, caixa: Caixa) -> Caixa:
        return self._aplicar(np.array(self.matriz).reshape(3, 3), caixa, self.tamanho_normalizado)

    def para_original(self, caixa: Caixa) -> Caixa:
        inversa = np.linalg.inv(np.array(self.matriz).reshape(3, 3))
        return self._aplicar(inversa, caixa, self.tamanho_original)


def _matriz_rotacao(largura: int, altura: int, graus: float):
    m = cv2.getRotationMatrix2D((largura / 2, altura / 2), graus, 1.0)
    cos, sen = abs(m[0, 0]), abs(m[0, 1])
    nova_l = math.ceil(altura * sen + largura * cos)
    nova_a = math.ceil(altura * cos + largura * sen)
    m[0, 2] += nova_l / 2 - largura / 2
    m[1, 2] += nova_a / 2 - altura / 2
    return m, (nova_l, nova_a)


def _girar_imagem(imagem: np.ndarray, graus: float) -> np.ndarray:
    altura, largura = imagem.shape[:2]
    m, tamanho = _matriz_rotacao(largura, altura, graus)
    return cv2.warpAffine(imagem, m, tamanho, flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def _area_tinta(imagem: np.ndarray) -> float:
    cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
    _, binaria = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    pontos = cv2.findNonZero(binaria)
    if pontos is None:
        return 0.0
    _, _, largura, altura = cv2.boundingRect(pontos)
    return float(largura * altura)


def estimar_inclinacao(imagem: np.ndarray) -> float:
    """Correção anti-horária, em graus, que alinha o conteúdo aos eixos (0 se não houver)."""
    cinza = cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY)
    _, binaria = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    pontos = cv2.findNonZero(binaria)
    if pontos is None or len(pontos) < 50:
        return 0.0
    angulo = cv2.minAreaRect(pontos)[2] % 90
    magnitude = min(angulo, 90 - angulo)
    if not _INCLINACAO_MIN <= magnitude <= _INCLINACAO_MAX:
        return 0.0
    reduzida = cv2.resize(imagem, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    candidatos = [magnitude, -magnitude]
    return min(candidatos, key=lambda g: _area_tinta(_girar_imagem(reduzida, g)))


def _realcar_contraste(imagem: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(imagem, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


@dataclass(frozen=True)
class PaginaNormalizada:
    numero: int
    imagem: Path
    largura: int
    altura: int
    transformacao: Transformacao
    rotacao: int
    espelhada: bool
    inclinacao_graus: float


def normalizar(
    pagina: Pagina,
    classificador: ClassificadorOrientacao | None,
    avaliador: AvaliadorOCR,
    diretorio: Path,
    orientacao_exif: int | None = None,
) -> PaginaNormalizada:
    imagem = Image.open(pagina.imagem).convert("RGB")
    transformacao = Transformacao.identidade(*imagem.size)

    if classificador is not None:
        rotacao = int(classificador.angulo(imagem)) % 360
    else:  # EXIF só como sinal auxiliar, na falta do classificador
        rotacao = _EXIF_PARA_ROTACAO.get(orientacao_exif or 1, 0)
    if rotacao not in (0, 90, 180, 270):
        raise ValueError(f"rotação inválida: {rotacao}")
    if rotacao:
        imagem = imagem.rotate(rotacao, expand=True)
        transformacao = transformacao.girar_90(rotacao // 90)

    espelho = imagem.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    espelhada = bool(avaliador.confianca_media(espelho) > avaliador.confianca_media(imagem))
    if espelhada:
        imagem = espelho
        transformacao = transformacao.espelhar()

    matriz = np.asarray(imagem)
    inclinacao = estimar_inclinacao(matriz)
    if inclinacao:
        matriz = _girar_imagem(matriz, inclinacao)
        transformacao = transformacao.girar(inclinacao)

    matriz = _realcar_contraste(matriz)
    destino = Path(diretorio) / f"{Path(pagina.imagem).stem}-normalizada.png"
    Image.fromarray(matriz).save(destino, "PNG")
    altura, largura = matriz.shape[:2]
    assert transformacao.tamanho_normalizado == (largura, altura)
    return PaginaNormalizada(
        pagina.numero,
        destino,
        largura,
        altura,
        transformacao,
        rotacao,
        espelhada,
        float(inclinacao),
    )
