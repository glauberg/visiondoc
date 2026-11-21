# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["torch", "transformers", "peft", "accelerate"]
# ///
"""Cria um adaptador LoRA de teste para a prova de conceito T020.

O adaptador usa a configuração inicial do ADR-010/ADR-015 (rank 16, alpha 32,
dropout 0,05, atenção e MLP do modelo de linguagem). Os pesos B são iniciados
em zero, então o adaptador não altera as respostas: serve apenas para provar
que o vLLM carrega LoRA sobre o modelo quantizado.
"""

import argparse
import re
import sys

import torch
from peft import LoraConfig, get_peft_model

ALVOS = r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"


def carregar(modelo: str):
    from transformers import AutoModelForImageTextToText

    return AutoModelForImageTextToText.from_pretrained(
        modelo, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, device_map="cpu"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--modelo", default="Qwen/Qwen3.5-4B")
    p.add_argument("--saida", default="adaptador-teste")
    a = p.parse_args()

    modelo = carregar(a.modelo)
    nomes = [n for n, _ in modelo.named_modules()]
    alvos = [n for n in nomes if re.fullmatch(ALVOS, n)]
    if not alvos:
        print("Nenhum módulo corresponde ao padrão de alvos. Exemplos de nomes:", file=sys.stderr)
        for n in nomes[:60]:
            print("  ", n, file=sys.stderr)
        return 1
    print(f"{len(alvos)} módulos-alvo, por exemplo {alvos[0]}")

    config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, target_modules=ALVOS, init_lora_weights=True
    )
    get_peft_model(modelo, config).save_pretrained(a.saida)
    print(f"Adaptador de teste salvo em {a.saida}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
