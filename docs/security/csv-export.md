# Especificação de segurança: exportação CSV

## Objetivo e escopo

Definir o esquema mínimo e os controles de segurança para a saída CSV por documento. A saída contém dados pessoais e texto derivado de arquivos não confiáveis. Documento com alerta continua sendo exportado.

## Campos obrigatórios

Cada documento processado deve ter uma linha com, no mínimo:

- `categoria_documento` — `RG`, `CPF`, `CNH`, `outros` ou `indefinido`;
- `nome_arquivo` — nome original, sem caminho local;
- `hash_arquivo` — hash criptográfico de identificação; algoritmo proposto: SHA-256;
- `data_hora_verificacao` — timestamp com fuso explícito; formato proposto: ISO 8601 UTC;
- `nome_completo_parte`;
- `numero_documento`.

Para disponibilizar todos os campos de extração definidos pelo domínio, incluir também:

- `data_nascimento`;
- `nome_mae`;
- `nome_pai`;
- `data_emissao`;
- `orgao_emissor`;
- `tipo_documento`;
- `inteiro_teor`, quando produzido pelo fluxo OCR.

Manter ainda `alerta_seguranca`, `severidade_alerta`, `detalhe_alerta` e `situacao`, com valores `processado` ou `erro`. A revisão humana aleatória não é pré-condição por linha e não exige coluna obrigatória no CSV. Definir tipos, codificação, delimitador e representação de campos ausentes antes da implementação.

## Requisitos de segurança

- **CSV-SEC-01 — Neutralização:** neutralizar valores não confiáveis que poderiam ser interpretados como fórmulas por planilhas. Aplicar a todos os campos derivados de arquivo, OCR, modelos, revisão ou alertas.
- **CSV-SEC-02 — Prefixos perigosos:** considerar prefixos de fórmula (`=`, `+`, `-`, `@`) e variantes com espaços, caracteres de controle ou outros prefixos ignorados por leitores de planilha. Testar nos leitores aprovados.
- **CSV-SEC-03 — Codificação CSV:** escapar/quotar delimitadores, aspas, CR/LF e estrutura CSV de modo consistente. Quoting correto não substitui neutralização de fórmulas.
- **CSV-SEC-04 — Fidelidade:** neutralização pode alterar representação textual. Identificar/documentar valores neutralizados; não remover silenciosamente o texto de origem nem reexportá-lo sem neutralização.
- **CSV-SEC-05 — Dados ausentes:** campo ilegível, ausente ou ambíguo não pode ser preenchido por inferência do modelo; usar representação definida para ausência ou indefinição.
- **CSV-SEC-06 — Semântica de situação:** `processado` exige conclusão integral do pipeline; não significa documento seguro, sem alerta ou revisado. `erro` identifica falha/interrupção, nunca resultado limpo.
- **CSV-SEC-07 — Erro explícito:** falha de processamento gera linha `situacao=erro` com campos de resultado vazios e identificação disponível.
- **CSV-SEC-08 — Uso a jusante:** consumidores verificam os campos de alerta e tratam todas as células, em especial texto completo, como dado não confiável. Sistemas que usam CSV como entrada para modelos mantêm instruções confiáveis separadas dos dados.
- **CSV-SEC-09 — Proteção de dados:** controlar geração, acesso, transferência e retenção do CSV; evitar cópias e logging do conteúdo. Modelos/consumidores de processamento não podem estar em nuvem pública.

## Comportamento de alertas e revisão

Ocorrência detectada acompanha a linha CSV e não interrompe o fluxo. Ausência de alerta não certifica segurança. Revisão humana pode selecionar amostra aleatória de documentos processados e registrar conferência/correções fora do esquema mínimo do CSV; taxa e política de seleção são decisões pendentes.

A linha de erro não contém campos inferidos nem resultado parcial. Apenas identifica o arquivo e o estado de falha.

## Critérios de aceitação

- [ ] Cada linha processada contém os campos obrigatórios e todos os campos de extração acordados.
- [ ] `hash_arquivo` identifica os bytes exatos recebidos; algoritmo e codificação estão declarados.
- [ ] `data_hora_verificacao` tem fuso explícito e registra o momento definido pela política de verificação.
- [ ] Todos os campos não confiáveis são protegidos contra injeção de fórmulas, inclusive variantes de prefixo aprovadas.
- [ ] Arquivos de teste abertos nos leitores de planilha suportados não executam conteúdo como fórmula.
- [ ] Aspas, delimitadores e quebras de linha não alteram células/linhas de forma inesperada.
- [ ] Valores neutralizados permanecem identificáveis e a representação exportada é documentada.
- [ ] Linha de erro contém identificação e situação, sem campos parciais.
- [ ] `processado`, `erro` e ausência/presença de alerta não são apresentados como indicadores de segurança ou revisão.
- [ ] Logs de teste/produção não incluem inteiro teor nem cópias desnecessárias do CSV.

## Decisões pendentes

Confirmar SHA-256 e timestamp UTC; fechar esquema/tipos/codificação/delimitador/escape; estratégia de neutralização interoperável; representação de valores ausentes; política para múltiplos alertas; campo de erro; leitores suportados; registro separado das revisões; controle de acesso e retenção.

