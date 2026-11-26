"""Envia uma imagem a um modelo do Ollama e confere se a resposta valida no contrato (T020).

Uso (na raiz do repositório): ``uv run python infrastructure/treino-t038/verificar_ollama.py
--modelo visiondoc-prova --imagem data/raw/imagens/test-01137.png``
"""

import argparse
import io
import sys
from pathlib import Path

import ollama
from PIL import Image

from visiondoc.treino.esquema import SaidaVLM
from visiondoc.treino.instrucao import INSTRUCAO, TEXTO_USUARIO


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelo", required=True)
    p.add_argument("--imagem", type=Path, required=True)
    p.add_argument("--host", default="http://localhost:11434")
    a = p.parse_args()

    img = Image.open(a.imagem).convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    resposta = ollama.Client(host=a.host).chat(
        model=a.modelo,
        messages=[
            {"role": "system", "content": INSTRUCAO},
            {"role": "user", "content": TEXTO_USUARIO, "images": [buf.getvalue()]},
        ],
        format=SaidaVLM.model_json_schema(),
        think=False,
        options={"temperature": 0, "num_predict": 1024},
    )
    texto = resposta.message.content
    print(texto)
    try:
        SaidaVLM.model_validate_json(texto)
    except Exception as erro:  # noqa: BLE001
        print(f"INVÁLIDO: {erro}")
        return 1
    print("OK: resposta válida no contrato")
    return 0


if __name__ == "__main__":
    sys.exit(main())
