# ADR-016: Inventário com pikepdf e neutralização própria de fórmulas

- **Status:** Aceito
- **Data:** 2026-11-21
- **Altera:** [ADR-005](ADR-005-deteccao-nao-bloqueante.md) (troca do `pdfid`) e [ADR-006](ADR-006-alertas-em-csv.md) (troca do `defusedcsv` e regra de aspas)

## Contexto

A implementação das tarefas T024 a T030 da [especificação 001](../../specs/001-pipeline-documental-seguro/spec.md) usou componentes diferentes dos previstos em dois pontos:

- O ADR-005 previa o `pdfid` para conteúdo ativo. O `pdfid` conta palavras-chave nos bytes brutos do PDF, o mesmo que as regras YARA já fazem. Ele também não vê nomes dentro de fluxos de objetos comprimidos.
- O ADR-006 previa o `defusedcsv` para neutralizar fórmulas. A [RN-014](../domain/business-rules.md#rn-014) já define a regra exata: NFC, remoção de caracteres de controle e `Cf` e apóstrofo antes de `=`, `+`, `-`, `@`, tabulação ou retorno de carro.

## Decisão

1. **Conteúdo ativo:** inventário estrutural com `pikepdf`, percorrendo o grafo de objetos do PDF já descomprimido (JavaScript, ações automáticas, `Launch`, arquivos embutidos, formulários, RichMedia), mais as regras YARA sobre os bytes originais e o ClamAV. O `pdfid` não é usado.
2. **Neutralização:** função própria em `visiondoc.csv_seguro`, que implementa exatamente a RN-014. O `defusedcsv` não é usado.
3. **Aspas:** o CSV usa aspas duplas em todos os campos de texto, e números sem aspas, conforme a [RN-017](../domain/business-rules.md#rn-017) e os exemplos dos contratos. Isso substitui "aspas em todos os campos" do ADR-006.

## Alternativas consideradas

| Alternativa | Motivo de não adotar |
|---|---|
| Manter o `pdfid` | Duplica as regras YARA e não lê fluxos de objetos comprimidos |
| Manter o `defusedcsv` | Dependência a mais para uma regra de poucas linhas, cujo comportamento precisaria ser conferido contra a RN-014 |

## Consequências

- Uma dependência a menos para cada função ([P8](../../.specify/memory/constitution.md)).
- A neutralização é testada diretamente contra a RN-014 (`tests/backend/test_csv_seguro.py`).
- O inventário estrutural detecta conteúdo ativo que a varredura por palavras-chave não vê; ofuscações que o `pikepdf` não normalize continuam possíveis, e a ausência de alerta segue sem significar segurança.
