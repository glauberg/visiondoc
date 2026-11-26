"""Converte o adaptador LoRA para GGUF e escreve o Modelfile do Ollama (T038).

Usa o ``convert_lora_to_gguf.py`` do llama.cpp. Rode onde estiver o modelo-base em HF
(na nuvem, depois do treino) e leve o ``.gguf`` e o ``Modelfile`` para a máquina local.
"""

import argparse
import subprocess
import sys
from pathlib import Path

MODELFILE = Path(__file__).with_name("Modelfile.template")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adaptador", type=Path, required=True, help="pasta com o adaptador PEFT")
    p.add_argument("--base", required=True, help="modelo-base em HF (ex.: Qwen/Qwen3.5-4B)")
    p.add_argument("--llama-cpp", type=Path, required=True, help="pasta do repositório llama.cpp")
    p.add_argument("--saida", type=Path, required=True, help="arquivo .gguf de saída")
    a = p.parse_args()

    conversor = a.llama_cpp / "convert_lora_to_gguf.py"
    subprocess.run(
        [sys.executable, str(conversor), "--base", a.base, "--outfile", str(a.saida), str(a.adaptador)],
        check=True,
    )
    modelfile = a.saida.with_name("Modelfile")
    modelfile.write_text(
        MODELFILE.read_text("utf-8").replace("{{ADAPTADOR}}", f"./{a.saida.name}"), "utf-8"
    )
    print(f"GGUF: {a.saida}\nModelfile: {modelfile}")
    print(f"Local: ollama create <nome> -f {modelfile.name}  (na pasta do .gguf)")


if __name__ == "__main__":
    main()
