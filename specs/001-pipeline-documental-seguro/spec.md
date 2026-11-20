# Especificação: pipeline documental multimodal seguro

- **Estado:** proposta para revisão
- **Base:** roteiro de arquitetura recebido e `docs/domain/requirements.md`
- **Última atualização:** 2026-11-14

## Contexto e problema

O pipeline recebe documentos de identificação associados à petição inicial, processa imagem/texto por OCR, modelos semânticos e visão, sugere categoria e extrai campos. Deve detectar conteúdo potencialmente malicioso, auditar cada etapa e exportar resultados.

O escopo documental preliminar é RG, CPF e CNH. Entradas são PDF ou JPEG abaixo de 2.000.000 bytes, em português do Brasil, podendo estar horizontais, verticais, inclinadas, rotacionadas ou espelhadas. Modelos executam localmente ou em recurso/API implantado e controlado pela instituição; nuvem pública é proibida.

Alertas de conteúdo suspeito não interrompem o processamento. A gravação de alerta é melhor esforço ao fim do lote e não desvia nem cancela o documento.

## Partes interessadas

- Pessoas que submetem ou administram documentos.
- Profissionais responsáveis por conferência humana amostral.
- Equipe de segurança que recebe alertas.
- Responsáveis por operação, privacidade, revisão e consumidores do CSV.

## Objetivos

- Receber e preparar com segurança PDF/JPEG nos limites definidos.
- Classificar RG, CPF e CNH, permitindo rejeições `outros` e `indefinido`.
- Extrair campos de identificação com proveniência e incerteza.
- Atingir pelo menos 90% de precisão em nível de caractere no conjunto de avaliação aprovado.
- Disponibilizar revisão humana aleatória e rastreável, sem gate por documento.
- Operar modelos apenas localmente ou em recurso/API institucional, sem nuvem pública.
- Exportar os campos acordados e proteger CSV contra conteúdo hostil.

## Fora de escopo

- Decidir mérito, autenticidade, admissibilidade ou estratégia jurídica.
- Garantir precisão de 90% para cada documento ou detectar todos os ataques.
- Enviar documentos ou dados processuais para APIs/serviços de nuvem pública.
- Exigir revisão humana de todos os documentos antes da operação.
- Implementar código nesta etapa documental.

## Requisitos funcionais

- **RF-SDD-01 — Entrada:** aceitar PDF/JPEG com tamanho `<2.000.000` bytes; validar formato real; suportar `pt-BR`, orientação horizontal/vertical, inclinação, rotação e espelhamento.
- **RF-SDD-02 — Saneamento:** em PDFs, inventariar/remover conteúdo ativo sem executar; rasterizar páginas e preservar texto nativo separadamente para comparação. Preparar JPEG em decoder isolado e tratar metadados como não confiáveis.
- **RF-SDD-03 — Categorias:** classificar RG, CPF ou CNH; usar `outros` e `indefinido` quando fora do escopo ou inconclusivo.
- **RF-SDD-04 — Extração:** extrair nome completo, data de nascimento, nome da mãe, nome do pai, número do documento, data de emissão, órgão emissor e tipo de documento. Ausências/ambiguidades não podem ser inventadas.
- **RF-SDD-05 — Percepção:** executar ramos paralelos OCR com coordenadas/confiança, análise semântica e análise de imagem, mantendo proveniência e localização.
- **RF-SDD-06 — Segurança de conteúdo:** correlacionar conteúdo ativo, divergência nativo/OCR, texto oculto, injeção de prompt e indícios de adulteração; classe incompatível é apenas sinal auxiliar.
- **RF-SDD-07 — Revisão:** permitir seleção aleatória para revisão humana e registrar conferência/correções; revisão não é pré-condição por documento nem coluna obrigatória do CSV.
- **RF-SDD-08 — Versão:** registrar versão do pipeline e do modelo visual em cada saída.
- **RF-SDD-09 — Alertas:** sinalizar ocorrência em `alertas.csv` e no CSV principal sem bloquear o documento.
- **RF-SDD-10 — CSV:** gerar uma linha por documento com identificação, tipo, campos extraídos, alertas, situação, versão e inteiro teor quando aplicável. Falha de gravação de alerta não impede a linha.
- **RF-SDD-11 — Neutralização:** neutralizar todos os valores não confiáveis contra fórmulas antes de exportar CSV.

