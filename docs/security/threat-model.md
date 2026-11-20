# Modelo de ameaças

## Escopo

O modelo cobre PDF/JPEG, pré-processamento, OCR, classificação visual/textual, detecção de atos maliciosos, CSV e revisão amostral.

## Ativos

- Dados pessoais e informações extraídas.
- Arquivos originais e intermediários.
- Modelos, versões e configurações.
- CSV principal, alertas e evidências.
- Ambiente local/institucional.

## Fronteiras de confiança

1. PDF/JPEG e metadados são não confiáveis.
2. Parsers, decodificadores e modelos são isolados e operam com privilégio mínimo.
3. O processamento permanece em infraestrutura própria.
4. CSV e alertas podem conter texto hostil e dados pessoais.
5. Consumidores recebem dados, não instruções confiáveis.

## Ameaças e mitigação

| Ameaça | Consequência | Mitigação |
|---|---|---|
| PDF/JPEG malformado | Corrupção ou consumo excessivo | Validação, limites, isolamento e falha explícita |
| Conteúdo ativo | Execução não autorizada | Inventário, remoção/rasterização e nenhum parser com execução ativa |
| Texto oculto ou divergente | Extração incorreta ou instrução hostil | Comparação nativo/OCR e registro limitado de evidência |
| Injeção de prompt | Manipulação de modelo generativo | Texto nunca entra como instrução; classificador apenas em domínio fechado |
| Nuvem pública | Vazamento de dados pessoais | Proibir transmissão e executar localmente ou em recurso institucional |
| Saída alucinada | Classificação falsa | Evidência, confiança, campos vazios e revisão amostral |
| Injeção de fórmula | Execução ao abrir planilha | Neutralizar todos os campos não confiáveis |
| Falha de alerta | Ocorrência não gravada | Retenção em memória e regravação ao fim do lote |
| Vazamento via CSV ou log | Exposição de dados pessoais | Minimização, acesso restrito, retenção e truncamento |
| Licença incompatível | Uso indevido de componente | Verificação e ADR antes da produção |

## Invariantes

- Conteúdo ativo nunca é executado.
- Texto extraído nunca altera instruções ou fluxo.
- Detecção sinaliza e não interrompe.
- Falha de alerta não interrompe o documento.
- Ausência de alerta não certifica segurança.
- CSV neutraliza fórmulas.
- Processamento não usa nuvem pública.
- `processado` não significa seguro ou revisado.
