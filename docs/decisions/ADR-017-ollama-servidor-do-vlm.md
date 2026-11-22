# ADR-017: Ollama como servidor do VLM

- **Status:** Aceito
- **Data:** 2026-11-22
- **Altera:** [ADR-015](ADR-015-vlm-qwen35-4b.md) (servidor de inferência, quantização e GPU de referência; o modelo Qwen3.5-4B, o método LoRA e a restrição a dados sintéticos permanecem)

## Contexto

O [ADR-015](ADR-015-vlm-qwen35-4b.md) adotou o `vLLM` com pesos em 8 bits e LoRA sobre o modelo quantizado, condicionado a uma prova de conceito (T020) que exigia uma GPU de 8 GB. A máquina de desenvolvimento tem o Ollama 0.40.17 instalado com `qwen3.5:4b` (Q4_K_M, 3,3 GB) e uma GPU GTX 1650 de 4 GB.

Verificação feita em 2026-11-22 com uma imagem do BID, sem transcrição, em `/api/chat`:

- imagem e texto na entrada: funciona;
- saída restrita a esquema JSON (`format`), com `think: false` e temperatura 0: funciona;
- `logprobs` e `top_logprobs`: funcionam, mas refletem a distribuição anterior à restrição do esquema (na posição do `tipo`, as alternativas foram `cart`, `Cart`, `cn`, `CN` e `RG`);
- coordenadas de `bbox`: normalizadas de 0 a 1000 (veio `[2,10,996,985]` para uma imagem de 675×491);
- desempenho: modelo 35% em CPU e 65% em GPU; 76 s na primeira chamada (13 s de carga) e 22 s por página nas seguintes (14 s de processamento do prompt);
- adaptador LoRA: não verificado.

## Decisão

Adotar o **Ollama** como servidor local do Qwen3.5-4B, em substituição ao `vLLM`:

- integração por HTTP em `/api/chat`, atrás do `Protocol ClienteVLM`; o endereço só pode ser da própria máquina ([ADR-009](ADR-009-execucao-local.md));
- pesos `qwen3.5:4b` em Q4_K_M (GGUF), no lugar de FP8/INT8; o efeito da quantização na precisão é medido na avaliação;
- a confiança do tipo ([RN-004](../domain/business-rules.md#rn-004)) é calculada com `top_logprobs` na posição do valor de `tipo`; para rótulos que não foram gerados, usa apenas a primeira posição, o que é uma aproximação, a ser medida (ECE) depois do ajuste;
- o adaptador LoRA treinado com QLoRA precisa ser convertido para GGUF e carregado pelo Ollama (`ADAPTER` no Modelfile); a T020 passa a ser a prova de conceito dessa conversão com o modelo multimodal, antes do treino da T038;
- `modelo_vlm` registra `<modelo>@<digest do Ollama>` e o hash da instrução de sistema;
- `vLLM` permanece como alternativa se o adaptador não carregar no Ollama ou se houver GPU de 8 GB ou mais.

## Alternativas consideradas

| Alternativa | Motivo da recusa |
|---|---|
| Manter `vLLM` com 8 bits | Exige a GPU de 8 GB, indisponível; o Ollama já está instalado e funcionou de ponta a ponta |
| `llama.cpp` direto | Mesma base do Ollama, com mais integração a manter |
| `transformers` em processo | Acopla o pipeline à GPU e perde a decodificação por esquema pronta |

## Consequências

- A inferência é lenta nesta máquina (cerca de 22 s por página); avaliações usam amostras e o desempenho é registrado (RNF-SDD-09).
- A confiança do tipo em *zero-shot* é pouco confiável; deve ser recalibrada com o adaptador.
- As seções do `spec.md` e do `plan.md` que citam o `vLLM` (RF-SDD-08, Q-23, riscos) ficam desatualizadas e precisam de revisão e aprovação.
- Risco: o adaptador LoRA pode não carregar no Ollama com o modelo multimodal; nesse caso a decisão volta a este ADR.