## Requisitos não funcionais

- **RNF-SDD-01 — Precisão:** mínimo de 90% de precisão de caracteres no conjunto aprovado, com método e resultado por categoria definidos.
- **RNF-SDD-02 — Execução institucional:** modelos apenas localmente ou em recurso/API implantado e controlado pela instituição; nuvem pública proibida.
- **RNF-SDD-03 — Segurança:** entrada, conteúdo derivado e saídas de modelos são não confiáveis; aplicar isolamento, limites, validação, privilégio mínimo e nenhuma execução de conteúdo.
- **RNF-SDD-04 — Privacidade:** minimizar dados em CSV, alertas, filas, logs e revisão; controlar acesso, transferência e retenção.
- **RNF-SDD-05 — Licenças:** componentes restritivos exigem ADR e autorização institucional.
- **RNF-SDD-06 — Revisabilidade:** resultados expõem incerteza/proveniência e podem ser conferidos por amostra humana.
- **RNF-SDD-07 — Sem falso sucesso:** `processado` exige pipeline concluído; não equivale a seguro, sem alerta ou revisado.

## Dados e privacidade

Documentos, imagens, campos extraídos, hashes, nomes de arquivos, CSV, identificadores processuais e evidências podem ser sensíveis. Uso de dados reais depende de autorização, avaliação jurídica/privacidade e salvaguardas. Dados de avaliação devem ser sintéticos ou autorizados. Execução em nuvem pública é proibida; APIs devem ser implantadas/controladas pela instituição.

A evidência de alerta pode conter apenas um trecho curto, truncado e escapado. CSV contém dados de identificação, portanto acesso e retenção devem ser limitados. Revisões/correções precisam ser rastreáveis e protegidas.

## Cenários e critérios de aceitação

### Cenário: falha na gravação de alerta

- **Dado** um documento processado com ocorrência detectada
- **Quando** o arquivo de alertas não pode ser escrito imediatamente
- **Então** o alerta é mantido em memória, o documento continua até a saída e o alerta é regravado ao fim do lote

### Cenário: revisão aleatória

- **Dado** documentos concluídos em operação normal
- **Quando** a política amostral seleciona um documento
- **Então** uma pessoa pode conferir/corrigir e o registro da revisão fica rastreável sem que os demais documentos aguardem revisão

### Cenário: documento fora de orientação padrão

- **Dado** RG, CPF ou CNH JPEG/PDF em orientação horizontal, vertical, inclinada ou invertida
- **Quando** passa pela preparação de imagem
- **Então** a etapa normaliza orientação, mantém localização rastreável e tenta reconhecer sem confiar em metadados como fonte única

### Critérios transversais

- [ ] Tipos e tamanho são validados antes do processamento; nuvem pública não é chamada.
- [ ] As categorias e campos de extração correspondem ao escopo preliminar.
- [ ] 90% de precisão de caracteres é medido em corpus autorizado e reportado por categoria.
- [ ] Alertas não bloqueiam processamento; falha de gravação é registrada/retryada sem interromper o documento.
- [ ] CSV contém campos mínimos, proteção contra fórmula e estado inequívoco.
- [ ] Ausência de alerta e situação `processado` não significam documento seguro ou revisado.

## Riscos e decisões pendentes

- Confirmar unidade decimal de 2 MB versus 2 MiB.
- Definir método de cálculo e conjunto de avaliação para os 90%.
- Definir taxa/frequência de revisão, seleção aleatória e papéis.
- Confirmar algoritmo de hash, formato de timestamp e esquema completo do CSV.
- Definir limites de dimensões e metadados JPEG, severidades e política de repetição de alertas.

## Referências

- `docs/architecture/overview.md`
- `docs/domain/requirements.md`
- `docs/security/README.md`
- `docs/privacy/data-governance.md`

