# Regras de negócio

Regras numeradas para rastreio em especificações, testes e implementação. Valores marcados como **a calibrar** são definidos no conjunto de validação e registrados na configuração versionada do pipeline.

## Entrada

### RN-001
Todo arquivo de entrada é associado a uma numeração única do CNJ. Arquivos que não forem PDF ou JPEG válido geram linha com `situacao = erro`.

### RN-002
Antes de qualquer outra etapa, o arquivo é identificado e saneado. Em PDF, elementos ativos são inventariados e removidos; o SHA-256 do arquivo original é registrado em `hash_arquivo`.

## Classificação

### RN-003
O conjunto de tipos é fechado: `cnh`, `rg`, `cpf`, `outros`, `indefinido`.

- `outros`: documento reconhecível fora de CNH, RG e CPF.
- `indefinido`: confiança abaixo do limiar de rejeição.

### RN-004
Se `confianca_tipo` for menor que o limiar de rejeição (**a calibrar**), o tipo será `indefinido`.

### RN-005
Os modelos são treinados nas classes BID e na classe `outros`. Na saída, as classes são mapeadas para tipo e face: `frente`, `verso` ou `ambas`.

### RN-006
`confianca_tipo` é a média ponderada das probabilidades calibradas do classificador visual e textual. Os pesos são **a calibrar** e somam 1.

### RN-007
Com detecção visual, cada documento detectado gera uma linha própria com `bbox`. Com classificação por página, a página inteira gera um documento e `bbox` fica vazio.

## Detecção e alerta

### RN-008
A detecção nunca interrompe nem desvia o processamento. O documento segue até a saída com resumo de alertas.

### RN-009
Categorias: `conteudo_ativo`, `texto_oculto`, `injecao_prompt`, `divergencia_texto_imagem`.

### RN-010
Severidade: `alta` para conteúdo ativo executável ou injeção acima do limiar alto; `media` para texto oculto, divergência ou injeção intermediária; `baixa` para padrão isolado de regra.

### RN-011
Texto imperativo dirigido a modelos em documento `cnh`, `rg` ou `cpf` eleva a severidade da ocorrência de injeção em um nível, até `alta`.

### RN-012
Cada ocorrência gera uma linha em `alertas.csv`. No CSV principal, `alerta_seguranca` usa categorias separadas por `|` e `severidade_alerta` registra a maior severidade. Sem ocorrência: `nenhum` e severidade vazia.

### RN-013
Falha na gravação de alerta não interrompe o pipeline. O alerta permanece em memória e é regravado ao fim do lote.

## Saída

### RN-014
Todo campo textual dos CSVs é normalizado em NFC, sem caracteres de controle ou `Cf`, com exceção das quebras de linha do inteiro teor. O texto recebe apóstrofo se começar por `=`, `+`, `-`, `@`, tabulação ou retorno de carro.

### RN-015
Evidência é truncada em 500 caracteres no alerta e em `detalhe_alerta`.

### RN-016
`inteiro_teor` é preenchido sempre que o OCR produzir texto, inclusive em documentos com alerta.

### RN-017
CSV usa UTF-8 sem BOM, vírgula, aspas duplas em todos os campos de texto, cabeçalho na primeira linha, ISO 8601 com fuso, ponto decimal e escore entre 0 e 1. Ausência é campo vazio.

### RN-018
Erro de processamento gera linha com `situacao = erro` e resultados vazios; os demais documentos continuam processados.

### RN-019
Toda linha registra `versao_pipeline`, `modelo_visual` e `data_processamento`.

## Dados pessoais

### RN-020
Nenhum documento, imagem ou trecho extraído é enviado a serviço externo. Todo o processamento ocorre em infraestrutura própria.
