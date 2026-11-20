# Tarefas: pipeline documental multimodal seguro

- **Especificação:** `spec.md`
- **Plano:** `plan.md`
- **Estado:** documentação inicial concluída; implementação não autorizada

## Tarefas de definição e aprovação

- [ ] **T001** Confirmar unidade do limite de 2 MB, limites de páginas/dimensões/recursos e política para EXIF/JPEG — depende de: nenhuma.
- [ ] **T002** Aprovar a taxonomia final, regras de campo por RG/CPF/CNH e representação de ausências/ambiguidades — depende de: T001.
- [ ] **T003** Definir representação da situação `erro` e campos vazios — depende de: nenhuma.
- [ ] **T004** Confirmar algoritmo de hash, timestamp, esquema/codificação do CSV e neutralização — depende de: T002, T003.
- [ ] **T005** Definir método/corpus autorizado para medir 90% de precisão de caracteres por categoria — depende de: T002.
- [ ] **T006** Definir taxa, frequência, papéis e fluxo de revisão humana amostral — depende de: T002.
- [ ] **T007** Definir severidades, canal de alerta e política de repetição — depende de: T003.
- [ ] **T008** Aprovar avaliação jurídica/privacidade para dados reais, processamento institucional, retenção e evidências — depende de: T001, T004, T006, T007.

## Tarefas futuras de implementação

- [ ] **T009** Implementar ingestão PDF/JPEG, identificação inicial e validação de limites — depende de: T001, T003, T008.
- [ ] **T010** Implementar retenção em memória e regravação ao fim do lote para alertas — depende de: T003, T007.
- [ ] **T011** Implementar OCR, semântica, visão e fusão para categorias/campos aprovados — depende de: T002, T005, T008.
- [ ] **T012** Implementar detecção, alertas, revisão amostral e registro de correções — depende de: T006, T007, T008, T010, T011.
- [ ] **T013** Implementar CSV com campos acordados, estado de erro e neutralização de fórmulas — depende de: T004, T011.
- [ ] **T014** Executar avaliação de precisão, revisão de segurança e validação de critérios antes do uso operacional — depende de: T009, T010, T011, T012, T013.

## Verificação de conclusão

- [x] Escopo de formatos, categorias, campos, orientação, modelo operacional, precisão e revisão documentados.
- [x] Regras de alerta não bloqueante e campos mínimos do CSV documentados.
- [ ] Decisões pendentes aprovadas antes da implementação.
- [ ] Critérios de aceitação verificados em implementação futura.

