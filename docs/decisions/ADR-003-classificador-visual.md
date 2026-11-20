# ADR-003: Classificador visual com ConvNeXt-Tiny ou YOLO26/YOLO11

- **Status:** Proposto (escolha entre as opções pendente)
- **Data:** 2026-11-20

## Contexto

Com a simplificação do [ADR-002](ADR-002-ocr-bertimbau.md), a classificação poderia depender só do texto do OCR. Isso traz quatro problemas:

1. O trabalho é da área de visão computacional; sem um classificador de imagem, o único componente visual seria o OCR, que é uma ferramenta pronta.
2. Fotocópias ruins e versos com pouco texto derrubam o OCR, mas não um classificador de imagem.
3. O dataset BID foi criado para classificação de imagens de documentos.
4. Páginas com vários documentos (por exemplo, RG e CPF lado a lado) não são separadas por um classificador de texto.

## Decisão

Incluir um classificador visual no fluxo principal, entre o pré-processamento e o OCR, com duas saídas:

- probabilidades por classe, que seguem para a fusão ([ADR-004](ADR-004-fusao-media-ponderada.md));
- a região de cada documento (página inteira ou caixas detectadas), sobre a qual o OCR é executado.

A implementação será uma das opções abaixo.

### Opção A: ConvNeXt-Tiny

- Classifica a página inteira.
- `timm` (por exemplo, `convnext_tiny.fb_in22k_ft_in1k`) ou `torchvision`, pré-treinado no ImageNet e ajustado no BID.
- Explicabilidade com Grad-CAM.
- Licença permissiva (MIT no código e pesos oficiais; confirmar a versão adotada).
- Não separa vários documentos na mesma página.

### Opção B: YOLO26 ou YOLO11 (Ultralytics)

- **Modo classificação** (`yolo26s-cls`, `yolo11s-cls`): equivalente à opção A; serve de comparação.
- **Modo detecção** (`yolo26s`, `yolo11s`, ou variante OBB): localiza e classifica cada documento, gera recortes para o OCR e lida com documentos inclinados (OBB).
- YOLO26 tem inferência de ponta a ponta sem NMS; YOLO11 tem mais resultados publicados para comparação.
- Requer caixas anotadas, que podem ser sintetizadas compondo imagens do BID sobre fundos A4.
- **Licença AGPL-3.0, inclusive para modelos treinados.** Em produção, exige publicar toda a solução sob AGPL-3.0 ou contratar a licença Enterprise da Ultralytics.

## Critério de escolha

| Critério | ConvNeXt-Tiny | YOLO (classificação) | YOLO (detecção) |
|---|---|---|---|
| Vários documentos por página | Não resolve | Não resolve | Resolve |
| Anotação necessária | Rótulo por imagem | Rótulo por imagem | Caixas (sintetizáveis) |
| Licença | Permissiva | AGPL-3.0 | AGPL-3.0 |
| Explicabilidade | Grad-CAM | Possível, menos usual | Caixa explica a decisão |
| Esforço | Baixo | Baixo | Médio |

- Se a maioria das páginas da base real tiver um documento: ConvNeXt-Tiny.
- Se páginas com vários documentos forem frequentes: YOLO26 em modo de detecção, condicionado à solução da licença para produção.
- Para o artigo: comparar as três colunas e fazer o estudo de ablação (texto, imagem, fusão) sobre a melhor.

## Consequências

- O pipeline passa a ter dois modelos treináveis (visual e textual).
- Com o YOLO em detecção, a unidade de saída passa a ser o documento detectado, não a página ([ADR-008](ADR-008-saida-csv.md)).
- Com o YOLO em detecção, o recorte por contornos do pré-processamento vira alternativa usada apenas quando o detector não encontra nada.
- A decisão final deve ser registrada em um novo ADR após a medição da frequência de páginas com vários documentos na base da JFRN.
