"""Converte o rótulo nativo do br-doc-extraction para o contrato da saída do VLM.

Dentro do mesmo tipo as chaves do rótulo variam por linha (ex.: ``nome``, ``nome_completo`` ou
``titular``); as tabelas abaixo listam os sinônimos em ordem de prioridade.
"""

import json

from visiondoc.treino.esquema import Campos, Documento, SaidaVLM

BBOX_IMAGEM_INTEIRA = [0, 0, 1000, 1000]

# campo do contrato -> chaves do rótulo, da mais para a menos prioritária
CHAVES: dict[str, dict[str, tuple[str, ...]]] = {
    "cnh": {
        "nome": ("nome_completo", "nome", "titular"),
        "cpf": ("cpf",),
        "numero_documento": ("num_registro", "doc_identidade"),
        "data_nascimento": ("data_nascimento",),
        "data_emissao": ("data_emissao",),
        "data_validade": ("data_validade",),
        "categoria_habilitacao": ("categoria_habilitacao",),
    },
    "rg": {
        "nome": ("nome_completo",),
        "cpf": ("cpf",),
        "numero_documento": ("registro_geral", "rg_numero"),
        "data_nascimento": ("data_nascimento",),
        "data_emissao": ("data_expedicao",),
        "orgao_emissor": ("orgao_emissor",),
        "naturalidade": ("naturalidade", "local_nascimento"),
        "doc_origem": ("doc_origem",),
    },
}
CHAVES_FILIACAO = ("filiacao_pai", "filiacao_mae")


def _texto(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _valor(rotulo: dict, chaves: tuple[str, ...]) -> tuple[bool, str | None]:
    """(alguma chave presente, primeiro valor não vazio por prioridade)."""
    presente = False
    for chave in chaves:
        if chave in rotulo:
            presente = True
            texto = _texto(rotulo[chave])
            if texto is not None:
                return True, texto
    return presente, None


def converter_rotulo(tipo: str, response: str) -> SaidaVLM | None:
    """Rótulo nativo -> SaidaVLM de um documento; None se o rótulo não for utilizável."""
    if tipo not in ("cnh", "rg", "invoice"):
        return None
    try:
        rotulo = json.loads(response)
    except (TypeError, ValueError):
        return None
    if not isinstance(rotulo, dict):
        return None

    valores: dict[str, object] = {}
    if tipo != "invoice":
        for campo, chaves in CHAVES[tipo].items():
            presente, texto = _valor(rotulo, chaves)
            if presente:
                valores[campo] = texto
        filiacao = [t for t in (_texto(rotulo.get(c)) for c in CHAVES_FILIACAO) if t]
        if filiacao:
            valores["filiacao"] = filiacao

    documento = Documento(
        tipo="outros" if tipo == "invoice" else tipo,
        face=None,
        bbox=list(BBOX_IMAGEM_INTEIRA),
        campos=Campos(**valores),
    )
    return SaidaVLM(documentos=[documento])


def serializar_alvo(saida: SaidaVLM) -> str:
    """JSON compacto só com as chaves definidas explicitamente (ausente != null)."""
    return saida.model_dump_json(exclude_unset=True)
