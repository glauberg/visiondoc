# ADR-012: Detecção de atos maliciosos antes do VLM, com mascaramento

- **Status:** Aceito
- **Data:** 2026-11-20
- **Altera:** [ADR-005](ADR-005-deteccao-nao-bloqueante.md) (ordem no pipeline e mascaramento; o caráter não bloqueante permanece)

## Contexto

Com o Qwen3.5-9B ([ADR-010](ADR-010-vlm-qwen35-9b-lora.md)), um modelo generativo passa a ler a imagem e a transcrição. Uma instrução escrita no documento (visível ou oculta) pode tentar alterar a classificação ou os campos extraídos. No arranjo anterior, a detecção rodava depois da classificação, porque o BERTimbau não segue instruções.

## Decisão

1. A detecção roda **depois da transcrição e antes do VLM**, sobre a camada de texto nativa, a transcrição do PaddleOCR-VL e o inventário da ingestão.
2. Continua **não bloqueante** ([P3](../../.specify/memory/constitution.md#p3-a-detecção-sinaliza-não-interrompe)): sinaliza, grava em `alertas.csv` e o documento segue.
3. **Mascaramento:** quando há ocorrência de `injecao_prompt` ou `texto_oculto` com localização conhecida:
   - a região correspondente é coberta por um retângulo de cor sólida (`OpenCV`) na imagem enviada ao VLM;
   - o trecho é substituído por `[TRECHO REMOVIDO]` na transcrição enviada ao VLM;
   - o inteiro teor gravado no CSV e a evidência no `alertas.csv` permanecem completos (com a higienização de [RN-014](../domain/business-rules.md#rn-014)).
4. Defesa em camadas no VLM:
   - instrução de sistema fixa, com o conteúdo do documento delimitado e identificado como dado;
   - saída restrita ao esquema JSON, com domínios fechados;
   - validação posterior ([ADR-013](ADR-013-validacao-saida-vlm.md)).

## Alternativas consideradas

- **Detecção depois do VLM:** descartada; o VLM receberia a injeção intacta.
- **Não processar documentos com injeção:** descartada pelo princípio [P3](../../.specify/memory/constitution.md#p3-a-detecção-sinaliza-não-interrompe).

## Consequências

- Uma injeção não detectada ainda pode influenciar o VLM, mas apenas dentro do esquema; a validação contra a transcrição é a última barreira.
- O alerta registra se houve mascaramento (`mascarado` em [`contratos/alertas-csv.md`](../contracts/alertas-csv.md)).
- O mascaramento pode cobrir texto legítimo em caso de falso positivo, com perda de campos; a taxa de falsos positivos deve ser medida.
