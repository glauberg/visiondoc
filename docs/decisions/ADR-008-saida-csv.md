# ADR-008: Saída em CSV com uma linha por documento

- **Status:** Aceito, alterado por [ADR-010](ADR-010-vlm-qwen35-9b-lora.md) (localização pelo VLM) e [ADR-014](ADR-014-extracao-de-campos.md) (colunas de campos)
- **Data:** 2026-11-20

## Contexto

O resultado deve trazer o inteiro teor e o tipo de cada documento em formato CSV. Um PDF pode conter vários documentos, e uma página pode conter mais de um.

## Decisão

- A saída principal é `documentos.csv`, com uma linha por documento identificado (não por arquivo).
- O VLM identifica cada documento e devolve suas coordenadas em `bbox`.
- Esquema em [`contratos/documentos-csv.md`](../contracts/documentos-csv.md).

## Alternativas consideradas

- **Uma linha por arquivo:** descartada; mistura documentos de tipos diferentes.
- **JSON:** usado internamente pelo contrato da saída do VLM; a saída principal permanece em CSV.

## Consequências

- O inteiro teor contém quebras de linha e separadores, o que exige aspas em todos os campos (RFC 4180).
- O CSV guarda apenas o texto corrido; campos estruturados exigiriam colunas por tipo ou arquivo complementar.
