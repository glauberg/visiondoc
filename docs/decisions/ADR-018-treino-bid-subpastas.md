# ADR-018: Decisão histórica de treino em subpastas, divisão 70-15-15 e saídas em visiondoc/logs

- **Status:** Substituído por [ADR-019](ADR-019-treino-imagens-preparadas-invoice.md); mantido apenas como histórico, não orienta etapas atuais da T038
- **Data:** 2026-11-26
- **Altera:** [ADR-017](ADR-017-treino-br-doc-extraction.md) (fonte de dados, partições e alvo do treino)

## Contexto

> **Histórico:** esta decisão descreve uma configuração anterior da T038. Sua fonte de dados e classes foram substituídas pela ADR-019; o conteúdo abaixo não é aplicável ao fluxo atual.

Na configuração registrada em 2026-11-26, a T038 usava uma cópia do BID no Google Drive, em `/content/drive/MyDrive/visiondoc/BID-Dataset`. As imagens eram JPEG, em três subpastas (CNH, RG e CPF), sem anotação de campos, face ou região. Esta fonte foi substituída pela ADR-019 e não é usada nas etapas atuais da T038.

## Decisão

1. **Dados (decisão histórica):** o BID foi definido como fonte do treino. Cada subpasta (sem diferenciar maiúsculas) era uma classe: `cnh`, `rg` ou `cpf`. Subpasta com outro nome era erro.
2. **Divisão:** 70% treino, 15% validação e 15% teste sobre o dataset inteiro, estratificada por classe e com a semente de `config/treino.yaml`, antes de qualquer amostragem. A divisão é gravada em `particoes.csv`.
3. **Alvo:** treino só de classificação. A resposta-alvo traz o tipo, `face = null`, `bbox` da imagem inteira e todos os campos fora da perda. A extração de campos não é avaliada nesta fase.
4. **Classe `outros`:** sem exemplos nesta fase; a rejeição de documentos fora do escopo não é treinada.
5. **Saídas:** logs, gráficos, JSON e CSV vão para `/content/drive/MyDrive/visiondoc/logs`. O cache dos exemplos e o adaptador treinado ficam em `/content/drive/MyDrive/visiondoc`.
6. **Execução curta:** a opção `--por-classe N` do script prepara só N imagens por classe em cada partição, a partir da mesma divisão.

## Consequências

- Na configuração histórica, o script `infrastructure/colab/t038_colab.py` lia aquela fonte no Drive.
- As métricas históricas de classificação cobriam CNH, RG e CPF; não havia métricas de face, região, extração nem de `outros`.
- A preparação histórica podia levar muitas horas no Colab; a amostra por classe permitia validar o fluxo antes.
- A fonte, as classes e a preparação vigentes são as definidas pela ADR-019.
