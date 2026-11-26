"""Treino QLoRA do Qwen3.5-4B (T038). Roda na GPU de nuvem (24 GB); descartável, fora do pipeline.

Instalação: seguir o notebook oficial do Unsloth para Qwen3.5 com visão (ver README) e
``pip install mlflow``. Os JSONL e as imagens vêm de ``visiondoc.treino.preparar``.
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path

from PIL import Image


def argumentos() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", type=Path, required=True, help="train.jsonl")
    p.add_argument("--valid", type=Path, help="valid.jsonl")
    p.add_argument("--imagens", type=Path, required=True)
    p.add_argument("--saida", type=Path, required=True)
    p.add_argument("--modelo", default="unsloth/Qwen3.5-4B")
    p.add_argument("--passos", type=int, default=-1, help="-1 = usar --epocas")
    p.add_argument("--epocas", type=int, default=3)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--semente", type=int, default=0)
    p.add_argument("--mlflow-uri", default="file:./mlruns")
    return p.parse_args()


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def carregar(jsonl: Path, imagens: Path) -> list[dict]:
    """Troca o marcador de imagem pelo PIL da imagem, como o coletor de visão espera."""
    exemplos = []
    for linha in jsonl.read_text("utf-8").splitlines():
        ex = json.loads(linha)
        imagem = Image.open(imagens / ex["imagem"]).convert("RGB")
        mensagens = json.loads(json.dumps(ex["messages"]))
        for parte in mensagens[1]["content"]:
            if parte["type"] == "image":
                parte["image"] = imagem
        # sistema e assistente em lista de partes, formato do coletor de visão
        mensagens[0]["content"] = [{"type": "text", "text": mensagens[0]["content"]}]
        mensagens[2]["content"] = [{"type": "text", "text": mensagens[2]["content"]}]
        exemplos.append({"messages": mensagens})
    return exemplos


def main() -> None:
    a = argumentos()
    import os

    os.environ["MLFLOW_TRACKING_URI"] = a.mlflow_uri
    os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", "visiondoc-t038")

    import torch
    import transformers
    import trl
    import unsloth
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastVisionModel, is_bf16_supported
    from unsloth.trainer import UnslothVisionDataCollator

    modelo, tokenizador = FastVisionModel.from_pretrained(
        a.modelo, load_in_4bit=True, use_gradient_checkpointing="unsloth"
    )
    modelo = FastVisionModel.get_peft_model(
        modelo,
        finetune_vision_layers=False,  # codificador de visão congelado (ADR-015)
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        random_state=a.semente,
    )
    FastVisionModel.for_training(modelo)

    treino = carregar(a.dados, a.imagens)
    valid = carregar(a.valid, a.imagens) if a.valid else None

    # perda só no turno do assistente; se esta versão do Unsloth não aceitar, avisa
    try:
        coletor = UnslothVisionDataCollator(
            modelo,
            tokenizador,
            train_on_responses_only=True,
            instruction_part="<|im_start|>user\n",
            response_part="<|im_start|>assistant\n",
        )
    except TypeError:
        print("AVISO: coletor sem train_on_responses_only; a perda cobre a sequência inteira")
        coletor = UnslothVisionDataCollator(modelo, tokenizador)
    lote = coletor(treino[:2])
    rotulos = lote["labels"]
    fracao = float((rotulos != -100).sum() / rotulos.numel())
    print(f"fração de tokens com perda: {fracao:.3f}")

    config = SFTConfig(
        output_dir=str(a.saida),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=a.epocas,
        max_steps=a.passos,
        learning_rate=a.lr,
        warmup_steps=5,
        lr_scheduler_type="linear",
        weight_decay=0.01,
        optim="adamw_8bit",
        bf16=is_bf16_supported(),
        fp16=not is_bf16_supported(),
        logging_steps=1,
        seed=a.semente,
        eval_strategy="epoch" if valid and a.passos < 0 else "no",
        save_strategy="epoch" if valid and a.passos < 0 else "no",
        load_best_model_at_end=bool(valid) and a.passos < 0,
        metric_for_best_model="eval_loss",
        report_to="mlflow",
        remove_unused_columns=False,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
        max_length=2048,
    )
    treinador = SFTTrainer(
        model=modelo,
        tokenizer=tokenizador,
        data_collator=coletor,
        train_dataset=treino,
        eval_dataset=valid,
        args=config,
    )
    treinador.train()

    a.saida.mkdir(parents=True, exist_ok=True)
    modelo.save_pretrained(str(a.saida))
    tokenizador.save_pretrained(str(a.saida))

    historico = treinador.state.log_history
    meta = {
        "tarefa": "T038",
        "parametros": {k: str(v) for k, v in vars(a).items()},
        "lora": {"r": 16, "alpha": 32, "dropout": 0.05, "visao_congelada": True},
        "fracao_tokens_com_perda": fracao,
        "melhor_checkpoint": treinador.state.best_model_checkpoint,
        "melhor_eval_loss": treinador.state.best_metric,
        "perdas_validacao": [h for h in historico if "eval_loss" in h],
        "sha256_dados": sha256(a.dados),
        "sha256_valid": sha256(a.valid) if a.valid else None,
        "hash_instrucao": hashlib.sha256(
            treino[0]["messages"][0]["content"][0]["text"].encode("utf-8")
        ).hexdigest(),
        "versoes": {
            "unsloth": getattr(unsloth, "__version__", "?"),
            "transformers": transformers.__version__,
            "trl": trl.__version__,
            "torch": torch.__version__,
            "python": platform.python_version(),
        },
        "gpu": torch.cuda.get_device_name(0),
    }
    (a.saida / "treino-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({k: meta[k] for k in ("melhor_eval_loss", "versoes", "gpu")}, indent=2))


if __name__ == "__main__":
    main()
