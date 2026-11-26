"""Relatório por treinamento: Markdown, gráficos PNG e metricas.json (T039, RF-SDD-18).

Gerado ao fim de cada treinamento concluído e de cada avaliação da linha de
base. Não registra nome de máquina, usuário, caminhos locais nem credenciais.
"""

import json
import os
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from importlib import metadata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from visiondoc.avaliacao.metricas import (
    Calibracao,
    ResultadoClassificacao,
    ResultadoExtracao,
)

META_TEMPO_PAGINA_S = 30.0  # RNF-SDD-09, indicador reportado
META_MEMORIA_GB = 7.5
_PACOTES = [
    "torch",
    "transformers",
    "peft",
    "trl",
    "bitsandbytes",
    "vllm",
    "paddleocr",
    "paddlepaddle",
    "llm-guard",
    "scikit-learn",
    "visiondoc",
]


@dataclass(frozen=True)
class Execucao:
    id: str
    inicio: str
    fim: str
    versao_pipeline: str
    versao_config: str
    semente: int
    mlflow_id: str | None
    commit: str | None
    alteracoes_pendentes: bool | None
    tipo: str  # lora ou zero-shot


@dataclass(frozen=True)
class InfoModelo:
    base: str
    revisao: str | None
    parametros_totais: int
    parametros_treinaveis: int
    quantizacao_treino: str | None
    quantizacao_inferencia: str
    lora: dict
    modulos_alvo: int
    tamanho_adaptador_bytes: int | None
    max_model_len: int
    lado_max_imagem: int


@dataclass(frozen=True)
class InfoDados:
    particoes: dict[str, dict[str, dict[str, int]]]  # dataset -> partição -> classe -> n
    aumentos: list[str]
    semente_particao: int | None  # None: partições do próprio dataset


@dataclass(frozen=True)
class InfoTreino:
    hiperparametros: dict
    tempo_total_s: float
    exemplos_por_s: float
    pico_memoria_gb: float
    curva_perda: list[tuple[int, float | None, float | None]]


@dataclass(frozen=True)
class InfoInferencia:
    tempo_carga_s: float
    tempos_pagina_s: list[float]
    tempos_por_etapa: dict[str, list[float]]
    pico_memoria_gb: float
    tokens_medios: float
    taxa_json_valido: float


@dataclass
class Avaliacao:
    classificacao: dict[str, dict[str, ResultadoClassificacao]]
    curva_cobertura: list[tuple[float, float, float]]
    calibracao: Calibracao
    extracao: dict[str, ResultadoExtracao]
    taxa_campos_sem_respaldo: float
    extras: dict = field(default_factory=dict)


# --- ambiente ------------------------------------------------------------------


def _versao(pacote: str) -> str:
    try:
        return metadata.version(pacote)
    except metadata.PackageNotFoundError:
        return "não instalado"


def _gpu() -> dict | None:
    try:
        import torch

        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            return {
                "modelo": p.name,
                "memoria_gb": round(p.total_memory / 1024**3, 2),
                "compute_capability": f"{p.major}.{p.minor}",
                "cuda": torch.version.cuda,
                "driver": None,
            }
    except Exception:  # noqa: BLE001
        return _gpu_nvidia_smi()
    return _gpu_nvidia_smi()


def _gpu_nvidia_smi() -> dict | None:
    try:
        saida = (
            subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,compute_cap,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            .stdout.strip()
            .splitlines()[0]
        )
        nome, memoria, cc, driver = (v.strip() for v in saida.split(","))
        return {
            "modelo": nome,
            "memoria_gb": round(float(memoria) / 1024, 2),
            "compute_capability": cc,
            "cuda": None,
            "driver": driver,
        }
    except Exception:  # noqa: BLE001
        return None


def _ram_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().total / 1024**3, 1)
    except ImportError:
        psutil = None  # sem psutil: tenta sysconf (POSIX)
    if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3, 1)
    return None


