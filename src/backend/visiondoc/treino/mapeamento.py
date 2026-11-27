"""Mapeamento das linhas do `tech4humans/br-doc-extraction` para o contrato (ADR-017).

Cada linha tem `type` (cnh, rg, invoice), `schema` (prompt com os campos
anotados naquela variante) e `response` (JSON). Campos pertinentes ao tipo e
não anotados pela linha ficam em `sem_anotacao`, para serem ignorados na perda.
Campos não pertinentes ao tipo são null conhecidos (RN-023).
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date

CAMPOS_CONTRATO = [
    "nome",
    "cpf",
    "numero_documento",
    "data_nascimento",
    "data_emissao",
    "data_validade",
    "orgao_emissor",
    "filiacao",
    "naturalidade",
    "doc_origem",
    "categoria_habilitacao",
]

# Tabela "Campos por tipo" de docs/contracts/saida-vlm.md
PERTINENTES = {
    "cnh": {
        "nome",
        "cpf",
        "numero_documento",
        "data_nascimento",
        "data_emissao",
        "data_validade",
        "orgao_emissor",
        "filiacao",
        "categoria_habilitacao",
    },
    "rg": {
        "nome",
        "cpf",
        "numero_documento",
        "data_nascimento",
        "data_emissao",
        "orgao_emissor",
        "filiacao",
        "naturalidade",
        "doc_origem",
    },
    "cpf": {"nome", "cpf", "data_nascimento"},
    "outros": set(),
}

TIPOS = {"cnh": "cnh", "rg": "rg", "invoice": "outros"}

_FONTES = {
    "nome": ["nome_completo", "nome", "titular"],
    "cpf": ["cpf"],
    "numero_documento": ["num_registro", "registro_geral", "rg_numero"],
    "data_nascimento": ["data_nascimento"],
    "data_emissao": ["data_emissao", "data_expedicao"],
    "data_validade": ["data_validade"],
    "orgao_emissor": ["orgao_emissor"],
    "naturalidade": ["naturalidade", "local_nascimento"],
    "doc_origem": ["doc_origem"],
    "categoria_habilitacao": ["categoria_habilitacao"],
}
_FILIACAO = ["filiacao_pai", "filiacao_mae"]
_DATAS = {"data_nascimento", "data_emissao", "data_validade"}
_MAIUSCULAS = {"nome", "orgao_emissor", "naturalidade", "categoria_habilitacao"}
_FORMATOS_DATA = [
    re.compile(r"(?P<d>\d{1,2})[/.\- ](?P<m>\d{1,2})[/.\- ](?P<a>\d{4})"),
    re.compile(r"(?P<a>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})"),
]


@dataclass
class LinhaMapeada:
    tipo: str
    campos: dict
    sem_anotacao: set[str] = field(default_factory=set)


def _chaves_do_esquema(texto: str) -> set[str]:
    inicio = texto.find("{")
    if inicio < 0:
        return set()
    try:
        esquema, _ = json.JSONDecoder().raw_decode(texto[inicio:])
    except json.JSONDecodeError:
        return set()
    return set(esquema) if isinstance(esquema, dict) else set()


def normalizar_data(valor: str) -> str | None:
    for padrao in _FORMATOS_DATA:
        m = padrao.fullmatch(valor.strip())
        if m:
            try:
                return date(int(m["a"]), int(m["m"]), int(m["d"])).isoformat()
            except ValueError:
                return None
    return None


def normalizar_cpf(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return valor.strip()


def _maiusculas(valor: str) -> str:
    return " ".join(valor.upper().split())


def mapear_linha(linha: dict) -> LinhaMapeada:
    if linha["type"] not in TIPOS:
        raise ValueError(f"tipo não suportado: {linha['type']!r}")
    tipo = TIPOS[linha["type"]]
    campos: dict = {c: None for c in CAMPOS_CONTRATO}
    campos["filiacao"] = []
    if tipo == "outros":
        return LinhaMapeada(tipo, campos)

    anotadas = _chaves_do_esquema(linha.get("schema") or "")
    resposta = json.loads(linha.get("response") or "{}")
    sem_anotacao: set[str] = set()

    for campo in PERTINENTES[tipo]:
        if campo == "filiacao":
            chaves = [k for k in _FILIACAO if k in anotadas]
            if not chaves:
                sem_anotacao.add(campo)
                continue
            campos[campo] = [
                _maiusculas(str(resposta[k])) for k in _FILIACAO if k in chaves and resposta.get(k)
            ]
            continue
        chave = next((k for k in _FONTES[campo] if k in anotadas), None)
        if chave is None:
            sem_anotacao.add(campo)
            continue
        bruto = resposta.get(chave)
        if bruto is None or str(bruto).strip() == "":
            continue  # anotado como ausente: null conhecido
        valor = str(bruto).strip()
        if campo in _DATAS:
            valor = normalizar_data(valor)
            if valor is None:
                sem_anotacao.add(campo)
                continue
        elif campo == "cpf":
            valor = normalizar_cpf(valor)
        elif campo in _MAIUSCULAS:
            valor = _maiusculas(valor)
        campos[campo] = valor
    return LinhaMapeada(tipo, campos, sem_anotacao)


def mapear_classe(tipo: str) -> LinhaMapeada:
    """Exemplo só de classificação (ADR-018): todos os campos pertinentes ficam fora da perda."""
    if tipo not in PERTINENTES:
        raise ValueError(f"tipo não suportado: {tipo!r}")
    campos: dict = {c: None for c in CAMPOS_CONTRATO}
    campos["filiacao"] = []
    return LinhaMapeada(tipo, campos, set(PERTINENTES[tipo]))
