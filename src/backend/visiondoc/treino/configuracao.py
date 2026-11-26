"""Configuração versionada do treino (config/treino.yaml)."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Quantizacao(_Base):
    bits: Literal[4]
    tipo: Literal["nf4", "fp4"]
    dupla: bool


class Lora(_Base):
    r: int = Field(gt=0)
    alpha: int = Field(gt=0)
    dropout: float = Field(ge=0, lt=1)
    alvos: str


class Otimizacao(_Base):
    taxa_aprendizado: float = Field(gt=0)
    epocas: float = Field(gt=0)
    lote: Literal[1]  # o coletor monta um exemplo multimodal por vez
    acumulacao: int = Field(gt=0)
    aquecimento: float = Field(ge=0, lt=1)
    agendador: str
    checkpointing: bool


class AvaliacaoTreino(_Base):
    max_novos_tokens: int = Field(gt=0)
    limiar_rejeicao: float = Field(gt=0, lt=1)
    limiar_respaldo: float = Field(gt=0, le=100)
    n_bootstrap: int = Field(ge=0)


class ConfigTreino(_Base):
    versao: str
    dataset: str
    modelo_base: str
    revisao: str | None
    semente: int
    formato_bbox: Literal["relativo_1000", "pixels"]
    lado_max_imagem: int = Field(gt=0)
    max_comprimento: int = Field(gt=0)
    quantizacao: Quantizacao
    lora: Lora
    otimizacao: Otimizacao
    avaliacao: AvaliacaoTreino


def carregar_config_treino(caminho: str | Path) -> ConfigTreino:
    return ConfigTreino.model_validate(yaml.safe_load(Path(caminho).read_text(encoding="utf-8")))


def bbox_documento_inteiro(cfg: ConfigTreino, largura: int, altura: int) -> list[int]:
    """Alvo de bbox para imagens com um único documento recortado (ADR-017)."""
    return [0, 0, 1000, 1000] if cfg.formato_bbox == "relativo_1000" else [0, 0, largura, altura]
