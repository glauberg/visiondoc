# ADR-013: Validação da saída do VLM

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Mesmo com saída restrita a um esquema, o VLM pode produzir valores plausíveis que não estão no documento (alucinação) ou valores influenciados por uma injeção não detectada.

## Decisão

Toda saída do Qwen3.5-9B passa por uma etapa de validação antes da gravação:

1. **Esquema:** conformidade com [`contratos/saida-vlm.md`](../contracts/saida-vlm.md) (`pydantic`).
2. **Confiança:** tipo com confiança abaixo do limiar vira `indefinido` ([RN-004](../domain/business-rules.md#rn-004)).
3. **Respaldo na transcrição:** cada campo extraído precisa aparecer na transcrição do PaddleOCR-VL, após normalização ([RN-024](../domain/business-rules.md#rn-024)).
4. **Consistência:** dígitos verificadores do CPF, datas válidas e em ordem plausível ([RN-025](../domain/business-rules.md#rn-025)).
5. **Coerência entre campos e tipo:** campos que não pertencem ao tipo previsto são descartados ([RN-023](../domain/business-rules.md#rn-023)).

Falhas geram ocorrências em `alertas.csv` (categorias `campo_sem_respaldo` e `dado_inconsistente`) e não interrompem o pipeline.

## Alternativas consideradas

- **Confiar na saída estruturada do VLM:** descartada; o esquema garante a forma, não a veracidade.
- **Segundo VLM como verificador:** descartada por custo; a transcrição já é uma referência independente.

## Consequências

- Campos sem respaldo são removidos da saída, o que reduz a cobertura em troca de confiabilidade.
- A taxa de campos sem respaldo passa a ser métrica de alucinação no artigo.
- Um campo sem respaldo num documento que também teve `injecao_prompt` indica possível sucesso da injeção e eleva a severidade ([RN-026](../domain/business-rules.md#rn-026)).
