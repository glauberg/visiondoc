# ADR-001: Entrada em PDF tratada como não confiável

- **Status:** Aceito
- **Data:** 2026-11-20

## Contexto

Os documentos chegam como PDFs anexados pelas partes no peticionamento inicial. Um PDF pode conter JavaScript, ações automáticas, arquivos embutidos, formulários e uma camada de texto que não corresponde ao que se vê na página. A proposta de origem (classificação a partir da imagem) não trata da entrada em PDF.

## Decisão

Toda entrada passa por uma etapa de ingestão e saneamento antes de qualquer outra:

1. Validar a estrutura do PDF.
2. Inventariar e remover `/JavaScript`, `/OpenAction`, `/AA`, `/Launch`, `/EmbeddedFiles` e `/AcroForm`.
3. Verificar malware conhecido com antivírus.
4. Calcular o SHA-256 do arquivo original.
5. Rasterizar cada página.
6. Preservar a camada de texto nativa à parte, com posição, fonte, cor e modo de renderização de cada trecho, para uso na detecção de texto oculto.

Todo o processamento posterior trabalha sobre as imagens rasterizadas.

## Alternativas consideradas

- **Processar o PDF diretamente, extraindo o texto nativo:** descartada, porque o texto nativo pode divergir do conteúdo visível e é o principal vetor de texto oculto.
- **Aceitar apenas imagens:** descartada, porque o sistema de peticionamento recebe PDFs.

## Consequências

- O inventário do que foi removido alimenta a detecção de conteúdo ativo ([ADR-005](ADR-005-deteccao-nao-bloqueante.md)).
- A rasterização tem custo de processamento e memória, compensado pela uniformidade da entrada.
- `PyMuPDF` foi preterido em favor de `pypdfium2` por licença (AGPL-3.0 no primeiro).
