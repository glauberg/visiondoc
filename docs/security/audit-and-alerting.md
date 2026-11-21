# Especificação de segurança: alertas

## Objetivo

Definir a gravação não bloqueante de alertas de conteúdo potencialmente malicioso.

A trilha transversal append-only foi removida da arquitetura definida pelos princípios vigentes e pelo [ADR-007](../decisions/ADR-007-remocao-auditoria.md). Não se presume rastreabilidade operacional além das informações presentes na saída e dos controles existentes.

## Comportamento

- Uma ocorrência gera uma linha em `alertas_AAAA-MM-DD.csv`.
- Um documento pode gerar várias ocorrências.
- O alerta contém página/região quando disponível, etapa, categoria, severidade, campo quando aplicável, mascaramento e evidência limitada.
- A ocorrência não interrompe extração, reconstrução ou exportação.
- Falha imediata de escrita mantém o alerta em memória e tenta regravá-lo ao fim do lote.
- Se a regravação falhar, os alertas pendentes vão para `alertas_pendentes_<id_lote>.csv` em diretório de contingência; se também falhar, o lote termina com código de saída de falha e log sem conteúdo documental ([RN-013](../domain/business-rules.md#rn-013)).
- Falhas de escrita não são apresentadas como ausência de ameaça.

## Proteções

- Truncar evidência em 500 caracteres.
- Remover caracteres invisíveis e neutralizar fórmulas.
- Nunca repassar evidência a modelo generativo como instrução.
- Restringir acesso aos CSVs e controlar retenção.
- Não incluir inteiro teor ou OCR completo em alertas.

## Revisão humana

Revisão amostral é uma capacidade desejada, separada do CSV mínimo. Política de seleção, papéis e persistência de correções precisam ser aprovados.

## Critérios de aceitação

- [ ] Alertas não bloqueiam documentos processados.
- [ ] Falha de escrita regrava alertas ao fim do lote.
- [ ] Evidência é truncada e neutralizada.
- [ ] Ausência de alerta não é apresentada como segurança.
- [ ] CSV principal e CSV de alertas seguem os contratos publicados.
