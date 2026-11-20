# Plano: pipeline documental multimodal seguro

- **Especificação:** `spec.md`
- **Estado:** proposta; decisões operacionais e aprovação pendentes
- **Última atualização:** 2026-11-14

## Abordagem

Manter a arquitetura lógica independente de tecnologia. A detecção de conteúdo suspeito não interrompe nem desvia o documento. Ocorrências seguem ao CSV principal e ao CSV de alertas; falha de gravação de alerta é regravada ao fim do lote.

Suportar PDF e JPEG abaixo de 2.000.000 bytes, categorias preliminares RG/CPF/CNH, idioma `pt-BR` e correção de orientação/rotação/inclinação/espelhamento. OCR, semântica e análise visual são ramos paralelos com proveniência. Revisão humana é amostral e não é gate por arquivo.

Modelos operam localmente ou em recurso/API implantado e controlado pela instituição. Não integrar com nuvem pública.

## Componentes afetados

- `src/backend/`: futuro recebimento, processamento, orquestração e geração CSV.
- `src/frontend/`: futura operação e revisão amostral/correção.
- `infrastructure/`: isolamento e execução local/institucional.
- `config/`: limites, configuração e segredos sem inclusão de credenciais no repositório.
- `tests/`: testes sintéticos de formatos, orientação, extração, ataque, falha auditável e CSV.
- `docs/` e `specs/`: requisitos, arquitetura e critérios de aceitação.

## Interfaces e contratos conceituais

- Entrada PDF/JPEG, nome e hash de identificação, timestamp da verificação.
- Evento de início persistido antes de chamar qualquer modelo.
- Imagens/páginas preparadas e texto nativo separado para PDF.
- Resultados de OCR com texto, coordenadas e confiança; resultados semânticos/visuais com evidência, localização e versão.
- Categoria preliminar, campos extraídos, indicação de incerteza e estado de revisão separado.
- Alertas com evidência limitada.
- CSV com identidade, tempo, categoria, campos extraídos, alertas, inteiro teor quando aplicável e situação.

Esquemas completos, métodos de confiança, tratamento de campos ausentes e contrato de erro devem ser aprovados antes do código.

## Segurança, privacidade e falhas

- Isolar parsers e decodificadores; nunca executar conteúdo ativo.
- Tratar entradas, saídas de modelos, dados extraídos e CSV como não confiáveis.
- Não transmitir documentos a nuvem pública; restringir modelos a ambiente local ou institucional controlado.
- Minimizar e restringir dados em CSV, logs, revisão e alertas.
- Não apresentar falha de detector como ausência de ameaça; alerta por ameaça não bloqueia.
- Neutralizar valores do CSV contra fórmulas e documentar efeito na representação.

## Estratégia de validação

- Cobrir PDF/JPEG válidos e inválidos, limites de tamanho, páginas rotacionadas/inclinadas/espelhadas e metadados.
- Usar dados sintéticos ou autorizados para testar campos de RG, CPF e CNH e comparar resultado com referência.
- Medir precisão de caracteres no conjunto de avaliação aprovado, no agregado e por categoria, com alvo mínimo de 90%.
- Simular indisponibilidade no evento inicial e em cada etapa para provar que não há chamada subsequente a modelo nem saída processada.
- Validar que alerta de conteúdo suspeito não bloqueia e que falha de escrita é regravada.
- Verificar revisão aleatória, registro de correção e neutralização CSV nos leitores acordados.

## Riscos, dependências e decisões

Pendências: confirmar unidade exata de 2 MB; algoritmo de hash/timestamp; dimensões máximas e tratamento EXIF; taxa e política de revisão; método/corpus para precisão; esquema CSV e neutralização; severidades e política de repetição de alertas.

Não iniciar implementação enquanto a especificação não for aprovada e as decisões de segurança, qualidade e privacidade necessárias não forem resolvidas.

