# ADR-010: Qwen3.5-9B ajustado com LoRA para classificação e extração

- **Status:** Aceito, alterado por [ADR-015](ADR-015-vlm-qwen35-4b.md) quanto ao modelo e por [ADR-019](ADR-019-treino-imagens-preparadas-invoice.md) quanto à fonte atual da T038
- **Data:** 2026-11-20
- **Substitui:** [ADR-002](ADR-002-ocr-bertimbau.md), [ADR-003](ADR-003-classificador-visual.md), [ADR-004](ADR-004-fusao-media-ponderada.md)

## Contexto

O título do trabalho é *"Classificação e extração de informações de documentos em processos judiciais: uma abordagem multimodal baseada em Modelos de Linguagem Visuais"*. A arquitetura anterior combinava um classificador visual (ConvNeXt-Tiny ou YOLO) e um classificador textual (BERTimbau), com fusão por média ponderada, e não extraía campos.

Requisitos para o modelo:

- pesos abertos e licença permissiva, para execução local ([ADR-009](ADR-009-execucao-local.md));
- bom desempenho em português e em documentos;
- porte compatível com uma GPU de 24 GB para inferência e ajuste com QLoRA;
- saída estruturada (JSON) e capacidade de localizar documentos na página.

## Decisão

Adotar o **Qwen3.5-9B** (Alibaba, Apache 2.0, multimodal nativo), ajustado com **LoRA**, como modelo único de:

- localização dos documentos na página;
- classificação do tipo e da face;
- extração dos campos.

### Configuração inicial do ajuste (a calibrar)

| Parâmetro | Valor inicial |
|---|---|
| Método | LoRA sobre o modelo de linguagem; codificador de visão congelado |
| Precisão | QLoRA 4 bits (GPU de 24 GB) ou LoRA bf16 (GPU de 48 GB ou mais) |
| Rank / alpha / dropout | 16 / 32 / 0,05 |
| Módulos-alvo | Projeções de atenção e MLP do modelo de linguagem |
| Formato dos exemplos | Imagem + transcrição delimitada → JSON conforme [`contratos/saida-vlm.md`](../contracts/saida-vlm.md) |
| Dados | T038: exclusivamente imagens preparadas de `br-doc-extraction`, conforme ADR-019 |

### Inferência

- Servida pelo `vLLM`, com o adaptador LoRA carregado sobre o modelo base.
- Saída restrita ao esquema JSON por decodificação estruturada (*structured outputs*), com o tipo limitado à lista fechada ([RN-003](../domain/business-rules.md#rn-003)).
- Instrução de sistema fixa; imagem e transcrição entram no turno do usuário, delimitadas e identificadas como dado ([P2](../../.specify/memory/constitution.md#p2-texto-extraído-é-dado-nunca-instrução)).
- Temperatura 0.
- A confiança do tipo vem das probabilidades (*logprobs*) do token da classe.

## Alternativas consideradas

| Alternativa | Motivo de não adotar como principal |
|---|---|
| Qwen3.5-4B | Mais leve, porém menos capaz; reserva para GPU limitada |
| Qwen3.8-27B | Mais forte, mas ajuste exige muito mais memória; usado como referência *zero-shot* no artigo |
| Gemma 4 (E4B, 12B) | Usado como segunda família para comparação no artigo |
| ConvNeXt-Tiny + BERTimbau | Mantido apenas como linha de base nos experimentos |
| YOLO26/YOLO11 | Licença AGPL-3.0; localização passa a ser feita pelo VLM |

## Consequências

- Um modelo único substitui três (visual, textual e fusão) e devolve também os campos.
- A questão de licença do YOLO desaparece; toda a pilha de modelos é Apache 2.0.
- **Volta a existir um modelo generativo no fluxo**, que lê a imagem diretamente. Isso reabre o risco de injeção de prompt; as mitigações estão no [ADR-012](ADR-012-deteccao-antes-do-vlm.md) e no [ADR-013](ADR-013-validacao-saida-vlm.md).
- **Risco de alucinação de campos**, mitigado pela validação contra a transcrição ([ADR-013](ADR-013-validacao-saida-vlm.md)).
- Maior custo de inferência; o tempo por página entra nas métricas.
- É preciso verificar se a versão do `vLLM` adotada suporta a arquitetura do Qwen3.5 e LoRA multimodal.
