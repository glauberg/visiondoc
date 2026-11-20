# Segurança

Documentação de segurança do pipeline documental:

- [Modelo de ameaças](threat-model.md): ativos, fronteiras, ameaças e invariantes.
- [Ingestão e preparação de PDF/JPEG](pdf-ingestion.md): validação, inventário e saneamento de PDF, decodificação segura e orientação de imagens.
- [Detecção de conteúdo malicioso](malicious-content-detection.md): texto oculto, injeção de prompt, correlação e evidências.
- [Alertas](audit-and-alerting.md): tratamento não bloqueante, evidência limitada e regravação.
- [Exportação CSV](csv-export.md): neutralização de fórmulas e requisitos dos consumidores.

A especificação SDD que relaciona esses mecanismos está em `specs/001-pipeline-documental-seguro/`. Todos os documentos são propostas a validar; não garantem detecção integral nem substituem revisão de segurança.