def coletar_ambiente() -> dict:
    """Ambiente técnico, sem nome de máquina, usuário ou caminhos."""
    return {
        "gpu": _gpu(),
        "cpu": {"modelo": platform.processor() or platform.machine(), "nucleos": os.cpu_count()},
        "ram_gb": _ram_gb(),
        "sistema": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "pacotes": {p: _versao(p) for p in _PACOTES},
    }


def commit_atual() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        pendentes = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
        return commit, bool(pendentes)
    except Exception:  # noqa: BLE001
        return None, None


# --- formatação ----------------------------------------------------------------


def _n(valor, casas: int = 3) -> str:
    if valor is None:
        return "—"
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".")
    return f"{valor:.{casas}f}".replace(".", ",")


def _delta(atual, anterior) -> str:
    if atual is None or anterior is None:
        return "—"
    return f"{atual - anterior:+.3f}".replace(".", ",")


def _tabela(cabecalho: list[str], linhas: list[list]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def _json_padrao(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(type(obj).__name__)


# --- gráficos ------------------------------------------------------------------


def _salvar(figura, destino: Path) -> None:
    figura.tight_layout()
    figura.savefig(destino, dpi=120)
    plt.close(figura)


def _grafico_matriz(r: ResultadoClassificacao, normalizada: bool, titulo: str, destino: Path):
    dados = r.matriz_normalizada if normalizada else r.matriz
    figura, eixo = plt.subplots(figsize=(1.0 + 0.9 * len(r.colunas), 1.0 + 0.7 * len(r.classes)))
    imagem = eixo.imshow(dados, cmap="Blues", vmin=0, vmax=1 if normalizada else None)
    eixo.set_xticks(range(len(r.colunas)), r.colunas, rotation=45, ha="right")
    eixo.set_yticks(range(len(r.classes)), r.classes)
    eixo.set_xlabel("Prevista")
    eixo.set_ylabel("Referência")
    eixo.set_title(titulo)
    limite = dados.max() / 2 if dados.size else 0
    for i in range(dados.shape[0]):
        for j in range(dados.shape[1]):
            texto = f"{dados[i, j]:.2f}" if normalizada else str(int(dados[i, j]))
            eixo.text(
                j,
                i,
                texto,
                ha="center",
                va="center",
                fontsize=8,
                color="white" if dados[i, j] > limite else "black",
            )
    figura.colorbar(imagem, ax=eixo, fraction=0.046)
    _salvar(figura, destino)


# --- relatório -----------------------------------------------------------------


def gerar_relatorio(
    diretorio_base: str | Path,
    execucao: Execucao,
    ambiente: dict,
    modelo: InfoModelo,
    dados: InfoDados,
    treino: InfoTreino | None,
    inferencia: InfoInferencia,
    avaliacao: Avaliacao,
    linha_base: dict | None = None,
    anterior: dict | None = None,
) -> Path:
    destino = Path(diretorio_base) / f"{execucao.inicio[:10]}-{execucao.id}"
    graficos = destino / "graficos"
    graficos.mkdir(parents=True, exist_ok=True)
    md: list[str] = [f"# Relatório de treinamento {execucao.id}", ""]

    # Identificação
    md += [
        "## Identificação",
        "",
        _tabela(
            ["Item", "Valor"],
            [
                ["Tipo de execução", execucao.tipo],
                ["Início", execucao.inicio],
                ["Fim", execucao.fim],
                ["Commit", execucao.commit or "—"],
                [
                    "Alterações não commitadas",
                    {True: "sim", False: "não", None: "—"}[execucao.alteracoes_pendentes],
                ],
                ["versao_pipeline", execucao.versao_pipeline],
                ["Configuração", execucao.versao_config],
                ["Semente", execucao.semente],
                ["Execução no MLflow", execucao.mlflow_id or "—"],
            ],
        ),
        "",
    ]

    # Ambiente
    gpu = ambiente.get("gpu") or {}
    md += [
        "## Ambiente",
        "",
        _tabela(
            ["Item", "Valor"],
            [
                ["GPU", gpu.get("modelo", "indisponível")],
                ["Memória da GPU (GB)", _n(gpu.get("memoria_gb"), 1)],
                ["Compute capability", gpu.get("compute_capability", "—")],
                ["Driver / CUDA", f"{gpu.get('driver') or '—'} / {gpu.get('cuda') or '—'}"],
                ["CPU", f"{ambiente['cpu']['modelo']} ({ambiente['cpu']['nucleos']} núcleos)"],
                ["RAM (GB)", _n(ambiente.get("ram_gb"), 1)],
                ["Sistema", ambiente["sistema"]],
                ["Python", ambiente["python"]],
            ],
        ),
        "",
        _tabela(["Pacote", "Versão"], [[p, v] for p, v in ambiente["pacotes"].items()]),
        "",
    ]

    # Modelo
    percentual = 100 * modelo.parametros_treinaveis / modelo.parametros_totais
    md += [
        "## Modelo",
        "",
        _tabela(
            ["Item", "Valor"],
            [
                ["Modelo base", f"{modelo.base} ({modelo.revisao or 'revisão não informada'})"],
                ["Parâmetros totais", _n(modelo.parametros_totais)],
                [
                    "Parâmetros treináveis (LoRA)",
                    f"{_n(modelo.parametros_treinaveis)} ({_n(percentual, 2)}%)",
                ],
                ["Quantização no ajuste", modelo.quantizacao_treino or "—"],
                ["Quantização na inferência", modelo.quantizacao_inferencia],
                ["LoRA", ", ".join(f"{k}={v}" for k, v in modelo.lora.items())],
                ["Módulos-alvo", modelo.modulos_alvo],
                [
                    "Tamanho do adaptador (MB)",
                    _n(modelo.tamanho_adaptador_bytes / 1024**2, 1)
                    if modelo.tamanho_adaptador_bytes
                    else "—",
                ],
                ["Contexto máximo (tokens)", modelo.max_model_len],
                ["Lado máximo da imagem (px)", modelo.lado_max_imagem],
            ],
        ),
        "",
    ]

    # Dados
    totais = {}
    linhas_dados = []
    for dataset, particoes in dados.particoes.items():
        for particao, classes in particoes.items():
            n = sum(classes.values())
            totais[particao] = totais.get(particao, 0) + n
            linhas_dados.append([dataset, particao, _n(n)])
    linhas_dados += [["total", p, _n(n)] for p, n in totais.items()]
    md += [
        "## Dados",
        "",
        _tabela(["Dataset", "Partição", "Documentos"], linhas_dados),
        "",
        (
            f"Aumentos: {', '.join(dados.aumentos) or 'nenhum'}. Particionamento: "
            + (
                f"semente {dados.semente_particao}."
                if dados.semente_particao is not None
                else "partições do próprio dataset."
            )
        ),
        "",
    ]
    classes = sorted({c for p in dados.particoes.values() for d in p.values() for c in d})
    figura, eixo = plt.subplots(figsize=(8, 4))
    largura = 0.8 / max(1, len(totais))
    for k, particao in enumerate(totais):
        contagens = [
            sum(p.get(particao, {}).get(c, 0) for p in dados.particoes.values()) for c in classes
        ]
        eixo.bar(np.arange(len(classes)) + k * largura, contagens, largura, label=particao)
    eixo.set_xticks(
        np.arange(len(classes)) + largura * (len(totais) - 1) / 2, classes, rotation=45, ha="right"
    )
    eixo.set_ylabel("Documentos")
    eixo.set_title("Distribuição por classe e partição")
    eixo.legend()
    _salvar(figura, graficos / "dados_distribuicao.png")
    md += ["![Distribuição por classe](graficos/dados_distribuicao.png)", ""]

    # Treinamento
    md += ["## Treinamento", ""]
    if treino is None:
        md += ["Execução sem treinamento (linha de base).", ""]
    else:
        md += [
            _tabela(
                ["Item", "Valor"],
                [
                    *[[k, v] for k, v in treino.hiperparametros.items()],
                    ["Tempo total (s)", _n(treino.tempo_total_s, 1)],
                    ["Exemplos por segundo", _n(treino.exemplos_por_s, 2)],
                    ["Pico de memória da GPU (GB)", _n(treino.pico_memoria_gb, 2)],
                ],
            ),
            "",
        ]
        figura, eixo = plt.subplots(figsize=(7, 4))
        for indice, rotulo in ((1, "treino"), (2, "validação")):
            pontos = [(p[0], p[indice]) for p in treino.curva_perda if p[indice] is not None]
            if pontos:
                eixo.plot(*zip(*pontos), marker="o", label=rotulo)
        eixo.set_xlabel("Passo")
        eixo.set_ylabel("Perda")
        eixo.set_title("Curvas de perda")
        eixo.legend()
        _salvar(figura, graficos / "treino_perda.png")
        md += ["![Curvas de perda](graficos/treino_perda.png)", ""]

    # Inferência
    tempos = np.array(inferencia.tempos_pagina_s, dtype=float)
    resumo_inf = {
        "tempo_carga_s": inferencia.tempo_carga_s,
        "tempo_medio_pagina_s": float(tempos.mean()),
        "tempo_mediano_pagina_s": float(np.median(tempos)),
        "tempo_p95_pagina_s": float(np.percentile(tempos, 95)),
        "tempo_maximo_pagina_s": float(tempos.max()),
        "tempo_medio_por_etapa_s": {
            k: float(np.mean(v)) for k, v in inferencia.tempos_por_etapa.items() if v
        },
        "pico_memoria_gb": inferencia.pico_memoria_gb,
        "tokens_medios": inferencia.tokens_medios,
        "taxa_json_valido": inferencia.taxa_json_valido,
        "metas": {
            "tempo_pagina_s": META_TEMPO_PAGINA_S,
            "memoria_gb": META_MEMORIA_GB,
            "tempo_atendido": bool(tempos.mean() <= META_TEMPO_PAGINA_S),
            "memoria_atendida": bool(inferencia.pico_memoria_gb <= META_MEMORIA_GB),
        },
    }
    sim_nao = {True: "atendida", False: "não atendida"}
    md += [
        "## Inferência e desempenho",
        "",
        _tabela(
            ["Item", "Valor"],
            [
                ["Tempo de carga (s)", _n(inferencia.tempo_carga_s, 1)],
                [
                    "Tempo por página: média / mediana / p95 / máximo (s)",
                    " / ".join(
                        _n(resumo_inf[k], 2)
                        for k in (
                            "tempo_medio_pagina_s",
                            "tempo_mediano_pagina_s",
                            "tempo_p95_pagina_s",
                            "tempo_maximo_pagina_s",
                        )
                    ),
                ],
                *[
                    [f"Tempo médio da etapa {k} (s)", _n(v, 2)]
                    for k, v in resumo_inf["tempo_medio_por_etapa_s"].items()
                ],
                ["Pico de memória da GPU (GB)", _n(inferencia.pico_memoria_gb, 2)],
                ["Tokens gerados por página (média)", _n(inferencia.tokens_medios, 1)],
                ["JSON válido no contrato", _n(inferencia.taxa_json_valido, 3)],
            ],
        ),
        "",
        (
            "Metas de desempenho (RNF-SDD-09), reportadas como indicador, sem efeito eliminatório: "
            f"até 30 s por página ({sim_nao[resumo_inf['metas']['tempo_atendido']]}) e até "
            f"7,5 GB de memória de GPU ({sim_nao[resumo_inf['metas']['memoria_atendida']]})."
        ),
        "",
    ]
    figura, eixo = plt.subplots(figsize=(7, 4))
    eixo.hist(tempos, bins=min(20, max(5, len(tempos))))
    eixo.axvline(META_TEMPO_PAGINA_S, color="red", linestyle="--", label="meta de 30 s")
    eixo.set_xlabel("Segundos por página")
    eixo.set_ylabel("Páginas")
    eixo.set_title("Tempo por página")
    eixo.legend()
    _salvar(figura, graficos / "inferencia_tempos.png")
    md += ["![Tempo por página](graficos/inferencia_tempos.png)", ""]

    # Classificação
    md += [
        "## Classificação",
        "",
        (
            "Acurácia, F1 macro e métricas por classe sobre os documentos aceitos; a cobertura é "
            "a fração aceita (não `indefinido`). IC de 95% por *bootstrap*."
        ),
        "",
    ]
    resumo_cls = {}
    for nivel, recortes in avaliacao.classificacao.items():
        resumo_cls[nivel] = {}
        md += [
            f"### Nível: {nivel}",
            "",
            _tabela(
                ["Recorte", "Documentos", "Cobertura", "Acurácia", "IC 95%", "F1 macro", "IC 95%"],
                [
                    [
                        recorte,
                        r.total,
                        _n(r.cobertura),
                        _n(r.acuracia),
                        f"{_n(r.ic_acuracia[0])}–{_n(r.ic_acuracia[1])}" if r.ic_acuracia else "—",
                        _n(r.f1_macro),
                        f"{_n(r.ic_f1_macro[0])}–{_n(r.ic_f1_macro[1])}" if r.ic_f1_macro else "—",
                    ]
                    for recorte, r in recortes.items()
                ],
            ),
            "",
        ]
        for recorte, r in recortes.items():
            resumo_cls[nivel][recorte] = r.resumo()
            md += [
                f"#### {nivel} / {recorte}",
                "",
                _tabela(
                    ["Classe", "Precisão", "Revocação", "F1", "Suporte", "Rejeições"],
                    [
                        [
                            c,
                            _n(m.precisao),
                            _n(m.revocacao),
                            _n(m.f1),
                            m.suporte,
                            r.rejeicoes_por_classe[c],
                        ]
                        for c, m in r.por_classe.items()
                    ],
                ),
                "",
            ]
            pares = ", ".join(f"{a} → {b} ({n})" for a, b, n in r.pares_confundidos[:5])
            md += [
                (
                    f"Pares mais confundidos: {pares or 'nenhum'}. "
                    f"Documentos `outros` classificados como identidade: "
                    f"{r.confusoes_de_outros or 'nenhum'}. Espúrios: {r.espurios or 'nenhum'}."
                ),
                "",
            ]
            for normalizada, sufixo in ((False, "absoluta"), (True, "normalizada")):
                nome = f"matriz_{nivel}_{recorte}_{sufixo}.png".replace(" ", "_")
                _grafico_matriz(
                    r, normalizada, f"Matriz {sufixo}: {nivel} / {recorte}", graficos / nome
                )
                md += [f"![Matriz de confusão {sufixo}](graficos/{nome})"]
            md += [""]

    _limiares, coberturas, acuracias = zip(*avaliacao.curva_cobertura)
    figura, eixo = plt.subplots(figsize=(6, 4))
    eixo.plot(coberturas, acuracias, marker="o")
    for lim, cob, acc in avaliacao.curva_cobertura:
        eixo.annotate(_n(lim, 2), (cob, acc), fontsize=7)
    eixo.set_xlabel("Cobertura")
    eixo.set_ylabel("Acurácia dos aceitos")
    eixo.set_title("Cobertura × acurácia por limiar de rejeição")
    _salvar(figura, graficos / "cobertura_acuracia.png")
    faixas = [f for f in avaliacao.calibracao.faixas if f[4]]
    figura, eixo = plt.subplots(figsize=(5, 5))
    eixo.plot([0, 1], [0, 1], linestyle="--", color="gray")
    if faixas:
        eixo.bar([f[2] for f in faixas], [f[3] for f in faixas], width=0.08, alpha=0.7)
    eixo.set_xlabel("Confiança média")
    eixo.set_ylabel("Acurácia")
    eixo.set_title(f"Diagrama de confiabilidade (ECE = {_n(avaliacao.calibracao.ece)})")
    _salvar(figura, graficos / "confiabilidade.png")
    md += [
        "### Rejeição e calibração",
        "",
        "![Cobertura × acurácia](graficos/cobertura_acuracia.png)",
        "![Diagrama de confiabilidade](graficos/confiabilidade.png)",
        "",
    ]

    # Extração
    md += [
        "## Extração",
        "",
        _tabela(
            ["Dataset", "1 − CER", "Meta de 90%"],
            [
                [
                    d,
                    _n(r.precisao_caracteres),
                    "atendida" if r.precisao_caracteres >= 0.9 else "não atendida",
                ]
                for d, r in avaliacao.extracao.items()
            ],
        ),
        "",
        f"Taxa de campos sem respaldo: {_n(avaliacao.taxa_campos_sem_respaldo)}.",
        "",
    ]
    for dataset, r in avaliacao.extracao.items():
        md += [
            f"### {dataset}",
            "",
            _tabela(
                ["Campo", "Acerto exato", "Precisão", "Revocação", "F1", "1 − CER"],
                [
                    [
                        c,
                        _n(m.acerto_exato),
                        _n(m.precisao),
                        _n(m.revocacao),
                        _n(m.f1),
                        _n(m.precisao_caracteres),
                    ]
                    for c, m in r.por_campo.items()
                ],
            ),
            "",
        ]

    metricas = {
        "execucao": asdict(execucao),
        "ambiente": ambiente,
        "modelo": {**asdict(modelo), "percentual_treinavel": round(percentual, 4)},
        "dados": {
            "particoes": dados.particoes,
            "totais": totais,
            "aumentos": dados.aumentos,
            "semente_particao": dados.semente_particao,
        },
        "treino": asdict(treino) if treino else None,
        "inferencia": resumo_inf,
        "classificacao": resumo_cls,
        "curva_cobertura": [list(p) for p in avaliacao.curva_cobertura],
        "calibracao": {
            "ece": avaliacao.calibracao.ece,
            "faixas": [list(f) for f in avaliacao.calibracao.faixas],
        },
        "extracao": {d: r.resumo() for d, r in avaliacao.extracao.items()},
        "taxa_campos_sem_respaldo": avaliacao.taxa_campos_sem_respaldo,
        **avaliacao.extras,
    }

    # Comparação
    md += ["## Comparação", ""]
    referencias = [
        (n, m) for n, m in (("Linha de base", linha_base), ("Execução anterior", anterior)) if m
    ]
    if not referencias:
        md += ["Sem linha de base nem execução anterior informadas.", ""]
    else:
        indicadores = [
            (
                "Acurácia (tipo, agregado)",
                lambda m: m["classificacao"].get("tipo", {}).get("agregado", {}).get("acuracia"),
            ),
            (
                "F1 macro (tipo, agregado)",
                lambda m: m["classificacao"].get("tipo", {}).get("agregado", {}).get("f1_macro"),
            ),
            (
                "Cobertura (tipo, agregado)",
                lambda m: m["classificacao"].get("tipo", {}).get("agregado", {}).get("cobertura"),
            ),
            *[
                (
                    f"1 − CER ({d})",
                    lambda m, d=d: m["extracao"].get(d, {}).get("precisao_caracteres"),
                )
                for d in avaliacao.extracao
            ],
            ("Tempo médio por página (s)", lambda m: m["inferencia"]["tempo_medio_pagina_s"]),
            ("Pico de memória na inferência (GB)", lambda m: m["inferencia"]["pico_memoria_gb"]),
        ]
        cabecalho = ["Indicador", "Esta execução"]
        for nome, _ in referencias:
            cabecalho += [nome, "Diferença"]
        linhas = []
        for rotulo, extrair in indicadores:
            atual = extrair(metricas)
            linha = [rotulo, _n(atual)]
            for _, ref in referencias:
                valor = extrair(ref)
                linha += [_n(valor), _delta(atual, valor)]
            linhas.append(linha)
        md += [_tabela(cabecalho, linhas), ""]

    (destino / "relatorio.md").write_text("\n".join(md), encoding="utf-8")
    (destino / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2, default=_json_padrao), encoding="utf-8"
    )
    return destino
