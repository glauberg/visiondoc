# Especificação de segurança: detecção de conteúdo malicioso

## Objetivo e escopo

Definir como correlacionar sinais de conteúdo ativo, texto oculto, injeção de prompt e adulteração visual sem executar conteúdo ou interromper o pipeline principal. Esta especificação deriva de RF-08, RF-09 e RNF-02 em [requisitos do domínio](../domain/requirements.md) e do [ADR-012](../decisions/ADR-012-deteccao-antes-do-vlm.md).

## Fontes de sinal

- Inventário estrutural de conteúdo ativo gerado na ingestão com `pikepdf` ([ADR-016](../decisions/ADR-016-inventario-e-neutralizacao.md)), regras YARA iniciais (JavaScript, `OpenAction`, `Launch`, `EmbeddedFile`, `AcroForm`) e ClamAV.
- Diferenças entre texto nativo do PDF e texto OCR, relacionadas por página/região (`partial_ratio` < 80).
- Sinais visuais de texto pequeno, cor semelhante ao fundo ou caracteres invisíveis, quando detectáveis.
- Scanner `PromptInjection` do llm-guard, regras e expressões regulares para instruções potencialmente dirigidas a modelos.
- Saídas de classificação e análise de imagem, incluindo indícios de adulteração visual.
- Incompatibilidade entre instruções detectadas e classe documental como evidência auxiliar, nunca como prova isolada.

## Requisitos

- **MAL-SEC-01 — Não executar:** evidências, instruções e anexos detectados permanecem dados; não podem alterar prompts de sistema, políticas, ferramentas, permissões ou fluxo de controle.
- **MAL-SEC-02 — Correlação:** correlacionar sinais por arquivo, página e região quando disponíveis, preservando a origem de cada sinal.
- **MAL-SEC-03 — Incerteza:** classificador e regras devem produzir resultado com versão e evidência suficiente para revisão. Não declarar documento seguro só porque nada foi detectado.
- **MAL-SEC-04 — Categoria e localização:** cada ocorrência inclui categoria, severidade, referência de página/região e resumo da evidência. Categorias: `conteudo_ativo`, `texto_oculto`, `injecao_prompt`, `campo_sem_respaldo`, `dado_inconsistente` e `falha_deteccao`.
- **MAL-SEC-05 — Limites da evidência:** incompatibilidade com a classe prevista é sinal de contexto, não confirmação de ataque; um indício visual não autentica nem confirma adulteração.
- **MAL-SEC-06 — Continuidade:** a detecção roda antes do VLM, não bloqueia extração nem exportação e gera alerta. Regiões conhecidas são mascaradas na entrada do VLM.
- **MAL-SEC-07 — Falha do detector:** falha ou indisponibilidade não pode ser interpretada como ausência de ameaça. Deve produzir uma falha explícita: ocorrência `falha_deteccao` em `alertas.csv`, com o documento seguindo processado ([RN-009](../domain/business-rules.md#rn-009)).
- **MAL-SEC-08 — Evidência hostil:** incluir somente trecho limitado, truncado e escapado no alerta. Não incluir inteiro teor ou texto OCR completo.

## Registro de ocorrência e resposta

O registro de ocorrência contém identificador do processo, hash do arquivo, categoria, severidade, página/região e referência de evidência, além de trecho curto, truncado e escapado. A notificação à equipe de segurança inclui esse trecho limitado. O trecho continua sensível e hostil; não deve ser interpretado ou renderizado como HTML, fórmula ou instrução.

A detecção gera sinalização, mas não quarentena nem interrupção automática. O contrato dos consumidores do CSV exige leitura dos campos de alerta e trata todo texto integral como não confiável. A ausência de alerta não constitui liberação de segurança.

## Critérios de aceitação

- [ ] Casos sintéticos cobrem texto visível, divergência OCR/nativo, sinais de caracteres ocultos, conteúdo ativo, instrução direcionada a modelo e sinal visual.
- [ ] Evidência aponta à página/região e ao mecanismo que originou o sinal quando disponível.
- [ ] A incompatibilidade entre instrução e classe, isoladamente, não é registrada como confirmação de ataque.
- [ ] Conteúdo detectado não é executado nem usado para controlar agente, modelo ou ferramenta.
- [ ] Ocorrência sinalizada acompanha a saída e o alerta é disparado sem bloqueio do pipeline.
- [ ] Indisponibilidade do detector produz falha explícita, não uma saída interpretável como “sem ameaças”.
- [ ] O mesmo trecho de evidência limitado, truncado e escapado acompanha o alerta; o registro não contém inteiro teor ou texto OCR completo.

## Decisões registradas

- Regras, classificador e componentes: [componentes tecnológicos](../architecture/components.md).
- Categorias e severidades: [RN-009](../domain/business-rules.md#rn-009), [RN-010](../domain/business-rules.md#rn-010), [RN-011](../domain/business-rules.md#rn-011) e [RN-026](../domain/business-rules.md#rn-026).
- Limiares iniciais por mecanismo, ajustáveis em `config/pipeline.yaml`: [RN-010](../domain/business-rules.md#rn-010).
- Falha do detector: ocorrência `falha_deteccao`, severidade `media`, documento segue processado.
- Avaliação de falsos positivos e falsos negativos: com injeções sintéticas, conforme [dados e avaliação](../domain/evaluation.md).

## Decisões pendentes

- Critérios de correlação entre sinais além das regras de elevação de severidade (RN-011 e RN-026).
- Tratamento de indícios de adulteração visual, que ainda não têm categoria nem detector definidos.
- Retenção de `alertas.csv` e das evidências para eventual uso operacional (Q-25 da [especificação 001](../../specs/001-pipeline-documental-seguro/spec.md)).

