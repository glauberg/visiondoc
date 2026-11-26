"""Orquestração da T038: linha de base zero-shot, treino e relatórios.

Sequência: (1) avalia o modelo base na partição de teste e gera o relatório
zero-shot; (2) treina o adaptador com train/valid; (3) avalia com o adaptador
e gera o relatório com a comparação (RF-SDD-17, RF-SDD-18).

A avaliação usa transformers com o modelo em 4 bits e geração sem decodificação
guiada; a inferência em 8 bits pelo vLLM depende da T031.
"""

import json
import time
import uuid
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from visiondoc.avaliacao.relatorio import (
    Execucao,
    InfoDados,
    InfoModelo,
    coletar_ambiente,
    commit_atual,
    gerar_relatorio,
)
from visiondoc.configuracao import carregar_configuracao, versao_pipeline
from visiondoc.treino.avaliacao import avaliar_itens
from visiondoc.treino.configuracao import ConfigTreino, carregar_config_treino
from visiondoc.treino.preparacao import DATASET, carregar_preparados

_AUMENTOS = ["do próprio dataset, só em train: rotação, brilho, desfoque e ruído"]
_QUANT_AVALIACAO = "4 bits (nf4, bitsandbytes), avaliação com transformers"


def _agora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _avaliar(cfg: ConfigTreino, cache: Path, itens, adaptador=None):
    import torch

    from visiondoc.treino.treinar import carregar_modelo, contar_parametros, gerador_hf, liberar

    torch.cuda.reset_peak_memory_stats()
    inicio = time.perf_counter()
    modelo, processor = carregar_modelo(cfg, adaptador)
    carga = time.perf_counter() - inicio
    totais, _ = contar_parametros(modelo)
    avaliacao, inferencia = avaliar_itens(
        gerador_hf(modelo, processor, cfg, cache), itens, cfg, tempo_carga_s=carga
    )
    pico = torch.cuda.max_memory_allocated() / 1024**3
    inferencia = replace(inferencia, pico_memoria_gb=pico)
    liberar(modelo)
    return avaliacao, inferencia, totais


def _ultimo_treino(relatorios: Path) -> dict | None:
    candidatos = []
    for arquivo in relatorios.glob("*/metricas.json"):
        metricas = json.loads(arquivo.read_text(encoding="utf-8"))
        if metricas["execucao"]["tipo"] == "lora":
            candidatos.append((metricas["execucao"]["fim"], metricas))
    return max(candidatos, key=lambda c: c[0])[1] if candidatos else None


def executar(
    config_pipeline: str | Path,
    config_treino: str | Path,
    cache: str | Path,
    saida: str | Path,
    relatorios: str | Path,
    limite_treino: int | None = None,
    limite_teste: int | None = None,
    avaliar_zero_shot: bool = True,
) -> dict[str, Path]:
    """Executa a T038. Os limites servem para uma execução curta de verificação."""
    from visiondoc.treino.treinar import treinar

    cfg_pipeline = carregar_configuracao(config_pipeline)
    cfg = carregar_config_treino(config_treino)
    cache, saida, relatorios = Path(cache), Path(saida), Path(relatorios)
    particoes = carregar_preparados(cache)
    treino = particoes["train"][:limite_treino]
    validacao = particoes["valid"]
    teste = particoes["test"][:limite_teste]

    usados = {"train": treino, "valid": validacao, "test": teste}
    dados = InfoDados(
        {DATASET: {p: dict(Counter(i.tipo for i in itens)) for p, itens in usados.items()}},
        _AUMENTOS,
        None,
    )
    ambiente = coletar_ambiente()
    commit, pendentes = commit_atual()
    versoes = f"pipeline {cfg_pipeline.versao}, treino {cfg.versao}"
    resultado: dict[str, Path] = {}

    linha_base = None
    if avaliar_zero_shot:
        inicio = _agora()
        avaliacao, inferencia, totais = _avaliar(cfg, cache, teste)
        execucao = Execucao(
            f"zero-shot-{uuid.uuid4().hex[:8]}",
            inicio,
            _agora(),
            versao_pipeline(cfg_pipeline),
            versoes,
            cfg.semente,
            None,
            commit,
            pendentes,
            "zero-shot",
        )
        modelo = InfoModelo(
            cfg.modelo_base,
            cfg.revisao,
            totais,
            0,
            None,
            _QUANT_AVALIACAO,
            {},
            0,
            None,
            cfg.max_comprimento,
            cfg.lado_max_imagem,
        )
        resultado["zero_shot"] = gerar_relatorio(
            relatorios, execucao, ambiente, modelo, dados, None, inferencia, avaliacao
        )
        linha_base = json.loads((resultado["zero_shot"] / "metricas.json").read_text("utf-8"))

    anterior = _ultimo_treino(relatorios)
    inicio = _agora()
    treinado = treinar(cfg, cache, saida, treino, validacao)
    avaliacao, inferencia, _ = _avaliar(cfg, cache, teste, treinado.adaptador)
    execucao = Execucao(
        f"lora-{uuid.uuid4().hex[:8]}",
        inicio,
        _agora(),
        versao_pipeline(cfg_pipeline),
        versoes,
        cfg.semente,
        treinado.mlflow_id,
        commit,
        pendentes,
        "lora",
    )
    modelo = InfoModelo(
        cfg.modelo_base,
        cfg.revisao,
        treinado.parametros_totais,
        treinado.parametros_treinaveis,
        f"{cfg.quantizacao.bits} bits ({cfg.quantizacao.tipo})",
        _QUANT_AVALIACAO,
        {"r": cfg.lora.r, "alpha": cfg.lora.alpha, "dropout": cfg.lora.dropout},
        treinado.modulos_alvo,
        treinado.tamanho_adaptador_bytes,
        cfg.max_comprimento,
        cfg.lado_max_imagem,
    )
    resultado["lora"] = gerar_relatorio(
        relatorios,
        execucao,
        ambiente,
        modelo,
        dados,
        treinado.info,
        inferencia,
        avaliacao,
        linha_base=linha_base,
        anterior=anterior,
    )
    resultado["adaptador"] = treinado.adaptador
    return resultado
