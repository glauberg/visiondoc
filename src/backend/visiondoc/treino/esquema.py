"""Esquema da saída do VLM (contrato docs/contracts/saida-vlm.md).

Cópia do esquema da prova de conceito T020; trocar pelo esquema do pipeline quando a T031 o criar.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Campos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = None
    cpf: str | None = None
    numero_documento: str | None = None
    data_nascimento: str | None = None
    data_emissao: str | None = None
    data_validade: str | None = None
    orgao_emissor: str | None = None
    filiacao: list[str] = Field(default_factory=list)
    naturalidade: str | None = None
    doc_origem: str | None = None
    categoria_habilitacao: str | None = None


class Documento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["cnh", "rg", "cpf", "outros"]
    face: Literal["frente", "verso", "ambas"] | None = None
    bbox: list[int] = Field(min_length=4, max_length=4)
    campos: Campos


class SaidaVLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentos: list[Documento] = Field(min_length=1)
