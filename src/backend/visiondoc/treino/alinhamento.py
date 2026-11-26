"""Alinhamento entre os arquivos locais e as linhas do br-doc-extraction.

Os arquivos ``<split>-<NNNNN>.png`` usam numeração global: o índice da linha dentro do split é o
número do arquivo menos o deslocamento da partição.
"""

import re
from pathlib import Path

# split -> (deslocamento global, quantidade de linhas)
PARTICOES: dict[str, tuple[int, int]] = {
    "train": (0, 1062),
    "valid": (1062, 75),
    "test": (1137, 81),
}

_PADRAO = re.compile(r"^(train|valid|test)-(\d{5})\.png$")


def linha_do_arquivo(nome: str) -> tuple[str, int]:
    """``test-01137.png`` -> ``("test", 0)``; ValueError se o prefixo não bate com a faixa."""
    achado = _PADRAO.match(nome)
    if not achado:
        raise ValueError(f"nome fora do padrão <split>-NNNNN.png: {nome!r}")
    split, indice = achado.group(1), int(achado.group(2))
    inicio, quantidade = PARTICOES[split]
    if not inicio <= indice < inicio + quantidade:
        raise ValueError(f"{nome!r}: índice {indice} fora da faixa de {split} ({inicio}..)")
    return split, indice - inicio


def verificar_pasta(pasta: Path) -> None:
    """ValueError se houver arquivo estranho ou faltar alguma linha de algum split."""
    presentes: dict[str, set[int]] = {s: set() for s in PARTICOES}
    for arquivo in pasta.iterdir():
        split, linha = linha_do_arquivo(arquivo.name)
        presentes[split].add(linha)
    for split, (_, quantidade) in PARTICOES.items():
        faltando = quantidade - len(presentes[split])
        if faltando:
            raise ValueError(f"{split}: faltam {faltando} de {quantidade} arquivos")
