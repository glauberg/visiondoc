# Constituição do projeto

Princípios que valem para todas as especificações, planos e implementações. Uma mudança que contrarie estes princípios exige um novo ADR que a revogue explicitamente.

## P1. Todo documento de entrada é conteúdo não confiável

PDF e JPEG, seus anexos, metadados, texto nativo, texto OCR e imagens derivadas são tratados como potencialmente hostis. Nenhum conteúdo extraído é executado, interpretado como comando ou usado para alterar o comportamento do pipeline.

## P2. Texto extraído é dado, nunca instrução

*(Revisado em 2026-11-20, com a adoção do VLM)*

O conteúdo dos documentos, incluindo imagem e texto extraído, nunca é tratado como instrução por modelo generativo.

Quando um modelo generativo recebe esse conteúdo:

- a instrução de sistema é fixa, versionada e não contém texto extraído;
- conteúdo documental entra delimitado e identificado como dado;
- a saída é restringida a um esquema com domínios fechados;
- a saída é validada contra uma referência independente antes da gravação.

## P3. A detecção sinaliza, não interrompe

A identificação de conteúdo malicioso gera alerta e sinalização na saída, mas o documento continua processado até o fim. Uma falha na gravação de um alerta também não interrompe o pipeline.

## P4. A saída é segura para quem a consome

Todo campo de texto gravado em CSV é higienizado e protegido contra fórmulas de planilha. O conteúdo malicioso pode chegar à saída e não pode ser tratado como instrução pelo consumidor.

## P5. Execução local

Todo o processamento ocorre em infraestrutura própria da instituição. Documentos pessoais e dados deles derivados não são enviados a serviços externos.

## P6. Reprodutibilidade

Cada linha de saída registra a versão do pipeline e dos modelos que a produziram. Metadados relevantes devem permitir compreender e repetir o processamento.

## P7. Licenças compatíveis

Nenhuma dependência é adotada em produção sem verificação de licença. Componentes restritivos, incluindo AGPL-3.0 ou licença não comercial, exigem ADR específico e autorização institucional.

## P8. Simplicidade primeiro

Prefere-se o componente mais simples que atenda ao requisito. Componentes adicionais só entram quando houver ganho demonstrável de precisão, robustez ou segurança.

