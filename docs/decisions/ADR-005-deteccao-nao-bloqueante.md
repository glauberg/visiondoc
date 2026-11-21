# ADR-005: Detecção de atos maliciosos sem interrupção do pipeline

- **Status:** Aceito, alterado por [ADR-012](ADR-012-deteccao-antes-do-vlm.md) (ordem no pipeline, mascaramento) e [ADR-013](ADR-013-validacao-saida-vlm.md) (novas categorias); [ADR-016](ADR-016-inventario-e-neutralizacao.md) (`pdfid` substituído pelo inventário com `pikepdf`)
- **Data:** 2026-11-20

> A categoria `divergencia_texto_imagem` deixou de existir com o fim dos dois classificadores. A detecção agora antecede o VLM e mascara ocorrências conhecidas.

## Contexto

Os documentos podem conter scripts, texto oculto ou instruções dirigidas a modelos de linguagem (injeção de prompt). Uma versão anterior da arquitetura desviava os documentos suspeitos para quarentena e revisão humana.

## Decisão

A detecção identifica e sinaliza o caso, mas não interrompe nem desvia o documento. Ele segue para a extração e a saída normalmente, com as colunas de alerta preenchidas.

A detecção cobre quatro frentes:

1. **Conteúdo ativo:** inventário da ingestão, `pdfid` e regras YARA sobre a estrutura do PDF.
2. **Texto oculto:** divergência entre a camada de texto nativa e o OCR (`rapidfuzz`); trechos com fonte menor que 1 pt, cor igual à do fundo ou modo de renderização invisível; caracteres de largura zero e marcas de direção.
3. **Injeção de prompt:** classificador dedicado (Llama Prompt Guard 2 ou o scanner `PromptInjection` do LLM Guard), regras YARA e expressões regulares com padrões imperativos em português e inglês.
4. **Mascaramento:** regiões de texto oculto ou injeção são cobertas na imagem e substituídas na transcrição enviada ao VLM.

## Alternativas consideradas

- **Quarentena com revisão humana:** descartada por interromper o fluxo do peticionamento.
- **Descartar documentos suspeitos:** descartada; o documento pode ser legítimo e a ocorrência pode ter relevância processual.

## Consequências

- O conteúdo malicioso chega ao CSV de saída; a higienização e a neutralização de fórmulas passam a ser obrigatórias ([RN-014](../domain/business-rules.md#rn-014)).
- A sinalização na saída é a única barreira para quem consome o CSV; consumidores devem tratar `inteiro_teor` como dado.
- A taxa de falsos positivos deve ser medida e o limiar calibrado.
