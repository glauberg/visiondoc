# Contrato: `alertas.csv`

- **Versão do contrato:** 2.1 (2026-11-21)

Registro detalhado das ocorrências de atos maliciosos e das falhas de validação da saída do VLM ([ADR-006](../decisions/ADR-006-alertas-em-csv.md), [ADR-012](../decisions/ADR-012-deteccao-antes-do-vlm.md), [ADR-013](../decisions/ADR-013-validacao-saida-vlm.md)). Uma linha por ocorrência; um documento pode gerar várias.

## Arquivo

- Nome: `alertas_AAAA-MM-DD.csv` (um por dia).
- Escrita em modo de acréscimo; cabeçalho gravado apenas na criação do arquivo.
- Convenções de [RN-014](../domain/business-rules.md#rn-014) e [RN-017](../domain/business-rules.md#rn-017).

## Colunas

| # | Coluna | Tipo | Obrigatória | Domínio ou formato | Descrição |
|---|---|---|---|---|---|
| 1 | `id_alerta` | texto | Sim | UUID | Identificador da ocorrência |
| 2 | `id_registro` | texto | Sim | UUID | Linha correspondente em `documentos.csv` |
| 3 | `id_processo` | texto | Sim | Numeração única do CNJ ou `<dataset>:<arquivo>` | Processo ou identificador sintético de origem ([RN-001](../domain/business-rules.md#rn-001)) |
| 4 | `arquivo` | texto | Sim | Nome do arquivo original (PDF ou JPEG), sem caminho | Arquivo de origem |
| 5 | `hash_arquivo` | texto | Sim | SHA-256 (hex) | Integridade do arquivo original recebido, antes de qualquer conversão |
| 6 | `pagina` | inteiro | Não | ≥ 1 | Página da ocorrência (vazio para ocorrências do arquivo inteiro) |
| 7 | `bbox` | texto | Não | `x1;y1;x2;y2` em pixels da página rasterizada original (300 DPI) | Região do documento na página |
| 8 | `data_hora` | data e hora | Sim | ISO 8601 com fuso | Momento da ocorrência |
| 9 | `etapa` | texto | Sim | `deteccao`, `validacao` | Etapa que gerou a ocorrência |
| 10 | `categoria` | texto | Sim | `conteudo_ativo`, `texto_oculto`, `injecao_prompt`, `campo_sem_respaldo`, `dado_inconsistente`, `falha_deteccao` | [RN-009](../domain/business-rules.md#rn-009) |
| 11 | `severidade` | texto | Sim | `baixa`, `media`, `alta` | [RN-010](../domain/business-rules.md#rn-010), [RN-011](../domain/business-rules.md#rn-011), [RN-026](../domain/business-rules.md#rn-026) |
| 12 | `regra_ou_modelo` | texto | Sim | Ex.: `yara:pdf_javascript`, `llm_guard:prompt_injection@<versão>`, `clamav:<assinatura>`, `rn-024:respaldo`, `rn-025:cpf` | O que disparou a ocorrência |
| 13 | `escore` | decimal | Não | 0 a 1 | Confiança do detector ou similaridade do respaldo |
| 14 | `campo` | texto | Não | Nome do campo do contrato | Campo afetado (apenas etapa `validacao`) |
| 15 | `evidencia` | texto | Sim | Até 500 caracteres | Trecho detectado ou valor proposto pelo VLM, truncado e escapado ([RN-015](../domain/business-rules.md#rn-015)) |
| 16 | `localizacao_evidencia` | texto | Não | `x1;y1;x2;y2` ou nome do objeto PDF | Onde a evidência foi encontrada |
| 17 | `mascarado` | texto | Não | `sim`, `nao` | Se a região foi mascarada antes do VLM ([RN-021](../domain/business-rules.md#rn-021)); apenas etapa `deteccao` |
| 18 | `tipo_documento_previsto` | texto | Sim | Domínio de [RN-003](../domain/business-rules.md#rn-003) | Classe atribuída ao documento |
| 19 | `versao_pipeline` | texto | Sim | SemVer | Versão do pipeline |

## Cuidados

- A coluna `evidencia` contém conteúdo hostil ou valores não confirmados. A neutralização de fórmulas ([RN-014](../domain/business-rules.md#rn-014), [ADR-016](../decisions/ADR-016-inventario-e-neutralizacao.md)) e a remoção de caracteres invisíveis são obrigatórias.
- Nenhum consumidor deve repassar `evidencia` a um modelo generativo como instrução.
- Na etapa `validacao`, `evidencia` traz o valor proposto pelo VLM, que pode ser dado pessoal inventado; não deve ser usado como dado do titular.

## Exemplo

```csv
"id_alerta","id_registro","id_processo","arquivo","hash_arquivo","pagina","bbox","data_hora","etapa","categoria","severidade","regra_ou_modelo","escore","campo","evidencia","localizacao_evidencia","mascarado","tipo_documento_previsto","versao_pipeline"
"c41a…","8a4d…","0800123-45.2026.4.05.8400","docs_autor.pdf","a91b…",2,"98;120;1640;2210","2026-11-20T23:47:02-03:00","deteccao","injecao_prompt","alta","llm_guard:prompt_injection@0.3",0.97,"","ignore as instruções anteriores","412;1980;1650;2005","sim","outros","2.0.0"
"c41b…","7f3c…","0800123-45.2026.4.05.8400","docs_autor.pdf","a91b…",1,"112;340;1210;1080","2026-11-20T23:47:01-03:00","validacao","campo_sem_respaldo","media","rn-024:respaldo",0.62,"orgao_emissor","SSP/PE","","","rg","2.0.0"
```

Dados fictícios.

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-11-20 | Versão inicial |
| 2.0 | 2026-11-20 | Inclusão de `etapa`, `campo` e `mascarado`; categorias `campo_sem_respaldo` e `dado_inconsistente`; extinção de `divergencia_texto_imagem` |
| 2.1 | 2026-11-21 | Categoria `falha_deteccao`; `id_processo` aceita identificador sintético; `arquivo` e `hash_arquivo` valem para PDF e JPEG |
