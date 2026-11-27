"""Métricas de classificação e extração (T037).

Referências: RNF-SDD-04, RNF-SDD-10, Q-24, Q-27 e docs/domain/evaluation.md.
Acurácia, F1 macro e métricas por classe são calculadas apenas sobre os
documentos aceitos (não `indefinido`), sempre com a cobertura. A matriz de
confusão mantém as colunas `indefinido` e `nao_localizado`.
"""

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
from rapidfuzz.distance import Levenshtein
from sklearn.metrics import f1_score, precision_recall_fscore_support

from visiondoc.modelos import Caixa

INDEFINIDO = "indefinido"
NAO_LOCALIZADO = "nao_localizado"
CLASSES_TIPO = ["cnh", "rg", "cpf", "invoice", "outros"]
CLASSES_TIPO_FACE = [
    "cnh_ambas",
    "cnh_frente",
    "cnh_verso",
    "cpf_frente",
    "cpf_verso",
    "rg_ambas",
    "rg_frente",
    "rg_verso",
    "invoice",
    "outros",
]


@dataclass(frozen=True)
class MetricasClasse:
    precisao: float
    revocacao: float
    f1: float
    suporte: int


@dataclass
class ResultadoClassificacao:
    classes: list[str]
    colunas: list[str]
    total: int
    aceitos: int
    cobertura: float
    acuracia: float
    f1_macro: float
    por_classe: dict[str, MetricasClasse]
    matriz: np.ndarray
    matriz_normalizada: np.ndarray
    rejeicoes_por_classe: dict[str, int]
    pares_confundidos: list[tuple[str, str, int]]
    confusoes_de_outros: dict[str, int]
    espurios: dict[str, int] = field(default_factory=dict)
    ic_acuracia: tuple[float, float] | None = None
    ic_f1_macro: tuple[float, float] | None = None

    def resumo(self) -> dict:
        return {
            "total": self.total,
            "aceitos": self.aceitos,
            "cobertura": self.cobertura,
            "acuracia": self.acuracia,
            "f1_macro": self.f1_macro,
            "ic_acuracia": self.ic_acuracia,
            "ic_f1_macro": self.ic_f1_macro,
            "por_classe": {c: vars(m) for c, m in self.por_classe.items()},
            "colunas": self.colunas,
            "matriz": self.matriz.tolist(),
            "rejeicoes_por_classe": self.rejeicoes_por_classe,
            "pares_confundidos": [list(p) for p in self.pares_confundidos],
            "confusoes_de_outros": self.confusoes_de_outros,
            "espurios": self.espurios,
        }


def _acuracia_f1(ref: list[str], pred: list[str], classes: list[str]) -> tuple[float, float]:
    if not ref:
        return 0.0, 0.0
    acuracia = float(np.mean([a == b for a, b in zip(ref, pred)]))
    presentes = [c for c in classes if c in ref or c in pred]
    f1 = f1_score(ref, pred, labels=presentes, average="macro", zero_division=0)
    return acuracia, float(f1)


