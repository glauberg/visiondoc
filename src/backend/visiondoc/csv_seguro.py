"""Higienização e neutralização de valores para CSV (RN-014, RN-015, RN-017, CSV-SEC-01)."""

import unicodedata

from visiondoc.modelos import Caixa

_PREFIXOS_FORMULA = ("=", "+", "-", "@", "\t", "\r")
_QUEBRAS_COMO_ESPACO = {"\n", "\r", "\t"}


def higienizar(valor: str, preservar_quebras: bool = False) -> str:
    """NFC, sem caracteres de controle (Cc) nem de formatação (Cf).

    Quebras de linha só são preservadas quando pedido (inteiro teor).
    """
    texto = unicodedata.normalize("NFC", valor)
    if preservar_quebras:
        texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    saida = []
    for c in texto:
        categoria = unicodedata.category(c)
        if c == "\n" and preservar_quebras:
            saida.append(c)
        elif c in _QUEBRAS_COMO_ESPACO:
            saida.append(" ")
        elif categoria in ("Cc", "Cf"):
            continue
        else:
            saida.append(c)
    return "".join(saida)


def neutralizar(valor: str) -> str:
    """Prefixa apóstrofo em valores que planilhas interpretariam como fórmula."""
    return "'" + valor if valor.startswith(_PREFIXOS_FORMULA) else valor


def preparar_texto(valor: str, limite: int | None = None, preservar_quebras: bool = False) -> str:
    texto = neutralizar(higienizar(valor, preservar_quebras))
    return texto[:limite] if limite is not None else texto


def formatar_caixa(caixa: Caixa | None) -> str | None:
    return None if caixa is None else ";".join(str(int(v)) for v in caixa)
