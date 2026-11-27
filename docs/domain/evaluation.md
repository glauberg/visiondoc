# Dados e avaliação

Versão: 2.0 (2026-11-20).

## Conjuntos de dados

### br-doc-extraction

Fonte exclusiva do treino T038: imagens preparadas em `/content/drive/MyDrive/visiondoc/cache/imagens/`, com classes lidas de `/content/drive/MyDrive/visiondoc/cache/MANIFESTO.JSONL` ([ADR-019](../decisions/ADR-019-treino-imagens-preparadas-invoice.md)). A divisão 70-15-15 é refeita sobre todas as imagens válidas; a partição original do manifesto é ignorada.

O conjunto contém imagens e anotações associadas. Para T038, o alvo é apenas classificação das classes CNH, RG e INVOICE; a extração de campos não é avaliada nessa etapa.

### Dados sintéticos complementares

- páginas compostas sobre fundos A4;
- injeções sintéticas de texto oculto e instruções;
- degradações de fotocópia, desfoque, compressão, ruído e JPEG;
- caixas conhecidas automaticamente para treino de detecção.

## Cuidados

1. Resultados em dados sintéticos não comprovam o desempenho em documentos reais; relatórios devem explicitar essa limitação.
2. A classe `outros` evita que documentos não suportados sejam forçados para RG, CPF ou CNH.
3. Treino, validação e teste são separados antes de composição ou aumento de dados.
4. *(Definido em 2026-11-21; fonte T038 atualizada em 2026-11-27)* Na fase de desenvolvimento e testes não são admitidos dados reais nem documentos de processos judiciais. O treino, a validação e o teste da T038 usam exclusivamente as imagens preparadas de `br-doc-extraction` indicadas acima; os testes unitários usam dados sintéticos/fictícios.

## Métricas

| Componente | Métrica |
|---|---|
| Tipo e face | F1 macro, acurácia e matriz de confusão |
| Rejeição | Cobertura por acurácia em função do limiar |
| Calibração | Erro de calibração esperado (ECE) |
| Localização | IoU médio e acerto com IoU ≥ 0,5 |
| Extração | Acerto exato, F1 por campo e ANLS |
| Alucinação | Taxa de campos sem respaldo |
| Transcrição | CER e WER |
| Atos maliciosos | Precisão, revocação e falsos positivos por categoria |
| Segurança da injeção | Taxa de sucesso com e sem mascaramento e validação |
| Desempenho | Tempo por página, GPU e memória; metas reportadas, não eliminatórias: pipeline completo ≤ 30 s por página e memória de GPU ≤ 7,5 GB na GPU de 8 GB |

O alvo mínimo é 90% de precisão em nível de caractere em conjunto aprovado, reportado por categoria e condição representativa. Esse limite não é garantia por documento. *(Definido em 2026-11-21; conjunto atualizado em 2026-11-27)* Quando a extração for avaliada, a meta é medida sobre os **campos extraídos**: 1 − CER entre o valor extraído e o valor de referência, por tipo de documento, na partição de teste aprovada de `br-doc-extraction`.

## Análise de desempenho da classificação

A análise de desempenho do trabalho usa **acurácia**, **F1 macro** e **matriz de confusão**, calculadas sobre o conjunto de teste separado antes de composição ou aumento de dados.

### Granularidade

