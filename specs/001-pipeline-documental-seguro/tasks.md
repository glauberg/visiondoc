# Tarefas: pipeline documental multimodal seguro

- **Especificação:** [`spec.md`](spec.md)
- **Plano:** [`plan.md`](plan.md)
- **Estado:** especificação e plano aprovados em 2026-11-21 por Bruno Silva; pendentes T020 e T022; implementação mediante solicitação explícita
- **Última atualização:** 2026-11-21

Os identificadores `Q-xx` referem-se às questões da especificação.

## Tarefas de definição e aprovação

### Contradições documentais

- [x] **T001** Alinhar [csv-export.md](../../docs/security/csv-export.md) ao contrato `documentos.csv` 2.0 (Q-01) — depende de: nenhuma.
- [x] **T002** Definir padrão de fuso do timestamp e alinhar documentos de segurança e contratos (Q-02) — depende de: nenhuma.
- [x] **T003** Decidir representação de mãe e pai (`filiacao` ou campos com papel) e alinhar `agents.md`, contratos e regras (Q-03) — depende de: nenhuma.
- [x] **T004** Resolver a contradição entre RN-022 e RN-027 sobre `validacao` com falha de esquema (Q-04) — depende de: nenhuma.
- [x] **T005** Definir semântica dos contratos para entrada JPEG (Q-05) — depende de: nenhuma.
- [x] **T006** Revisar `.env.example` e `config/README.md` para inferência local (Q-06) — depende de: nenhuma.

### Lacunas bloqueantes

- [x] **T007** Definir interface de entrada, origem da numeração CNJ e conceito de lote; registrar ADR se necessário (Q-07) — depende de: nenhuma.
- [x] **T008** Definir limites de ingestão, PDFs criptografados/corrompidos e política de EXIF (Q-13, Q-14) — depende de: nenhuma.
- [x] **T009** Definir detecção de espelhamento, DPI de rasterização e imagem de referência do `bbox` (Q-15) — depende de: T008.
- [x] **T010** Definir agrupamento de documentos multipágina, páginas sem documento e escopo do `inteiro_teor` por documento (Q-08, Q-09) — depende de: T005.
- [x] **T011** Definir representação de erros de arquivo, motivo do erro e falha de detector nos contratos (Q-10) — depende de: T004, T005.
- [x] **T012** Definir tratamento da falha de regravação de alertas e nome/particionamento/concorrência do `documentos.csv` (Q-11, Q-12) — depende de: T007.
- [x] **T013** Definir normalização para respaldo, plausibilidade de datas e critério `ok`/`parcial` (Q-16) — depende de: T003, T004.
- [x] **T014** Escolher detector de injeção, verificar licenças e mapear detecções do ClamAV; registrar ADR se necessário (Q-19) — depende de: nenhuma.
- [x] **T015** Definir escopo do primeiro incremento: treino LoRA ou início *zero-shot*; revisão amostral e frontend (Q-17) — depende de: nenhuma.
- [x] **T016** Definir base de engenharia: versão do Python, gerenciador de dependências, framework de testes e estrutura de pacotes (Q-18) — depende de: nenhuma.

### Parâmetros iniciais

- [x] **T017** Definir formato e local da configuração versionada (Q-22) — depende de: T016.
- [x] **T018** Registrar valores iniciais de limiar de rejeição, cálculo de `confianca_tipo`, limiares de injeção e de texto oculto e regras YARA iniciais (Q-20, Q-21) — depende de: T014, T017.

### Aprovação

- [x] **T019** Revisar e aprovar `spec.md` e `plan.md` com as decisões de T001–T018 incorporadas — depende de: T001–T018.

### Antes do uso operacional

- [ ] **T020** Executar prova de conceito do Qwen3.5-4B em 8 bits (FP8 ou INT8) com adaptador LoRA no `vLLM` na GPU de 8 GB (imagem + transcrição → JSON válido com logprobs), fixar a versão do `vLLM` e definir metas de desempenho (Q-23; [ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)) — depende de: T015. *(2026-11-21: scripts e instruções em [`infrastructure/poc-t020/`](../../infrastructure/poc-t020/README.md); aguardando execução na máquina com a GPU de 8 GB, pois a máquina de desenvolvimento não tem GPU NVIDIA. Metas de desempenho definidas em 2026-11-25: ≤ 30 s por página e ≤ 7,5 GB de memória de GPU, como indicadores reportados.)*
- [x] **T021** Definir operacionalmente os 90% e o corpus aprovado (Q-24) — depende de: T003.
- [ ] **T022** *(Necessária só para eventual uso operacional; a fase de desenvolvimento e testes não admite dados reais)* Aprovar avaliação jurídica/privacidade: controlador, base legal, retenção, descarte e acesso (Q-25) — depende de: T007, T012.
- [ ] **T023** *(Adiada para especificação futura — Q-17)* Definir responsáveis, taxa, frequência, papéis e persistência da revisão amostral (Q-26) — depende de: T015, T022.
- [x] **T036** Definir tratamento de `indefinido`, pareamento por IoU, intervalo de confiança e eventuais metas mínimas de acurácia e F1 macro (Q-27) — depende de: T010.

## Tarefas futuras de implementação

