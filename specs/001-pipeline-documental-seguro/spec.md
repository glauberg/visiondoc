# Especificação: pipeline documental multimodal seguro

- **Estado:** aprovada em 2026-11-21 (alinhada à versão 2.1 da documentação)
- **Responsáveis:** Bruno Silva (aprovação)
- **Última atualização:** 2026-11-21
- **Base:** [requisitos do domínio 2.0](../../docs/domain/requirements.md), [regras de negócio](../../docs/domain/business-rules.md), [ADR-010](../../docs/decisions/ADR-010-vlm-qwen35-9b-lora.md) a [ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md) e contratos em [`docs/contracts/`](../../docs/contracts/)

## Contexto e problema

Documentos de identificação anexados à petição inicial precisam ser classificados e ter seus campos extraídos para apoiar a triagem. Os arquivos são não confiáveis e podem conter conteúdo ativo, texto oculto ou instruções dirigidas a modelos.

O pipeline:

1. valida e saneia o arquivo PDF/JPEG;
2. pré-processa a imagem (orientação, inclinação, qualidade);
3. transcreve o inteiro teor com PaddleOCR-VL;
4. detecta conteúdo suspeito e mascara regiões conhecidas;
5. usa Qwen3.5-4B ajustado com LoRA ([ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)) para localizar, classificar e extrair campos em JSON restrito;
6. valida a saída do VLM contra esquema, confiança, pertinência, transcrição e consistência;
7. grava `documentos.csv` e `alertas.csv` com higienização e neutralização de fórmulas.

A detecção não interrompe nem desvia o documento. Os resultados são apoio à triagem e não decidem mérito, autenticidade ou validade jurídica.

## Usuários e partes interessadas

- Pessoas que submetem ou administram documentos.
- Profissionais responsáveis por conferência humana amostral.
- Equipe de segurança que consome os alertas.
- Responsáveis por operação, privacidade e consumidores dos CSVs.
- Pesquisa responsável pela avaliação dos modelos.

## Objetivos

- Receber e preparar com segurança PDF/JPEG estritamente menores que 2.000.000 bytes, em `pt-BR`, em qualquer orientação.
- Classificar cada documento identificado na página em `cnh`, `rg`, `cpf`, `outros` ou `indefinido`, com face e `bbox`.
- Extrair os campos pertinentes a CNH, RG e CPF sem inventar valores ausentes ou ambíguos.
- Validar a saída do VLM contra a transcrição independente antes da gravação.
- Sinalizar conteúdo suspeito em `alertas.csv` e no CSV principal sem bloquear o processamento.
- Operar todos os modelos em infraestrutura própria da instituição.
- Medir as métricas definidas em [dados e avaliação](../../docs/domain/evaluation.md), com alvo mínimo de 90% de precisão em nível de caractere nos campos extraídos, em cada um dos dois datasets (BID e `br-doc-extraction`).

## Fora de escopo

- Uso de dados reais ou de documentos de processos judiciais para treinamento, teste ou avaliação na fase de desenvolvimento e testes.
- Decidir mérito, autenticidade, admissibilidade ou estratégia jurídica.
- Garantir precisão por documento ou detecção integral de ataques.
- Enviar documentos, imagens, transcrições ou campos a serviços externos ou nuvem pública.
- Quarentena, descarte ou bloqueio de documentos suspeitos.
- Extração de campos de documentos `outros` (procurações, comprovantes) — trabalho futuro ([ADR-014](../../docs/decisions/ADR-014-extracao-de-campos.md)).
- Revisão humana amostral e frontend de revisão, adiados para especificação futura (Q-17).
- Trilha de auditoria transversal ([ADR-007](../../docs/decisions/ADR-007-remocao-auditoria.md)).
- Exigir revisão humana de cada documento antes da conclusão.

## Requisitos funcionais

