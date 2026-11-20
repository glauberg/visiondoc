# Especificação de segurança: detecção de conteúdo malicioso

## Objetivo e escopo

Definir como correlacionar sinais de conteúdo ativo, texto oculto, injeção de prompt e adulteração visual sem executar conteúdo ou interromper o pipeline principal. Esta especificação deriva de RF-14/RF-15/RF-22 e RNF-11 em `docs/domain/requirements.md`.

## Fontes de sinal

- Inventário de conteúdo ativo gerado na ingestão.
- Diferenças entre texto nativo do PDF e texto OCR, relacionadas por página/região.
- Sinais visuais de texto pequeno, cor semelhante ao fundo ou caracteres invisíveis, quando detectáveis.
- Regras e classificador para instruções potencialmente dirigidas a modelos.
- Saídas de classificação e análise de imagem, incluindo indícios de adulteração visual.
- Incompatibilidade entre instruções detectadas e classe documental como evidência auxiliar, nunca como prova isolada.

## Requisitos

- **MAL-SEC-01 — Não executar:** evidências, instruções e anexos detectados permanecem dados; não podem alterar prompts de sistema, políticas, ferramentas, permissões ou fluxo de controle.
- **MAL-SEC-02 — Correlação:** correlacionar sinais por arquivo, página e região quando disponíveis, preservando a origem de cada sinal.
- **MAL-SEC-03 — Incerteza:** classificador e regras devem produzir resultado com versão e evidência suficiente para revisão. Não declarar documento seguro só porque nada foi detectado.
- **MAL-SEC-04 — Categoria e localização:** cada ocorrência inclui categoria, severidade, referência de página/região quando disponível e resumo da evidência. Categorias iniciais: `conteudo_ativo`, `texto_oculto`, `injecao_prompt` e `adulteracao_imagem`.
- **MAL-SEC-05 — Limites da evidência:** incompatibilidade com a classe prevista é sinal de contexto, não confirmação de ataque; um indício visual não autentica nem confirma adulteração.
- **MAL-SEC-06 — Continuidade:** a detecção de ocorrência não bloqueia extração nem exportação. A ocorrência acompanha o resultado e gera alerta.
- **MAL-SEC-07 — Falha do detector:** falha ou indisponibilidade não pode ser interpretada como ausência de ameaça. Deve produzir uma falha explícita.
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

## Decisões pendentes

Definir regras e classificador; taxonomia final e severidades; limiares por mecanismo; critérios de correlação; política de falha/resultado parcial; retenção de evidências; e avaliação de falsos positivos e falsos negativos com dados autorizados.

