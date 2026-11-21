# Classificação e extração de informações de documentos em processos judiciais

## Autores

- Bruno dos Santos F. Silva (brunosfs@gmail.com)
- Glauber Galvão de Araújo (glauber.galvao@gmail.com)

## Contexto acadêmico

Este trabalho foi realizado como requisito da disciplina de Visão Computacional do PPgTI - Doutorado Profissional em Tecnologia da Informação, ministrada pelo prof. Helton Maia Peixoto (helton.maia@ufrn.br).

O desenvolvimento contou com apoio tecnológico dos recursos computacionais do NPAD - Núcleo de Processamento de Alto Desempenho da UFRN.

## Visão do projeto

Título do trabalho:

> *Classificação e extração de informações de documentos em processos judiciais: uma abordagem multimodal baseada em Modelos de Linguagem Visuais*

Versão da especificação: 2.0 (2026-11-20). Mudanças em [CHANGELOG.md](CHANGELOG.md).

O VisionDoc especifica um pipeline para triagem de documentos digitalizados em petições iniciais judiciais. O pipeline identifica tipos de documentos, extrai campos e o inteiro teor, sinaliza conteúdo potencialmente malicioso e gera saída em CSV.

O escopo preliminar inclui RG, CPF, CNH e a classe de rejeição `outros`; `indefinido` representa classificação inconclusiva. PDFs e JPEG podem estar em orientação horizontal, vertical, inclinada ou espelhada. O tamanho máximo e demais limites seguem as regras aprovadas em `docs/domain/business-rules.md`.

Os resultados são apoio à triagem. Não decidem mérito, autenticidade ou admissibilidade. Revisão humana amostral é desejável, mas não é pré-condição por documento.

## Princípios definitivos

Os princípios permanentes estão em [constituição](.specify/memory/constitution.md):

1. documentos e derivados são conteúdo não confiável;
2. texto extraído é dado, nunca instrução;
3. detecção gera sinalização sem interromper o processamento;
4. todo texto CSV é protegido contra fórmulas de planilha;
5. processamento ocorre apenas em infraestrutura própria;
6. saída registra versões para reprodutibilidade;
7. licenças de componentes precisam ser compatíveis;
8. a solução prefere o componente mais simples com ganho demonstrável.


## Visão geral da arquitetura

```mermaid
flowchart TD
    A[Ingestão e saneamento] --> B[Pré-processamento]
    B --> C[Transcrição do inteiro teor<br/>PaddleOCR-VL 1.6]
    C --> D[Detecção e mascaramento]
    D -. ocorrências .-> G[(alertas.csv)]
    D --> E[VLM: classificação e extração<br/>Qwen3.5-4B + LoRA]
    E --> F[Validação da saída]
    F -. falhas de validação .-> G
    F --> H[Saída CSV]
    H --> I[(documentos.csv)]
```

## Etapas

1. **Ingestão e saneamento:** valida o PDF, remove e inventaria elementos ativos, rasteriza as páginas e preserva a camada de texto nativa.
2. **Pré-processamento:** corrige orientação e inclinação, trata contraste e ruído e normaliza o tamanho da imagem.
3. **Transcrição:** o PaddleOCR-VL produz o inteiro teor em ordem de leitura e caixas de texto.
4. **Detecção e mascaramento:** identifica conteúdo ativo, texto oculto e injeção de prompt. Ocasionalmente mascara regiões suspeitas antes do VLM e não interrompe o fluxo.
5. **VLM:** o Qwen3.5-4B ajustado com LoRA recebe imagem e transcrição e devolve documentos com tipo, face, coordenadas e campos em JSON estruturado.
6. **Validação:** confere esquema, confiança, pertinência dos campos ao tipo, respaldo na transcrição, CPF e datas.
7. **Saída CSV:** uma linha por documento identificado, com campos extraídos e inteiro teor.

## Estrutura

```text
.
├── .specify/
│   ├── memory/                 # Princípios permanentes do projeto
│   └── templates/              # Templates SDD: spec, plano e tarefas
├── config/                     # Orientações de configuração e provedores
├── docs/
│   ├── architecture/           # Contexto e visão arquitetural
│   │   └── components.md       # Componentes tecnológicos definitivos
│   ├── decisions/              # Registro de decisões (ADRs)
│   ├── domain/                 # Visão do domínio e requisitos
│   │   ├── business-rules.md   # Regras de negócio RN-xxx
│   │   └── evaluation.md       # Dados, métricas e avaliação
│   ├── contracts/              # Contratos dos arquivos CSV
│   │   └── saida-vlm.md        # Contrato JSON do VLM
│   ├── privacy/                # Questões de privacidade e dados
│   └── security/               # Modelo de ameaças e segurança
├── infrastructure/             # Reservado para documentação de infraestrutura
├── specs/                      # Especificações SDD por funcionalidade
├── src/
│   ├── backend/                # Reservado ao backend; sem código neste estágio
│   └── frontend/               # Reservado ao frontend; sem código neste estágio
└── tests/
    ├── backend/                # Reservado à validação do backend
    └── frontend/               # Reservado à validação do frontend
```

`agents.md` e `claude.md` registram orientações para agentes de desenvolvimento.

## Documentação de partida

- [Requisitos do domínio](docs/domain/requirements.md)
- [Regras de negócio](docs/domain/business-rules.md)
- [Dados e avaliação](docs/domain/evaluation.md)
- [Visão arquitetural](docs/architecture/overview.md)
- [Componentes tecnológicos](docs/architecture/components.md)
- [Contrato do CSV principal](docs/contracts/documentos-csv.md)
- [Contrato do CSV de alertas](docs/contracts/alertas-csv.md)
- [Contrato da saída do VLM](docs/contracts/saida-vlm.md)
- [Documentação de segurança](docs/security/README.md)
- [Privacidade e dados](docs/privacy/data-governance.md)
- [Princípios SDD](.specify/memory/constitution.md)
- [Como organizar especificações](specs/README.md)
- [Especificação do pipeline seguro](specs/001-pipeline-documental-seguro/spec.md)
- [Configuração e segredos](config/README.md)

## Configuração

Não há aplicação executável ainda. Consulte [config/README.md](config/README.md) e `.env.example` para as convenções futuras. Nunca preencha o arquivo de exemplo com chaves reais.

