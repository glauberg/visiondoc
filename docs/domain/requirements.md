# Requisitos do domínio

Versão 2.0 (2026-11-20).

## Objetivo

O VisionDoc apoia a triagem de documentos em petições iniciais. O pipeline transcreve o documento, sinaliza conteúdo suspeito, classifica e extrai campos por VLM e gera CSV.

Os resultados são apoio à triagem e não decidem mérito, autenticidade ou validade jurídica.

## Requisitos funcionais

- **RF-01 — Entrada:** aceitar PDF/JPEG reais estritamente menores que 2.000.000 bytes.
- **RF-02 — Orientação:** processar documentos em português do Brasil em orientações horizontal, vertical, inclinada, girada, invertida ou espelhada.
- **RF-03 — Transcrição:** produzir inteiro teor em ordem de leitura e caixas com PaddleOCR-VL.
- **RF-04 — Classificação:** produzir `cnh`, `rg`, `cpf`, `invoice`, `outros` ou `indefinido`.
- **RF-05 — Extração:** extrair campos pertinentes a CNH, RG e CPF. Ausência ou ambiguidade não pode ser inferida.
- **RF-06 — Localização:** produzir `bbox` para cada documento identificado pelo VLM.
- **RF-07 — Revisão:** disponibilizar revisão humana amostral sem pré-condição por documento.
- **RF-08 — Segurança:** detectar conteúdo ativo, texto oculto e injeção sem executar ou obedecer a conteúdo documental.
- **RF-09 — Mascaramento:** mascarar regiões suspeitas conhecidas na imagem e substituir trechos na transcrição enviada ao VLM.
- **RF-10 — Validação:** validar esquema, confiança, pertinência, respaldo na transcrição e consistência.
- **RF-11 — Alertas:** registrar ocorrências em `alertas.csv` e no resumo do CSV principal sem bloquear o processamento.
- **RF-12 — CSV:** gerar uma linha por documento identificado, com campos, inteiro teor, modelos, situação e alertas.
- **RF-13 — Segurança do CSV:** neutralizar fórmulas e higienizar todos os campos derivados.

## Requisitos não funcionais

- **RNF-01 — Execução institucional:** nenhum documento ou trecho pode ir a nuvem pública.
- **RNF-02 — Segurança:** isolar parsers, decodificadores e modelos; nunca executar conteúdo recebido.
- **RNF-03 — Precisão:** medir CER, classificação, extração e alucinação em conjunto autorizado.
- **RNF-04 — Privacidade:** minimizar dados em logs, alertas, CSV e revisão.
- **RNF-05 — Licenças:** verificar licenças e registrar componentes restritivos em ADR.
- **RNF-06 — Reprodutibilidade:** registrar versão do pipeline, modelo VLM e modelo de transcrição.
- **RNF-07 — Honestidade:** ausência de alerta não indica segurança e `processado` não indica documento seguro ou revisado.
