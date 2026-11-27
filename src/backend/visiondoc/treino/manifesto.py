"""Treino com as imagens já preparadas do `br-doc-extraction` (ADR-019).

A fonte é um diretório com `MANIFESTO.JSONL` e a subpasta `imagens/`, no formato
do cache da preparação (uma linha por imagem, com `id`, `tipo`, `imagem`,
`transcricao`, `inteiro_teor`, `largura`, `altura` e `erro`). As classes são
`cnh`, `rg` e `invoice`; `outros`, como a preparação do ADR-017 gravava as notas
fiscais, é lido como `invoice`. A partição original do manifesto é ignorada: a
divisão 70-15-15 estratificada do ADR-018 é refeita sobre todas as imagens
válidas. O treino é só de classificação.
"""

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from visiondoc.treino.bid import ArquivoClasse
from visiondoc.treino.mapeamento import mapear_classe
from visiondoc.treino.preparacao import MANIFESTO, ItemPreparado

ARQUIVO_MANIFESTO = "MANIFESTO.JSONL"
TIPOS_MANIFESTO = {"cnh": "cnh", "rg": "rg", "invoice": "invoice", "outros": "invoice"}
CLASSES = ("cnh", "rg", "invoice")


@dataclass(frozen=True)
class ImagemManifesto(ArquivoClasse):
    linha: dict = field(default_factory=dict, compare=False, hash=False)


def localizar_manifesto(raiz: str | Path) -> Path:
    """`MANIFESTO.JSONL` na raiz, sem diferenciar maiúsculas."""
    raiz = Path(raiz)
    if raiz.is_dir():
        for caminho in sorted(raiz.iterdir()):
            if caminho.is_file() and caminho.name.lower() == ARQUIVO_MANIFESTO.lower():
                return caminho
    raise ValueError(f"{ARQUIVO_MANIFESTO} não encontrado em {raiz}")


def listar_manifesto(raiz: str | Path) -> tuple[list[ImagemManifesto], Counter]:
    """Imagens válidas do manifesto e a contagem das descartadas, por motivo."""
    raiz = Path(raiz)
    imagens: list[ImagemManifesto] = []
    descartes: Counter = Counter()
    texto = localizar_manifesto(raiz).read_text(encoding="utf-8")
    for numero, bruta in enumerate(texto.splitlines(), start=1):
        if not bruta.strip():
            continue
        linha = json.loads(bruta)
        tipo = TIPOS_MANIFESTO.get(str(linha.get("tipo", "")).lower())
        if tipo is None:
            raise ValueError(f"linha {numero}: tipo não suportado: {linha.get('tipo')!r}")
        if linha.get("erro") is not None:
            descartes["erro na preparação"] += 1
            continue
        if not linha.get("imagem") or not (raiz / linha["imagem"]).is_file():
            descartes["imagem ausente"] += 1
            continue
        relativo = Path(linha["imagem"]).as_posix()
        imagens.append(ImagemManifesto(raiz / relativo, relativo, tipo, linha))
    if not imagens:
        raise ValueError(f"nenhuma imagem válida no manifesto de {raiz}")
    return imagens, descartes


def montar_cache(
    divisao: dict[str, list[ImagemManifesto]], destino: str | Path
) -> list[ItemPreparado]:
    """Grava o manifesto do cache de treino; as imagens ficam na fonte (caminho absoluto)."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    itens: list[ItemPreparado] = []
    for particao, imagens in divisao.items():
        for indice, imagem in enumerate(imagens):
            mapeada = mapear_classe(imagem.classe)
            linha = imagem.linha
            itens.append(
                ItemPreparado(
                    f"{particao}-{indice:05d}",
                    particao,
                    mapeada.tipo,
                    mapeada.campos,
                    sorted(mapeada.sem_anotacao),
                    imagem=str(imagem.caminho.resolve()),
                    transcricao=linha.get("transcricao") or "",
                    inteiro_teor=linha.get("inteiro_teor") or "",
                    largura=linha.get("largura"),
                    altura=linha.get("altura"),
                    origem=imagem.relativo,
                )
            )
    conteudo = "".join(json.dumps(asdict(i), ensure_ascii=False) + "\n" for i in itens)
    (destino / MANIFESTO).write_text(conteudo, encoding="utf-8")
    return itens