def avaliar_classificacao(
    referencias: list[str],
    previstas: list[str],
    classes: list[str],
    n_bootstrap: int = 1000,
    semente: int = 0,
    espurios: list[str] | None = None,
) -> ResultadoClassificacao:
    if len(referencias) != len(previstas):
        raise ValueError("referências e previsões com tamanhos diferentes")
    colunas = [*classes, INDEFINIDO, NAO_LOCALIZADO]
    indice = {c: i for i, c in enumerate(colunas)}
    matriz = np.zeros((len(classes), len(colunas)), dtype=int)
    for ref, pred in zip(referencias, previstas):
        matriz[indice[ref], indice[pred]] += 1
    somas = matriz.sum(axis=1, keepdims=True)
    normalizada = np.divide(matriz, somas, out=np.zeros_like(matriz, dtype=float), where=somas > 0)

    aceitos = [(r, p) for r, p in zip(referencias, previstas) if p != INDEFINIDO]
    ref_ac = [r for r, _ in aceitos]
    pred_ac = [p for _, p in aceitos]
    acuracia, f1_macro = _acuracia_f1(ref_ac, pred_ac, classes)
    precisao, revocacao, f1, suporte = (
        precision_recall_fscore_support(ref_ac, pred_ac, labels=classes, zero_division=0)
        if aceitos
        else ([0.0] * len(classes),) * 3 + ([0] * len(classes),)
    )
    por_classe = {
        c: MetricasClasse(float(precisao[i]), float(revocacao[i]), float(f1[i]), int(suporte[i]))
        for i, c in enumerate(classes)
    }

    pares = [
        (classes[i], colunas[j], int(matriz[i, j]))
        for i in range(len(classes))
        for j in range(len(classes))
        if i != j and matriz[i, j] > 0
    ]
    pares.sort(key=lambda p: -p[2])
    linha_outros = classes.index("outros") if "outros" in classes else None
    confusoes_outros = (
        {
            colunas[j]: int(matriz[linha_outros, j])
            for j in range(len(classes))
            if j != linha_outros and matriz[linha_outros, j] > 0
        }
        if linha_outros is not None
        else {}
    )

    ic_acuracia = ic_f1 = None
    if n_bootstrap and aceitos:
        gerador = np.random.default_rng(semente)
        amostras_ac, amostras_f1 = [], []
        n = len(aceitos)
        for _ in range(n_bootstrap):
            idx = gerador.integers(0, n, n)
            a, f = _acuracia_f1([ref_ac[i] for i in idx], [pred_ac[i] for i in idx], classes)
            amostras_ac.append(a)
            amostras_f1.append(f)
        ic_acuracia = tuple(float(v) for v in np.percentile(amostras_ac, [2.5, 97.5]))
        ic_f1 = tuple(float(v) for v in np.percentile(amostras_f1, [2.5, 97.5]))

    return ResultadoClassificacao(
        classes=classes,
        colunas=colunas,
        total=len(referencias),
        aceitos=len(aceitos),
        cobertura=len(aceitos) / len(referencias) if referencias else 0.0,
        acuracia=acuracia,
        f1_macro=f1_macro,
        por_classe=por_classe,
        matriz=matriz,
        matriz_normalizada=normalizada,
        rejeicoes_por_classe={c: int(matriz[i, indice[INDEFINIDO]]) for i, c in enumerate(classes)},
        pares_confundidos=pares,
        confusoes_de_outros=confusoes_outros,
        espurios=dict(Counter(espurios or [])),
        ic_acuracia=ic_acuracia,
        ic_f1_macro=ic_f1,
    )


def por_recorte(
    referencias: list[str],
    previstas: list[str],
    grupos: list[str],
    classes: list[str],
    **opcoes,
) -> dict[str, ResultadoClassificacao]:
    resultado = {"agregado": avaliar_classificacao(referencias, previstas, classes, **opcoes)}
    for grupo in sorted(set(grupos)):
        idx = [i for i, g in enumerate(grupos) if g == grupo]
        resultado[grupo] = avaliar_classificacao(
            [referencias[i] for i in idx], [previstas[i] for i in idx], classes, **opcoes
        )
    return resultado


def _iou(a: Caixa, b: Caixa) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersecao = max(0, x2 - x1) * max(0, y2 - y1)
    uniao = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersecao
    return intersecao / uniao if uniao > 0 else 0.0


def parear_documentos(
    referencias: list[tuple[Caixa, str]],
    previstos: list[tuple[Caixa, str]],
    limiar_iou: float = 0.5,
) -> tuple[list[tuple[str, str]], list[str]]:
    """Pareamento guloso por IoU (Q-27). Devolve pares (referência, prevista) e espúrios."""
    candidatos = sorted(
        (
            (_iou(r[0], p[0]), i, j)
            for i, r in enumerate(referencias)
            for j, p in enumerate(previstos)
        ),
        reverse=True,
    )
    par_de: dict[int, int] = {}
    usados: set[int] = set()
    for iou, i, j in candidatos:
        if iou < limiar_iou:
            break
        if i not in par_de and j not in usados:
            par_de[i] = j
            usados.add(j)
    pares = [
        (rotulo, previstos[par_de[i]][1] if i in par_de else NAO_LOCALIZADO)
        for i, (_, rotulo) in enumerate(referencias)
    ]
    espurios = [rotulo for j, (_, rotulo) in enumerate(previstos) if j not in usados]
    return pares, espurios


