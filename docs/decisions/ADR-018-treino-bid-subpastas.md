# ADR-018: Treino com o BID em subpastas, divisão 70-15-15 e saídas em visiondoc/logs

- **Status:** Aceito
- **Data:** 2026-11-26
- **Altera:** [ADR-017](ADR-017-treino-br-doc-extraction.md) (fonte de dados, partições e alvo do treino)

## Contexto

O treino da T038 passa a usar o BID, disponível no Google Drive em `/content/drive/MyDrive/visiondoc/BID-Dataset`. As imagens estão em JPEG, em três subpastas, CNH, RG e CPF, que são as classes. Não há outros arquivos nas subpastas, nem anotação de campos, face ou região, nem documentos fora dessas três classes.

## Decisão

1. **Dados:** o BID substitui o `tech4humans/br-doc-extraction` como fonte do treino. Cada subpasta (sem diferenciar maiúsculas) é uma classe: `cnh`, `rg` ou `cpf`. Subpasta com outro nome é erro.
2. **Divisão:** 70% treino, 15% validação e 15% teste sobre o dataset inteiro, estratificada por classe e com a semente de `config/treino.yaml`, antes de qualquer amostragem. A divisão é gravada em `particoes.csv`.
3. **Alvo:** treino só de classificação. A resposta-alvo traz o tipo, `face = null`, `bbox` da imagem inteira e todos os campos fora da perda. A extração de campos não é avaliada nesta fase.
4. **Classe `outros`:** sem exemplos nesta fase; a rejeição de documentos fora do escopo não é treinada.
5. **Saídas:** logs, gráficos, JSON e CSV vão para `/content/drive/MyDrive/visiondoc/logs`. O cache dos exemplos e o adaptador treinado ficam em `/content/drive/MyDrive/visiondoc`.
6. **Execução curta:** a opção `--por-classe N` do script prepara só N imagens por classe em cada partição, a partir da mesma divisão.

## Consequências

- O treino roda pelo script `infrastructure/colab/t038_colab.py`, com o BID e as saídas no Drive.
- As métricas de classificação (acurácia, F1 macro e matriz de confusão) cobrem CNH, RG e CPF; não há métricas de face, região, extração nem de `outros`.
- Preparar o BID inteiro com PaddleOCR-VL pode levar muitas horas no Colab; a amostra por classe permite validar o fluxo antes.
- O código de mapeamento do `br-doc-extraction` continua disponível, mas não é usado pelo script.
