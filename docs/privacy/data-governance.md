# Privacidade e governança de dados

## Princípios

Documentos associados a processos podem conter dados pessoais, informações financeiras, de saúde, identificadores e conteúdo sigiloso. Tratar esse material como altamente sensível até que uma avaliação formal determine classificação e controles aplicáveis.

- Definir finalidade e base apropriada antes de coletar ou processar dados reais.
- Minimizar conteúdo, acessos, cópias e duração de retenção.
- Restringir acesso por necessidade.
- Não incluir conteúdo documental em logs, telemetria, exemplos ou prompts de desenvolvimento sem aprovação específica. A exceção limitada é o trecho mínimo de evidência do alerta, truncado e escapado.
- Executar modelos localmente ou em API de recurso implantado e controlado pela instituição. Não enviar documentos, imagens, OCR ou dados processuais para APIs ou serviços de nuvem pública.
- Avaliar localização, retenção e uso dos dados em APIs institucionais; a implantação institucional não dispensa controle de acesso, minimização, contratos e revisão de privacidade.
- Definir descarte seguro e tratamento de cópias, caches, backups e conjuntos de avaliação.

## Ciclo de vida a especificar

1. Origem e autorização do documento.
2. Recepção, validação e minimização.
3. Processamento e eventual transferência a serviços.
4. Revisão e correção.
5. Retenção, exportação e descarte.

## Dados de teste

Priorizar dados sintéticos. Se dados reais forem indispensáveis, exigir autorização, minimização/anonimização adequada, controle de acesso, ambiente aprovado e prazo de descarte documentado.

## Evidência de incidente

O alerta pode conter somente um trecho mínimo da evidência necessária para revisar o incidente. O trecho deve ser truncado e escapado antes da persistência e do envio; texto integral e OCR completo não devem ser incluídos. Tratar esse trecho como dado pessoal potencial e conteúdo hostil.

## Questões pendentes

Identificar controlador e operadores, finalidades, base aplicável, classificação, jurisdição, direitos dos titulares, retenção, localização, compartilhamentos e procedimento de incidente com responsáveis jurídicos e de privacidade. Este documento não constitui parecer jurídico.

