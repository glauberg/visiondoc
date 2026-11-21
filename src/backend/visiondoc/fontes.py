"""Entrada do lote: arquivos carregados dos datasets (Q-07, RN-001)."""

import re
from dataclasses import dataclass
from pathlib import Path

_NOME_DATASET = re.compile(r"[a-z0-9][a-z0-9-]*")


@dataclass(frozen=True)
class EntradaArquivo:
    caminho: Path
    nome_arquivo: str
    id_processo: str


def listar_entradas(diretorio: str | Path, dataset: str) -> list[EntradaArquivo]:
    """Lista os arquivos do dataset com id_processo sintético `<dataset>:<arquivo>`."""
    if not _NOME_DATASET.fullmatch(dataset):
        raise ValueError(f"nome de dataset inválido: {dataset!r}")
    raiz = Path(diretorio)
    entradas = []
    for caminho in sorted(p for p in raiz.rglob("*") if p.is_file()):
        relativo = caminho.relative_to(raiz).as_posix()
        entradas.append(
            EntradaArquivo(
                caminho=caminho, nome_arquivo=caminho.name, id_processo=f"{dataset}:{relativo}"
            )
        )
    return entradas
