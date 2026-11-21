# ADR-015: Qwen3.5-4B como modelo principal por limite de hardware

- **Status:** Aceito
- **Data:** 2026-11-21
- **Altera:** [ADR-010](ADR-010-vlm-qwen35-9b-lora.md) (modelo e configuração de hardware; o método de ajuste com LoRA e a forma de inferência permanecem)

## Contexto

O [ADR-010](ADR-010-vlm-qwen35-9b-lora.md) adotou o Qwen3.5-9B com hardware de referência de 24 GB (QLoRA) ou 48 GB (LoRA bf16). A GPU disponível para o trabalho tem 8 GB. Nessa memória, o ajuste do modelo de 9B com imagens não é viável sem recursos adicionais. O próprio ADR-010 já prevê o Qwen3.5-4B como alternativa para GPU limitada.

## Decisão

Adotar o **Qwen3.5-4B** (Apache 2.0, multimodal) como modelo principal de localização, classificação e extração, ajustado com **QLoRA 4 bits**, mantendo o restante do ADR-010:

- LoRA sobre o modelo de linguagem, com o codificador de visão congelado; rank 16, alpha 32 e dropout 0,05 como valores iniciais;
- exemplos no formato do [contrato da saída do VLM](../contracts/saida-vlm.md);
- dados de ajuste e avaliação restritos ao BID e ao `br-doc-extraction`: na fase de desenvolvimento e testes não são admitidos dados reais nem documentos de processos judiciais, o que substitui a linha "Dados" da configuração do ADR-010;
- inferência pelo `vLLM`, com decodificação estruturada, instrução de sistema fixa, temperatura 0 e confiança a partir dos logprobs.

### Inferência quantizada *(definida em 2026-11-21)*

- A inferência usa pesos do Qwen3.5-4B quantizados em **8 bits** (FP8 ou INT8, conforme o suporte da GPU; FP8 exige arquitetura compatível), com o adaptador LoRA carregado sobre o modelo quantizado.
- **Requisito do `vLLM`:** a versão adotada deve suportar, em conjunto, a arquitetura Qwen3.5, entrada multimodal (imagem + texto), adaptador LoRA sobre modelo quantizado em 8 bits, decodificação estruturada e logprobs. A versão é fixada nas dependências do projeto.
- **Verificação obrigatória antes da implementação:** uma prova de conceito na GPU de 8 GB carrega o modelo em 8 bits com o adaptador, processa uma página sintética com imagem e transcrição e devolve JSON válido com logprobs, dentro da memória disponível. Se a verificação falhar, a decisão é revista em novo ADR.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Manter Qwen3.5-9B com QLoRA e *offload* | Viabilidade incerta e tempo de treino e inferência elevado em 8 GB |
| Manter Qwen3.5-9B e obter GPU maior | Depende de recurso ainda não disponível |

## Consequências

- `modelo_vlm` passa a registrar `qwen3.5-4b+lora@<versão>`.
- O ajuste usa QLoRA 4 bits e a inferência usa 8 bits; o efeito dessa diferença na precisão deve ser medido na avaliação.
- Espera-se menor capacidade que a do 9B; a diferença só pode ser medida se houver hardware para o 9B.
- O Qwen3.5-9B, o Qwen3.8-27B e o Gemma ficam como referências *zero-shot* apenas se houver hardware adequado.
- A PaddleOCR-VL (0,9B) e o detector de injeção dividem a mesma GPU; a execução pode precisar ser sequencial por etapa.
