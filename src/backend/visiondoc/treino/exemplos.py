"""Montagem dos exemplos de treino no formato do contrato da saída do VLM.

A resposta-alvo traz todas as chaves do contrato. Os valores dos campos sem
anotação são escritos como null, mas seus trechos são devolvidos para que os
tokens correspondentes fiquem fora da perda (rótulo -100).
"""

import json
from pathlib import Path

from visiondoc.treino.mapeamento import CAMPOS_CONTRATO

IGNORAR = -100
ARQUIVO_INSTRUCAO = Path(__file__).resolve().parents[4] / "config" / "prompts" / "instrucao_vlm.txt"


def carregar_instrucao(caminho: str | Path = ARQUIVO_INSTRUCAO) -> str:
    return Path(caminho).read_text(encoding="utf-8").strip()


def montar_resposta(
    tipo: str, campos: dict, sem_anotacao: set[str], face: str | None, bbox: list[int]
) -> tuple[str, list[tuple[int, int]]]:
    partes: list[str] = []
    trechos: list[tuple[int, int]] = []
    posicao = 0

    def escrever(texto: str, ignorar: bool = False) -> None:
        nonlocal posicao
        if ignorar:
            trechos.append((posicao, posicao + len(texto)))
        partes.append(texto)
        posicao += len(texto)

    escrever(
        '{"documentos": [{"tipo": '
        + json.dumps(tipo)
        + ', "face": '
        + json.dumps(face)
        + ', "bbox": '
        + json.dumps(bbox)
        + ', "campos": {'
    )
    for i, campo in enumerate(CAMPOS_CONTRATO):
        escrever(("" if i == 0 else ", ") + json.dumps(campo) + ": ")
        if campo in sem_anotacao:
            escrever("[]" if campo == "filiacao" else "null", ignorar=True)
        else:
            escrever(json.dumps(campos[campo], ensure_ascii=False))
    escrever("}}]}")
    return "".join(partes), trechos


def rotular_tokens(
    ids: list[int], offsets: list[tuple[int, int]], trechos: list[tuple[int, int]]
) -> list[int]:
    """Rótulos da resposta: -100 nos tokens que tocam um trecho sem anotação."""
    return [
        IGNORAR if any(ini < fim_t and fim > ini_t for ini_t, fim_t in trechos) else token
        for token, (ini, fim) in zip(ids, offsets)
    ]


def mensagens(instrucao: str, transcricao: str, imagem) -> list[dict]:
    """Mensagens no formato de chat; o conteúdo documental entra delimitado como dado (P2)."""
    return [
        {"role": "system", "content": [{"type": "text", "text": instrucao}]},
        {
            "role": "user",
            "content": [
                {"type": "image", "image": imagem},
                {"type": "text", "text": f"<transcricao>\n{transcricao}\n</transcricao>"},
            ],
        },
    ]


def montar_sequencia(
    prompt_ids: list[int],
    resposta_ids: list[int],
    offsets: list[tuple[int, int]],
    trechos: list[tuple[int, int]],
) -> tuple[list[int], list[int]]:
    """Concatena prompt e resposta; o prompt e os campos sem anotação ficam fora da perda."""
    rotulos = [IGNORAR] * len(prompt_ids) + rotular_tokens(resposta_ids, offsets, trechos)
    return list(prompt_ids) + list(resposta_ids), rotulos
