# Prova de conceito T020: Qwen3.5-4B em 8 bits com LoRA no vLLM

Verifica a viabilidade da inferência definida no [ADR-015](../../docs/decisions/ADR-015-vlm-qwen35-4b.md) antes da implementação do pipeline ([T020](../../specs/001-pipeline-documental-seguro/tasks.md)). Não é código do pipeline.

Usa apenas uma página sintética com dados fictícios (`pagina_sintetica.py`). Nenhum dado real é usado.

## Critérios de aprovação

O relatório `relatorio-t020.json` marca `aprovado: true` quando, na GPU de 8 GB:

1. o `vLLM` carrega o Qwen3.5-4B quantizado em 8 bits com um adaptador LoRA;
2. aceita imagem + transcrição delimitada no turno do usuário;
3. devolve JSON válido para o [contrato da saída do VLM](../../docs/contracts/saida-vlm.md), por decodificação estruturada;
4. devolve logprobs do rótulo do tipo.

O relatório também registra versões (`vllm`, `torch`, CUDA), GPU, memória, tempo de carga e tempo por página, dados usados para fixar a versão do `vLLM` e as metas de desempenho.

## Requisitos da máquina

- Linux x86_64 ou WSL2, com GPU NVIDIA de 8 GB e driver compatível com CUDA 12.
- `uv` instalado; o `uv` baixa o Python 3.12 e as dependências de cada script.
- Acesso ao Hugging Face para baixar os pesos do modelo (alguns GB) na primeira execução.
- FP8 exige GPU com *compute capability* 8.0 ou superior (8.9 ou superior para FP8 completo; abaixo disso o `vLLM` usa FP8 só nos pesos). Em GPUs mais antigas, use um checkpoint já quantizado em INT8 (ver abaixo).

## Execução

Confirme antes o identificador exato do modelo no Hugging Face; os comandos usam `Qwen/Qwen3.5-4B`.

```bash
cd infrastructure/poc-t020
nvidia-smi
uv run criar_adaptador.py --modelo Qwen/Qwen3.5-4B --saida adaptador-teste
uv run poc_vllm.py --modelo Qwen/Qwen3.5-4B --adaptador adaptador-teste --quantizacao fp8
```

- `criar_adaptador.py` carrega o modelo na CPU (cerca de 9 GB de RAM em bf16) e salva um adaptador LoRA de teste com a configuração inicial do ADR-015 (rank 16, alpha 32, atenção e MLP do modelo de linguagem). Os pesos B começam em zero: o adaptador não muda as respostas e serve só para provar o carregamento. Se nenhum módulo corresponder ao padrão de alvos, o script lista nomes de módulos para ajuste.
- `poc_vllm.py` executa três inferências e grava `relatorio-t020.json`. Código de saída 0 = aprovado; 1 = carregou mas falhou em algum critério; 2 = erro de importação, carga ou inferência (detalhe no campo `erro`).

### Alternativas em caso de falha

- **Falta de memória:** reduza `--max-model-len` (por exemplo, 4096) ou ajuste `--gpu-mem`.
- **GPU sem suporte a FP8:** use um checkpoint INT8 (W8A8) do mesmo modelo, se existir, com `--modelo <id-int8> --quantizacao none`.
- **Erro de LoRA ou de arquitetura:** registre a mensagem; indica que a versão do `vLLM` não suporta a combinação exigida, e a decisão volta a ADR.

## O que trazer de volta

- O arquivo `relatorio-t020.json` (contém apenas dados sintéticos).
- A saída do terminal, se houver erro.
- A saída de `uv pip list` ou a versão do `vllm` instalada, se não aparecer no relatório.

Com esses dados, a T020 é concluída: fixa-se a versão do `vLLM`, registra-se o resultado no ADR-015 e definem-se as metas de desempenho.
