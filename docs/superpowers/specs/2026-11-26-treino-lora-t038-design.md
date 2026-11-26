# Desenho: treino do adaptador LoRA e teste contra o modelo sem treino (T038)

- **Data:** 2026-11-26
- **Estado:** aguardando aprovação de Glauber Galvão
- **Tarefas relacionadas:** T038 (treino), T020 (carga do adaptador no Ollama), T037 (métricas, fora deste desenho)
- **Decisões que este desenho respeita:** [ADR-015](../../decisions/ADR-015-vlm-qwen35-4b.md) (QLoRA 4 bits, dados só BID e `br-doc-extraction`), [ADR-017](../../decisions/ADR-017-ollama-servidor-do-vlm.md) (Ollama; adaptador convertido para GGUF), [contrato da saída do VLM](../../contracts/saida-vlm.md)

## Intenção

Ajustar o Qwen3.5-4B com LoRA para localizar, classificar e extrair campos de documentos de identificação, e medir, nas mesmas imagens de teste, se o adaptador melhora o resultado em relação ao modelo sem treino (*zero-shot*). Hoje o modelo sem treino erra campos legíveis (ex.: CPF `366…` no lugar de `386…`, data em `DD/MM/AAAA` em vez de `AAAA-MM-DD`) e devolve `bbox` fora de escala.

O resultado serve ao trabalho acadêmico: a comparação *zero-shot* × adaptador é o dado principal. O treino é feito em GPU de 24 GB na nuvem; o teste final roda na máquina local, no Ollama, que é o servidor do pipeline.

## Dados

`data/raw/imagens/` é a exportação completa do `tech4humans/br-doc-extraction` (1218 imagens, sintéticas e públicas).

- **Alinhamento (verificado):** a numeração dos arquivos é global: treino `0–1061`, validação `1062–1136`, teste `1137–1217`. O índice da linha no split é o número do arquivo menos o deslocamento do split. Verificado em `test-01137.png` ↔ linha 0 do teste (mesmo nome do titular).
- **Partição:** a do próprio dataset, sem reparticionar: 1062 treino, 75 validação, 81 teste. O teste não é usado em nenhuma decisão de treino.
- **Tipos:** `cnh`, `rg` e `invoice`, em partes iguais (354/25/27 de cada). Não há CPF, então o modelo não aprende essa classe neste treino.
- **Rótulos nativos:** `response` é um JSON cujas chaves variam por linha dentro do mesmo tipo (ex.: `nome`, `nome_completo` ou `titular`). `schema` lista os campos pedidos naquela linha. Não há `bbox` nem `face`.

## Conversão dos rótulos para o contrato

Cada linha vira o alvo `SaidaVLM` com um único documento.

| Contrato | CNH (chaves aceitas) | RG (chaves aceitas) |
|---|---|---|
| `tipo` | `cnh` | `rg` |
| `nome` | `nome_completo`, `nome`, `titular` | `nome_completo` |
| `cpf` | `cpf` | `cpf` |
| `numero_documento` | `num_registro`, `doc_identidade` | `registro_geral`, `rg_numero` |
| `data_nascimento` | `data_nascimento` | `data_nascimento` |
| `data_emissao` | `data_emissao` | `data_expedicao` |
| `data_validade` | `data_validade` | — |
| `orgao_emissor` | — | `orgao_emissor` |
| `filiacao` | `[filiacao_pai, filiacao_mae]` sem vazios | idem |
| `naturalidade` | — | `naturalidade`, `local_nascimento` |
| `doc_origem` | — | `doc_origem` |
| `categoria_habilitacao` | `categoria_habilitacao` | — |

- `invoice` → `tipo: "outros"`, `campos` vazio.
- `bbox` = `[0, 0, 1000, 1000]` (imagem inteira, na escala 0–1000 do modelo), pois cada imagem tem um só documento. É um valor fixo declarado, não localização aprendida.
- `face` = `null` (o dataset não informa).
- Chaves sem correspondência no contrato (`data_1a_habilitacao`, `local_emissao`) são descartadas.
- Valor vazio (`""`) vira `null`.
- **Campo ausente no rótulo não vira `null`:** a chave é omitida do alvo. A ausência no rótulo vem do esquema daquela linha e não prova que o campo não está na imagem; gravar `null` ensinaria o modelo a deixar em branco campos legíveis. O esquema do contrato aceita chaves omitidas.
- A instrução de sistema é a mesma da prova de conceito T020 (`INSTRUCAO`), fixa e com o hash registrado.

