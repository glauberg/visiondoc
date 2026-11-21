"""Mascaramento das regiões suspeitas na entrada do VLM (T029, RN-021, ADR-012).

Ocorrências de `injecao_prompt` ou `texto_oculto` com localização conhecida
são cobertas por retângulo sólido na imagem enviada ao VLM, e as linhas da
transcrição que caem na região viram `[TRECHO REMOVIDO]`. A imagem normalizada,
o inteiro teor e a evidência dos alertas permanecem completos.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image, ImageDraw

from visiondoc.modelos import Caixa, Categoria, Ocorrencia
from visiondoc.preprocessamento import PaginaNormalizada
from visiondoc.transcricao import Transcricao

MARCADOR = "[TRECHO REMOVIDO]"
_MASCARAVEIS = {Categoria.INJECAO_PROMPT, Categoria.TEXTO_OCULTO}
_COBERTURA_MINIMA = 0.5  # fração da caixa da linha dentro da região mascarada


@dataclass(frozen=True)
class EntradaVLM:
    pagina: int
    imagem: Path
    transcricao: str


def _fracao_coberta(linha: Caixa, regiao: Caixa) -> float:
    x1, y1 = max(linha[0], regiao[0]), max(linha[1], regiao[1])
    x2, y2 = min(linha[2], regiao[2]), min(linha[3], regiao[3])
    intersecao = max(0, x2 - x1) * max(0, y2 - y1)
    area = max(1, (linha[2] - linha[0]) * (linha[3] - linha[1]))
    return intersecao / area


def _mascarar_pagina(
    normalizada: PaginaNormalizada,
    transcricao: Transcricao,
    regioes: list[Caixa],
    diretorio: Path,
) -> EntradaVLM:
    with Image.open(normalizada.imagem) as original:
        imagem = original.convert("RGB")
    desenho = ImageDraw.Draw(imagem)
    for x1, y1, x2, y2 in regioes:
        desenho.rectangle((x1, y1, max(x1, x2 - 1), max(y1, y2 - 1)), fill=(0, 0, 0))
    destino = Path(diretorio) / f"{Path(normalizada.imagem).stem}-mascarada.png"
    imagem.save(destino, "PNG")
    linhas = [
        MARCADOR
        if any(_fracao_coberta(linha.caixa, r) > _COBERTURA_MINIMA for r in regioes)
        else linha.texto
        for linha in transcricao.linhas
    ]
    return EntradaVLM(normalizada.numero, destino, "\n".join(linhas))


def mascarar_documento(
    normalizadas: list[PaginaNormalizada],
    transcricoes: list[Transcricao],
    ocorrencias: list[Ocorrencia],
    diretorio: Path,
) -> tuple[list[EntradaVLM], list[Ocorrencia]]:
    """Devolve a entrada do VLM por página e as ocorrências com `mascarado` preenchido."""
    paginas = {n.numero for n in normalizadas}
    regioes: dict[int, list[Caixa]] = {numero: [] for numero in paginas}
    atualizadas = []
    for oc in ocorrencias:
        if oc.categoria in _MASCARAVEIS:
            localizada = oc.localizacao is not None and oc.pagina in paginas
            if localizada:
                regioes[oc.pagina].append(oc.localizacao)
            oc = replace(oc, mascarado=localizada)
        atualizadas.append(oc)
    entradas = [
        _mascarar_pagina(normalizada, transcricao, regioes[normalizada.numero], diretorio)
        for normalizada, transcricao in zip(normalizadas, transcricoes)
    ]
    return entradas, atualizadas
