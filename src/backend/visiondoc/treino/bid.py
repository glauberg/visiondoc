"""Leitura do BID organizado em subpastas por classe e divisão 70-15-15 (ADR-018).

Estrutura esperada: `<raiz>/CNH`, `<raiz>/RG` e `<raiz>/CPF` (sem diferenciar
maiúsculas), com as imagens JPEG de cada classe. A divisão é estratificada por
classe, com semente fixa, e feita sobre o dataset inteiro antes de qualquer
amostragem.
"""

import csv
import math
import random
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from visiondoc.csv_seguro import preparar_texto
from visiondoc.treino.mapeamento import mapear_classe
from visiondoc.treino.preparacao import Exemplo

CLASSES_BID = {"cnh": "cnh", "rg": "rg", "cpf": "cpf"}
EXTENSOES = {".jpg", ".jpeg"}
PROPORCOES = {"train": 0.70, "valid": 0.15, "test": 0.15}


@dataclass(frozen=True)
class ArquivoBID:
    caminho: Path
    relativo: str
    classe: str


def listar_bid(raiz: str | Path) -> list[ArquivoBID]:
    raiz = Path(raiz)
    if not raiz.is_dir():
        raise ValueError(f"diretório do dataset não encontrado: {raiz}")
    arquivos = []
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")):
        classe = CLASSES_BID.get(pasta.name.lower())
        if classe is None:
            raise ValueError(f"subpasta não reconhecida: {pasta.name}; esperadas CNH, RG e CPF")
        for caminho in sorted(pasta.rglob("*")):
            if caminho.is_file() and caminho.suffix.lower() in EXTENSOES:
                arquivos.append(ArquivoBID(caminho, caminho.relative_to(raiz).as_posix(), classe))
    if not arquivos:
        raise ValueError(f"nenhuma imagem JPEG encontrada em {raiz}")
    return arquivos


def _arredondar(valor: float) -> int:
    return math.floor(valor + 0.5)


def dividir(
    arquivos: list[ArquivoBID], semente: int, proporcoes: dict[str, float] = PROPORCOES
) -> dict[str, list[ArquivoBID]]:
    """Divisão estratificada por classe; a última partição recebe o restante."""
    nomes = list(proporcoes)
    divisao: dict[str, list[ArquivoBID]] = {nome: [] for nome in nomes}
    gerador = random.Random(semente)
    for classe in sorted({a.classe for a in arquivos}):
        da_classe = sorted((a for a in arquivos if a.classe == classe), key=lambda a: a.relativo)
        gerador.shuffle(da_classe)
        inicio = 0
        for i, nome in enumerate(nomes):
            fim = (
                len(da_classe)
                if i == len(nomes) - 1
                else inicio + _arredondar(len(da_classe) * proporcoes[nome])
            )
            divisao[nome].extend(da_classe[inicio:fim])
            inicio = fim
    return divisao


def amostrar(divisao: dict[str, list[ArquivoBID]], por_classe: int) -> dict[str, list[ArquivoBID]]:
    """Primeiros N de cada classe em cada partição (a ordem já é aleatória)."""
    amostra = {}
    for particao, arquivos in divisao.items():
        contagem: dict[str, int] = {}
        amostra[particao] = []
        for a in arquivos:
            if contagem.get(a.classe, 0) < por_classe:
                contagem[a.classe] = contagem.get(a.classe, 0) + 1
                amostra[particao].append(a)
    return amostra


def gravar_particoes_csv(divisao: dict[str, list[ArquivoBID]], destino: str | Path) -> Path:
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / "particoes.csv"
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, quoting=csv.QUOTE_NONNUMERIC)
        escritor.writerow(["particao", "classe", "arquivo"])
        for particao, arquivos in divisao.items():
            for a in arquivos:
                escritor.writerow([particao, a.classe, preparar_texto(a.relativo)])
    return caminho


def exemplos_bid(divisao: dict[str, list[ArquivoBID]]) -> Iterator[Exemplo]:
    for particao, arquivos in divisao.items():
        for a in arquivos:
            yield Exemplo(
                particao,
                {"bytes": None, "path": str(a.caminho)},
                mapear_classe(a.classe),
                a.relativo,
            )
