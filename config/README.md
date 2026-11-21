# Configuração e segredos

Este diretório documenta convenções de configuração; ainda não há aplicação para configurá-las.

- `.env.example` lista somente nomes ilustrativos de variáveis e não deve conter valores secretos.
- Arquivos `.env` locais são ignorados pelo Git. Não os compartilhe nem os adicione ao repositório.
- Não usar segredos reais em documentação, tarefas, logs, testes, capturas de tela ou prompts.
- Modelos devem executar localmente ou em API de recurso implantado e controlado pela instituição. Não configurar APIs de nuvem pública para processar documentos, imagens ou dados processuais.
- Definir endpoint institucional, permissões, escopo, rotação, armazenamento e tratamento de falha de chaves em especificação antes de integrar serviços.
- `pipeline.yaml` (futuro) guarda limiares e parâmetros calibráveis do pipeline, versionado e validado com `pydantic`; não contém segredos nem caminhos locais.
- `.env.example` descreve apenas variáveis de execução local (endpoint do `vLLM`, modelos, adaptador, diretórios e configuração versionada). Não há chaves de API: os modelos não são acessados por serviços externos.

