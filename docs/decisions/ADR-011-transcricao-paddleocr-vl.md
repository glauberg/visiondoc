# ADR-011: Transcrição do inteiro teor com PaddleOCR-VL

- **Status:** Aceito
- **Data:** 2026-11-20
- **Substitui (em parte):** [ADR-002](ADR-002-ocr-bertimbau.md), no que se refere ao OCR

## Contexto

Um VLM generativo de uso geral pode "completar" trechos ilegíveis com texto plausível que não está no documento. O inteiro teor precisa ser fiel à imagem, e serve também de referência para validar os campos extraídos.

## Decisão

Usar o **PaddleOCR-VL 1.6** (0,9B parâmetros, Apache 2.0), modelo de linguagem visual especializado em transcrição de documentos, para produzir:

- o inteiro teor, em ordem de leitura;
- as caixas de cada linha ou bloco de texto, usadas na detecção e no mascaramento ([ADR-012](ADR-012-deteccao-antes-do-vlm.md)).

A transcrição é feita uma vez por página, antes da detecção e do Qwen3.5-9B.

## Alternativas consideradas

- **Inteiro teor gerado pelo próprio Qwen3.5-9B:** descartada pelo risco de alucinação e por eliminar a referência independente para validação.
- **PaddleOCR tradicional (PP-OCR):** mantido como alternativa de menor custo e como linha de base de CER.

## Consequências

- Dois VLMs no pipeline, com papéis separados: transcrever (fidelidade) e interpretar (classificação e extração).
- A transcrição é a fonte de verdade para a regra de respaldo dos campos ([RN-024](../domain/business-rules.md#rn-024)).
- O texto transcrito também é entrada do Qwen3.5-9B, delimitado como dado.
