# ADR-009: Execução local dos modelos

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Os documentos são pessoais (identidade, CPF, CNH, comprovantes) e estão sujeitos à LGPD.

## Decisão

Todos os modelos (OCR, classificadores, detecção de injeção) rodam em infraestrutura própria da instituição. Nenhum documento ou trecho extraído é enviado a API externa.

## Consequências

- Necessidade de GPU para treino e, conforme o volume, para inferência.
- Modelos escolhidos devem ter pesos abertos e licença compatível ([P7](../../.specify/memory/constitution.md#p7-licenças-compatíveis)).
- Serviços de OCR ou classificação em nuvem ficam fora de escopo.
