"""Rótulos do br-doc-extraction e geração dos JSONL de treino, validação e teste."""

import json
import re
from collections import Counter
from pathlib import Path

import httpx

from visiondoc.treino.alinhamento import PARTICOES, linha_do_arquivo
from visiondoc.treino.instrucao import INSTRUCAO, TEXTO_USUARIO, hash_instrucao
from visiondoc.treino.rotulos import converter_rotulo, serializar_alvo

URL_LINHAS = "https://datasets-server.huggingface.co/rows"
DATASET = "tech4humans/br-doc-extraction"
TAMANHO_PAGINA = 100
_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CAMPOS_DATA = ("data_nascimento", "data_emissao", "data_validade")


def baixar_rotulos(
    split: str, cache: Path, cliente: httpx.Client | None = None
) -> list[dict[str, str]]:
    """Linhas ``{"type", "response"}`` do split, em ordem; usa e grava o cache local."""
    esperado = PARTICOES[split][1]
    arquivo = cache / f"rotulos-{split}.json"
    if arquivo.exists():
        rotulos = json.loads(arquivo.read_text("utf-8"))
    else:
        proprio = cliente is None
        cliente = cliente or httpx.Client(timeout=60)
        try:
            rotulos = []
            for offset in range(0, esperado, TAMANHO_PAGINA):
                resposta = cliente.get(
                    URL_LINHAS,
                    params={
                        "dataset": DATASET,
                        "config": "default",
                        "split": split,
                        "offset": offset,
                        "length": TAMANHO_PAGINA,
                    },
                )
                resposta.raise_for_status()
                for linha in resposta.json()["rows"]:
                    rotulos.append(
                        {"type": linha["row"]["type"], "response": linha["row"]["response"]}
                    )
        finally:
            if proprio:
                cliente.close()
    if len(rotulos) != esperado:
        raise ValueError(f"{split}: {len(rotulos)} linhas, esperado {esperado}")
    if not arquivo.exists():
        cache.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(rotulos, ensure_ascii=False), "utf-8")
    return rotulos


def montar_exemplos(
    pasta: Path, rotulos: dict[str, list[dict[str, str]]]
) -> tuple[dict[str, list[dict]], dict]:
    """Exemplos por split (um por imagem presente na pasta) e o relatório da geração."""
    exemplos: dict[str, list[dict]] = {s: [] for s in PARTICOES}
    tipos: dict[str, Counter] = {s: Counter() for s in PARTICOES}
    descartadas = datas_fora_iso = 0
    for arquivo in sorted(pasta.glob("*.png")):
        split, linha = linha_do_arquivo(arquivo.name)
        try:
            rotulo = rotulos[split][linha]
        except IndexError as erro:
            raise ValueError(f"{arquivo.name}: sem rótulo na linha {linha} de {split}") from erro
        saida = converter_rotulo(rotulo["type"], rotulo["response"])
        if saida is None:
            descartadas += 1
            continue
        campos = saida.documentos[0].campos
        for nome in _CAMPOS_DATA:
            valor = getattr(campos, nome)
            if valor is not None and not _DATA_ISO.match(valor):
                datas_fora_iso += 1
        tipo = saida.documentos[0].tipo
        tipos[split][tipo] += 1
        exemplos[split].append(
            {
                "id": arquivo.stem,
                "split": split,
                "imagem": arquivo.name,
                "tipo": tipo,
                "messages": [
                    {"role": "system", "content": INSTRUCAO},
                    {
                        "role": "user",
                        "content": [{"type": "image"}, {"type": "text", "text": TEXTO_USUARIO}],
                    },
                    {"role": "assistant", "content": serializar_alvo(saida)},
                ],
            }
        )
    relatorio = {
        "contagem_por_split": {s: len(e) for s, e in exemplos.items()},
        "contagem_por_tipo": {s: dict(c) for s, c in tipos.items()},
        "descartadas": descartadas,
        "datas_fora_do_padrao_iso": datas_fora_iso,
        "hash_instrucao": hash_instrucao(),
    }
    return exemplos, relatorio


def gravar_jsonl(exemplos: dict[str, list[dict]], relatorio: dict, saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    for split, linhas in exemplos.items():
        texto = "".join(json.dumps(linha, ensure_ascii=False) + "\n" for linha in linhas)
        (saida / f"{split}.jsonl").write_text(texto, "utf-8")
    (saida / "relatorio.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), "utf-8"
    )
