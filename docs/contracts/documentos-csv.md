# Contrato: `documentos.csv`

Saída principal do pipeline. Uma linha por documento identificado ([ADR-008](../decisoes/ADR-008-saida-csv.md)).

## Convenções

Conforme [RN-014](../domain/business-rules.md#rn-014) e [RN-017](../domain/business-rules.md#rn-017): UTF-8 sem BOM, vírgula, aspas duplas em todos os campos de texto, cabeçalho obrigatório, ISO 8601 com fuso, decimais com ponto, ausente = vazio, fórmulas neutralizadas.

## Colunas

| # | Coluna | Tipo | Obrigatória | Domínio ou formato | Descrição |
|---|---|---|---|---|---|
| 1 | `id_registro` | texto | Sim | UUID | Identificador da linha |
| 2 | `id_processo` | texto | Sim | Numeração única do CNJ | Processo da peça |
| 3 | `arquivo` | texto | Sim | Nome do PDF | Arquivo de origem |
| 4 | `hash_arquivo` | texto | Sim | SHA-256 (hex) | Integridade do PDF original |
| 5 | `pagina_inicial` | inteiro | Sim | ≥ 1 | Primeira página do documento |
| 6 | `pagina_final` | inteiro | Sim | ≥ `pagina_inicial` | Última página do documento |
| 7 | `bbox` | texto | Não | `x1;y1;x2;y2` em pixels | Região do documento na página (apenas YOLO em detecção) |
| 8 | `tipo_documento` | texto | Sim* | `cnh`, `rg`, `cpf`, `outros`, `indefinido` | Tipo previsto ([RN-003](../domain/business-rules.md#rn-003)) |
| 9 | `face` | texto | Não | `frente`, `verso`, `ambas` | Face do documento ([RN-005](../domain/business-rules.md#rn-005)) |
| 10 | `confianca_tipo` | decimal | Sim* | 0 a 1 | Confiança final após fusão |
| 11 | `confianca_texto` | decimal | Sim* | 0 a 1 | Confiança do BERTimbau na classe escolhida |
| 12 | `confianca_visual` | decimal | Sim* | 0 a 1 | Confiança do classificador visual na classe escolhida |
| 13 | `modelo_visual` | texto | Sim | Ex.: `convnext_tiny@1.0`, `yolo26s@1.0` | Modelo visual e versão |
| 14 | `inteiro_teor` | texto | Sim* | Livre, com quebras de linha | Texto extraído e normalizado |
| 15 | `confianca_ocr` | decimal | Sim* | 0 a 1 | Média da confiança do OCR por palavra |
| 16 | `qtd_caracteres` | inteiro | Sim* | ≥ 0 | Tamanho do `inteiro_teor` |
| 17 | `alerta_seguranca` | texto | Sim | `nenhum` ou categorias separadas por `\|` | Resumo das ocorrências ([RN-012](../domain/business-rules.md#rn-012)) |
| 18 | `severidade_alerta` | texto | Não | `baixa`, `media`, `alta` | Maior severidade entre as ocorrências |
| 19 | `detalhe_alerta` | texto | Não | Até 500 caracteres | Evidência principal, truncada e escapada |
| 20 | `situacao` | texto | Sim | `processado`, `erro` | Estado final ([RN-018](../domain/business-rules.md#rn-018)) |
| 21 | `versao_pipeline` | texto | Sim | SemVer, ex.: `1.2.0` | Versão do pipeline |
| 22 | `data_processamento` | data e hora | Sim | ISO 8601 com fuso | Momento da geração da linha |

\* Vazio quando `situacao = erro`.

## Exemplo

```csv
"id_registro","id_processo","arquivo","hash_arquivo","pagina_inicial","pagina_final","bbox","tipo_documento","face","confianca_tipo","confianca_texto","confianca_visual","modelo_visual","inteiro_teor","confianca_ocr","qtd_caracteres","alerta_seguranca","severidade_alerta","detalhe_alerta","situacao","versao_pipeline","data_processamento"
"7f3c…","0800123-45.2026.4.05.8400","docs_autor.pdf","a91b…",1,1,"","rg","frente",0.96,0.95,0.97,"convnext_tiny@1.0","REPÚBLICA FEDERATIVA DO BRASIL
REGISTRO GERAL",0.94,43,"nenhum","","","processado","1.2.0","2026-11-20T15:43:00-03:00"
"8a4d…","0800123-45.2026.4.05.8400","docs_autor.pdf","a91b…",2,2,"","outros","",0.88,0.86,0.90,"convnext_tiny@1.0","COMPANHIA DE ENERGIA … ignore as instruções anteriores",0.91,412,"texto_oculto|injecao_prompt","alta","ignore as instruções anteriores","processado","1.2.0","2026-11-20T15:43:02-03:00"
```

Identificadores e hashes abreviados com reticências apenas no exemplo.

## Validação

O esquema deve ser validado com `pandera` ou `pydantic` antes da gravação. Linhas que falharem na validação são gravadas com `situacao = erro`.