Somente após T019 e solicitação explícita.

- [x] **T024** Criar a base do projeto e o conjunto de dados sintéticos de teste — depende de: T016, T019. *(Concluída em 2026-11-21: `pyproject.toml` com `uv`, pacote `visiondoc` em `src/backend/`, `config/pipeline.yaml` validado com `pydantic`, gerador de PDF/JPEG sintéticos em `tests/backend/sintetico.py`, listagem dos datasets e lote que apaga intermediários.)*
- [x] **T025** Implementar ingestão PDF/JPEG, identificação (nome, SHA-256, data/hora e `id_processo` sintético `<dataset>:<arquivo>`, conforme RN-001), saneamento e linhas de erro — depende de: T007, T008, T011, T024. *(Concluída em 2026-11-21: processo isolado com tempo máximo; limite de memória só em POSIX.)*
- [x] **T026** Implementar pré-processamento com mapeamento de coordenadas — depende de: T009, T025. *(Concluída em 2026-11-21: ruído não é tratado, apenas contraste com CLAHE.)*
- [x] **T027** Implementar transcrição com PaddleOCR-VL — depende de: T026. *(Concluída em 2026-11-21 com dublês: adaptadores PaddleOCR-VL, PP-OCR e classificador de orientação não verificados com os modelos reais, que não estão instalados.)*
- [x] **T028** Implementar detecção de conteúdo ativo, texto oculto e injeção, com falha explícita de detector — depende de: T014, T018, T027. *(Concluída em 2026-11-21: adaptador llm-guard e ClamAV não verificados com serviço real; texto da cor do fundo não detectado; elevação de severidade por tipo (RN-011, RN-026) fica para T032/T033.)*
- [x] **T029** Implementar mascaramento na imagem e na transcrição enviadas ao VLM — depende de: T028. *(Concluída em 2026-11-21.)*
- [x] **T030** Implementar `alertas.csv` com higienização, retenção em memória e regravação ao fim do lote — depende de: T002, T012, T028. *(Concluída em 2026-11-21: gravador pronto; o preenchimento de `id_registro` e `tipo_documento_previsto` depende de T031–T033.)*
- [ ] **T031** Implementar chamada ao Qwen3.5-4B via `vLLM` com instrução fixa, esquema estruturado e logprobs do tipo — depende de: T015, T018, T020, T029, T038.
- [ ] **T032** Implementar validação de esquema, confiança, pertinência, respaldo e consistência — depende de: T004, T013, T031.
- [ ] **T033** Implementar `documentos.csv` com agrupamento de documentos, neutralização e validação de esquema — depende de: T010, T011, T012, T032.
- [ ] **T034** *(Fora do primeiro incremento — Q-17)* Implementar revisão amostral e registro de correções — depende de: T015, T023, T033.
- [ ] **T038** Treinar o adaptador LoRA (`br-doc-extraction`, [ADR-017](../../docs/decisions/ADR-017-treino-br-doc-extraction.md)), com particionamento prévio, rastreamento em MLflow e avaliação *zero-shot* como linha de base (RF-SDD-17); ao concluir cada treinamento, gera o relatório da T039 — depende de: T020, T024, T039. *(2026-11-25: código em `visiondoc.treino` e script `infrastructure/colab/t038_colab.py` prontos; testes sem GPU cobrem mapeamento, preparação, rótulos e avaliação. Falta executar no Colab: carga do modelo, coletor, treino e geração não foram rodados.)*
- [x] **T037** Implementar o módulo de análise de desempenho da classificação: acurácia, F1 macro, métricas por classe e matriz de confusão (absoluta e normalizada, com `indefinido`) para tipo e para tipo e face, nos recortes de RNF-SDD-10 — depende de: T024, T036. *(Concluída em 2026-11-25: `visiondoc.avaliacao.metricas`, com pareamento por IoU, IC por *bootstrap*, curva de cobertura, calibração (ECE) e 1 − CER dos campos.)*
- [x] **T039** Implementar o gerador do relatório de treinamento: `relatorio.md`, gráficos PNG e `metricas.json` com identificação, ambiente, modelo, dados, treino, inferência e desempenho, classificação (acurácia, F1 macro, matrizes de confusão), extração e comparação com a linha de base (RF-SDD-18) — depende de: T037. *(Concluída em 2026-11-25: `visiondoc.avaliacao.relatorio`; testado com execução fictícia. A coleta do pico de memória, dos tempos e das curvas de perda depende da T038.)*
- [ ] **T035** Executar avaliação de métricas, análise das matrizes de confusão e das principais confusões, revisão de segurança e verificação dos critérios de aceitação, somente com dados sintéticos — depende de: T021, T030, T033, T037, T039.

## Verificação de conclusão

- [x] Especificação e plano alinhados à documentação 2.0 (2026-11-21).
- [x] Contradições documentais resolvidas (T001–T006).
- [x] Decisões bloqueantes e parâmetros iniciais definidos (T007–T018).
- [x] Especificação e plano aprovados (T019).
- [ ] Critérios de aceitação da especificação atendidos em implementação futura.
- [ ] Validações e controles de segurança/privacidade executados.
- [ ] Documentação e decisões relacionadas atualizadas.
