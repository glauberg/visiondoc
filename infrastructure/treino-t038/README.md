# Treino do adaptador LoRA (T038) e prova de carga no Ollama (T020)

Scripts descartáveis, fora do pipeline. Desenho: [`2026-11-26-treino-lora-t038-design.md`](../../docs/superpowers/specs/2026-11-26-treino-lora-t038-design.md). Plano: [`2026-11-26-treino-lora-t038.md`](../../docs/superpowers/plans/2026-11-26-treino-lora-t038.md).

Só o dataset público e sintético `br-doc-extraction` (as imagens de `data/raw/imagens/` e os JSONL gerados) vai para a nuvem (ADR-009, ADR-015). Nenhum outro dado.

## Estado

- [x] Dados gerados localmente em `data/processed/treino/` (`uv run python -m visiondoc.treino.preparar`).
- [ ] Prova pequena (passos 1 a 4 abaixo) — **não executada**; precisa de GPU de 24 GB.
- [ ] Treino completo (passo 5).

## Arquivos

| Arquivo | Onde roda | O que faz |
|---|---|---|
| `treinar.py` | nuvem (GPU 24 GB) | QLoRA 4 bits com Unsloth; grava o adaptador e `treino-meta.json`; registra no MLflow |
| `converter.py` | nuvem (precisa do modelo-base em HF e do llama.cpp) | adaptador → `.gguf` e `Modelfile` |
| `Modelfile.template` | — | `FROM qwen3.5:4b` + `ADAPTER` |
| `verificar_ollama.py` | local | envia uma imagem ao modelo do Ollama e valida a resposta no contrato |

## Prova pequena (bloqueia o treino completo)

**1. Preparar a nuvem.** Instância com GPU de 24 GB (Colab Pro, RunPod, etc.). Instalar o Unsloth seguindo o notebook oficial do Qwen3.5 com visão (a versão de `transformers` depende dele; um guia de terceiros usa `transformers==5.2.0`) e `pip install mlflow pillow`. Enviar `imagens/` (cópia de `data/raw/imagens/`), `train.jsonl`, `valid.jsonl` e este diretório. **Registrar neste README** as versões instaladas e o identificador exato do modelo (`unsloth/Qwen3.5-4B`, a confirmar). Se o Unsloth não suportar o modelo, usar TRL + PEFT + bitsandbytes e adaptar `treinar.py`.

**2. Treinar 20 passos.**

```bash
python treinar.py --dados train.jsonl --imagens imagens/ --saida adaptador-prova --passos 20
```

Esperado: sem erro de memória; `adaptador-prova/adapter_model.safetensors` existe; o log mostra `fração de tokens com perda` bem abaixo de 1 (só o turno do assistente). Se for `1.0`, o coletor está calculando a perda na sequência inteira: ajustar `instruction_part`/`response_part` ao *template* do Qwen3.5.

**3. Converter.**

```bash
git clone https://github.com/ggml-org/llama.cpp
python converter.py --adaptador adaptador-prova --base Qwen/Qwen3.5-4B \
  --llama-cpp llama.cpp --saida adaptador-prova.gguf
```

**4. Carregar no Ollama (local).** Trazer `adaptador-prova.gguf` e `Modelfile` para uma pasta e:

```bash
ollama create visiondoc-prova -f Modelfile
uv run python infrastructure/treino-t038/verificar_ollama.py \
  --modelo visiondoc-prova --imagem data/raw/imagens/test-01137.png
```

Esperado: `success` e `OK: resposta válida no contrato`.

**Portão.** Se a conversão ou a carga falhar, **parar**, registrar a mensagem aqui e voltar ao [ADR-017](../../docs/decisions/ADR-017-ollama-servidor-do-vlm.md). Alternativa a tentar antes de desistir: mesclar o adaptador ao modelo-base, converter o modelo inteiro e o projetor de visão com `convert_hf_to_gguf.py` e usar `FROM` no Modelfile (sem `ADAPTER`). Se passar, anotar aqui "T020: adaptador carrega no Ollama".

## Treino completo

```bash
python treinar.py --dados train.jsonl --valid valid.jsonl --imagens imagens/ \
  --saida adaptador-t038 --epocas 3 --semente 0
python converter.py --adaptador adaptador-t038 --base Qwen/Qwen3.5-4B \
  --llama-cpp llama.cpp --saida adaptador-t038.gguf
```

A época escolhida é a de menor perda de validação (o teste não é usado). Se a perda de validação piorar desde a primeira época, reduzir `--lr` e repetir. Local: `ollama create visiondoc-qwen35-4b-lora -f Modelfile`; anotar aqui o digest de `ollama list` e o `hash_instrucao` de `treino-meta.json` (`modelo_vlm`, ADR-017). Os pesos não vão ao git.
