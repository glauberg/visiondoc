# Regras de negócio

Regras numeradas para rastreio em especificações, testes e implementação. Valores marcados como **a calibrar** são definidos no conjunto de validação e registrados na configuração versionada do pipeline. Regras revogadas mantêm o número para evitar quebra de referências.

## Entrada

### RN-001
*(Alterada em 2026-11-21)* Todo arquivo de entrada é associado a um identificador de origem em `id_processo`: a numeração única do CNJ, quando houver processo, ou, para arquivos carregados de datasets (BID e `tech4humans/br-doc-extraction`), um identificador sintético no formato `<dataset>:<arquivo>` (ex.: `bid:00012345_in.jpg`). Arquivos que não forem PDF ou JPEG válido geram linha com `situacao = erro`.

### RN-002
Antes de qualquer outra etapa, o arquivo é identificado e saneado. Em PDF, elementos ativos são inventariados e removidos; o SHA-256 do arquivo original é registrado em `hash_arquivo`.

## Classificação

### RN-003
O conjunto de tipos é fechado: `cnh`, `rg`, `cpf`, `outros`, `indefinido`.

- `outros`: documento reconhecível fora de CNH, RG e CPF.
- `indefinido`: confiança abaixo do limiar de rejeição; não é produzido diretamente pelo VLM.

### RN-004
Se `confianca_tipo`, calculada a partir dos logprobs do VLM, for menor que o limiar de rejeição (**a calibrar**; valor inicial 0,5), o tipo será `indefinido` e os campos serão descartados. *(Complementada em 2026-11-21)* A confiança de cada rótulo é o produto das probabilidades dos seus tokens, renormalizado entre `cnh`, `rg`, `cpf` e `outros`.

### RN-005
*(Alterada em 2026-11-20)* Os exemplos de ajuste usam as oito classes BID convertidas em tipo e face, mais exemplos da classe `outros`.

### RN-006
*(Revogada em 2026-11-20 pelo ADR-010)* ~~Fusão por média ponderada dos classificadores visual e textual.~~

### RN-007
*(Alterada em 2026-11-20)* O VLM identifica cada documento da página e devolve suas coordenadas. Cada documento gera uma linha própria com `bbox`.

## Detecção e alerta

### RN-008
A detecção nunca interrompe nem desvia o processamento. O documento segue até a saída com resumo de alertas.

### RN-009
*(Alterada em 2026-11-20)* Categorias: `conteudo_ativo`, `texto_oculto`, `injecao_prompt`, `campo_sem_respaldo`, `dado_inconsistente`, `falha_deteccao`. `divergencia_texto_imagem` foi extinta.

