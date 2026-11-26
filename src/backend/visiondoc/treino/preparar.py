"""CLI: ``python -m visiondoc.treino.preparar --imagens data/raw/imagens --saida data/processed/treino``."""

import argparse
import json
from pathlib import Path

from visiondoc.treino.alinhamento import PARTICOES, verificar_pasta
from visiondoc.treino.dados import baixar_rotulos, gravar_jsonl, montar_exemplos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imagens", type=Path, default=Path("data/raw/imagens"))
    parser.add_argument("--saida", type=Path, default=Path("data/processed/treino"))
    args = parser.parse_args(argv)

    verificar_pasta(args.imagens)
    rotulos = {split: baixar_rotulos(split, args.saida / "cache") for split in PARTICOES}
    exemplos, relatorio = montar_exemplos(args.imagens, rotulos)
    gravar_jsonl(exemplos, relatorio, args.saida)
    print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
