# ADR-019: Treino com as imagens preparadas do br-doc-extraction e classe invoice

- **Status:** Aceito
- **Data:** 2026-11-27
- **Altera:** [ADR-015](ADR-015-vlm-qwen35-4b.md) (fonte da T038), [ADR-017](ADR-017-treino-br-doc-extraction.md) e [ADR-018](ADR-018-treino-bid-subpastas.md) (fonte de dados e classes do treino), [RN-003](../domain/business-rules.md#rn-003) e o [contrato da saída do VLM](../contracts/saida-vlm.md) (tipo `invoice`)

## Contexto

O treino da T038 usa exclusivamente as imagens já preparadas em `/content/drive/MyDrive/visiondoc/cache/imagens/`. As classes são lidas de `/content/drive/MyDrive/visiondoc/cache/MANIFESTO.JSONL`, cujas linhas seguem o formato do cache de preparação: `id`, `particao`, `tipo`, `campos`, `sem_anotacao`, `imagem`, `transcricao`, `inteiro_teor`, `largura`, `altura` e `erro`. As classes são CNH, RG e INVOICE (nota fiscal).

## Decisão

1. **Dados:** a fonte do treino é o `MANIFESTO.JSONL`, procurado sem diferenciar maiúsculas, com as imagens em `imagens/`. Linhas com `erro` ou sem imagem são descartadas e contadas. Um tipo fora de `cnh`, `rg` e `invoice` é erro. `outros`, nome com que a preparação do ADR-017 gravava as notas fiscais, é lido como `invoice`.
2. **Classe `invoice`:** passa a ser um tipo próprio no conjunto fechado (RN-003) e no contrato da saída do VLM, sem campos pertinentes: todos são `null`, como em `outros`. `outros` continua no contrato para os documentos fora do escopo.
3. **Divisão:** 70% para treino, 15% para validação e 15% para teste, sobre todas as imagens válidas, estratificada por classe e com a semente de `config/treino.yaml`. A divisão é gravada em `particoes.csv`. A partição original do manifesto é ignorada.
4. **Alvo:** treino só de classificação, como no ADR-018:
   - os campos de `cnh` e `rg` ficam fora da perda, mesmo quando o manifesto os anota;
   - em `invoice`, os `null` entram na perda.
   A extração de campos não é avaliada.
5. **Sem nova preparação:** as imagens e a transcrição são usadas como estão no manifesto, e o PaddleOCR não é executado nem instalado. O cache de treino guarda só o manifesto, em `/content/drive/MyDrive/visiondoc/treino/cache`, e as imagens são referenciadas na fonte por caminho absoluto. O adaptador fica em `/content/drive/MyDrive/visiondoc/treino/saida`.
6. **Saídas:** continuam em `/content/drive/MyDrive/visiondoc/logs` (ADR-018).

## Consequências

- **Classes avaliadas:** as métricas de classificação (acurácia, F1 macro e matriz de confusão) cobrem CNH, RG e INVOICE. CPF e `outros` não têm exemplos nesta fase.
- **Instrução do VLM:** passa a listar `invoice`, o que vale também para a linha de base *zero-shot* e para o pipeline.
- **Transcrição vazia:** quando o manifesto não tem transcrição, o modelo é treinado sem ela, enquanto na inferência recebe a do PaddleOCR-VL. Essa diferença foge da regra de entrada igual à da inferência (RF-SDD-17). A etapa de verificação conta as transcrições vazias e avisa.