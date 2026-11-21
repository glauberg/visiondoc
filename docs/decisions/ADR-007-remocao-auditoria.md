# ADR-007: Remoção da trilha de auditoria

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Uma versão anterior previa uma trilha de auditoria transversal: cada etapa emitia um evento estruturado (`structlog`, `OpenTelemetry`) gravado em PostgreSQL somente de inserção, com encadeamento por hash.

## Decisão

Remover a trilha de auditoria da arquitetura.

## Consequências

- A coluna `id_evento_auditoria` sai do CSV principal.
- `versao_pipeline`, `modelo_vlm`, `modelo_transcricao` e `data_processamento` passam a ser o registro de como cada linha foi gerada.
- A evidência dos incidentes fica apenas em `alertas.csv` e nas colunas de alerta do CSV principal.
- Não é possível reconstituir as ações de cada etapa (o que foi removido do PDF, tempo de cada modelo). Para a pesquisa, isso é suprido pela documentação dos experimentos; em produção, a ausência pesa mais.
- Se a rastreabilidade voltar a ser necessária, a forma mais leve é um log JSON por documento, sem componente separado.
