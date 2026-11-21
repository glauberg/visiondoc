"""Esquema da saída do VLM usado na prova de conceito T020.

Reproduz o contrato docs/contracts/saida-vlm.md. Não é o código do pipeline.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Campos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = None
    cpf: Optional[str] = None
    numero_documento: Optional[str] = None
    data_nascimento: Optional[str] = None
    data_emissao: Optional[str] = None
    data_validade: Optional[str] = None
    orgao_emissor: Optional[str] = None
    filiacao: list[str] = Field(default_factory=list)
    naturalidade: Optional[str] = None
    doc_origem: Optional[str] = None
    categoria_habilitacao: Optional[str] = None


class Documento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["cnh", "rg", "cpf", "outros"]
    face: Optional[Literal["frente", "verso", "ambas"]] = None
    bbox: list[int] = Field(min_length=4, max_length=4)
    campos: Campos


class SaidaVLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentos: list[Documento] = Field(min_length=1)
