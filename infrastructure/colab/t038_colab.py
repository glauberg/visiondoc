#!/usr/bin/env python
"""Execução da T038 (treino do adaptador LoRA) no ambiente Python do Google Colab.

Dataset: imagens já preparadas do `tech4humans/br-doc-extraction` no Google Drive
(`cache/MANIFESTO.JSONL` e `cache/imagens/`), com as classes CNH, RG e INVOICE
indicadas no manifesto (ADR-019). A divisão é 70-15-15, estratificada por classe
e com a semente de config/treino.yaml, sobre todas as imagens válidas (a
partição original do manifesto é ignorada). Treino só de classificação. As
imagens já passaram pela preparação; o PaddleOCR não é usado nem instalado.

Uso, em células do Colab:

    from google.colab import drive
    drive.mount("/content/drive")
    !git clone https://github.com/glauberg/visiondoc.git /content/visiondoc
    !python /content/visiondoc/infrastructure/colab/t038_colab.py --etapa tudo --por-classe 20

Etapas (`--etapa`):
  verificar  Python, GPU com bfloat16, espaço em disco, Google Drive e o manifesto
  instalar   instala o pacote com o extra `treino`
  preparar   divide as imagens em 70-15-15, grava particoes.csv e o cache de treino
  treinar    linha de base zero-shot, treino QLoRA e relatórios (RF-SDD-18)
  tudo       todas as anteriores; preparar e treinar rodam em processos separados

Saídas (logs, gráficos, JSON e CSV): /content/drive/MyDrive/visiondoc/logs.
Cache de treino (só o manifesto; as imagens ficam na fonte) e adaptador treinado:
/content/drive/MyDrive/visiondoc/treino.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DRIVE = Path("/content/drive/MyDrive")
BASE_DRIVE = DRIVE / "visiondoc"
DADOS_PADRAO = BASE_DRIVE / "cache"
SAIDAS_PADRAO = BASE_DRIVE / "logs"
ETAPAS = ("verificar", "instalar", "preparar", "treinar", "tudo")
CLASSES = ("cnh", "rg", "invoice")
TIPOS_MANIFESTO = {"cnh": "cnh", "rg": "rg", "invoice": "invoice", "outros": "invoice"}
PYTHON_ACEITO = ((3, 12), (3, 13))  # requires-python do pyproject.toml
CC_MINIMA = 8.0  # bfloat16 (L4, A100); a T4 (7.5) não atende
ESPACO_MINIMO_GB = 30.0  # pesos do modelo, adaptador e checkpoints

_log: Path | None = None


@dataclass(frozen=True)
class Gpu:
    nome: str
    memoria_gb: float
    compute_capability: float
    driver: str


def argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Executa a T038 no Google Colab.")
    p.add_argument("--etapa", choices=ETAPAS, default="tudo")
    p.add_argument(
        "--dados",
        type=Path,
        default=DADOS_PADRAO,
        help="diretório com MANIFESTO.JSONL e a subpasta imagens/",
    )
    p.add_argument("--saidas", type=Path, default=SAIDAS_PADRAO, help="logs, gráficos, JSON e CSV")
    p.add_argument(
        "--base", type=Path, default=BASE_DRIVE / "treino", help="cache de treino e adaptador"
    )
    p.add_argument(
        "--por-classe",
        type=int,
        default=None,
        help="prepara só N imagens por classe em cada partição (execução curta)",
    )
    p.add_argument(
        "--limite-treino",
        type=int,
        default=None,
        help="usa só os N primeiros exemplos preparados de train",
    )
    p.add_argument(
        "--limite-teste",
        type=int,
        default=None,
        help="usa só os N primeiros exemplos preparados de test",
    )
    p.add_argument(
        "--sem-zero-shot",
        dest="zero_shot",
        action="store_false",
        help="não avalia a linha de base zero-shot",
    )
    p.add_argument(
        "--ignorar-condicoes",
        action="store_true",
        help="segue mesmo se a verificação apontar problemas",
    )
    return p.parse_args(argv)


# --- verificação ---------------------------------------------------------------


def ler_gpu(saida: str) -> Gpu | None:
    """Lê a primeira linha de `nvidia-smi --query-gpu=name,memory.total,compute_cap,driver_version`."""
    linhas = [linha for linha in saida.strip().splitlines() if linha.strip()]
    if not linhas:
        return None
    nome, memoria, cc, driver = (v.strip() for v in linhas[0].split(","))
    return Gpu(nome, round(float(memoria) / 1024, 2), float(cc), driver)


def consultar_gpu() -> Gpu | None:
    try:
        saida = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,compute_cap,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return ler_gpu(saida)


def avaliar_condicoes(
    gpu: Gpu | None,
    espaco_livre_gb: float,
    drive_montado: bool,
    versao_python: tuple[int, int] = sys.version_info[:2],
) -> tuple[list[str], list[str]]:
    problemas, avisos = [], []
    if not PYTHON_ACEITO[0] <= versao_python <= PYTHON_ACEITO[1]:
        problemas.append(
            f"Python {versao_python[0]}.{versao_python[1]} não suportado: o pacote aceita 3.12 e 3.13."
        )
    if gpu is None:
        problemas.append(
            "Nenhuma GPU NVIDIA encontrada: ative uma GPU L4 ou A100 em "
            "Ambiente de execução > Alterar tipo de ambiente de execução."
        )
    elif gpu.compute_capability < CC_MINIMA:
        problemas.append(
            f"A GPU {gpu.nome} (compute capability {gpu.compute_capability}) não "
            "suporta bfloat16: use L4 ou A100."
        )
    if espaco_livre_gb < ESPACO_MINIMO_GB:
        problemas.append(
            f"Pouco espaço em disco: {espaco_livre_gb:.0f} GB livres, mínimo de "
            f"{ESPACO_MINIMO_GB:.0f} GB."
        )
    if not drive_montado:
        problemas.append(
            "Google Drive não montado: o dataset e as saídas ficam no Drive. Monte "
            "com drive.mount('/content/drive') numa célula antes do script."
        )
    return problemas, avisos


def verificar_dataset(raiz: Path) -> tuple[list[str], list[str], dict[str, int]]:
    """Confere o MANIFESTO.JSONL, conta as imagens válidas por classe e as transcrições vazias."""
    manifesto = None
    if raiz.is_dir():
        manifesto = next(
            (
                f
                for f in sorted(raiz.iterdir())
                if f.is_file() and f.name.lower() == "manifesto.jsonl"
            ),
            None,
        )
    if manifesto is None:
        return [f"MANIFESTO.JSONL não encontrado em {raiz}."], [], {}
    problemas, avisos = [], []
    contagem: dict[str, int] = {}
    descartes = sem_transcricao = 0
    for numero, bruta in enumerate(manifesto.read_text(encoding="utf-8").splitlines(), start=1):
        if not bruta.strip():
            continue
        try:
            linha = json.loads(bruta)
        except json.JSONDecodeError:
            problemas.append(f"Linha {numero} do manifesto não é JSON válido.")
            continue
        classe = TIPOS_MANIFESTO.get(str(linha.get("tipo", "")).lower())
        if classe is None:
            problemas.append(f"Linha {numero}: tipo não suportado: {linha.get('tipo')!r}.")
            continue
        if linha.get("erro") is not None or not (raiz / str(linha.get("imagem") or "")).is_file():
            descartes += 1
            continue
        contagem[classe] = contagem.get(classe, 0) + 1
        sem_transcricao += not linha.get("transcricao")
    for classe in CLASSES:
        if not contagem.get(classe):
            problemas.append(f"Classe {classe.upper()} sem imagens válidas no manifesto.")
    if descartes:
        avisos.append(f"{descartes} linha(s) com erro ou sem imagem serão descartadas.")
    if sem_transcricao:
        avisos.append(
            f"{sem_transcricao} imagem(ns) sem transcrição: o modelo treina com a transcrição "
            "vazia, diferente da inferência, que recebe a transcrição do PaddleOCR-VL."
        )
    return problemas, avisos, contagem


def drive_montado() -> bool:
    return DRIVE.is_dir()


def diretorio_cache(args: argparse.Namespace, semente: int) -> Path:
    """Um cache por divisão e amostra, para não misturar exemplos de execuções diferentes."""
    amostra = f"n{args.por_classe}" if args.por_classe else "todos"
    return args.base / "cache" / f"br-doc-s{semente}-{amostra}"


def _semente() -> int:
    from visiondoc.treino.configuracao import carregar_config_treino

    return carregar_config_treino(RAIZ / "config" / "treino.yaml").semente


# --- registro ------------------------------------------------------------------


def registrar(mensagem: str) -> None:
    linha = f"[{datetime.now():%H:%M:%S}] {mensagem}"
    print(linha, flush=True)
    if _log is not None:
        with open(_log, "a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")


def _executar(comando: list[str]) -> int:
    registrar("$ " + " ".join(comando))
    return subprocess.run(comando, cwd=RAIZ, check=False).returncode


# --- etapas --------------------------------------------------------------------


def verificar(args: argparse.Namespace) -> int:
    gpu = consultar_gpu()
    livre = shutil.disk_usage("/content" if Path("/content").exists() else RAIZ).free / 1024**3
    registrar(f"Python {sys.version.split()[0]}; GPU: {gpu or 'nenhuma'}")
    registrar(f"Espaço livre: {livre:.0f} GB; Drive montado: {drive_montado()}")
    problemas, avisos = avaliar_condicoes(gpu, livre, drive_montado())
    problemas_dados, avisos_dados, contagem = verificar_dataset(args.dados)
    registrar(f"Dataset {args.dados}: {contagem or 'sem imagens'}")
    for aviso in avisos + avisos_dados:
        registrar(f"AVISO: {aviso}")
    for problema in problemas + problemas_dados:
        registrar(f"PROBLEMA: {problema}")
    if (problemas or problemas_dados) and not args.ignorar_condicoes:
        registrar("Condições de execução não atendidas; use --ignorar-condicoes para seguir.")
        return 2
    return 0


def instalar(args: argparse.Namespace) -> int:
    if _executar([sys.executable, "-m", "pip", "install", "-q", "-e", f"{RAIZ}[treino]"]) != 0:
        registrar("Falha na instalação do pacote com o extra treino.")
        return 3
    return 0


def preparar(args: argparse.Namespace) -> int:
    from collections import Counter

    from visiondoc.treino.bid import amostrar, dividir, gravar_particoes_csv
    from visiondoc.treino.manifesto import listar_manifesto, montar_cache

    semente = _semente()
    imagens, descartes = listar_manifesto(args.dados)
    registrar(f"Imagens válidas: {dict(Counter(i.classe for i in imagens))}")
    if descartes:
        registrar(f"Descartadas: {dict(descartes)}")
    divisao = dividir(imagens, semente)
    registrar(f"Divisão 70-15-15 (semente {semente}): { {p: len(v) for p, v in divisao.items()} }")
    registrar(f"Partições gravadas em {gravar_particoes_csv(divisao, args.saidas)}")
    if args.por_classe:
        divisao = amostrar(divisao, args.por_classe)
        registrar(
            f"Amostra de {args.por_classe} por classe: { {p: len(v) for p, v in divisao.items()} }"
        )
    destino = diretorio_cache(args, semente)
    itens = montar_cache(divisao, destino)
    registrar(f"Cache de treino: {len(itens)} itens em {destino}")
    return 0


def treinar(args: argparse.Namespace) -> int:
    import os

    os.environ.setdefault("MLFLOW_TRACKING_URI", f"file://{args.saidas / 'mlruns'}")
    from visiondoc.treino.executar import executar

    resultado = executar(
        RAIZ / "config" / "pipeline.yaml",
        RAIZ / "config" / "treino.yaml",
        cache=diretorio_cache(args, _semente()),
        saida=args.base / "saida",
        relatorios=args.saidas,
        limite_treino=args.limite_treino,
        limite_teste=args.limite_teste,
        avaliar_zero_shot=args.zero_shot,
    )
    for nome in ("zero_shot", "lora"):
        if nome not in resultado:
            continue
        metricas = json.loads((resultado[nome] / "metricas.json").read_text(encoding="utf-8"))
        tipo = metricas["classificacao"]["tipo"]["agregado"]
        registrar(
            f"{nome}: acurácia {tipo['acuracia']:.3f}, F1 macro {tipo['f1_macro']:.3f}, "
            f"cobertura {tipo['cobertura']:.3f}; relatório em {resultado[nome]}"
        )
    registrar(f"Adaptador: {resultado['adaptador']}")
    return 0


def opcoes_da_subetapa(args: argparse.Namespace, etapa: str) -> list[str]:
    """Argumentos para executar uma etapa em processo separado, com as mesmas opções."""
    opcoes = [
        "--etapa",
        etapa,
        "--dados",
        str(args.dados),
        "--saidas",
        str(args.saidas),
        "--base",
        str(args.base),
    ]
    for nome, valor in (
        ("--por-classe", args.por_classe),
        ("--limite-treino", args.limite_treino),
        ("--limite-teste", args.limite_teste),
    ):
        if valor is not None:
            opcoes += [nome, str(valor)]
    if not args.zero_shot:
        opcoes.append("--sem-zero-shot")
    if args.ignorar_condicoes:
        opcoes.append("--ignorar-condicoes")
    return opcoes


def tudo(args: argparse.Namespace) -> int:
    for etapa in (verificar, instalar):
        codigo = etapa(args)
        if codigo:
            return codigo
    for etapa in ("preparar", "treinar"):  # processos separados, cada um com seu log
        codigo = _executar([sys.executable, __file__, *opcoes_da_subetapa(args, etapa)])
        if codigo:
            registrar(f"Etapa {etapa} terminou com código {codigo}.")
            return codigo
    return 0


def main(argv: list[str] | None = None) -> int:
    global _log
    args = argumentos(argv)
    sys.path.insert(0, str(RAIZ / "src" / "backend"))
    args.saidas.mkdir(parents=True, exist_ok=True)
    _log = args.saidas / f"t038-{datetime.now():%Y%m%d-%H%M%S}-{args.etapa}.log"
    inicio = time.perf_counter()
    registrar(f"T038, etapa {args.etapa}; dataset {args.dados}; saídas em {args.saidas}")
    codigo = {
        "verificar": verificar,
        "instalar": instalar,
        "preparar": preparar,
        "treinar": treinar,
        "tudo": tudo,
    }[args.etapa](args)
    registrar(
        f"Etapa {args.etapa} concluída com código {codigo} em "
        f"{(time.perf_counter() - inicio) / 60:.1f} min."
    )
    return codigo


if __name__ == "__main__":
    sys.exit(main())
