# ADR-002: Classificação por OCR e BERTimbau em vez de ramos semântico e de fundo

- **Status:** Substituído por [ADR-010](ADR-010-vlm-qwen35-9b-lora.md), [ADR-011](ADR-011-transcricao-paddleocr-vl.md) e [ADR-014](ADR-014-extracao-de-campos.md)
- **Data:** 2026-11-20

> Mantido como registro histórico. O BERTimbau permanece apenas como linha de base nos experimentos.

## Contexto

A primeira versão da arquitetura tinha três ramos de percepção (caracteres, layout semântico com Docling e LayoutLMv3, e imagem de fundo com ViT e SigLIP) e uma rede de fusão aprendida. Uma proposta posterior sugeriu um fluxo mais simples: pré-processamento, OCR com PaddleOCR ou EasyOCR, montagem de um dataset textual rotulado e fine-tuning do BERTimbau para classificar o texto.

## Decisão

Adotar o fluxo simplificado:

- Pré-processamento com correção de orientação.
- OCR com PaddleOCR (EasyOCR como alternativa).
- Classificação do texto com BERTimbau ajustado.
- O inteiro teor passa a ser o próprio texto do OCR, normalizado.

Remover:

- O ramo semântico de layout (Docling, LayoutLMv3).
- O ramo de imagem de fundo com ViT, SigLIP e detector de selos.
- A rede de fusão aprendida.
- A extração estruturada de campos.

O componente visual é mantido em forma reduzida ([ADR-003](ADR-003-classificador-visual.md)).

## Alternativas consideradas

- **Manter os três ramos:** descartada por custo de implementação e treinamento desproporcional para documentos de identidade, que têm pouco texto e layout fixo.
- **Classificação apenas textual, sem componente visual:** descartada; ver [ADR-003](ADR-003-classificador-visual.md).

## Consequências

- Menos modelos para treinar, servir e manter.
- Desaparece a restrição de licença não comercial dos pesos do LayoutLMv3.
- O BERTimbau é um classificador do tipo *encoder*, que não segue instruções: uma injeção de prompt não consegue comandá-lo, o que reduz a superfície de ataque.
- Texto adversarial ainda pode enviesar a classificação textual.
- A extração estruturada de campos fica para trabalho futuro.
