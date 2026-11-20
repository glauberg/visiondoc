# ADR-004: Fusão por média ponderada

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Há dois classificadores (visual e textual) produzindo probabilidades sobre o mesmo conjunto de classes. A primeira versão da arquitetura previa uma rede de fusão aprendida (concatenação de embeddings e MLP, ou atenção cruzada).

## Decisão

Combinar as probabilidades por média ponderada:

```
p_final = w_visual * p_visual + w_texto * p_texto,   com w_visual + w_texto = 1
```

Os pesos são calibrados no conjunto de validação. As probabilidades de cada classificador são calibradas antes da fusão (por exemplo, *temperature scaling*).

## Alternativas consideradas

- **Rede de fusão aprendida:** descartada por exigir treino adicional e mais dados, com ganho incerto.
- **Votação simples:** descartada por perder a informação de confiança.

## Consequências

- Nenhum treino adicional além dos dois classificadores.
- Os escores individuais são mantidos na saída (`confianca_visual`, `confianca_texto`) para análise e para a regra de divergência ([RN-011](../domain/business-rules.md#rn-011)).
- Se os pesos calibrados indicarem que um dos classificadores não contribui, o estudo de ablação registra o fato.
