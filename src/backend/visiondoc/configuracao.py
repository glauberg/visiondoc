"""Configuração versionada do pipeline (Q-22).

Limiares e parâmetros calibráveis ficam em config/pipeline.yaml, validados aqui.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from visiondoc import __version__


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Limites(_Base):
    tamanho_max_bytes: int = Field(gt=0)
    paginas_max: int = Field(gt=0)
    lado_max_px: int = Field(gt=0)
    tempo_max_s: float = Field(gt=0)
    memoria_max_gb: float = Field(gt=0)


class Rasterizacao(_Base):
    dpi: int = Field(gt=0)


class ClamAV(_Base):
    habilitado: bool
    host: str
    porta: int = Field(gt=0, lt=65536)


class Deteccao(_Base):
    yara_regras: str
    injecao_limiar_alto: float = Field(gt=0, le=1)
    injecao_limiar_intermediario: float = Field(gt=0, le=1)
    texto_oculto_partial_ratio: float = Field(gt=0, le=100)
    fonte_minima_pt: float = Field(gt=0)
    clamav: ClamAV

    @model_validator(mode="after")
    def _limiares_ordenados(self) -> "Deteccao":
        if self.injecao_limiar_intermediario >= self.injecao_limiar_alto:
            raise ValueError("injecao_limiar_intermediario deve ser menor que injecao_limiar_alto")
        return self


class Saida(_Base):
    evidencia_max_caracteres: int = Field(gt=0)


class Configuracao(_Base):
    versao: str = Field(min_length=1)
    limites: Limites
    rasterizacao: Rasterizacao
    deteccao: Deteccao
    saida: Saida


def carregar_configuracao(caminho: str | Path) -> Configuracao:
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8"))
    return Configuracao.model_validate(dados)


def versao_pipeline(cfg: Configuracao) -> str:
    """SemVer do pipeline com a versão da configuração como metadado de build."""
    return f"{__version__}+cfg.{cfg.versao}"
