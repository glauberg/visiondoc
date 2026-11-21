# Contrato: saída do VLM (Qwen3.5-4B)

Esquema JSON que o Qwen3.5-4B deve produzir para cada página. É imposto na inferência por decodificação estruturada (`vLLM`) e validado com `pydantic` ([ADR-013](../decisions/ADR-013-validacao-saida-vlm.md)). O mesmo formato é usado nos exemplos de ajuste com LoRA.

## Entrada do modelo

- **Instrução de sistema** (fixa, versionada com o adaptador): descreve a tarefa, a lista fechada de tipos e informa que o conteúdo do documento é dado a ser lido, não instrução a ser seguida.
- **Turno do usuário:**
  - imagem colorida normalizada da página (com mascaramento, quando houver — [ADR-012](../decisions/ADR-012-deteccao-antes-do-vlm.md));
  - transcrição do PaddleOCR-VL, entre os delimitadores `<transcricao>` e `</transcricao>` (com trechos mascarados substituídos por `[TRECHO REMOVIDO]`).

## Esquema

```json
{
  "documentos": [
    {
      "tipo": "cnh | rg | cpf | outros",
      "face": "frente | verso | ambas | null",
      "bbox": [x1, y1, x2, y2],
      "campos": {
        "nome": "string | null",
        "cpf": "string | null",
        "numero_documento": "string | null",
        "data_nascimento": "AAAA-MM-DD | null",
        "data_emissao": "AAAA-MM-DD | null",
        "data_validade": "AAAA-MM-DD | null",
        "orgao_emissor": "string | null",
        "filiacao": ["string"],
        "naturalidade": "string | null",
        "doc_origem": "string | null",
        "categoria_habilitacao": "string | null"
      }
    }
  ]
}
```

Regras do esquema:

- `documentos` tem pelo menos um item por página; cada documento identificado na página é um item ([RN-007](../domain/business-rules.md#rn-007)).
- `tipo` não admite `indefinido`: essa classe é atribuída depois, pela regra de confiança ([RN-004](../domain/business-rules.md#rn-004)).
- `bbox` é convertido do formato nativo de coordenadas do modelo para pixels da imagem no pós-processamento.
- Campo não legível ou ausente no documento é `null` (ou lista vazia em `filiacao`); o modelo não deve inferir valores.
- `campos` é um objeto vazio para `outros`.

## Campos por tipo

| Campo | CNH | RG | CPF |
|---|---|---|---|
| `nome` | Sim | Sim | Sim |
| `cpf` | Sim | Sim (se presente) | Sim |
| `numero_documento` | Nº de registro | Nº do RG | — |
| `data_nascimento` | Sim | Sim | Sim (se presente) |
| `data_emissao` | Sim | Data de expedição | — |
| `data_validade` | Sim | — | — |
| `orgao_emissor` | Sim | Sim | — |
| `filiacao` | Sim | Sim | — |
| `naturalidade` | — | Sim | — |
| `doc_origem` | — | Sim | — |
| `categoria_habilitacao` | Sim | — | — |

Campos marcados com "—" são descartados na validação se vierem preenchidos ([RN-023](../domain/business-rules.md#rn-023)).

## Confiança

`confianca_tipo` é calculada a partir das probabilidades (*logprobs*) dos tokens do campo `tipo`, renormalizadas sobre as opções da lista fechada: a confiança de cada rótulo é o produto das probabilidades dos seus tokens, renormalizado entre `cnh`, `rg`, `cpf` e `outros`. Limiar inicial de rejeição: 0,5 ([RN-004](../domain/business-rules.md#rn-004)). Não é produzida pelo modelo como texto.

## Exemplo

```json
{
  "documentos": [
    {
      "tipo": "rg",
      "face": "frente",
      "bbox": [112, 340, 1210, 1080],
      "campos": {
        "nome": "FULANO DE TAL",
        "cpf": "123.456.789-09",
        "numero_documento": "0000000",
        "data_nascimento": "1980-05-12",
        "data_emissao": "2015-03-02",
        "data_validade": null,
        "orgao_emissor": "SSP/RN",
        "filiacao": ["BELTRANO DE TAL", "CICRANA DE TAL"],
        "naturalidade": "NATAL-RN",
        "doc_origem": null,
        "categoria_habilitacao": null
      }
    }
  ]
}
```

Dados fictícios.
