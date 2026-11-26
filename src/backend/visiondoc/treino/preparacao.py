"""Preparação dos exemplos: entrada do modelo idêntica à da inferência (T038).

Cada linha do dataset passa por ingestão, pré-processamento, transcrição,
detecção e mascaramento (T025 a T029). Guardam-se a imagem mascarada, a
transcrição mascarada enviada ao modelo, o inteiro teor e os rótulos mapeados.
O cache é um artefato de treino; os intermediários do lote são apagados ao fim
(ING-SEC-11). A preparação é retomável pelo manifesto.
"""

import io
import json
import shutil
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from visiondoc.configuracao import Configuracao
from visiondoc.deteccao import Detectores, detectar
from visiondoc.fontes import EntradaArquivo
from visiondoc.ingestao import ingerir
from visiondoc.lote import Lote
from visiondoc.mascaramento import mascarar_documento
from visiondoc.modelos import ErroIngestao
from visiondoc.preprocessamento import normalizar
from visiondoc.transcricao import transcrever_pagina
from visiondoc.treino.mapeamento import mapear_linha

DATASET = "br-doc-extraction"
MANIFESTO = "manifesto.jsonl"


@dataclass
class ItemPreparado:
    id: str
    particao: str
    tipo: str
    campos: dict
    sem_anotacao: list[str]
    imagem: str | None = None  # relativo ao diretório do cache
    transcricao: str | None = None  # mascarada, como enviada ao modelo
    inteiro_teor: str | None = None
    largura: int | None = None
    altura: int | None = None
    erro: str | None = None


def _bytes_jpeg(imagem) -> bytes:
    """Bytes JPEG da linha; outros formatos de imagem são convertidos (qualidade 95)."""
    if isinstance(imagem, dict):
        dados = imagem.get("bytes")
        if dados is None and imagem.get("path"):
            dados = Path(imagem["path"]).read_bytes()
    elif isinstance(imagem, Image.Image):
        saida = io.BytesIO()
        imagem.convert("RGB").save(saida, "JPEG", quality=95)
        return saida.getvalue()
    else:
        dados = bytes(imagem)
    if dados.startswith(b"\xff\xd8\xff"):
        return dados
    try:
        saida = io.BytesIO()
        Image.open(io.BytesIO(dados)).convert("RGB").save(saida, "JPEG", quality=95)
        return saida.getvalue()
    except Exception:  # noqa: BLE001  (a ingestão registra o formato inválido)
        return dados


def _ler_manifesto(destino: Path) -> dict[str, ItemPreparado]:
    arquivo = destino / MANIFESTO
    if not arquivo.exists():
        return {}
    itens = (
        ItemPreparado(**json.loads(linha))
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    )
    return {item.id: item for item in itens}


def preparar(
    linhas: Iterable[tuple[str, dict]],
    destino: str | Path,
    cfg: Configuracao,
    transcritor,
    avaliador,
    classificador,
    detectores: Detectores,
    regras_yara: str | Path,
) -> list[ItemPreparado]:
    destino = Path(destino)
    (destino / "imagens").mkdir(parents=True, exist_ok=True)
    existentes = _ler_manifesto(destino)
    itens: list[ItemPreparado] = []
    with Lote() as lote, open(destino / MANIFESTO, "a", encoding="utf-8") as manifesto:
        trabalho = lote.diretorio_trabalho
        for indice, (particao, linha) in enumerate(linhas):
            identificador = f"{particao}-{indice:05d}"
            if identificador in existentes:
                itens.append(existentes[identificador])
                continue
            mapeada = mapear_linha(linha)
            item = ItemPreparado(
                identificador, particao, mapeada.tipo, mapeada.campos, sorted(mapeada.sem_anotacao)
            )
            arquivo = trabalho / f"{identificador}.jpg"
            arquivo.write_bytes(_bytes_jpeg(linha["image"]))
            entrada = EntradaArquivo(arquivo, arquivo.name, f"{DATASET}:{identificador}")
            ingerido = ingerir(entrada, trabalho, cfg)
            if isinstance(ingerido, ErroIngestao):
                item.erro = str(ingerido.motivo)
            else:
                normalizada = normalizar(
                    ingerido.paginas[0],
                    classificador,
                    avaliador,
                    trabalho,
                    ingerido.orientacao_exif,
                )
                transcricao = transcrever_pagina(normalizada, transcritor)
                ocorrencias = detectar(
                    ingerido, [normalizada], [transcricao], detectores, cfg, regras_yara
                )
                entradas, _ = mascarar_documento(
                    [normalizada], [transcricao], ocorrencias, trabalho
                )
                relativo = f"imagens/{identificador}.png"
                shutil.copyfile(entradas[0].imagem, destino / relativo)
                item.imagem = relativo
                item.transcricao = entradas[0].transcricao
                item.inteiro_teor = transcricao.inteiro_teor
                item.largura, item.altura = normalizada.largura, normalizada.altura
            manifesto.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
            manifesto.flush()
            itens.append(item)
    return itens


def carregar_preparados(destino: str | Path) -> dict[str, list[ItemPreparado]]:
    """Itens válidos do cache, por partição, na ordem do manifesto."""
    particoes: dict[str, list[ItemPreparado]] = {}
    for item in _ler_manifesto(Path(destino)).values():
        if item.erro is None:
            particoes.setdefault(item.particao, []).append(item)
    return particoes
