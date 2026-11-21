# Dados e avaliação

Versão: 2.0 (2026-11-20).

## Conjuntos de dados

### BID Dataset

O Brazilian Identity Document Dataset contém imagens sintéticas e informações falsas. Inclui oito classes de frente e verso de CNH, CPF e RG, totalizando 28.800 imagens. É usado no ajuste do VLM e nas linhas de base.

### br-doc-extraction

O dataset `tech4humans/br-doc-extraction` contém imagem e resposta JSON de campos. Serve ao ajuste de extração e, pela sua própria partição de teste, à medição da meta de 90%; seus resultados são reportados separadamente e não substituem os do BID.

### Dados sintéticos complementares

- páginas compostas sobre fundos A4;
- injeções sintéticas de texto oculto e instruções;
- degradações de fotocópia, desfoque, compressão, ruído e JPEG;
- caixas conhecidas automaticamente para treino de detecção.

## Cuidados

1. Resultados em dados sintéticos não comprovam o desempenho em documentos reais; relatórios devem explicitar essa limitação.
2. A classe `outros` evita que documentos não suportados sejam forçados para RG, CPF ou CNH.
3. Treino, validação e teste são separados antes de composição ou aumento de dados.
4. *(Definido em 2026-11-21)* Na fase de desenvolvimento e testes não são admitidos dados reais nem documentos de processos judiciais, nem para treinamento nem para teste ou avaliação. Treino, validação e teste usam apenas os dados sintéticos/fictícios do BID, do `br-doc-extraction` e das composições sintéticas.

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
| Desempenho | Tempo por página, GPU e memória |

O alvo mínimo é 90% de precisão em nível de caractere em conjunto aprovado, reportado por categoria e condição representativa. Esse limite não é garantia por documento. *(Definido em 2026-11-21)* A meta é medida sobre os **campos extraídos**: 1 − CER entre o valor extraído e o valor de referência, por tipo de documento, nas partições de teste do BID e do `br-doc-extraction`. A meta vale para **cada um dos dois datasets**, reportados separadamente.

## Análise de desempenho da classificação

A análise de desempenho do trabalho usa **acurácia**, **F1 macro** e **matriz de confusão**, calculadas sobre o conjunto de teste separado antes de composição ou aumento de dados.

### Granularidade

- **Tipo:** classes de referência `cnh`, `rg`, `cpf` e `outros`.
- **Tipo e face:** as oito classes BID (tipo × frente/verso) mais `outros`.
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
  - documentos fora do escopo classificados como `cnh`, `rg` ou `cpf` (confusões a partir de `outros`), mais graves por gerarem extração indevida.

### Recortes

As três medidas são reportadas:

- no agregado e por conjunto (partições de teste do BID e do `br-doc-extraction`);
- por condição representativa: orientação (horizontal, vertical, girada, espelhada), degradação (fotocópia, desfoque, compressão, ruído) e páginas com vários documentos;
- com e sem a regra de rejeição, junto da curva cobertura × acurácia em função do limiar;
- para cada experimento (linhas de base ConvNeXt-Tiny/BERTimbau, VLM *zero-shot* e Qwen3.5-4B com LoRA), com o mesmo particionamento, para permitir comparação direta.

### Intervalo de confiança e metas

Intervalos de confiança de 95% são estimados por *bootstrap* com 1.000 reamostragens. Não há meta mínima de acurácia ou F1 macro (Q-27 da [especificação 001](../../specs/001-pipeline-documental-seguro/spec.md)).

## Experimentos

1. Comparar a arquitetura 1.0 com classificadores ConvNeXt-Tiny/BERTimbau como linha de base.
2. Avaliar VLM zero-shot do Qwen3.5-4B; Qwen3.5-9B, Qwen3.8-27B e Gemma apenas se houver hardware adequado ([ADR-015](../decisions/ADR-015-vlm-qwen35-4b.md)).
3. Avaliar Qwen3.5-4B ajustado com LoRA.
4. Fazer ablação da entrada: imagem, transcrição e imagem + transcrição.
5. Comparar PaddleOCR-VL, PaddleOCR tradicional e Tesseract.
6. Avaliar detecção e mascaramento sobre injeções sintéticas.
