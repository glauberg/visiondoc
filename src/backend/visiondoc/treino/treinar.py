"""Carga do modelo, coletor, treino QLoRA e geração (T038).

Requer GPU com suporte a bfloat16 e o extra `treino`. Não é coberto pelos
testes unitários: a lógica de montagem de exemplos e de métricas está em
`exemplos.py` e `avaliacao.py`, testados sem GPU.
"""

import gc
import re
import time
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image

from visiondoc.avaliacao.relatorio import InfoTreino
from visiondoc.treino.configuracao import ConfigTreino, bbox_documento_inteiro
from visiondoc.treino.exemplos import (
    carregar_instrucao,
    mensagens,
    montar_resposta,
    montar_sequencia,
)
from visiondoc.treino.preparacao import ItemPreparado

FIM_TURNO = "<|im_end|>"
_PENSAMENTO = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)


def _imagem(cache: Path, item: ItemPreparado, cfg: ConfigTreino) -> Image.Image:
    imagem = Image.open(Path(cache) / item.imagem).convert("RGB")
    imagem.thumbnail((cfg.lado_max_imagem, cfg.lado_max_imagem))
    return imagem


def texto_prompt(processor, instrucao: str, transcricao: str, imagem) -> str:
    msgs = mensagens(instrucao, transcricao, imagem)
    try:
        return processor.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        return processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def contar_parametros(modelo) -> tuple[int, int]:
    """(totais, treináveis), contando os pesos de 4 bits pelo tamanho original."""
    totais = treinaveis = 0
    for p in modelo.parameters():
        n = p.numel() * (2 if p.__class__.__name__ == "Params4bit" else 1)
        totais += n
        treinaveis += n if p.requires_grad else 0
    return totais, treinaveis


