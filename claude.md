# Instruções complementares para Claude

Estas instruções se aplicam especificamente a Claude/Claude Code e complementam a especificação principal do projeto. Antes de qualquer trabalho, leia [agents.md](agents.md), que é a fonte de orientação comum e autoritativa para todos os agentes de IA neste repositório.

## Fluxo para Claude Code

- Consulte `agents.md` e os documentos nele referenciados antes de agir; leia também os arquivos relevantes à tarefa.
- Trate este arquivo apenas como complemento operacional. Em caso de omissão ou divergência, siga `agents.md` e as especificações SDD aprovadas.
- Ao usar subagentes, forneça a eles o contexto e os requisitos relevantes de `agents.md`; revise o trabalho para garantir conformidade antes de integrá-lo.
- Antes de editar, inspecione o estado e o conteúdo existentes. Preserve mudanças de trabalho não relacionadas e integre alterações concorrentes em vez de sobrescrevê-las.
- Faça a menor alteração que atenda ao pedido. Não implemente código ou infraestrutura executável quando a tarefa for apenas documental.
- Ao concluir, informe resumidamente os arquivos alterados, verificações realizadas e limitações pendentes; não afirme que algo foi validado se não foi.

