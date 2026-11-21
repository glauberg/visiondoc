import numpy as np
from PIL import Image, ImageChops, ImageDraw

from visiondoc.modelos import Pagina
from visiondoc.preprocessamento import Transformacao, normalizar

CAIXA = (100, 150, 400, 300)


def _cartao() -> Image.Image:
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((40, 40, 1160, 760), outline="black", width=6)
    d.rectangle(CAIXA, fill="black")
    d.rectangle((600, 500, 1100, 560), fill="black")
    return img


def _pagina(tmp_path, img: Image.Image) -> Pagina:
    caminho = tmp_path / "p.png"
    img.save(caminho)
    return Pagina(1, caminho, img.width, img.height, [])


class Fixo:
    def __init__(self, angulo):
        self.angulo_fixo = angulo

    def angulo(self, imagem):
        return self.angulo_fixo


class SemelhancaComCartao:
    """Avaliador fictício: maior confiança quanto mais a imagem se parece com o cartão."""

    def confianca_media(self, imagem):
        ref = _cartao().resize(imagem.size).convert("L")
        dif = ImageChops.difference(ref, imagem.convert("L"))
        return 1 - np.asarray(dif).mean() / 255


def _escura(img: Image.Image, caixa) -> float:
    return np.asarray(img.convert("L").crop(caixa)).mean()


def test_transformacao_ida_e_volta():
    t = Transformacao.identidade(1200, 800).girar_90(1)  # 90 graus anti-horário
    assert t.tamanho_normalizado == (800, 1200)
    assert t.para_original(t.para_normalizada(CAIXA)) == CAIXA


def test_corrige_rotacao_e_mapeia_bbox_para_a_pagina_original(tmp_path):
    original = _cartao().rotate(-90, expand=True)  # página girada 90 graus horário
    r = normalizar(_pagina(tmp_path, original), Fixo(90), SemelhancaComCartao(), tmp_path)
    assert r.rotacao == 90
    assert Image.open(r.imagem).size == (1200, 800)
    caixa_original = r.transformacao.para_original(CAIXA)
    assert _escura(original, caixa_original) < 30


def test_detecta_espelhamento_pela_confianca_do_ocr(tmp_path):
    espelhada = _cartao().transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    r = normalizar(_pagina(tmp_path, espelhada), Fixo(0), SemelhancaComCartao(), tmp_path)
    assert r.espelhada is True
    assert _escura(espelhada, r.transformacao.para_original(CAIXA)) < 30


def test_corrige_inclinacao(tmp_path):
    inclinada = _cartao().rotate(5, expand=True, fillcolor="white")
    r = normalizar(_pagina(tmp_path, inclinada), Fixo(0), SemelhancaComCartao(), tmp_path)
    assert abs(abs(r.inclinacao_graus) - 5) < 1


def test_usa_exif_quando_nao_ha_classificador(tmp_path):
    original = _cartao().rotate(-90, expand=True)
    r = normalizar(
        _pagina(tmp_path, original), None, SemelhancaComCartao(), tmp_path, orientacao_exif=8
    )  # EXIF 8: girar 90 graus anti-horário
    assert r.rotacao == 90
