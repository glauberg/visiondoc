# ADR-014: Extração de campos no escopo

- **Status:** Aceito
- **Data:** 2026-11-20
- **Substitui (em parte):** [ADR-002](ADR-002-ocr-bertimbau.md), que retirava a extração estruturada do escopo

## Contexto

O título do trabalho inclui a extração de informações. O Qwen3.5-9B extrai campos sem componente adicional, e o dataset `br-doc-extraction` já traz esquemas e respostas em JSON para RG e CNH.

## Decisão

Extrair os campos de CNH, RG e CPF conforme [`contratos/saida-vlm.md`](../contracts/saida-vlm.md) e gravá-los no CSV principal:

- **colunas fixas** para os campos comuns a mais de um tipo: `nome`, `cpf`, `numero_documento`, `data_nascimento`, `data_emissao`, `data_validade`, `orgao_emissor`;
- **coluna `campos_json`** para os campos específicos de cada tipo (`filiacao`, `naturalidade`, `doc_origem`, `categoria_habilitacao`).

Documentos `outros` e `indefinido` não têm campos extraídos.

## Consequências

- O contrato do CSV principal ganha oito colunas ([`contratos/documentos-csv.md`](../contracts/documentos-csv.md)).
- Os campos são dados pessoais: a saída passa a concentrar mais informação sensível, o que reforça [ADR-009](ADR-009-execucao-local.md).
- A extração de campos de `outros` (procurações, comprovantes) fica para trabalho futuro.
