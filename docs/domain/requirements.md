# Requisitos do domínio

## Objetivo

O VisionDoc apoia a triagem de documentos de identificação apresentados em petições iniciais judiciais. O escopo preliminar é RG, CPF e CNH, além das rejeições `outros` e `indefinido`. A solução combina OCR, visão computacional e técnicas complementares.

Os resultados são apoio à triagem. Não decidem mérito, autenticidade, admissibilidade ou validade jurídica.

## Requisitos funcionais

- **RF-01 — Entrada:** aceitar PDF e JPEG (`.jpg`/`.jpeg`) estritamente menores que 2.000.000 bytes. Validar formato real, não apenas extensão.
- **RF-02 — Orientação:** processar documentos em português do Brasil, horizontais ou verticais, inclinados, girados, invertidos ou espelhados.
- **RF-03 — Classificação:** produzir `rg`, `cpf`, `cnh`, `outros` ou `indefinido`, sem forçar uma das três classes suportadas quando a evidência é insuficiente.
- **RF-04 — Extração:** sugerir nome completo, data de nascimento, nome da mãe, nome do pai, número do documento, data de emissão, órgão emissor e tipo. Ausência ou ambiguidade permanece vazia ou indefinida.
- **RF-05 — Rastreabilidade:** associar arquivo, hash, página/região, categoria, campos, confiança, evidência e versão dos modelos.
- **RF-06 — Revisão humana:** disponibilizar seleção aleatória e correção rastreável sem tornar a revisão pré-condição por documento.
- **RF-07 — Segurança de conteúdo:** sinalizar conteúdo ativo, texto oculto, injeção de prompt e divergência nativo/OCR sem executar ou obedecer a instruções.
- **RF-08 — Falhas:** expor leitura, formato, tamanho, qualidade, reconhecimento inconclusivo e indisponibilidade de componentes sem apresentar falso sucesso.
- **RF-09 — Inteiro teor:** reconstruir texto quando aplicável, normalizar Unicode e preservar quebras relevantes.
- **RF-10 — Alertas:** gerar uma ocorrência por incidente em `alertas.csv` e resumo no CSV principal, sem bloquear o processamento.
- **RF-11 — Falha de alerta:** manter alerta em memória e tentar novamente ao fim do lote. A falha não impede o processamento do documento.
- **RF-12 — CSV principal:** gerar uma linha por documento com identificação, tipo, campos extraídos, alertas, versão, situação e inteiro teor quando produzido.
- **RF-13 — CSV seguro:** neutralizar fórmulas e higienizar todos os campos derivados de arquivo, OCR, modelos ou alertas.

## Requisitos não funcionais

- **RNF-01 — Execução institucional:** executar modelos somente em infraestrutura própria ou API implantada e controlada pela instituição.
- **RNF-02 — Segurança:** isolar parsers e decodificadores, aplicar privilégio mínimo e nunca executar anexos ou conteúdo recebido.
- **RNF-03 — Precisão:** alcançar pelo menos 90% em CER no conjunto aprovado, por categoria e condição representativa.
- **RNF-04 — Robustez:** tratar orientações, inclinação, ruído, fotocópia e baixa qualidade sem presumir uma orientação única.
- **RNF-05 — Privacidade:** minimizar dados em logs, alertas, CSV e revisão; controlar acesso, uso, retenção e descarte.
- **RNF-06 — Licenças:** verificar licenças antes da produção; componentes restritivos exigem ADR específico.
- **RNF-07 — Reprodutibilidade:** registrar versões do pipeline e do modelo visual em cada linha.
- **RNF-08 — Honestidade:** ausência de alerta não indica segurança; `processado` não indica documento seguro ou revisado.

## Decisões pendentes

- Aprovar limites exatos de páginas, dimensões, memória e tempo.
- Aprovar método e conjunto autorizado para medir precisão de caracteres.
- Aprovar taxa e política de revisão humana.
- Aprovar representação final de campos ausentes e estado de erro.
- Aprovar severidades e limiares calibrados.
- Aprovar uso de dados reais e retenção em conjunto com privacidade e responsáveis institucionais.

As regras detalhadas estão em [regras de negócio](business-rules.md); dados e avaliação estão em [dados e avaliação](evaluation.md).