- **RF-SDD-01 — Entrada:** aceitar PDF e JPEG reais (formato verificado além da extensão) com tamanho estritamente menor que 2.000.000 bytes; demais arquivos geram linha com `situacao = erro` ([RF-01](../../docs/domain/requirements.md), [RN-001](../../docs/domain/business-rules.md#rn-001)).
- **RF-SDD-02 — Identificação:** associar cada arquivo à numeração única do CNJ ou, para arquivos carregados dos datasets BID e `tech4humans/br-doc-extraction`, ao identificador sintético `<dataset>:<arquivo>`, e registrar nome, SHA-256 do arquivo original e data/hora ([RN-001](../../docs/domain/business-rules.md#rn-001), [RN-002](../../docs/domain/business-rules.md#rn-002)).
- **RF-SDD-03 — Saneamento:** em PDF, inventariar e remover conteúdo ativo sem executá-lo, preservar o texto nativo separadamente e rasterizar as páginas; em JPEG, decodificar em ambiente isolado, tratar metadados como não confiáveis e converter em PDF de uma página, sem reamostragem, que segue o fluxo do PDF; `arquivo` e `hash_arquivo` referem-se ao original ([ADR-001](../../docs/decisions/ADR-001-entrada-pdf-nao-confiavel.md), [pdf-ingestion](../../docs/security/pdf-ingestion.md)).
- **RF-SDD-04 — Pré-processamento:** corrigir orientação horizontal/vertical, inclinação, rotação (inclusive 180°) e espelhamento, mantendo a relação entre coordenadas normalizadas e de origem ([RF-02](../../docs/domain/requirements.md)).
- **RF-SDD-05 — Transcrição:** produzir, com PaddleOCR-VL, o inteiro teor em ordem de leitura e as caixas de texto de cada página ([ADR-011](../../docs/decisions/ADR-011-transcricao-paddleocr-vl.md)).
- **RF-SDD-06 — Detecção:** antes do VLM, detectar `conteudo_ativo`, `texto_oculto` e `injecao_prompt` sobre o inventário da ingestão, o texto nativo e a transcrição ([RN-009](../../docs/domain/business-rules.md#rn-009), [ADR-012](../../docs/decisions/ADR-012-deteccao-antes-do-vlm.md)).
- **RF-SDD-07 — Mascaramento:** para `injecao_prompt` ou `texto_oculto` com localização conhecida, cobrir a região com retângulo sólido na imagem e substituir o trecho por `[TRECHO REMOVIDO]` na transcrição enviada ao VLM; o inteiro teor e a evidência permanecem completos e higienizados ([RN-021](../../docs/domain/business-rules.md#rn-021)).
- **RF-SDD-08 — VLM:** chamar o Qwen3.5-4B + LoRA, com pesos quantizados em 8 bits servidos por versão do `vLLM` que suporte Qwen3.5, entrada multimodal e LoRA sobre modelo quantizado ([ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)), com instrução de sistema fixa e versionada, imagem e transcrição delimitada no turno do usuário, decodificação estruturada conforme [contrato da saída do VLM](../../docs/contracts/saida-vlm.md) e temperatura 0 ([RN-022](../../docs/domain/business-rules.md#rn-022)).
- **RF-SDD-09 — Localização e classificação:** cada documento identificado na página gera um item com `tipo`, `face` e `bbox`; frente e verso do mesmo tipo em páginas consecutivas são unidos em uma linha com `face = ambas`, e página sem documento de identificação gera linha `outros` ([RN-029](../../docs/domain/business-rules.md#rn-029)); `indefinido` é atribuído apenas pela regra de confiança, calculada a partir dos logprobs ([RN-003](../../docs/domain/business-rules.md#rn-003), [RN-004](../../docs/domain/business-rules.md#rn-004), [RN-007](../../docs/domain/business-rules.md#rn-007)).
- **RF-SDD-10 — Extração:** extrair `nome`, `cpf`, `numero_documento`, `data_nascimento`, `data_emissao`, `data_validade`, `orgao_emissor`, `filiacao`, `naturalidade`, `doc_origem` e `categoria_habilitacao`, conforme a tabela de pertinência por tipo do contrato; campo ilegível ou ausente fica vazio ([ADR-014](../../docs/decisions/ADR-014-extracao-de-campos.md), [RN-023](../../docs/domain/business-rules.md#rn-023), [RN-028](../../docs/domain/business-rules.md#rn-028)).
- **RF-SDD-11 — Validação:** validar esquema, confiança, pertinência ao tipo, respaldo de cada campo na transcrição e consistência de CPF e datas; campo sem respaldo é esvaziado; falhas geram ocorrências `campo_sem_respaldo` ou `dado_inconsistente` ([ADR-013](../../docs/decisions/ADR-013-validacao-saida-vlm.md), [RN-024](../../docs/domain/business-rules.md#rn-024) a [RN-027](../../docs/domain/business-rules.md#rn-027)).
- **RF-SDD-12 — Alertas:** cada ocorrência gera uma linha em `alertas_AAAA-MM-DD.csv`; o CSV principal resume categorias e maior severidade; severidade segue [RN-010](../../docs/domain/business-rules.md#rn-010), [RN-011](../../docs/domain/business-rules.md#rn-011) e [RN-026](../../docs/domain/business-rules.md#rn-026). Falha de gravação mantém o alerta em memória e o regrava ao fim do lote, sem interromper o documento ([RN-012](../../docs/domain/business-rules.md#rn-012), [RN-013](../../docs/domain/business-rules.md#rn-013)).
- **RF-SDD-13 — CSV principal:** gerar uma linha por documento identificado conforme o [contrato `documentos.csv` 2.0](../../docs/contracts/documentos-csv.md), validada antes da gravação; erro de processamento gera linha `situacao = erro` com `motivo_erro` sem interromper os demais documentos ([RN-018](../../docs/domain/business-rules.md#rn-018)); `inteiro_teor` é restrito ao `bbox` do documento ([RN-016](../../docs/domain/business-rules.md#rn-016)).
- **RF-SDD-14 — Segurança do CSV:** normalizar NFC, remover caracteres de controle e `Cf` (exceto quebras de linha do inteiro teor), neutralizar fórmulas e truncar evidências em 500 caracteres ([RN-014](../../docs/domain/business-rules.md#rn-014), [RN-015](../../docs/domain/business-rules.md#rn-015), [RN-017](../../docs/domain/business-rules.md#rn-017)).
- **RF-SDD-15 — Versão:** toda linha registra `versao_pipeline`, `modelo_vlm`, `modelo_transcricao` e `data_processamento` ([RN-019](../../docs/domain/business-rules.md#rn-019)).
- **RF-SDD-16 — Revisão amostral:** permitir seleção aleatória de documentos para conferência humana e registrar conferências e correções de forma rastreável, sem pré-condição por documento nem coluna obrigatória no CSV ([RF-07](../../docs/domain/requirements.md)). **Fora do primeiro incremento:** adiado para especificação futura (Q-17).
- **RF-SDD-17 — Ajuste LoRA:** treinar o adaptador do Qwen3.5-4B com QLoRA 4 bits conforme [ADR-010](../../docs/decisions/ADR-010-vlm-qwen35-9b-lora.md), [ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md) e [ADR-017](../../docs/decisions/ADR-017-treino-br-doc-extraction.md): nesta fase, só com o `tech4humans/br-doc-extraction` e suas partições, `invoice` como `outros`, `face` nula, `bbox` da imagem inteira e campos sem anotação fora da perda; exemplos no formato do [contrato da saída do VLM](../../docs/contracts/saida-vlm.md), com entrada igual à da inferência, e rastreamento em MLflow; o modelo *zero-shot* é avaliado como linha de base. Execução no Colab por `infrastructure/colab/t038_treino.ipynb`.
- **RF-SDD-18 — Relatório de treinamento:** ao fim de cada treinamento concluído, e de cada avaliação da linha de base, gerar automaticamente um relatório em Markdown com gráficos PNG e um `metricas.json`, contendo identificação da execução, ambiente (GPU e versões), características do modelo (parâmetros totais e treináveis, quantização, LoRA), tamanho e distribuição das partições de treino, validação e teste, curvas e tempos de treino, tempo de carga, tempo médio de inferência e memória, acurácia, F1 macro e matrizes de confusão, métricas de extração e comparação com a linha de base, conforme [relatório por treinamento](../../docs/domain/evaluation.md#relatório-por-treinamento).

## Requisitos não funcionais

- **RNF-SDD-01 — Execução institucional:** todos os modelos rodam em infraestrutura própria; nenhum documento ou trecho é enviado a serviço externo ([ADR-009](../../docs/decisions/ADR-009-execucao-local.md), [RN-020](../../docs/domain/business-rules.md#rn-020)).
- **RNF-SDD-02 — Segurança:** parsers, decodificadores e modelos isolados, com privilégio mínimo e sem rede não aprovada; nenhum conteúdo recebido é executado ([P1](../../.specify/memory/constitution.md)).
- **RNF-SDD-03 — Texto como dado:** conteúdo documental nunca é tratado como instrução por modelo generativo ([P2](../../.specify/memory/constitution.md)).
- **RNF-SDD-04 — Precisão:** medir CER/WER, F1 de tipo e face, IoU, acerto por campo, ANLS, alucinação, ECE e detecção conforme [dados e avaliação](../../docs/domain/evaluation.md); alvo mínimo de 90% de precisão em nível de caractere nos campos extraídos, em cada um dos dois datasets, reportado por tipo e por dataset (ver Q-24).
- **RNF-SDD-05 — Privacidade:** minimizar dados em CSV, alertas, logs e revisão; restringir acesso e definir retenção antes de usar dados reais.
- **RNF-SDD-06 — Licenças:** componentes com licença restritiva exigem ADR e autorização institucional ([P7](../../.specify/memory/constitution.md)).
- **RNF-SDD-07 — Reprodutibilidade:** limiares e parâmetros calibráveis ficam em configuração versionada do pipeline ([P6](../../.specify/memory/constitution.md)).
- **RNF-SDD-08 — Honestidade:** `processado` exige pipeline concluído e não significa documento seguro ou revisado; ausência de alerta não indica segurança; falha de detector não é apresentada como ausência de ameaça.
- **RNF-SDD-09 — Desempenho:** registrar tempo por página, uso de GPU e memória. Metas (2026-11-25): tempo do pipeline completo ≤ 30 s por página e memória de GPU ≤ 7,5 GB na inferência, na GPU de 8 GB; sem meta para o tempo de carga dos modelos. As metas são **indicadores reportados** na avaliação e não reprovam a T035.
- **RNF-SDD-10 — Análise de desempenho da classificação:** reportar acurácia, F1 macro e matriz de confusão (absoluta e normalizada por linha, com coluna `indefinido`) para tipo e para tipo e face, no agregado, por conjunto, por condição representativa, com e sem rejeição e por experimento, conforme [dados e avaliação](../../docs/domain/evaluation.md#análise-de-desempenho-da-classificação); a análise identifica os pares mais confundidos, as rejeições por classe e as confusões a partir de `outros` (Q-27).

## Dados e privacidade

- **Dados tratados e finalidade:** documentos de identificação, imagens, transcrições, campos extraídos, hashes, nomes de arquivo e numeração CNJ, para apoio à triagem processual. Todos são dados pessoais e potencialmente sensíveis.
- **Sensibilidade e minimização:** o CSV principal concentra dados pessoais e o inteiro teor; `alertas.csv` contém apenas trecho truncado e escapado. Na etapa `validacao`, a evidência traz valor proposto pelo VLM, que pode ser dado inventado e não deve ser usado como dado do titular.
- **Retenção e descarte:** arquivos intermediários são apagados ao final do lote ([ING-SEC-11](../../docs/security/pdf-ingestion.md)); retenção de originais, CSVs e conjuntos de avaliação fica para eventual uso operacional futuro (Q-25); a fase de desenvolvimento e testes não admite dados reais.
- **Compartilhamento/serviços externos:** proibidos para documentos e derivados. Desenvolvimento, treinamento e testes usam apenas dados sintéticos ou fictícios (BID, `br-doc-extraction`, composições sintéticas); dados reais e documentos de processos judiciais não são admitidos nesta fase.

## Segurança e abuso

- **Entradas não confiáveis:** arquivo, metadados, texto nativo, transcrição, imagens derivadas e saída do VLM.
- **Ameaças e controles:** conteúdo ativo (inventário, remoção, rasterização, YARA), texto oculto (comparação nativo × transcrição, fonte < 1 pt, cor do fundo, caracteres invisíveis), injeção de prompt (classificador, regras, mascaramento, instrução fixa, esquema fechado, validação contra a transcrição), alucinação (respaldo), injeção de fórmula (neutralização). Ver [modelo de ameaças](../../docs/security/threat-model.md).
- **Resposta a conteúdo suspeito:** sinalizar e mascarar; nunca bloquear, desviar ou descartar ([P3](../../.specify/memory/constitution.md)).
- **Falhas e comportamento seguro:** erro em um documento gera linha de erro sem afetar os demais; falha de detector gera ocorrência `falha_deteccao`, sem ser tratada como ausência de ameaça; falha de gravação de alerta é regravada ao fim do lote.

## Fluxos e cenários

### Cenário: documento válido sem ocorrência

- **Dado** um PDF sintético de RG com uma página e menos de 2.000.000 bytes
- **Quando** o pipeline é executado
- **Então** `documentos.csv` recebe uma linha `rg` com campos respaldados, `validacao = ok`, `alerta_seguranca = nenhum`, `situacao = processado` e versões preenchidas

### Cenário: arquivo inválido ou acima do limite

- **Dado** um arquivo com extensão `.pdf` que não é PDF, ou com 2.000.000 bytes ou mais
- **Quando** é submetido
- **Então** gera uma linha com `situacao = erro`, `motivo_erro` (`formato_nao_suportado` ou `tamanho_excedido`), páginas e resultados vazios, nenhum modelo é chamado para ele e os demais arquivos do lote continuam

### Cenário: injeção de prompt localizada

- **Dado** uma página com instrução dirigida a modelo em região conhecida
- **Quando** a detecção a identifica
- **Então** a região é mascarada na imagem e na transcrição enviadas ao VLM, `alertas.csv` registra `injecao_prompt` com `mascarado = sim`, o inteiro teor permanece completo e higienizado e o documento segue até a saída

### Cenário: campo sem respaldo

- **Dado** que o VLM propõe um `orgao_emissor` ausente da transcrição
- **Quando** a validação compara valor e transcrição abaixo do limiar
- **Então** o campo é esvaziado, `alertas.csv` registra `campo_sem_respaldo` com o valor proposto na evidência e `validacao` não é `ok`

### Cenário: saída fora do esquema

- **Dado** uma resposta do VLM que não atende ao esquema
- **Quando** a validação de esquema falha
- **Então** o documento recebe tipo `indefinido`, nenhum campo e `validacao = falhou` ([RN-022](../../docs/domain/business-rules.md#rn-022), [RN-027](../../docs/domain/business-rules.md#rn-027))

### Cenário: falha na gravação de alerta

- **Dado** um documento com ocorrência detectada
- **Quando** o arquivo de alertas não pode ser escrito imediatamente
- **Então** o alerta é mantido em memória, o documento continua até a saída e o alerta é regravado ao fim do lote

### Cenário: documento fora de orientação padrão

- **Dado** RG, CPF ou CNH em JPEG/PDF girado, inclinado, invertido ou espelhado
- **Quando** passa pelo pré-processamento
- **Então** a orientação é normalizada sem depender apenas de metadados e o `bbox` é gravado em pixels da página rasterizada original

### Cenário: revisão aleatória

- **Dado** documentos concluídos em operação normal
- **Quando** a política amostral seleciona um documento
- **Então** uma pessoa pode conferir/corrigir e o registro fica rastreável sem que os demais documentos aguardem

## Critérios de aceitação

- [ ] Formato real e tamanho são validados antes de qualquer outra etapa; nenhum serviço externo é chamado.
- [ ] Conteúdo ativo de PDF sintético é inventariado antes da remoção e nunca executado.
- [ ] Documentos sintéticos em todas as orientações previstas são processados.
- [ ] Prova de conceito na GPU de 8 GB carrega o Qwen3.5-4B em 8 bits com o adaptador LoRA no `vLLM` e devolve JSON válido com logprobs para uma página sintética com imagem e transcrição.
- [ ] Tipos, faces, campos e formatos correspondem aos contratos `saida-vlm`, `documentos.csv` e `alertas.csv` vigentes.
- [ ] Campos não pertinentes ao tipo, sem respaldo ou com data inválida são esvaziados e geram a ocorrência correspondente.
- [ ] Regiões suspeitas localizadas são mascaradas na entrada do VLM e registradas com `mascarado = sim`.
- [ ] Alertas não bloqueiam documentos; falha de gravação é regravada ao fim do lote.
- [ ] Todo campo textual dos CSVs é normalizado e protegido contra fórmulas; evidências têm no máximo 500 caracteres.
- [ ] Arquivos intermediários são apagados ao final do lote, inclusive quando o lote termina com falha.
- [ ] Toda linha, inclusive de erro, registra identificação, situação e versões.
- [ ] Métricas de [dados e avaliação](../../docs/domain/evaluation.md) são medidas em conjunto aprovado e reportadas por categoria.
- [ ] Acurácia, F1 macro, métricas por classe e matriz de confusão são geradas reprodutivelmente a partir das previsões e referências do conjunto de teste, nos recortes de RNF-SDD-10, e acompanhadas da análise das principais confusões.
- [ ] Cada treinamento concluído gera `relatorio.md`, gráficos e `metricas.json` com todas as seções de RF-SDD-18, sem nome de máquina, usuário, caminhos locais ou credenciais.
- [ ] Ausência de alerta, `processado` e falha de detector nunca são apresentados como documento seguro ou revisado.

## Questões pendentes e riscos

Questões levantadas em 2026-11-21 e respondidas na mesma data. As resolvidas indicam onde a decisão foi registrada; as parcialmente resolvidas indicam o que ainda falta. **Proposta** indica sugestão ainda não decidida.

### Contradições na documentação

- **Q-01 — Resolvida (2026-11-21):** [csv-export.md](../../docs/security/csv-export.md) deixou de listar colunas e passou a referenciar os contratos `documentos.csv` e `alertas.csv` como única fonte do esquema.
- **Q-02 — Resolvida (2026-11-21):** timestamps usam ISO 8601 com o deslocamento do fuso local explícito (ex.: `-03:00`), conforme [RN-017](../../docs/domain/business-rules.md#rn-017).
- **Q-03 — Resolvida (2026-11-21):** mantém-se `filiacao` como lista sem distinção de papel; `agents.md` foi alinhado ao contrato.
- **Q-04 — Resolvida (2026-11-21):** prevalece `validacao = falhou` com tipo `indefinido` quando a saída foge do esquema; [RN-027](../../docs/domain/business-rules.md#rn-027) foi ajustada e mantém vazio para `outros`, `indefinido` por confiança e erro.
- **Q-05 — Resolvida (2026-11-21):** JPEG é convertido em PDF de uma página após decodificação isolada, sem reamostragem; `arquivo` e `hash_arquivo` referem-se ao original ([ING-SEC-10](../../docs/security/pdf-ingestion.md)).
- **Q-06 — Resolvida (2026-11-21):** `.env.example` passou a listar apenas variáveis de execução local (endpoint do `vLLM`, modelos, adaptador, diretórios e configuração), sem chaves de API.

### Lacunas que bloqueiam a implementação

- **Q-07 — Resolvida (2026-11-21):** os arquivos são carregados dos datasets BID e `tech4humans/br-doc-extraction`; `id_processo` recebe o identificador sintético `<dataset>:<arquivo>` quando não houver numeração CNJ ([RN-001](../../docs/domain/business-rules.md#rn-001)); um lote é uma execução sobre um conjunto ou partição do dataset.
- **Q-08 — Resolvida (2026-11-21):** frente e verso do mesmo tipo em páginas consecutivas formam uma linha com `face = ambas`; campo divergente entre as faces é esvaziado e gera `dado_inconsistente`; `bbox` da frente; `confianca_tipo` é a menor das duas; página sem documento de identificação gera linha `outros` ([RN-029](../../docs/domain/business-rules.md#rn-029)).
- **Q-09 — Resolvida (2026-11-21):** `inteiro_teor` contém as linhas cujas caixas estão majoritariamente dentro do `bbox`; na junção, concatena frente e verso ([RN-016](../../docs/domain/business-rules.md#rn-016)).
- **Q-10 — Resolvida (2026-11-21):** nova coluna `motivo_erro` com domínio fechado; arquivo inválido gera uma linha com páginas vazias ([RN-018](../../docs/domain/business-rules.md#rn-018)); falha de detector gera ocorrência `falha_deteccao` e o documento segue processado. Severidade de `falha_deteccao` incluída em Q-21.
- **Q-11 — Resolvida (2026-11-21):** se a regravação falhar, os alertas vão para `alertas_pendentes_<id_lote>.csv` em diretório de contingência; se também falhar, o lote termina com código de saída de falha e log sem conteúdo documental ([RN-013](../../docs/domain/business-rules.md#rn-013)).
- **Q-12 — Resolvida (2026-11-21):** um arquivo `documentos_<id_lote>.csv` por lote, escrito por um único processo ([contrato](../../docs/contracts/documentos-csv.md)).
- **Q-13 — Resolvida (2026-11-21):** limites iniciais configuráveis de 50 páginas, 10.000 px no lado maior, 120 s e 8 GB por arquivo; PDF criptografado ou corrompido gera `arquivo_ilegivel` ([ING-SEC-01](../../docs/security/pdf-ingestion.md)).
- **Q-14 — Resolvida (2026-11-21):** metadados descartados na conversão; orientação EXIF usada apenas como sinal auxiliar ([ING-SEC-09](../../docs/security/pdf-ingestion.md)).
- **Q-15 — Resolvida (2026-11-21):** espelhamento detectado por comparação da confiança do OCR entre a imagem e sua versão espelhada; rasterização a 300 DPI; `bbox` em pixels da página rasterizada original ([ING-SEC-08](../../docs/security/pdf-ingestion.md)).
- **Q-16 — Resolvida (2026-11-21):** respaldo com normalização canônica de texto, números e datas ([RN-024](../../docs/domain/business-rules.md#rn-024)); datas anteriores a 1900, futuras (exceto validade) ou fora da ordem nascimento < emissão < validade são esvaziadas ([RN-025](../../docs/domain/business-rules.md#rn-025)); `ok` sem campo esvaziado nem inconsistência, `parcial` com ao menos um ([RN-027](../../docs/domain/business-rules.md#rn-027)).
- **Q-17 — Resolvida (2026-11-21):** o primeiro incremento inclui o pipeline completo e o treino do adaptador LoRA (RF-SDD-17), com *zero-shot* como linha de base; revisão amostral e frontend ficam para especificação futura.
- **Q-18 — Resolvida (2026-11-21):** Python 3.12, `uv`, `pytest`, `ruff`, código em `src/backend/` como pacote `visiondoc` ([componentes](../../docs/architecture/components.md)).
- **Q-19 — Resolvida (2026-11-21):** scanner `PromptInjection` do llm-guard como detector principal, com licenças a confirmar na versão adotada; Prompt Guard 2 só em experimento; detecção do ClamAV gera `conteudo_ativo` com severidade `alta` ([RN-009](../../docs/domain/business-rules.md#rn-009), [RN-010](../../docs/domain/business-rules.md#rn-010)).

### Parâmetros a calibrar (exigem valor inicial e local de configuração)

- **Q-20 — Resolvida (2026-11-21):** limiar inicial de rejeição 0,5; confiança de cada rótulo = produto das probabilidades dos seus tokens, renormalizado entre as quatro classes ([RN-004](../../docs/domain/business-rules.md#rn-004)).
- **Q-21 — Resolvida (2026-11-21):** `falha_deteccao` com severidade `media`; injeção alta ≥ 0,9 e intermediária entre 0,5 e 0,9; padrão isolado = regra ou regex sem confirmação do classificador; `texto_oculto` com `partial_ratio` < 80; YARA inicial para JavaScript, `OpenAction`, `Launch`, `EmbeddedFile` e `AcroForm` ([RN-010](../../docs/domain/business-rules.md#rn-010)).
- **Q-22 — Resolvida (2026-11-21):** `config/pipeline.yaml` versionado, validado com `pydantic`; sua versão compõe `versao_pipeline`.

### Necessárias antes do uso operacional

- **Q-23 — Parcialmente resolvida (2026-11-21):** GPU disponível de 8 GB; Qwen3.5-4B com QLoRA 4 bits no ajuste e pesos em 8 bits (FP8 ou INT8) na inferência; o `vLLM` adotado deve suportar Qwen3.5, entrada multimodal e LoRA sobre modelo quantizado em 8 bits, confirmado por prova de conceito antes da implementação ([ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)). Metas de desempenho definidas em 2026-11-25 (RNF-SDD-09). Pendente: prova de conceito na GPU de 8 GB.
- **Q-24 — Resolvida (2026-11-21):** a meta de 90% é 1 − CER dos campos extraídos frente à referência, por tipo, nas partições de teste do BID e do `br-doc-extraction`, valendo para cada um dos dois datasets separadamente ([dados e avaliação](../../docs/domain/evaluation.md)).
- **Q-25 — Parcialmente resolvida (2026-11-21):** a fase de desenvolvimento e testes não admite dados reais nem documentos de processos judiciais; usa apenas BID e `br-doc-extraction`. Pendentes, para eventual uso operacional futuro: controlador, base legal, retenção, descarte e acesso ([governança de dados](../../docs/privacy/data-governance.md)).
- **Q-26 — Adiada (2026-11-21):** revisão amostral fora do primeiro incremento (Q-17); responsáveis, taxa, papéis e persistência das correções serão tratados na especificação futura.
- **Q-27 — Resolvida (2026-11-21):** acurácia, F1 macro e métricas por classe só sobre documentos aceitos, com a cobertura ao lado; matriz com coluna `indefinido` para análise de rejeição; pareamento por IoU ≥ 0,5 (não localizado = erro; espúrios em coluna própria); IC 95% por *bootstrap* com 1.000 reamostragens; sem metas mínimas ([dados e avaliação](../../docs/domain/evaluation.md#análise-de-desempenho-da-classificação)).

### Riscos

- Injeção não detectada ainda pode influenciar o VLM dentro do esquema; a validação contra a transcrição é a última barreira.
- Falso positivo de mascaramento pode remover texto legítimo e reduzir campos extraídos.
- Sem dados reais na fase de desenvolvimento e testes, a diferença entre dados sintéticos e documentos reais não pode ser medida; os resultados não comprovam desempenho em uso real.
- Sem trilha de auditoria, não é possível reconstituir as ações de cada etapa em produção.

## Referências e decisões

- [Constituição](../../.specify/memory/constitution.md)
- [Requisitos do domínio](../../docs/domain/requirements.md), [regras de negócio](../../docs/domain/business-rules.md), [dados e avaliação](../../docs/domain/evaluation.md)
- [Arquitetura lógica](../../docs/architecture/overview.md), [componentes](../../docs/architecture/components.md)
- Contratos: [saída do VLM](../../docs/contracts/saida-vlm.md), [`documentos.csv`](../../docs/contracts/documentos-csv.md), [`alertas.csv`](../../docs/contracts/alertas-csv.md)
- ADRs vigentes: [001](../../docs/decisions/ADR-001-entrada-pdf-nao-confiavel.md), [005](../../docs/decisions/ADR-005-deteccao-nao-bloqueante.md), [006](../../docs/decisions/ADR-006-alertas-em-csv.md), [007](../../docs/decisions/ADR-007-remocao-auditoria.md), [008](../../docs/decisions/ADR-008-saida-csv.md), [009](../../docs/decisions/ADR-009-execucao-local.md), [010](../../docs/decisions/ADR-010-vlm-qwen35-9b-lora.md), [011](../../docs/decisions/ADR-011-transcricao-paddleocr-vl.md), [012](../../docs/decisions/ADR-012-deteccao-antes-do-vlm.md), [013](../../docs/decisions/ADR-013-validacao-saida-vlm.md), [014](../../docs/decisions/ADR-014-extracao-de-campos.md), [015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md)
- Segurança: [ingestão](../../docs/security/pdf-ingestion.md), [detecção](../../docs/security/malicious-content-detection.md), [alertas](../../docs/security/audit-and-alerting.md), [exportação CSV](../../docs/security/csv-export.md), [modelo de ameaças](../../docs/security/threat-model.md)
- Privacidade: [governança de dados](../../docs/privacy/data-governance.md)
