"""Métricas provisórias do teste do adaptador (até a T037 existir)."""

CLASSES = ("cnh", "rg", "outros")


def _classe(rotulo: str) -> str:
    return rotulo if rotulo in CLASSES else "outros"


def acuracia_tipo(previstos: list[str], reais: list[str]) -> float:
    if not reais:
        return 0.0
    return sum(_classe(p) == _classe(r) for p, r in zip(previstos, reais)) / len(reais)


def matriz_confusao(previstos: list[str], reais: list[str]) -> list[list[int]]:
    """Linhas = classe real, colunas = classe prevista, na ordem de CLASSES."""
    matriz = [[0] * len(CLASSES) for _ in CLASSES]
    for p, r in zip(previstos, reais):
        matriz[CLASSES.index(_classe(r))][CLASSES.index(_classe(p))] += 1
    return matriz


def f1_macro(previstos: list[str], reais: list[str]) -> float:
    matriz = matriz_confusao(previstos, reais)
    notas = []
    for i in range(len(CLASSES)):
        tp = matriz[i][i]
        fn = sum(matriz[i]) - tp
        fp = sum(linha[i] for linha in matriz) - tp
        if tp + fn + fp == 0:  # classe sem exemplos reais nem previsões
            continue
        notas.append(2 * tp / (2 * tp + fp + fn))
    return sum(notas) / len(notas) if notas else 0.0


def _normalizar(valor: object) -> object:
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _vazio(valor: object) -> bool:
    return valor is None or valor == []


def acerto_por_campo(previsto: dict, real: dict) -> dict:
    """Compara os ``campos`` de uma página.

    ``rotulados``: acerto exato (após strip) só nos campos que o rótulo traz; ``extras``:
    campos previstos com valor que o rótulo omite (não contam como erro nem como acerto).
    """
    rotulados = {}
    for campo, esperado in real.items():
        obtido = _normalizar(previsto.get(campo))
        esperado = _normalizar(esperado)
        rotulados[campo] = (_vazio(obtido) and _vazio(esperado)) or obtido == esperado
    extras = [c for c, v in previsto.items() if c not in real and not _vazio(_normalizar(v))]
    return {"rotulados": rotulados, "extras": extras}
