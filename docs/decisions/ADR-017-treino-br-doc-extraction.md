# ADR-017: Treino inicial com o dataset tech4humans/br-doc-extraction

- **Status:** Aceito, alterado por [ADR-018](ADR-018-treino-bid-subpastas.md) (o treino passa a usar o BID)
- **Data:** 2026-11-25
- **Altera:** [ADR-015](ADR-015-vlm-qwen35-4b.md) (dados do ajuste) e o [contrato da saída do VLM](../contracts/saida-vlm.md) (campos de `outros`)

## Contexto

A T038 precisa de exemplos no formato do contrato. A fonte inicial definida é apenas o dataset `tech4humans/br-doc-extraction`, carregado com `load_dataset` no Google Colab. Ele tem as partições `train` (1.062 linhas, com três aumentos por imagem de origem), `valid` (75) e `test` (81) e as colunas `image`, `schema` (prompt com os campos anotados), `response` (JSON) e `type` (`cnh`, `rg`, `invoice`). As imagens de CNH e RG vêm do BID (dados fictícios); as notas fiscais, de um dataset do Zenodo. Não há licença declarada, nem anotação de face ou de região do documento, e cada linha anota só parte dos campos.

## Decisão

1. **Uso e licença:** aceitam-se as licenças informadas e desconhecidas das fontes, porque o objetivo desta fase é validar o pipeline, não distribuir dados ou modelos.
2. **Partições:** usam-se as do próprio dataset (`train`, `valid`, `test`); os aumentos existem só em `train`.
3. **Classes:** `cnh` e `rg` mantidos; `invoice` vira `outros`, sem campos. A classe `cpf` não tem exemplos nesta fase, e isso aparece nos relatórios.
4. **Face e bbox:** `face = null`; `bbox` cobre a imagem inteira, no formato de coordenadas do modelo definido em `config/treino.yaml` (`relativo_1000`, sugerido pela prova de conceito T020 e ainda não confirmado). As métricas de face e de IoU não são avaliadas com este dataset.
5. **Campos:** as chaves do dataset são mapeadas para o contrato (`visiondoc.treino.mapeamento`), com datas em `AAAA-MM-DD`, CPF em `000.000.000-00` e nomes em maiúsculas. Campos não pertinentes ao tipo são `null` conhecidos. Campos pertinentes que a linha não anota, ou com data inválida, entram no alvo como `null`, mas seus tokens ficam **fora da perda**.
6. **Saída com todas as chaves:** o alvo e a decodificação estruturada exigem todas as chaves do contrato, inclusive em `outros`, com `null` (achado da T020). Isso substitui "`campos` é um objeto vazio para `outros`".
7. **Entrada igual à da inferência:** os exemplos passam por ingestão, pré-processamento, PaddleOCR-VL, detecção e mascaramento antes do treino.
8. **Ferramentas:** `transformers` (`Trainer`), `peft` e `bitsandbytes`, com MLflow; o `trl` não é necessário, pois o coletor próprio monta os rótulos com os trechos ignorados.
9. **Avaliação nesta fase:** linha de base *zero-shot* e modelo treinado avaliados com `transformers` em 4 bits, sem decodificação guiada; a inferência em 8 bits pelo vLLM depende da T031.

## Consequências

- O treino é executável no Colab pelo script `infrastructure/colab/t038_colab.py`, com relatório por execução (RF-SDD-18).
- Os resultados não comprovam desempenho em documentos reais, nem em CPF, faces ou páginas com vários documentos.
- O formato do `bbox` precisa ser confirmado com o modelo; se for outro, muda só `formato_bbox` em `config/treino.yaml`.
- Rótulos semiautomáticos do dataset podem ter ruído (por exemplo, datas de validade anteriores à emissão).
