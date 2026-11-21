import pytest
from PIL import Image

from sintetico import imagem_cartao
from visiondoc.preprocessamento import PaginaNormalizada, Transformacao
from visiondoc.transcricao import (
    AvaliadorPorTranscricao,
    LinhaTranscrita,
    Transcricao,
    converter_resultado_paddleocr_vl,
    transcrever_pagina,
)


class TranscritorFalso:
    nome_modelo = "falso@0"

    def __init__(self, linhas):
        self.linhas = linhas
        self.chamadas = 0

    def transcrever(self, imagem, pagina):
        self.chamadas += 1
        return Transcricao(pagina, self.linhas, self.nome_modelo)


def _normalizada(tmp_path):
    caminho = tmp_path / "n.png"
    imagem_cartao().save(caminho)
    return PaginaNormalizada(
        2, caminho, 1200, 800, Transformacao.identidade(1200, 800), 0, False, 0.0
    )


def test_inteiro_teor_em_ordem_de_leitura_e_confianca_media():
    t = Transcricao(
        1,
        [
            LinhaTranscrita("NOME", (0, 0, 10, 10), 0.8),
            LinhaTranscrita("FULANO", (0, 20, 10, 30), 0.6),
            LinhaTranscrita("SEM SCORE", (0, 40, 10, 50), None),
        ],
        "x",
    )
    assert t.inteiro_teor == "NOME\nFULANO\nSEM SCORE"
    assert t.confianca_media == pytest.approx(0.7)


def test_transcreve_pagina_normalizada(tmp_path):
    falso = TranscritorFalso([LinhaTranscrita("NOME FULANO DE TAL", (80, 260, 600, 300), 0.9)])
    t = transcrever_pagina(_normalizada(tmp_path), falso)
    assert t.pagina == 2 and t.modelo == "falso@0"
    assert "FULANO" in t.inteiro_teor


def test_avaliador_usa_a_confianca_da_transcricao():
    falso = TranscritorFalso([LinhaTranscrita("A", (0, 0, 1, 1), 0.4)])
    assert AvaliadorPorTranscricao(falso).confianca_media(Image.new("RGB", (5, 5))) == 0.4


def test_converte_resultado_do_paddleocr_vl():
    resultado = {
        "parsing_res_list": [
            {
                "block_label": "text",
                "block_content": "REGISTRO GERAL 0000000",
                "block_bbox": [10.4, 20.6, 300.2, 50.9],
            },
            {"block_label": "image", "block_content": "", "block_bbox": [0, 0, 5, 5]},
            {
                "block_label": "text",
                "block_content": "NOME FULANO DE TAL\nFILIACAO X",
                "block_bbox": [10, 60, 300, 120],
            },
        ]
    }
    t = converter_resultado_paddleocr_vl(resultado, 1, "paddleocr-vl@1.6")
    assert [linha.texto for linha in t.linhas] == [
        "REGISTRO GERAL 0000000",
        "NOME FULANO DE TAL\nFILIACAO X",
    ]
    assert t.linhas[0].caixa == (10, 20, 301, 51)
    assert t.linhas[0].confianca is None


def test_integracao_paddleocr_vl(tmp_path):
    pytest.importorskip("paddleocr", reason="extra 'modelos' não instalado")
    from visiondoc.transcricao import TranscritorPaddleOCRVL

    t = transcrever_pagina(_normalizada(tmp_path), TranscritorPaddleOCRVL())
    assert "FULANO" in t.inteiro_teor
