"""Avaliação de um modelo (zero-shot ou com adaptador) na partição de teste (T038).

O gerador é injetado: recebe um item preparado e devolve o texto gerado, os
tokens, a probabilidade de cada token escolhido e o tempo. Assim a lógica de
métricas é testada sem GPU. Usa as métricas da T037 e produz as estruturas do
relatório da T039.
"""

import json
import re
import statistics
import unicodedata
from collections.abc import Callable

from pydantic import ValidationError
from rapidfuzz import fuzz

from visiondoc.avaliacao.metricas import (
    CLASSES_TIPO,
    INDEFINIDO,
    avaliar_extracao,
    calibracao,
    curva_cobertura,
    por_recorte,
)
from visiondoc.avaliacao.relatorio import Avaliacao, InfoInferencia
from visiondoc.contrato_vlm import SaidaVLM
from visiondoc.treino.configuracao import ConfigTreino
from visiondoc.treino.mapeamento import PERTINENTES
from visiondoc.treino.preparacao import ItemPreparado

Gerador = Callable[[ItemPreparado], tuple[str, list[str], list[float], float]]
_PADRAO_TIPO = re.compile('"tipo"\\s*:\\s*"(\\w*)$')
_ASPAS = '"'


def interpretar_resposta(texto: str) -> tuple[str | None, dict | None, bool]:
    """(tipo, campos, válido) do primeiro documento; inválido se fugir do esquema."""
    try:
        saida = SaidaVLM.model_validate(json.loads(texto))
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None, None, False
    documento = saida.documentos[0]
    return documento.tipo, documento.campos.model_dump(), True


def confianca_do_tipo(tokens: list[str], probabilidades: list[float]) -> float | None:
    """Produto das probabilidades dos tokens do rótulo do primeiro campo `tipo` (RN-004)."""
    texto, capturando, produto, achou = "", False, 1.0, False
    for token, prob in zip(tokens, probabilidades):
        if capturando:
            parte = token.split(_ASPAS)[0]
            if parte:
                produto *= prob
                achou = True
            if _ASPAS in token:
                break
            continue
        texto += token
        m = _PADRAO_TIPO.search(texto)
        if m:
            capturando = True
            if m.group(1):
                produto *= prob
                achou = True
    return produto if achou else None


def _normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acentos.upper().split())


def tem_respaldo(valor: str, transcricao: str, limiar: float) -> bool:
    """Respaldo do valor na transcrição (RN-024), com normalização de CPF e datas."""
    base = _normalizar(transcricao)
    candidatos = [_normalizar(valor)]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        a, m, d = valor.split("-")
        candidatos += [f"{d}{s}{m}{s}{a}" for s in ("/", "-", ".", " ")]
    if re.fullmatch(r"[\d.\-]{11,14}", valor.strip()):  # CPF ou número: compara só os dígitos
        digitos = re.sub(r"\D", "", valor)
        if digitos and digitos in re.sub(r"\D", "", base):
            return True
    return any(fuzz.partial_ratio(c, base) >= limiar for c in candidatos if c)


def _valores_extracao(tipo: str, campos: dict | None, chaves: list[str]) -> dict:
    if campos is None:
        return {}
    saida = {}
    for chave in chaves:
        valor = campos.get(chave)
        saida[chave] = "|".join(valor) if isinstance(valor, list) else valor
    return saida


def avaliar_itens(
    gerar: Gerador,
    itens: list[ItemPreparado],
    cfg: ConfigTreino,
    tempo_carga_s: float,
    pico_memoria_gb: float = 0.0,
    dataset: str = "bid",
) -> tuple[Avaliacao, InfoInferencia]:
    limiar = cfg.avaliacao.limiar_rejeicao
    referencias, previstas, brutas, confiancas, acertos, conf_validas = [], [], [], [], [], []
    tempos, tokens_gerados = [], []
    validas = preenchidos = sem_respaldo = 0
    refs_extracao, preds_extracao = [], []
    previsoes = []

    for item in itens:
        texto, tokens, probs, segundos = gerar(item)
        tempos.append(segundos)
        tokens_gerados.append(len(tokens))
        tipo, campos, valido = interpretar_resposta(texto)
        confianca = confianca_do_tipo(tokens, probs) if valido else None
        if valido:
            validas += 1
            for valor in campos.values():
                for v in valor if isinstance(valor, list) else [valor]:
                    if v:
                        preenchidos += 1
                        sem_respaldo += not tem_respaldo(
                            v, item.inteiro_teor or "", cfg.avaliacao.limiar_respaldo
                        )
        aceito = valido and confianca is not None and confianca >= limiar
        referencias.append(item.tipo)
        previstas.append(tipo if aceito else INDEFINIDO)
        brutas.append(tipo or INDEFINIDO)
        confiancas.append(confianca or 0.0)
        if valido and confianca is not None:
            acertos.append(tipo == item.tipo)
            conf_validas.append(confianca)
        chaves = [c for c in sorted(PERTINENTES.get(item.tipo, ())) if c not in item.sem_anotacao]
        if chaves:  # exemplos só de classificação não entram na extração (ADR-018)
            refs_extracao.append(_valores_extracao(item.tipo, item.campos, chaves))
            preds_extracao.append(_valores_extracao(item.tipo, campos if aceito else None, chaves))
        previsoes.append(
            {
                "id": item.id,
                "origem": item.origem,
                "classe_referencia": item.tipo,
                "classe_gerada": tipo,
                "classe_final": tipo if aceito else INDEFINIDO,
                "confianca": confianca,
                "json_valido": valido,
                "segundos": round(segundos, 3),
                "tokens": len(tokens),
            }
        )

    classificacao = {
        "tipo": por_recorte(
            referencias,
            previstas,
            [dataset] * len(itens),
            CLASSES_TIPO,
            n_bootstrap=cfg.avaliacao.n_bootstrap,
            semente=cfg.semente,
        )
    }
    limiares = [round(0.05 * k, 2) for k in range(20)]
    avaliacao = Avaliacao(
        classificacao=classificacao,
        curva_cobertura=curva_cobertura(referencias, brutas, confiancas, limiares),
        calibracao=calibracao(acertos, conf_validas),
        extracao=(
            {dataset: avaliar_extracao(refs_extracao, preds_extracao)} if refs_extracao else {}
        ),
        taxa_campos_sem_respaldo=sem_respaldo / preenchidos if preenchidos else 0.0,
        previsoes=previsoes,
    )
    inferencia = InfoInferencia(
        tempo_carga_s=tempo_carga_s,
        tempos_pagina_s=tempos,
        tempos_por_etapa={"vlm": tempos},
        pico_memoria_gb=pico_memoria_gb,
        tokens_medios=statistics.fmean(tokens_gerados) if tokens_gerados else 0.0,
        taxa_json_valido=validas / len(itens) if itens else 0.0,
    )
    return avaliacao, inferencia
