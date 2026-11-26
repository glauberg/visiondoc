import getpass
import json
import re
import socket

from visiondoc.avaliacao.metricas import (
    CLASSES_TIPO,
    INDEFINIDO,
    avaliar_extracao,
    calibracao,
    curva_cobertura,
    por_recorte,
)
from visiondoc.avaliacao.relatorio import (
    Avaliacao,
    Execucao,
    InfoDados,
    InfoInferencia,
    InfoModelo,
    InfoTreino,
    coletar_ambiente,
    gerar_relatorio,
)

REF = ["rg", "rg", "rg", "cnh", "cnh", "cpf", "outros", "outros"] * 3
PRED = ["rg", "rg", "cnh", "cnh", INDEFINIDO, "cpf", "rg", "outros"] * 3
CONF = [0.9, 0.95, 0.6, 0.8, 0.3, 0.99, 0.55, 0.9] * 3
DATASETS = (["bid"] * 4 + ["br-doc-extraction"] * 4) * 3


def _avaliacao() -> Avaliacao:
    acertos = [r == p for r, p in zip(REF, PRED)]
    return Avaliacao(
        classificacao={
            "tipo": por_recorte(REF, PRED, DATASETS, CLASSES_TIPO, n_bootstrap=50),
        },
        curva_cobertura=curva_cobertura(
            REF, [p if p != INDEFINIDO else "cnh" for p in PRED], CONF, [0.0, 0.25, 0.5, 0.75, 0.9]
        ),
        calibracao=calibracao(acertos, CONF),
        extracao={
            "bid": avaliar_extracao([{"nome": "FULANO"}], [{"nome": "FULANO"}]),
            "br-doc-extraction": avaliar_extracao([{"nome": "BELTRANO"}], [{"nome": "BELTRAN0"}]),
        },
        taxa_campos_sem_respaldo=0.04,
    )


def _gerar(tmp_path, linha_base=None):
    return gerar_relatorio(
        tmp_path / "relatorios",
        Execucao(
            "exec-1",
            "2026-11-25T10:00:00-03:00",
            "2026-11-25T12:00:00-03:00",
            "2.1.0+cfg.1",
            "1",
            42,
            "mlflow-1",
            "abc123",
            False,
            "lora",
        ),
        coletar_ambiente(),
        InfoModelo(
            "Qwen/Qwen3.5-4B",
            "rev1",
            4_000_000_000,
            20_000_000,
            "4 bits",
            "8 bits (fp8)",
            {"r": 16, "alpha": 32, "dropout": 0.05},
            196,
            80_000_000,
            8192,
            1280,
        ),
        InfoDados(
            {
                "bid": {
                    "treino": {"rg": 100, "cnh": 80},
                    "validacao": {"rg": 10, "cnh": 8},
                    "teste": {"rg": 12, "cnh": 9},
                }
            },
            ["desfoque"],
            7,
        ),
        InfoTreino(
            {"taxa_aprendizado": 2e-4, "epocas": 2},
            3600.0,
            5.5,
            7.1,
            [(10, 1.2, None), (20, 0.9, 1.0), (30, 0.7, 0.8)],
        ),
        InfoInferencia(150.0, [4.0, 5.0, 6.0, 31.0], {"vlm": [3.0, 4.0]}, 7.2, 180.0, 0.98),
        _avaliacao(),
        linha_base=linha_base,
    )


def test_gera_relatorio_markdown_graficos_e_json(tmp_path):
    diretorio = _gerar(tmp_path)
    assert diretorio.name.startswith("2026-11-25-exec-1")
    md = (diretorio / "relatorio.md").read_text(encoding="utf-8")
    for secao in [
        "## Identificação",
        "## Ambiente",
        "## Modelo",
        "## Dados",
        "## Treinamento",
        "## Inferência e desempenho",
        "## Classificação",
        "## Extração",
        "## Comparação",
    ]:
        assert secao in md
    imagens = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    assert imagens
    for imagem in imagens:
        assert (diretorio / imagem).is_file()
    assert any("matriz" in i for i in imagens)
    metricas = json.loads((diretorio / "metricas.json").read_text(encoding="utf-8"))
    tipo = metricas["classificacao"]["tipo"]["agregado"]
    assert 0 < tipo["acuracia"] <= 1 and "f1_macro" in tipo
    assert metricas["inferencia"]["tempo_medio_pagina_s"] == 11.5
    assert metricas["modelo"]["percentual_treinavel"] == 0.5


def test_relatorio_nao_expoe_maquina_usuario_ou_caminhos(tmp_path):
    diretorio = _gerar(tmp_path)
    for nome in ("relatorio.md", "metricas.json"):
        texto = (diretorio / nome).read_text(encoding="utf-8")
        assert socket.gethostname() not in texto
        assert getpass.getuser() not in texto
        assert str(tmp_path) not in texto


def test_metas_de_desempenho_sao_indicadores(tmp_path):
    md = (_gerar(tmp_path) / "relatorio.md").read_text(encoding="utf-8")
    assert "30 s" in md and "7,5 GB" in md
    assert "indicador" in md.lower()


def test_compara_com_linha_de_base(tmp_path):
    anterior = json.loads((_gerar(tmp_path / "a") / "metricas.json").read_text(encoding="utf-8"))
    anterior["classificacao"]["tipo"]["agregado"]["acuracia"] = 0.5
    md = (_gerar(tmp_path / "b", linha_base=anterior) / "relatorio.md").read_text(encoding="utf-8")
    assert "Linha de base" in md
    assert "+0,214" in md  # 0,714 - 0,500
