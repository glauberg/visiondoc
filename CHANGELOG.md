# Histórico de mudanças da especificação

## 2.1 — 2026-11-21: resolução das pendências da especificação 001

As 27 questões da [especificação 001](specs/001-pipeline-documental-seguro/spec.md) foram respondidas: 24 foram resolvidas, 2 resolvidas em parte (Q-23 e Q-25) e 1 adiada (Q-26).

- **Modelo:** Qwen3.5-4B com QLoRA 4 bits no ajuste e pesos em 8 bits na inferência, por GPU de 8 GB ([ADR-015](docs/decisions/ADR-015-vlm-qwen35-4b.md), altera o ADR-010); o `vLLM` adotado deve suportar Qwen3.5 multimodal com LoRA sobre modelo quantizado, confirmado por prova de conceito.
- **Entrada:** arquivos dos datasets BID e `br-doc-extraction`, com `id_processo` sintético `<dataset>:<arquivo>` ([RN-001](docs/domain/business-rules.md#rn-001)); JPEG convertido em PDF de uma página; limites de ingestão; EXIF apenas auxiliar.
- **Regras:** RN-004, 009, 010, 013, 016, 017, 018, 024, 025 e 027 complementadas; RN-029 nova (junção de frente e verso).
- **Contratos 2.1:** `motivo_erro`, `falha_deteccao`, arquivo por lote, `inteiro_teor` restrito ao `bbox`, `bbox` em pixels da página original a 300 DPI.
- **Implementação T024–T030:** inventário de conteúdo ativo com `pikepdf` no lugar do `pdfid` e neutralização própria conforme RN-014 no lugar do `defusedcsv`; aspas só nos campos de texto ([ADR-016](docs/decisions/ADR-016-inventario-e-neutralizacao.md), altera os ADR-005 e ADR-006).
- **Engenharia:** Python 3.12, `uv`, `pytest`, `ruff`, `config/pipeline.yaml` validado com `pydantic`, llm-guard como detector de injeção.
- **Avaliação:** meta de 90% sobre os campos extraídos; análise de acurácia, F1 macro e matriz de confusão sobre documentos aceitos, com cobertura, IoU ≥ 0,5 e IC por *bootstrap*.
- **Escopo:** treino LoRA incluído; revisão amostral e frontend adiados.
- **Dados:** a fase de desenvolvimento e testes não admite dados reais nem documentos de processos judiciais, nem para treinamento nem para teste; removidas as referências ao conjunto da JFRN, inclusive nos ADR-003 e ADR-010.
- **Ajustes finais e aprovação:** `pandas` como leitor de CSV; Pillow como decodificador de JPEG na ingestão; intermediários apagados ao final do lote (ING-SEC-11); meta de 90% válida para cada um dos dois datasets; pendências resolvidas retiradas da especificação de detecção maliciosa; seções de estado removidas dos READMEs; especificação e plano 001 aprovados por Bruno Silva em 2026-11-21.
- **Documentos alinhados:** `agents.md`, `.env.example`, `config/README.md`, `README.md`, arquitetura, contratos, regras, avaliação, governança e documentos de segurança.

## 2.0 — 2026-11-20: adoção do VLM Qwen3.5-9B ajustado com LoRA

Motivação: atender requisito explícito do trabalho proposto como  *"Classificação e extração de informações de documentos em processos judiciais: uma abordagem multimodal baseada em Modelos de Linguagem Visuais"*.

### Arquitetura

- **Novo modelo central:** Qwen3.5-9B ajustado com LoRA, para localização, classificação e extração de campos ([ADR-010](docs/decisions/ADR-010-vlm-qwen35-9b-lora.md)).
- **Nova transcrição:** PaddleOCR-VL 1.6 produz o inteiro teor e serve de referência para a validação ([ADR-011](docs/decisions/ADR-011-transcricao-paddleocr-vl.md)).
- **Detecção antes do VLM**, com mascaramento das regiões suspeitas na entrada do modelo ([ADR-012](docs/decisions/ADR-012-deteccao-antes-do-vlm.md)).
- **Nova etapa de validação** da saída do VLM ([ADR-013](docs/decisions/ADR-013-validacao-saida-vlm.md)).
- **Extração de campos** volta ao escopo ([ADR-014](docs/decisions/ADR-014-extracao-de-campos.md)).
- **Removidos do pipeline:** ConvNeXt-Tiny, BERTimbau e fusão (viram linhas de base nos experimentos); YOLO (descartado).

### Arquivos novos

- `docs/decisions/ADR-010-vlm-qwen35-9b-lora.md`
- `docs/decisions/ADR-011-transcricao-paddleocr-vl.md`
- `docs/decisions/ADR-012-deteccao-antes-do-vlm.md`
- `docs/decisions/ADR-013-validacao-saida-vlm.md`
- `docs/decisions/ADR-014-extracao-de-campos.md`
- `docs/contracts/saida-vlm.md`
- `CHANGELOG.md`

### Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `README.md` | Novo título, diagrama, etapas e pendências |
| `.specify/memory/constitution.md` | P2 revisado para o caso de modelo generativo no fluxo |
| `docs/decisions/README.md` | Índice separado entre vigentes e substituídos |
| `docs/decisions/ADR-002`, `ADR-003`, `ADR-004` | Status: substituídos |
| `docs/decisions/ADR-005`, `ADR-008` | Status: alterados por ADRs novos |
| `docs/architecture/components.md` | Reescrito para a pilha com VLM |
| `docs/domain/business-rules.md` | RN-006 revogada; RN-005, 007, 009, 010, 016 e 019 alteradas; RN-021 a RN-028 novas |
| `docs/contracts/documentos-csv.md` | Versão 2.0: colunas de campos, `validacao`, `modelo_vlm`, `modelo_transcricao`; removidas as colunas dos classificadores |
| `docs/contracts/alertas-csv.md` | Versão 2.0: colunas `etapa`, `campo`, `mascarado`; novas categorias |
| `docs/domain/evaluation.md` | Novas métricas e experimentos com VLM |

### Arquivos sem mudança

`docs/decisions/ADR-001`, `ADR-006`, `ADR-007`, `ADR-009`.

## 1.0 — 2026-11-20: versão inicial

Arquitetura com OCR (PaddleOCR), classificador visual (ConvNeXt-Tiny ou YOLO), classificador textual (BERTimbau), fusão por média ponderada, detecção não bloqueante e alertas em CSV.
