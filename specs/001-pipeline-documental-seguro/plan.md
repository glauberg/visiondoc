# Plano: pipeline documental multimodal seguro

- **Especificação:** [`spec.md`](spec.md)
- **Estado:** aprovado em 2026-11-21 por Bruno Silva. Questões abertas que não impedem a aprovação: Q-23 (prova de conceito do `vLLM` em 8 bits na GPU de 8 GB) e Q-25 (governança de dados para uso operacional futuro)
- **Última atualização:** 2026-11-21

## Abordagem

Implementar o pipeline em Python 3.12 ou 3.13 como uma sequência de etapas com contratos explícitos entre si, seguindo a [arquitetura lógica 2.0](../../docs/architecture/overview.md) e os [componentes tecnológicos](../../docs/architecture/components.md):

1. **Ingestão e saneamento:** validar formato real, tamanho e limites; calcular SHA-256; inventariar e remover conteúdo ativo de PDF, extrair texto nativo e rasterizar a 300 DPI; decodificar JPEG isolado com Pillow, descartar metadados e convertê-lo em PDF de uma página.
2. **Pré-processamento:** normalizar orientação, inclinação, espelhamento (comparação da confiança do OCR), contraste e ruído, registrando a transformação para converter `bbox` à página original.
3. **Transcrição:** PaddleOCR-VL gera inteiro teor e caixas por página.
4. **Detecção e mascaramento:** correlacionar conteúdo ativo (inventário com `pikepdf`, YARA, ClamAV; [ADR-016](../../docs/decisions/ADR-016-inventario-e-neutralizacao.md)), texto oculto e injeção (llm-guard); mascarar regiões localizadas na imagem e na transcrição enviadas ao VLM; falha de detector gera `falha_deteccao`.
5. **VLM:** Qwen3.5-4B + LoRA ([ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)) servido por `vLLM` com pesos em 8 bits (FP8 ou INT8) e adaptador LoRA sobre o modelo quantizado, instrução fixa, conteúdo delimitado, decodificação estruturada e temperatura 0.
6. **Validação:** esquema, confiança (limiar inicial 0,5), pertinência, respaldo com normalização canônica, consistência de CPF e datas, e junção de frente e verso.
7. **Saída:** `documentos_<id_lote>.csv` e `alertas_AAAA-MM-DD.csv` higienizados, com retenção em memória, regravação de alertas ao fim do lote e arquivo de contingência.

Em paralelo ao pipeline, o treino do adaptador com QLoRA 4 bits (BID + `br-doc-extraction`, rastreado em MLflow) e um módulo de avaliação separado.

Cada etapa recebe e devolve objetos tipados (`pydantic`); nenhuma etapa interpreta conteúdo documental como instrução. Falha em um documento produz linha de erro com `motivo_erro` sem interromper o lote. Detecção nunca bloqueia ([P3](../../.specify/memory/constitution.md)).

Seguindo [P8](../../.specify/memory/constitution.md), o primeiro incremento é um processamento em lote local por CLI sobre um conjunto ou partição dos datasets, sem orquestrador nem paralelismo distribuído; Prefect/Airflow e Celery/Ray só entram com necessidade demonstrada. Com uma GPU de 8 GB, as etapas que usam modelos podem precisar rodar em sequência. Revisão amostral e frontend ficam para especificação futura.

## Componentes afetados

- `src/backend/` (pacote `visiondoc`, gerenciado com `uv`): ingestão, pré-processamento, transcrição, detecção, chamada ao VLM, validação, gravação dos CSVs, treino LoRA e módulo de avaliação.
- `config/`: `pipeline.yaml` versionado com limiares e parâmetros, validado com `pydantic`; `.env.example` com variáveis de execução local.
- `infrastructure/`: isolamento de parsers/decodificadores, servidor `vLLM` e GPU de 8 GB em infraestrutura própria.
- `tests/backend/`: testes `pytest` com dados sintéticos.
- `src/frontend/` e `tests/frontend/`: sem alteração neste incremento.

## Interfaces e contratos

