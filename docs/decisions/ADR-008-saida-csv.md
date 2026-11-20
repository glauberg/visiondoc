# ADR-008: Saída em CSV com uma linha por documento

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

O resultado deve trazer o inteiro teor e o tipo de cada documento em formato CSV. Um PDF pode conter vários documentos, e uma página pode conter mais de um.

## Decisão

- A saída principal é `documentos.csv`, com uma linha por documento identificado (não por arquivo).
- Com ConvNeXt-Tiny, a unidade é a página; com YOLO em modo de detecção, a unidade é cada documento detectado, com suas coordenadas em `bbox`.
- Esquema em [`contratos/documentos-csv.md`](../contratos/documentos-csv.md).

## Alternativas consideradas

- **Uma linha por arquivo:** descartada; mistura documentos de tipos diferentes.
- **JSON:** adiado; pode complementar o CSV se a extração estruturada de campos voltar ao escopo, ligado por `id_registro`.

## Consequências

- O inteiro teor contém quebras de linha e separadores, o que exige aspas em todos os campos (RFC 4180).
- O CSV guarda apenas o texto corrido; campos estruturados exigiriam colunas por tipo ou arquivo complementar.
