# ADR-006: Alertas exportados em CSV próprio

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Versões anteriores previam notificação assíncrona por fila (Redis Streams ou RabbitMQ), SIEM e e-mail. Para o escopo atual, basta um registro estruturado das ocorrências que possa ser consultado e cruzado com a saída principal.

## Decisão

Cada ocorrência detectada é gravada como uma linha em `alertas.csv`, ligada à linha do CSV principal por `id_registro`. O esquema está em [`contratos/alertas-csv.md`](../contratos/alertas-csv.md).

Regras de escrita:

- Módulo `csv` da biblioteca padrão, em modo de acréscimo, com aspas em todos os campos e UTF-8.
- `defusedcsv` para neutralizar fórmulas.
- Escrita dentro de `try/except`; em caso de falha, o alerta fica em memória e é regravado ao fim do lote.
- Com processamento paralelo, `filelock` para serializar a escrita, ou um arquivo por processo consolidado com `pandas` ao fim do lote.
- Um arquivo por dia: `alertas_AAAA-MM-DD.csv`.

## Alternativas consideradas

- **Fila e SIEM:** adiada; pode ser acrescentada depois lendo o próprio `alertas.csv`.
- **Alertas apenas como colunas do CSV principal:** descartada, porque um documento pode ter várias ocorrências e a evidência detalhada sobrecarregaria a saída principal.

## Consequências

- Não há notificação em tempo real; a consulta aos alertas é feita sobre o arquivo.
- O CSV principal mantém apenas o resumo (`alerta_seguranca`, `severidade_alerta`, `detalhe_alerta`).
- A coluna `evidencia` contém conteúdo hostil; a neutralização é obrigatória.