def carregar_modelo(cfg: ConfigTreino, adaptador: str | Path | None = None):
    from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

    quantizacao = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type=cfg.quantizacao.tipo,
        bnb_4bit_use_double_quant=cfg.quantizacao.dupla,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    processor = AutoProcessor.from_pretrained(cfg.modelo_base, revision=cfg.revisao)
    modelo = AutoModelForImageTextToText.from_pretrained(
        cfg.modelo_base,
        revision=cfg.revisao,
        quantization_config=quantizacao,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    if adaptador is not None:
        from peft import PeftModel

        modelo = PeftModel.from_pretrained(modelo, str(adaptador))
    modelo.eval()
    return modelo, processor


def liberar(*objetos) -> None:
    for obj in objetos:
        del obj
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


class Coletor:
    """Monta um exemplo multimodal por vez: prompt fora da perda, campos sem anotação também."""

    def __init__(self, processor, cfg: ConfigTreino, cache: Path, instrucao: str) -> None:
        self.processor, self.cfg, self.cache, self.instrucao = (
            processor,
            cfg,
            Path(cache),
            instrucao,
        )

    def __call__(self, itens: list[ItemPreparado]) -> dict:
        (item,) = itens
        imagem = _imagem(self.cache, item, self.cfg)
        prompt = texto_prompt(self.processor, self.instrucao, item.transcricao, imagem)
        entrada = self.processor(text=[prompt], images=[imagem], return_tensors="pt")
        resposta, trechos = montar_resposta(
            item.tipo,
            item.campos,
            set(item.sem_anotacao),
            None,
            bbox_documento_inteiro(self.cfg, item.largura, item.altura),
        )
        tokens = self.processor.tokenizer(
            resposta + FIM_TURNO, add_special_tokens=False, return_offsets_mapping=True
        )
        ids, rotulos = montar_sequencia(
            entrada["input_ids"][0].tolist(),
            tokens["input_ids"],
            tokens["offset_mapping"],
            trechos,
        )
        lote = {k: v for k, v in entrada.items() if k not in ("input_ids", "attention_mask")}
        lote["input_ids"] = torch.tensor([ids])
        lote["attention_mask"] = torch.ones_like(lote["input_ids"])
        lote["labels"] = torch.tensor([rotulos])
        return lote


class _Lista(torch.utils.data.Dataset):
    def __init__(self, itens: list) -> None:
        self.itens = itens

    def __len__(self) -> int:
        return len(self.itens)

    def __getitem__(self, i):
        return self.itens[i]


@dataclass
class ResultadoTreino:
    adaptador: Path
    info: InfoTreino
    parametros_totais: int
    parametros_treinaveis: int
    modulos_alvo: int
    tamanho_adaptador_bytes: int
    mlflow_id: str | None


def treinar(
    cfg: ConfigTreino,
    cache: str | Path,
    saida: str | Path,
    itens_treino: list[ItemPreparado],
    itens_validacao: list[ItemPreparado],
) -> ResultadoTreino:
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import Trainer, TrainingArguments, set_seed

    set_seed(cfg.semente)
    saida = Path(saida)
    modelo, processor = carregar_modelo(cfg)
    modelo = prepare_model_for_kbit_training(
        modelo, use_gradient_checkpointing=cfg.otimizacao.checkpointing
    )
    modelo = get_peft_model(
        modelo,
        LoraConfig(
            r=cfg.lora.r,
            lora_alpha=cfg.lora.alpha,
            lora_dropout=cfg.lora.dropout,
            target_modules=cfg.lora.alvos,
            task_type="CAUSAL_LM",
        ),
    )
    totais, treinaveis = contar_parametros(modelo)
    modulos = sum(1 for nome, _ in modelo.named_modules() if nome.endswith(".lora_A"))

    o = cfg.otimizacao
    argumentos = TrainingArguments(
        output_dir=str(saida / "checkpoints"),
        per_device_train_batch_size=o.lote,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=o.acumulacao,
        num_train_epochs=o.epocas,
        learning_rate=o.taxa_aprendizado,
        warmup_ratio=o.aquecimento,
        lr_scheduler_type=o.agendador,
        bf16=True,
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        report_to=["mlflow"],
        remove_unused_columns=False,
        gradient_checkpointing=o.checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        seed=cfg.semente,
        dataloader_pin_memory=False,
    )
    treinador = Trainer(
        model=modelo,
        args=argumentos,
        train_dataset=_Lista(itens_treino),
        eval_dataset=_Lista(itens_validacao),
        data_collator=Coletor(processor, cfg, Path(cache), carregar_instrucao()),
    )
    torch.cuda.reset_peak_memory_stats()
    inicio = time.perf_counter()
    resultado = treinador.train()
    duracao = time.perf_counter() - inicio
    pico = torch.cuda.max_memory_allocated() / 1024**3

    adaptador = saida / "adaptador"
    modelo.save_pretrained(adaptador)
    processor.save_pretrained(adaptador)
    tamanho = sum(f.stat().st_size for f in adaptador.rglob("*") if f.is_file())

    perdas: dict[int, list] = {}
    for registro in treinador.state.log_history:
        passo = registro.get("step")
        if "loss" in registro:
            perdas.setdefault(passo, [None, None])[0] = registro["loss"]
        if "eval_loss" in registro:
            perdas.setdefault(passo, [None, None])[1] = registro["eval_loss"]
    curva = [(passo, t, v) for passo, (t, v) in sorted(perdas.items())]

    try:
        import mlflow

        ultima = mlflow.last_active_run()
        mlflow_id = ultima.info.run_id if ultima else None
    except Exception:  # noqa: BLE001
        mlflow_id = None

    info = InfoTreino(
        hiperparametros={
            "taxa_aprendizado": o.taxa_aprendizado,
            "epocas": o.epocas,
            "lote": o.lote,
            "acumulacao": o.acumulacao,
            "aquecimento": o.aquecimento,
            "agendador": o.agendador,
            "exemplos_treino": len(itens_treino),
            "exemplos_validacao": len(itens_validacao),
        },
        tempo_total_s=duracao,
        exemplos_por_s=float(resultado.metrics.get("train_samples_per_second", 0.0)),
        pico_memoria_gb=pico,
        curva_perda=curva,
    )
    liberar(treinador, modelo)
    return ResultadoTreino(adaptador, info, totais, treinaveis, modulos, tamanho, mlflow_id)


def gerador_hf(modelo, processor, cfg: ConfigTreino, cache: str | Path):
    """Gerador para `avaliar_itens`, com transformers (sem vLLM nem decodificação guiada)."""
    instrucao = carregar_instrucao()

    def gerar(item: ItemPreparado):
        imagem = _imagem(Path(cache), item, cfg)
        prompt = texto_prompt(processor, instrucao, item.transcricao, imagem)
        entrada = processor(text=[prompt], images=[imagem], return_tensors="pt").to(modelo.device)
        inicio = time.perf_counter()
        with torch.no_grad():
            saida = modelo.generate(
                **entrada,
                max_new_tokens=cfg.avaliacao.max_novos_tokens,
                do_sample=False,
                output_scores=True,
                return_dict_in_generate=True,
            )
        segundos = time.perf_counter() - inicio
        gerados = saida.sequences[0, entrada["input_ids"].shape[1] :]
        probs = [
            torch.softmax(passo[0].float(), dim=-1)[token].item()
            for passo, token in zip(saida.scores, gerados)
        ]
        tokens = [processor.tokenizer.decode([t]) for t in gerados]
        texto = _PENSAMENTO.sub("", processor.tokenizer.decode(gerados, skip_special_tokens=True))
        return texto.strip(), tokens, probs, segundos

    return gerar
