#!/usr/bin/env python
"""Execução da T038 (treino do adaptador LoRA) no ambiente Python do Google Colab.

Uso, em células do Colab:

    from google.colab import drive
    drive.mount("/content/drive")
    !git clone https://github.com/glauberg/visiondoc.git /content/visiondoc
    !python /content/visiondoc/infrastructure/colab/t038_colab.py --etapa tudo \
        --limite-treino 20 --limite-teste 10

Etapas (`--etapa`):
  verificar  confere GPU com bfloat16, espaço em disco e Google Drive
  instalar   instala o pacote com o extra `treino` e o PaddleOCR
  preparar   carrega `tech4humans/br-doc-extraction` com load_dataset e prepara os exemplos
  treinar    linha de base zero-shot, treino QLoRA e relatórios (RF-SDD-18)
  tudo       todas as anteriores; preparar e treinar rodam em processos separados,
             o que libera a memória de GPU do Paddle sem reiniciar o ambiente

Decisões em docs/decisions/ADR-017-treino-br-doc-extraction.md. Somente dados do
dataset público; nenhum documento real é usado.
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
BASE_LOCAL = Path("/content/visiondoc-dados")
ETAPAS = ("verificar", "instalar", "preparar", "treinar", "tudo")
CC_MINIMA = 8.0  # bfloat16 (L4, A100); a T4 (7.5) não atende
PYTHON_ACEITO = ((3, 12), (3, 13))  # requires-python do pyproject.toml
ESPACO_MINIMO_GB = 30.0  # pesos do modelo, cache de exemplos, adaptador e checkpoints
INDICE_PADDLE = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
DATASET = "tech4humans/br-doc-extraction"
PARTICOES = ("train", "valid", "test")

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
        "--base",
        type=Path,
        default=None,
        help="diretório de cache, saída e relatórios (padrão: Drive, se montado)",
    )
    p.add_argument(
        "--limite-treino",
        type=int,
        default=None,
        help="usa só as N primeiras linhas de train (verificação rápida)",
    )
    p.add_argument(
        "--limite-teste",
        type=int,
        default=None,
        help="usa só as N primeiras linhas de test (verificação rápida)",
    )
    p.add_argument(
        "--sem-zero-shot",
        dest="zero_shot",
        action="store_false",
        help="não avalia a linha de base zero-shot",
    )
    p.add_argument(
        "--indice-paddle",
        default=INDICE_PADDLE,
        help="índice do paddlepaddle-gpu compatível com o CUDA do ambiente",
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
        avisos.append(
            "Google Drive não montado: cache, adaptador e relatórios ficarão em "
            f"{BASE_LOCAL} e serão perdidos ao encerrar o ambiente. Monte com "
            "drive.mount('/content/drive') numa célula antes do script."
        )
    return problemas, avisos


def drive_montado() -> bool:
    return DRIVE.is_dir()


def base_de_dados(args: argparse.Namespace) -> Path:
    base = args.base or (BASE_DRIVE if drive_montado() else BASE_LOCAL)
    base.mkdir(parents=True, exist_ok=True)
    return base


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
    registrar(f"GPU: {gpu or 'nenhuma'}")
    registrar(f"Espaço livre: {livre:.0f} GB; Drive montado: {drive_montado()}")
    problemas, avisos = avaliar_condicoes(gpu, livre, drive_montado())
    for aviso in avisos:
        registrar(f"AVISO: {aviso}")
    for problema in problemas:
        registrar(f"PROBLEMA: {problema}")
    if problemas and not args.ignorar_condicoes:
        registrar("Condições de execução não atendidas; use --ignorar-condicoes para seguir.")
        return 2
    return 0


def instalar(args: argparse.Namespace) -> int:
    pip = [sys.executable, "-m", "pip", "install", "-q"]
    for comando in (
        [*pip, "-e", f"{RAIZ}[treino]"],
        [*pip, "paddlepaddle-gpu", "-i", args.indice_paddle],
        [*pip, "paddleocr[doc-parser]"],
    ):
        if _executar(comando) != 0:
            registrar("Falha na instalação; confira a versão do paddlepaddle-gpu para o CUDA.")
            return 3
    return 0


def preparar(args: argparse.Namespace) -> int:
    from collections import Counter

    from datasets import Image as ImagemHF
    from datasets import load_dataset

    from visiondoc.configuracao import carregar_configuracao
    from visiondoc.deteccao import Detectores
    from visiondoc.transcricao import (
        AvaliadorPorTranscricao,
        ClassificadorOrientacaoPaddle,
        TranscritorPaddleOCRVL,
        TranscritorPPOCR,
    )
    from visiondoc.treino.preparacao import preparar as preparar_exemplos

    base = base_de_dados(args)
    conjunto = load_dataset(DATASET).cast_column("image", ImagemHF(decode=False))
    registrar(f"Dataset: {{{', '.join(f'{p}: {len(conjunto[p])}' for p in PARTICOES)}}}")
    linhas = [(p, linha) for p in PARTICOES for linha in conjunto[p]]
    itens = preparar_exemplos(
        linhas,
        base / "cache",
        carregar_configuracao(RAIZ / "config" / "pipeline.yaml"),
        transcritor=TranscritorPaddleOCRVL(),
        avaliador=AvaliadorPorTranscricao(TranscritorPPOCR()),
        classificador=ClassificadorOrientacaoPaddle(),
        detectores=Detectores(None, None),  # regras e regex ativas; sem llm-guard e ClamAV
        regras_yara=RAIZ / "config" / "yara" / "pdf_conteudo_ativo.yar",
    )
    resumo = Counter((i.particao, i.erro or "ok") for i in itens)
    registrar(f"Preparação: {dict(resumo)}")
    validos = sum(1 for i in itens if i.erro is None)
    if validos == 0:
        registrar("Nenhum exemplo válido preparado.")
        return 4
    return 0


def treinar(args: argparse.Namespace) -> int:
    import os

    base = base_de_dados(args)
    os.environ.setdefault("MLFLOW_TRACKING_URI", f"file://{base / 'mlruns'}")
    from visiondoc.treino.executar import executar

    resultado = executar(
        RAIZ / "config" / "pipeline.yaml",
        RAIZ / "config" / "treino.yaml",
        cache=base / "cache",
        saida=base / "saida",
        relatorios=base / "relatorios",
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
    opcoes = ["--etapa", etapa, "--indice-paddle", args.indice_paddle]
    if args.base is not None:
        opcoes += ["--base", str(args.base)]
    if args.limite_treino is not None:
        opcoes += ["--limite-treino", str(args.limite_treino)]
    if args.limite_teste is not None:
        opcoes += ["--limite-teste", str(args.limite_teste)]
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
    for etapa in ("preparar", "treinar"):  # processos separados liberam a GPU entre as etapas
        codigo = _executar([sys.executable, __file__, *opcoes_da_subetapa(args, etapa)])
        if codigo:
            registrar(f"Etapa {etapa} terminou com código {codigo}.")
            return codigo
    return 0


def main(argv: list[str] | None = None) -> int:
    global _log
    args = argumentos(argv)
    sys.path.insert(0, str(RAIZ / "src" / "backend"))
    base = base_de_dados(args)
    (base / "logs").mkdir(exist_ok=True)
    _log = base / "logs" / f"t038-{datetime.now():%Y%m%d-%H%M%S}-{args.etapa}.log"
    inicio = time.perf_counter()
    registrar(f"T038, etapa {args.etapa}; dados em {base}")
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