def curva_cobertura(
    referencias: list[str], previstas: list[str], confiancas: list[float], limiares: list[float]
) -> list[tuple[float, float, float]]:
    """(limiar, cobertura, acurácia dos aceitos) para cada limiar de rejeição (RN-004)."""
    curva = []
    for limiar in limiares:
        aceitos = [(r, p) for r, p, c in zip(referencias, previstas, confiancas) if c >= limiar]
        acuracia = float(np.mean([r == p for r, p in aceitos])) if aceitos else 0.0
        curva.append((limiar, len(aceitos) / len(referencias), acuracia))
    return curva


@dataclass(frozen=True)
class Calibracao:
    ece: float
    faixas: list[tuple[float, float, float | None, float | None, int]]


def calibracao(acertos: list[bool], confiancas: list[float], n_faixas: int = 10) -> Calibracao:
    """Erro de calibração esperado (ECE) e faixas para o diagrama de confiabilidade."""
    limites = np.linspace(0, 1, n_faixas + 1)
    total = len(acertos)
    ece, faixas = 0.0, []
    for k in range(n_faixas):
        inf, sup = limites[k], limites[k + 1]
        idx = [i for i, c in enumerate(confiancas) if (inf < c <= sup) or (k == 0 and c == 0)]
        if idx:
            conf = float(np.mean([confiancas[i] for i in idx]))
            acc = float(np.mean([acertos[i] for i in idx]))
            ece += len(idx) / total * abs(acc - conf)
            faixas.append((float(inf), float(sup), conf, acc, len(idx)))
        else:
            faixas.append((float(inf), float(sup), None, None, 0))
    return Calibracao(float(ece), faixas)


@dataclass(frozen=True)
class MetricasCampo:
    acerto_exato: float
    precisao: float
    revocacao: float
    f1: float
    precisao_caracteres: float


@dataclass(frozen=True)
class ResultadoExtracao:
    precisao_caracteres: float  # 1 - CER agregado (meta de 90%, Q-24)
    por_campo: dict[str, MetricasCampo]

    def resumo(self) -> dict:
        return {
            "precisao_caracteres": self.precisao_caracteres,
            "por_campo": {c: vars(m) for c, m in self.por_campo.items()},
        }


def avaliar_extracao(referencias: list[dict], previstos: list[dict]) -> ResultadoExtracao:
    campos = sorted({c for d in referencias + previstos for c in d})
    total_dist = total_len = 0
    por_campo = {}
    for campo in campos:
        vp = fp = fn = exatos = com_ref = 0
        dist = comp = 0
        for ref_d, pred_d in zip(referencias, previstos):
            ref = (ref_d.get(campo) or "").strip()
            pred = (pred_d.get(campo) or "").strip()
            if ref:
                com_ref += 1
                exatos += ref == pred
                dist += Levenshtein.distance(pred, ref)
                comp += len(ref)
            if ref and pred == ref:
                vp += 1
            else:
                fp += bool(pred)
                fn += bool(ref)
        precisao = vp / (vp + fp) if vp + fp else 0.0
        revocacao = vp / (vp + fn) if vp + fn else 0.0
        f1 = 2 * precisao * revocacao / (precisao + revocacao) if precisao + revocacao else 0.0
        por_campo[campo] = MetricasCampo(
            exatos / com_ref if com_ref else 0.0,
            precisao,
            revocacao,
            f1,
            max(0.0, 1 - dist / comp) if comp else 0.0,
        )
        total_dist += dist
        total_len += comp
    geral = max(0.0, 1 - total_dist / total_len) if total_len else 0.0
    return ResultadoExtracao(geral, por_campo)