- `conteudo_ativo`: JavaScript, ação automática, arquivo embutido, formulário, regra YARA ou detecção do ClamAV.
- `texto_oculto`: divergência entre texto nativo e transcrição, fonte menor que 1 pt, cor do fundo, texto invisível ou caracteres invisíveis.
- `injecao_prompt`: instrução dirigida a modelo detectada por classificador ou regra.
- `campo_sem_respaldo`: campo extraído pelo VLM não encontrado na transcrição.
- `dado_inconsistente`: CPF com dígito inválido, data inválida ou impossível, ou valores divergentes entre frente e verso ([RN-029](#rn-029)).
- `falha_deteccao` *(nova em 2026-11-21)*: falha ou indisponibilidade de um detector. O documento segue processado, e a falha nunca é interpretada como ausência de ameaça. Severidade `media`.

### RN-010
*(Alterada em 2026-11-20)* `alta` para conteúdo ativo executável, detecção do ClamAV, injeção acima do limiar alto ou campo sem respaldo combinado com injeção. `media` para texto oculto, injeção intermediária ou campo sem respaldo. `baixa` para padrão isolado ou dado inconsistente. *(Complementada em 2026-11-21)* `media` também para `falha_deteccao`. Valores iniciais, ajustáveis na configuração versionada: injeção alta com escore do classificador ≥ 0,9 e intermediária entre 0,5 e 0,9; padrão isolado é ocorrência de regra ou expressão regular sem confirmação do classificador. `texto_oculto` por divergência ocorre quando `partial_ratio` entre texto nativo e transcrição é menor que 80.

### RN-011
Texto imperativo dirigido a modelos em documento `cnh`, `rg` ou `cpf` eleva a severidade da ocorrência de injeção em um nível, até `alta`.

### RN-012
Cada ocorrência gera uma linha em `alertas.csv`. No CSV principal, `alerta_seguranca` usa categorias separadas por `|` e `severidade_alerta` registra a maior severidade. Sem ocorrência: `nenhum` e severidade vazia.

### RN-013
Falha na gravação de alerta não interrompe o pipeline. O alerta permanece em memória e é regravado ao fim do lote. *(Complementada em 2026-11-21)* Se a regravação falhar, os alertas pendentes são gravados em `alertas_pendentes_<id_lote>.csv`, em diretório de contingência separado; se essa gravação também falhar, o lote termina com código de saída de falha e registro em log sem conteúdo documental.

## VLM

### RN-021
*(Nova)* Quando houver `injecao_prompt` ou `texto_oculto` com localização conhecida, mascara-se a região antes do envio ao VLM:

- retângulo sólido na imagem;
- `[TRECHO REMOVIDO]` na transcrição enviada ao VLM.

O inteiro teor do CSV e a evidência do alerta permanecem completos e higienizados. O alerta registra `mascarado = sim`.

### RN-022
*(Nova)* A chamada ao VLM usa instrução de sistema fixa e versionada, imagem e transcrição delimitada no turno do usuário, decodificação estruturada para o esquema de saída e temperatura 0.

Se a saída não atender ao esquema, o documento recebe `validacao = falhou`, tipo `indefinido` e nenhum campo.

### RN-023
*(Nova)* Somente campos pertinentes ao tipo são mantidos. Documentos `outros` e `indefinido` não têm campos.

### RN-024
*(Nova)* Campo extraído precisa ter respaldo na transcrição. Valor e transcrição são normalizados; o respaldo ocorre se `rapidfuzz.fuzz.partial_ratio` atingir o limiar a calibrar, com valor inicial 90. *(Complementada em 2026-11-21)* Normalização para a forma canônica: texto em maiúsculas, sem acentos e sem espaços duplicados; CPF e números apenas com dígitos; datas são buscadas na transcrição nas formas `DD/MM/AAAA`, `DD-MM-AAAA`, `DD.MM.AAAA` e `DD MM AAAA` equivalentes ao valor extraído.

Campo sem respaldo é esvaziado e gera `campo_sem_respaldo`, com o valor proposto pelo VLM na evidência.

### RN-025
*(Nova)* CPF com dígito verificador inválido permanece como consta no documento e gera `dado_inconsistente`. Datas inválidas ou impossíveis são esvaziadas e geram `dado_inconsistente`. *(Complementada em 2026-11-21)* São impossíveis: data anterior a 1900-01-01; data futura em relação a `data_processamento`, exceto `data_validade`; e quebra da ordem `data_nascimento` < `data_emissao` < `data_validade`. Na quebra de ordem, as datas envolvidas são esvaziadas.

### RN-026
*(Nova)* `campo_sem_respaldo` em documento que também teve `injecao_prompt` tem severidade `alta`.

### RN-027
*(Alterada em 2026-11-21)* `validacao` pode ser `ok`, `parcial`, `falhou` ou vazio. É `falhou` quando a saída do VLM não atende ao esquema ([RN-022](#rn-022)), caso em que o tipo é `indefinido`. É vazio para `outros`, para `indefinido` atribuído por confiança ([RN-004](#rn-004)) e para linhas de erro. Nos demais casos, é `ok` quando nenhum campo foi esvaziado e não houve `dado_inconsistente`, e `parcial` quando houve ao menos um dos dois.

### RN-028
*(Nova)* CPF usa `000.000.000-00`, datas usam `AAAA-MM-DD`, nomes são maiúsculos sem espaços duplicados e `filiacao` separa nomes por `|` em `campos_json`.

### RN-029
*(Nova em 2026-11-21)* Frente e verso do mesmo tipo identificados em páginas consecutivas do mesmo arquivo são unidos em uma única linha, com `face = ambas`, `pagina_inicial` e `pagina_final` correspondentes e os campos das duas faces combinados. Página sem documento de identificação gera uma linha `outros`. Na linha unida, campo com valores diferentes nas duas faces é esvaziado e gera `dado_inconsistente`; `bbox` é o da frente; `confianca_tipo` é a menor entre as duas faces.

## Saída

### RN-014
Todo campo textual dos CSVs é normalizado em NFC, sem caracteres de controle ou `Cf`, com exceção das quebras de linha do inteiro teor. O texto recebe apóstrofo se começar por `=`, `+`, `-`, `@`, tabulação ou retorno de carro.

### RN-015
Evidência é truncada em 500 caracteres no alerta e em `detalhe_alerta`.

### RN-016
*(Alterada em 2026-11-20)* `inteiro_teor` é a transcrição do PaddleOCR-VL, sem mascaramento, quando houver texto, inclusive em documentos com alerta. *(Complementada em 2026-11-21)* Contém apenas as linhas de texto cujas caixas estão majoritariamente (mais de 50% da área) dentro do `bbox` do documento; na linha unida de frente e verso ([RN-029](#rn-029)), concatena a transcrição da frente e a do verso, nessa ordem.

### RN-017
CSV usa UTF-8 sem BOM, vírgula, aspas duplas em todos os campos de texto, cabeçalho na primeira linha, ISO 8601 com o deslocamento do fuso local explícito (ex.: `2026-11-20T23:47:00-03:00`), ponto decimal e escore entre 0 e 1. Ausência é campo vazio.

### RN-018
Erro de processamento gera linha com `situacao = erro`, `motivo_erro` preenchido e resultados vazios; os demais documentos continuam processados. *(Complementada em 2026-11-21)* Arquivo inválido gera uma linha por arquivo, com `pagina_inicial` e `pagina_final` vazias. Valores de `motivo_erro`: `formato_nao_suportado`, `tamanho_excedido`, `arquivo_ilegivel`, `falha_processamento`, `contrato_invalido`.

### RN-019
*(Alterada em 2026-11-20)* Toda linha registra `versao_pipeline`, `modelo_vlm`, `modelo_transcricao` e `data_processamento`.

## Dados pessoais

### RN-020
Nenhum documento, imagem ou trecho extraído é enviado a serviço externo. Todo o processamento ocorre em infraestrutura própria.