## Abordagem escolhida

**A. Contrato como alvo, treino na nuvem, teste local.** Foi escolhida entre duas:

- **A (escolhida):** alvo no contrato do pipeline; o adaptador substitui o modelo sem treino sem mudar o resto.
- **B (descartada):** treinar com o esquema nativo do dataset e converter na saída. É mais fiel aos rótulos, mas foge do contrato (ADR-013) e deixa o pipeline com uma conversão a mais.

## Etapas

1. **Preparação dos dados (local):** script que lê os rótulos do Hugging Face, alinha pelos nomes e grava `data/processed/treino/{train,valid,test}.jsonl` (imagem + mensagens + alvo), com contagem de linhas descartadas. Testes unitários do mapeamento.
2. **Prova pequena do caminho completo:** treinar poucos passos, converter para GGUF e carregar no Ollama sobre o `qwen3.5:4b` com imagem. É a verificação da T020 que o ADR-017 deixou em aberto; se falhar, o treino completo não começa e a decisão volta ao ADR.
3. **Treino (nuvem, 24 GB):** QLoRA 4 bits, codificador de visão congelado, LoRA no modelo de linguagem, rank 16, alpha 32, dropout 0,05 (valores do ADR-015), com a validação acompanhada por época. Parâmetros e métricas rastreados em MLflow (arquivos locais).
4. **Conversão e carga:** adaptador → GGUF → `Modelfile` com `ADAPTER`; registro do digest e do hash da instrução (`modelo_vlm`, ADR-017).
5. **Teste local:** notebook que processa as 81 imagens de teste com o modelo sem treino e com o adaptador, mesma instrução, temperatura 0, e compara.

## Medida do teste (nas 81 imagens, sem consultar o teste durante o treino)

- acurácia do `tipo` e F1 macro (`cnh`, `rg`, `outros`), com matriz de confusão;
- acerto exato por campo, comparado ao rótulo convertido, separando campos que o rótulo traz dos que ele omite;
- JSON válido no contrato e tempo por página.

A métrica é provisória, calculada no próprio notebook. Quando a T037 existir, a mesma comparação é refeita com ela e com a meta de 90% da T021.

## Metas e não metas

**Metas**
- Adaptador carregado e funcionando no Ollama com imagem.
- Comparação registrada, adaptador × *zero-shot*, nas mesmas 81 imagens.
- Resultado reproduzível: versões, sementes, hash dos dados e da instrução anotados.

**Não metas**
- Aprender `bbox` e `face` (fixos/nulos neste treino).
- Classificar CPF (inexistente no dataset).
- Qualquer dado real ou de processo judicial (ADR-015).
- O módulo de métricas T037 e a calibração da confiança do tipo.

**Anti-metas** (falha mesmo que "funcione")
- Usar o teste para escolher hiperparâmetros ou a época.
- Apresentar o `bbox` fixo como localização aprendida.
- Subir para a nuvem qualquer coisa além do dataset público e sintético.

## Restrições e riscos

- **Memória local de 4 GB:** não treina aqui; só a inferência.
- **Suporte da arquitetura Qwen3.5 multimodal** nas bibliotecas de treino e na conversão para GGUF é incerto; a etapa 2 existe para descobrir isso cedo.
- **Rótulos incompletos** (omissão por linha) podem fazer o modelo omitir campos legíveis; o teste separa esses casos para medir.
- **Treino em Q4 e inferência em Q4_K_M:** a diferença de quantização não é medida isoladamente.
- **Execução na nuvem:** o treino roda fora da máquina local. Só o dataset público e sintético é enviado; qualquer outro dado exige nova decisão (ADR-009).

## A cargo de quem constrói

- Biblioteca de treino (Unsloth, TRL ou outra), versões e hiperparâmetros além dos iniciais acima.
- Formato exato do `Modelfile` e da conversão.
- Número de épocas, escolhido pela validação.
- Estrutura dos scripts e notebooks.