- **Tipo:** classes disponíveis na avaliação aprovada. No conjunto da T038: `cnh`, `rg` e `invoice`.
- **Tipo e face:** só reportar quando houver rótulos de face no conjunto de avaliação aprovado.
- A classe prevista pode ser também `indefinido` (rejeição por confiança, [RN-004](business-rules.md#rn-004)); a referência nunca é `indefinido`.
- *(Definido em 2026-11-21)* Acurácia, F1 macro e métricas por classe são calculadas **apenas sobre os documentos aceitos** (não `indefinido`), sempre acompanhadas da cobertura (proporção de aceitos). A matriz de confusão mantém a coluna `indefinido` para a análise de rejeição.
- Em páginas com vários documentos, previsão e referência são pareadas por IoU ≥ 0,5; documento de referência não localizado conta como erro, e documento previsto sem par é registrado em coluna própria de espúrios.

### Métricas

- **Acurácia:** proporção de documentos aceitos com classe prevista igual à de referência.
- **F1 macro:** média simples do F1 de cada classe de referência, com F1 = 2 · precisão · revocação / (precisão + revocação). Não é ponderada pelo suporte, para que classes menos frequentes, como `outros` ou versos, pesem igualmente.
- **Precisão, revocação e F1 por classe**, com o suporte de cada uma, acompanham o F1 macro.

### Matriz de confusão

- Linhas: classe de referência; colunas: classe prevista, incluindo a coluna `indefinido`.
- Apresentada em contagens absolutas e normalizada por linha (revocação por classe).
- A análise deve identificar:
  - os pares de classes mais confundidos e sua hipótese de causa (por exemplo, frente × verso do mesmo tipo, RG × CNH, documento de identidade × `outros`);
  - a proporção de rejeições (`indefinido`) por classe de referência;
  - Documentos fora do escopo classificados como uma classe suportada, quando houver exemplos rotulados de `outros` no conjunto de avaliação.

### Recortes

As três medidas são reportadas:

- no agregado e por partição de teste do conjunto de avaliação aprovado;
- por condição representativa: orientação (horizontal, vertical, girada, espelhada), degradação (fotocópia, desfoque, compressão, ruído) e páginas com vários documentos;
- com e sem a regra de rejeição, junto da curva cobertura × acurácia em função do limiar;
- para cada experimento (linhas de base ConvNeXt-Tiny/BERTimbau, VLM *zero-shot* e Qwen3.5-4B com LoRA), com o mesmo particionamento, para permitir comparação direta.

### Intervalo de confiança e metas

Intervalos de confiança de 95% são estimados por *bootstrap* com 1.000 reamostragens. Não há meta mínima de acurácia ou F1 macro (Q-27 da [especificação 001](../../specs/001-pipeline-documental-seguro/spec.md)).

## Relatório por treinamento

*(Definido em 2026-11-25.)* Cada treinamento concluído do adaptador, e cada avaliação da linha de base *zero-shot*, gera automaticamente um diretório `relatorios/treinamentos/<AAAA-MM-DD>-<id_execucao>/` com:

- `relatorio.md`: relatório em Markdown, com as tabelas abaixo e os gráficos embutidos por caminho relativo;
- `graficos/*.png`: gráficos gerados com `matplotlib`;
- `metricas.json`: os mesmos valores em formato legível por máquina, para comparar execuções.

O relatório contém apenas dados sintéticos e informações técnicas do ambiente. Não inclui nome de máquina, usuário, caminhos locais nem credenciais.

### Identificação da execução

- identificador, data/hora de início e fim (ISO 8601 com fuso), *commit* do repositório e indicação de alterações não commitadas;
- `versao_pipeline`, versão de `config/pipeline.yaml`, semente aleatória e identificador da execução no MLflow.

### Ambiente

- GPU: modelo, memória total, *compute capability*, versão do driver e do CUDA;
- CPU (modelo e núcleos), memória RAM e sistema operacional;
- versões de Python, `torch`, `transformers`, `peft`, `trl`, `bitsandbytes`, `vllm` e PaddleOCR.

### Modelo

- modelo base e revisão; quantidade total de parâmetros; parâmetros treináveis do LoRA (quantidade e percentual);
- quantização no ajuste (4 bits) e na inferência (8 bits); configuração do LoRA (rank, alpha, dropout, módulos-alvo e quantidade de módulos); tamanho do adaptador em disco;
- comprimento máximo de contexto e resolução máxima da imagem enviada.

### Dados

- tamanho das partições de treino, validação e teste das imagens aprovadas e no total;
- distribuição por classe de tipo e de tipo e face em cada partição (tabela e gráfico de barras);
- composições e aumentos aplicados e a semente do particionamento.

### Treinamento

- hiperparâmetros (taxa de aprendizado, épocas, tamanho de lote, acumulação de gradiente, agendador);
- tempo total de treino, exemplos por segundo e pico de memória de GPU;
- curvas de perda de treino e de validação por passo (gráfico).

### Inferência e desempenho

- tempo de carga dos modelos;
- tempo por página na partição de teste: média, mediana, percentil 95 e máximo, separado por etapa (transcrição, detecção, VLM e validação) quando disponível;
- pico de memória de GPU na inferência e média de tokens gerados por página;
- taxa de respostas em JSON válido no contrato;
- comparação com as metas de desempenho (até 30 s por página e até 7,5 GB de memória), como indicadores, sem efeito eliminatório.

### Classificação

Conforme a [análise de desempenho da classificação](#análise-de-desempenho-da-classificação), para tipo e, quando aplicável, para tipo e face, por conjunto aprovado e no agregado:

- acurácia e F1 macro com intervalo de confiança de 95% e cobertura;
- precisão, revocação, F1 e suporte por classe;
- matriz de confusão absoluta e normalizada por linha, com coluna `indefinido` (mapas de calor);
- curva de cobertura por acurácia em função do limiar de rejeição e diagrama de confiabilidade com o ECE (gráficos);
- lista dos pares de classes mais confundidos.

### Extração

- 1 − CER dos campos extraídos por tipo no conjunto de avaliação aprovado, frente à meta de 90%;
- acerto exato e F1 por campo e taxa de campos sem respaldo (alucinação).

### Comparação

- os mesmos indicadores da linha de base *zero-shot* e da execução anterior, lado a lado, com a diferença de cada métrica.
## Experimentos

1. Comparar a arquitetura 1.0 com classificadores ConvNeXt-Tiny/BERTimbau como linha de base.
2. Avaliar VLM zero-shot do Qwen3.5-4B; Qwen3.5-9B, Qwen3.8-27B e Gemma apenas se houver hardware adequado ([ADR-015](../decisions/ADR-015-vlm-qwen35-4b.md)).
3. Avaliar Qwen3.5-4B ajustado com LoRA.
4. Fazer ablação da entrada: imagem, transcrição e imagem + transcrição.
5. Comparar PaddleOCR-VL, PaddleOCR tradicional e Tesseract.
6. Avaliar detecção e mascaramento sobre injeções sintéticas.
