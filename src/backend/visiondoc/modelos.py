"""Tipos compartilhados entre as etapas do pipeline."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

Caixa = tuple[int, int, int, int]  # x1, y1, x2, y2 em pixels


class MotivoErro(StrEnum):  # RN-018
    FORMATO_NAO_SUPORTADO = "formato_nao_suportado"
    TAMANHO_EXCEDIDO = "tamanho_excedido"
    ARQUIVO_ILEGIVEL = "arquivo_ilegivel"
    FALHA_PROCESSAMENTO = "falha_processamento"
    CONTRATO_INVALIDO = "contrato_invalido"


@dataclass(frozen=True)
class Identificacao:  # RN-001, RN-002
    id_processo: str
    nome_arquivo: str
    hash_arquivo: str
    data_hora: str  # ISO 8601 com o deslocamento do fuso local


@dataclass(frozen=True)
class ItemAtivo:
    """Elemento ativo encontrado no PDF, inventariado sem execução (ING-SEC-04)."""

    tipo: str  # javascript, acao_automatica, launch, arquivo_embutido, formulario, rich_media
    objeto: str
    executavel: bool


@dataclass(frozen=True)
class SegmentoTexto:
    """Trecho da camada de texto nativa, em pixels da página rasterizada original."""

    texto: str
    caixa: Caixa
    tamanho_fonte: float | None


@dataclass(frozen=True)
class Pagina:
    numero: int
    imagem: Path
    largura: int
    altura: int
    texto_nativo: list[SegmentoTexto] = field(default_factory=list)


@dataclass(frozen=True)
class ArquivoIngerido:
    identificacao: Identificacao
    caminho_original: Path
    formato: str  # pdf ou jpeg
    paginas: list[Pagina]
    inventario: list[ItemAtivo]
    orientacao_exif: int | None = None


@dataclass(frozen=True)
class ErroIngestao:
    identificacao: Identificacao
    motivo: MotivoErro
    detalhe: str  # sem conteúdo documental


class Categoria(StrEnum):  # RN-009
    CONTEUDO_ATIVO = "conteudo_ativo"
    TEXTO_OCULTO = "texto_oculto"
    INJECAO_PROMPT = "injecao_prompt"
    CAMPO_SEM_RESPALDO = "campo_sem_respaldo"
    DADO_INCONSISTENTE = "dado_inconsistente"
    FALHA_DETECCAO = "falha_deteccao"


class Severidade(StrEnum):  # RN-010
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


@dataclass(frozen=True)
class Ocorrencia:
    """Ocorrência de detecção ou validação. Evidência é conteúdo hostil (MAL-SEC-08)."""

    categoria: Categoria
    severidade: Severidade
    regra_ou_modelo: str
    evidencia: str
    etapa: str = "deteccao"
    pagina: int | None = None
    escore: float | None = None
    localizacao: Caixa | None = None  # pixels da imagem normalizada (mascaramento)
    localizacao_original: Caixa | None = None  # pixels da página rasterizada original
    localizacao_evidencia: str | None = None  # nome do objeto PDF, quando não há região
    mascarado: bool | None = None
    campo: str | None = None
