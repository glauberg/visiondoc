"""Esquema da saída do VLM (docs/contracts/saida-vlm.md).

Todas as chaves são obrigatórias e aceitam null: a decodificação estruturada e
o treino obrigam o modelo a se pronunciar sobre cada campo (achado da T020).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Campos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None
    cpf: str | None
    numero_documento: str | None
    data_nascimento: str | None
    data_emissao: str | None
    data_validade: str | None
    orgao_emissor: str | None
    filiacao: list[str]
    naturalidade: str | None
    doc_origem: str | None
    categoria_habilitacao: str | None


class Documento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["cnh", "rg", "cpf", "outros"]
    face: Literal["frente", "verso", "ambas"] | None
    bbox: list[int] = Field(min_length=4, max_length=4)
    campos: Campos


class SaidaVLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentos: list[Documento] = Field(min_length=1)
