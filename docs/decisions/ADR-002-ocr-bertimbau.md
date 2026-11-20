# ADR-002: Classificação por OCR e BERTimbau em vez de ramos semântico e de fundo

- **Status:** Aceito
- **Data:** 2026-11-20

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
- Texto adversarial ainda pode enviesar a classificação textual; a divergência com o classificador visual vira sinal de alerta ([RN-011](../domain/business-rules.md#rn-011)).
- A extração estruturada de campos fica para trabalho futuro.