| Fronteira | Contrato |
|---|---|
| Entrada do lote | Arquivos dos datasets BID e `br-doc-extraction`; `id_processo` = `<dataset>:<arquivo>` ([RN-001](../../docs/domain/business-rules.md#rn-001)); limites de [pdf-ingestion](../../docs/security/pdf-ingestion.md) |
| Ingestão → pré-processamento | Páginas rasterizadas a 300 DPI, texto nativo separado, inventário de conteúdo ativo, identificação (nome, SHA-256, data/hora ISO 8601 com fuso local) |
| Pré-processamento → transcrição | Imagem colorida normalizada + transformação de coordenadas |
| Transcrição → detecção | Inteiro teor em ordem de leitura + caixas por página |
| Detecção → VLM | Imagem e transcrição mascaradas + ocorrências |
| VLM → validação | JSON do [contrato da saída do VLM](../../docs/contracts/saida-vlm.md) + logprobs do tipo |
| Validação → saída | Linha do [`documentos.csv` 2.1](../../docs/contracts/documentos-csv.md) + ocorrências do [`alertas.csv` 2.1](../../docs/contracts/alertas-csv.md) |
| Avaliação | Previsões e referências das partições de teste → métricas de [dados e avaliação](../../docs/domain/evaluation.md) |

Nenhum detalhe de contrato não decidido deve ser presumido na implementação; o código lê limiares de `config/pipeline.yaml`, não de constantes.

## Dados, segurança e privacidade

- **Fluxo de dados:** documentos e derivados permanecem na infraestrutura própria do início ao fim; o `vLLM` roda localmente; não há chamada a serviço externo ([ADR-009](../../docs/decisions/ADR-009-execucao-local.md)).
- **Controles:** parsers e decodificadores isolados e sem rede; nenhuma execução de conteúdo; instrução de sistema fixa e versionada; saída restrita ao esquema; validação contra a transcrição; neutralização de fórmulas e remoção de caracteres invisíveis em todos os campos textuais.
- **Dependências externas:** apenas bibliotecas e pesos de modelos com licença verificada na versão adotada (llm-guard e seu modelo, Qwen3.5-4B, PaddleOCR-VL); Prompt Guard 2 só em experimento, após verificação de licença.
- **Logs:** sem conteúdo documental; somente identificadores, etapas, durações e códigos de erro.
- **Intermediários:** apagados ao final do lote, inclusive em falha ([ING-SEC-11](../../docs/security/pdf-ingestion.md)).
- **Dados:** apenas dados sintéticos/fictícios públicos (BID e `br-doc-extraction`); dados reais e documentos de processos judiciais não são admitidos para treinamento nem testes nesta fase.

## Estratégia de validação

Todos os testes usam dados sintéticos (BID, `br-doc-extraction`, composições e injeções sintéticas). Cada critério de aceitação da especificação é coberto:

- **Ingestão:** remoção dos intermediários ao final do lote, inclusive em falha; PDF/JPEG válidos, extensão falsa, tamanho de 1.999.999 e 2.000.000 bytes, mais de 50 páginas, lado maior acima de 10.000 px, PDF com JavaScript/ação automática/anexo/formulário (inventariado e nunca executado), PDF criptografado/corrompido (`arquivo_ilegivel`), JPEG convertido sem reamostragem e com metadados descartados.
- **Pré-processamento:** imagens giradas em 90/180/270°, inclinadas e espelhadas; conversão de `bbox` para a página original.
- **Detecção e mascaramento:** texto com fonte < 1 pt, cor do fundo, caracteres de largura zero, divergência nativo × transcrição (`partial_ratio` < 80), instruções em português e inglês nos limiares 0,5 e 0,9, regras YARA iniciais e assinatura de teste do ClamAV; conferir `mascarado = sim`, inteiro teor completo e `falha_deteccao` com detector indisponível.
- **Validação:** saída fora do esquema (`validacao = falhou`), tipo abaixo de 0,5, campo não pertinente, campo sem respaldo com datas e CPF em formatos impressos variados, CPF com dígito inválido, datas antes de 1900, futuras ou fora de ordem, critério `ok`/`parcial`, junção de frente e verso com campo divergente.
- **Saída:** conformidade de esquema dos dois CSVs, `motivo_erro`, neutralização de fórmulas (`=`, `+`, `-`, `@`, tabulação, retorno de carro), truncamento em 500 caracteres, NFC, `inteiro_teor` restrito ao `bbox` e leitura com `pandas`.
- **Falhas:** arquivo de alertas indisponível (regravação ao fim do lote), regravação indisponível (contingência e código de saída), falha de uma etapa em um documento (linha de erro, lote continua).
- **Meta de 90%:** 1 − CER dos campos extraídos por tipo, nas partições de teste do BID e do `br-doc-extraction`; a meta vale para cada dataset separadamente.
- **Análise de desempenho da classificação (RNF-SDD-10):** módulo de avaliação separado do pipeline que gera acurácia, F1 macro e precisão/revocação/F1 por classe sobre os documentos aceitos, com a cobertura, e matriz de confusão (absoluta e normalizada por linha, com coluna `indefinido`), para tipo e para tipo e face, com pareamento por IoU ≥ 0,5 e IC 95% por *bootstrap* com 1.000 reamostragens. Proposta de componentes: `scikit-learn` e `matplotlib`, sujeitos à verificação de licença. O módulo é testado com casos de previsões conhecidas cujo resultado é calculado à mão.
- **Relatório de treinamento (RF-SDD-18):** gerador que recebe as métricas do módulo de análise, as informações de ambiente (`torch.cuda`, `platform`, versões dos pacotes), do modelo (contagem de parâmetros pelo `peft`), dos dados e dos tempos de treino e inferência, e grava `relatorio.md`, gráficos PNG (`matplotlib`) e `metricas.json`. É chamado ao fim do treino e da avaliação da linha de base. Testado com uma execução sintética fictícia, verificando a presença de cada seção e dos gráficos e a ausência de nome de máquina e caminhos locais.

Os testes dos modelos (PaddleOCR-VL, Qwen3.5-4B, detector de injeção) são separados dos testes unitários e substituídos por dublês nos testes das demais etapas.

## Riscos, dependências e decisões

- **Injeção não detectada** influencia o VLM dentro do esquema → mascaramento, instrução fixa, esquema fechado e validação contra a transcrição; medir taxa de sucesso de injeção com e sem mitigação.
- **Falso positivo de mascaramento** remove campos legítimos → medir e calibrar os limiares iniciais.
- **Alucinação** → respaldo obrigatório ([RN-024](../../docs/domain/business-rules.md#rn-024)); medir taxa de campos sem respaldo.
- **GPU de 8 GB** → modelo de 4B com QLoRA no ajuste e 8 bits na inferência; risco de capacidade menor que a do 9B e de perda de precisão pela diferença entre 4 bits no ajuste e 8 bits na inferência, medida na avaliação.
- **Suporte do `vLLM`** a Qwen3.5 multimodal com LoRA sobre modelo em 8 bits → versão fixada nas dependências e prova de conceito antes do código; se falhar, a decisão volta a ADR (Q-23).
- **Diferença sintético × real** → não mensurável nesta fase; relatórios explicitam que os resultados não comprovam desempenho em documentos reais.
- **Ausência de trilha de auditoria** limita a reconstituição em produção ([ADR-007](../../docs/decisions/ADR-007-remocao-auditoria.md)).

Não iniciar implementação enquanto a especificação não for aprovada.

## Etapas

1. Executar a prova de conceito: Qwen3.5-4B em 8 bits com adaptador LoRA no `vLLM`, na GPU de 8 GB, com imagem, transcrição, JSON estruturado e logprobs (Q-23).
2. Especificação e plano aprovados em 2026-11-21.
3. Preparar a base de engenharia (`uv`, `pytest`, `ruff`, pacote `visiondoc`), `config/pipeline.yaml` e o carregamento e particionamento dos datasets.
4. Implementar ingestão, identificação e linhas de erro.
5. Implementar pré-processamento e transcrição.
6. Implementar detecção, mascaramento e gravação de alertas com regravação e contingência.
7. Treinar o adaptador LoRA e medir o *zero-shot* como linha de base.
8. Implementar a chamada ao VLM, a validação, a junção de frente e verso e o CSV principal.
9. Implementar o módulo de análise de desempenho da classificação e o gerador do relatório de treinamento.
10. Executar avaliação, análise das confusões, revisão de segurança e verificação dos critérios de aceitação.
