# Especificação de segurança: ingestão e preparação de PDF/JPEG

## Objetivo e escopo

Definir controles para receber, validar, sanear e preparar PDFs e imagens JPEG antes do processamento multimodal. Arquivos e conteúdo são não confiáveis. Formatos aceitos: PDF e JPEG (`.jpg`/`.jpeg`), com tamanho estritamente inferior a 2.000.000 bytes por arquivo.

## Requisitos

- **ING-SEC-01 — Validação de formato/limite:** verificar formato real além da extensão, tamanho em bytes e decodificabilidade. Recusar tipo não suportado ou arquivo com tamanho igual/superior a 2.000.000 bytes. Os limites de páginas/dimensões, tempo e memória precisam ser definidos.
- **ING-SEC-02 — Identificação:** calcular hash criptográfico do arquivo e registrar nome, hash e data/hora da verificação. SHA-256 e timestamp ISO 8601 UTC são propostas a confirmar.
 - **ING-SEC-03 — Identificação:** calcular nome, SHA-256 e data/hora antes do processamento. A identificação não depende de trilha append-only.
- **ING-SEC-04 — Inspeção de PDF:** antes de remover elementos ativos, inventariar JavaScript, ações automáticas, anexos embutidos, formulários e demais elementos reconhecidos pelo parser aprovado.
- **ING-SEC-05 — Não execução:** nunca executar JavaScript, ações, macros, anexos ou conteúdo recebido. Parsers/renderizadores/decodificadores operam isolados, sem permissões desnecessárias nem rede não aprovada.
- **ING-SEC-06 — Saneamento PDF:** remover conteúdo ativo por reescrita segura e/ou renderização de páginas em imagens estáticas. Verificar a saída saneada e manter inventário para detecção.
- **ING-SEC-07 — Texto nativo:** extrair a camada de texto nativa do PDF, se existir, antes de transformação que possa descartá-la; preservá-la separadamente para comparação posterior com OCR, protegida como dado sensível e não confiável.
- **ING-SEC-08 — Orientação:** aceitar páginas/imagens horizontais ou verticais, inclinadas, rotacionadas/invertidas (inclusive 180 graus) e espelhadas nos eixos. Corrigir orientação/inclinação antes do reconhecimento e preservar a relação entre coordenadas normalizadas e origem.
- **ING-SEC-09 — JPEG:** decodificar JPEG em ambiente isolado; tratar EXIF, perfis de cor e demais metadados como entrada não confiável. Política de remoção/preservação de metadados e limites de dimensão devem ser aprovados.

## Fluxo exigido

1. Validar formato e tamanho do PDF/JPEG; rejeitar entrada inválida.
2. Gerar nome, SHA-256 e timestamp da tentativa.
3. No PDF, inventariar conteúdo ativo sem executá-lo, extrair texto nativo quando existir e sanear.
4. Rasterizar PDF e normalizar orientação/rotação/inclinação da imagem preparada.
5. Avançar ao OCR e aos classificadores com dados derivados não confiáveis.

## Critérios de aceitação

- [ ] PDF e JPEG abaixo do limite são aceitos; formato incompatível ou tamanho `>= 2.000.000` bytes é rejeitado e identificado.
- [ ] PDF sintético com conteúdo ativo suportado é inventariado antes da remoção; nenhum conteúdo recebido é executado.
- [ ] PDF é fornecido às etapas visuais como páginas estáticas; texto nativo, quando presente, permanece separado para comparação.
- [ ] JPEG e PDF em orientações horizontal/vertical, inclinada, girada e espelhada são preparados com localização rastreável.
- [ ] A identificação por nome e SHA-256 acompanha toda linha de erro ou processamento.
- [ ] Testes usam documentos sintéticos ou autorizados e nunca executam conteúdo ativo.

## Decisões pendentes

Confirmar unidade de 2 MB; parser/renderer/decoder aprovados; limites de páginas, dimensão, tempo e memória; política para PDFs criptografados/corrompidos; preservação/retensão do original e intermediários; tratamento de EXIF; algoritmo de hash e formato de data/hora.

