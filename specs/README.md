# Especificações SDD

Cada funcionalidade deve ter uma pasta própria, nomeada com identificador curto e kebab-case, por exemplo `001-ingestao-documental/`. Inclua nela:

- `spec.md`: necessidade, requisitos e critérios de aceitação;
- `plan.md`: abordagem, componentes afetados, dados e validação;
- `tasks.md`: tarefas rastreáveis e dependências.

Use os arquivos em `.specify/templates/`. Comece pela especificação e obtenha revisão/aprovação antes de planejar ou implementar. Não crie uma especificação para justificar retrospectivamente uma implementação.

Toda especificação deve considerar os princípios em `.specify/memory/constitution.md`, requisitos em `docs/domain/requirements.md`, ameaças em `docs/security/threat-model.md` e governança em `docs/privacy/data-governance.md`.

## Especificação atual

`001-pipeline-documental-seguro/` registra os requisitos derivados do roteiro arquitetural recebido, o plano lógico e as tarefas pendentes de definição. A especificação permanece proposta; sua documentação não autoriza implementação antes das decisões e aprovações listadas nela.

