# Componentes tecnológicos

Linguagem de implementação: Python 3.12. Versão: 2.0 (2026-11-20).

## Base de engenharia

*(Definida em 2026-11-21)*

- `uv` para dependências e ambiente;
- `pytest` para testes, em `tests/backend/`;
- `ruff` para lint e formatação;
- código em `src/backend/`, como pacote `visiondoc`.

## Ingestão e saneamento

| Função | Componente |
|---|---|
| Validação e reescrita PDF | `pikepdf` |
| Rasterização e texto nativo | `pypdfium2` |
| Decodificação isolada de JPEG e conversão em PDF | Pillow |
| Antivírus conhecido | ClamAV via `clamd` |
| Hash | `hashlib`/SHA-256 |

`PyMuPDF` é alternativa preterida por licença AGPL-3.0.

## Pré-processamento

PaddleOCR, OpenCV e Pillow corrigem orientação, inclinação, perspectiva, contraste e ruído. A saída é uma imagem colorida normalizada usada pela transcrição e pelo VLM. Rasterização a 300 DPI; espelhamento detectado pela comparação da confiança do OCR entre a imagem e sua versão espelhada; coordenadas convertidas de volta para a página original.

## Transcrição

- PaddleOCR-VL 1.6 para inteiro teor e caixas;
- PaddleOCR PP-OCR e Tesseract como linhas de base de CER;
- `vLLM` como servidor opcional.

Licenças Apache-2.0 a verificar na versão adotada.

## Detecção e mascaramento

- inventário estrutural com `pikepdf` e `yara-python` para conteúdo ativo ([ADR-016](../decisions/ADR-016-inventario-e-neutralizacao.md)), com conjunto inicial de regras para JavaScript, `OpenAction`, `Launch`, `EmbeddedFile` e `AcroForm` em PDF;
- `rapidfuzz`, `regex` e `unicodedata` para texto oculto;
- scanner `PromptInjection` do llm-guard (MIT; modelo DeBERTa Apache-2.0, licenças a confirmar na versão adotada) como detector de injeção; Llama Prompt Guard 2 apenas em experimento, após verificação de licença;
- ClamAV: detecção gera `conteudo_ativo` com severidade `alta`;
- OpenCV para mascarar regiões suspeitas na imagem;
- `[TRECHO REMOVIDO]` na transcrição enviada ao VLM.

## VLM

Modelo principal: Qwen3.5-4B ([ADR-015](../decisions/ADR-015-vlm-qwen35-4b.md)), Apache-2.0, ajustado com LoRA sobre o modelo de linguagem e codificador de visão congelado.

- Carga: Hugging Face `transformers`;
- Ajuste: `transformers` (`Trainer`), `peft` e `bitsandbytes`, com coletor próprio que exclui da perda os campos sem anotação ([ADR-017](../decisions/ADR-017-treino-br-doc-extraction.md));
- Rastreamento: MLflow;
- Inferência: `vLLM`;
- Saída: decodificação guiada por esquema JSON;
- Hardware disponível: GPU de 8 GB, com QLoRA 4 bits no ajuste e pesos em 8 bits (FP8 ou INT8) na inferência ([ADR-015](../decisions/ADR-015-vlm-qwen35-4b.md)).
- Requisito do `vLLM`: versão fixada que suporte Qwen3.5, entrada multimodal, LoRA sobre modelo quantizado em 8 bits, decodificação estruturada e logprobs, confirmada por prova de conceito antes da implementação.

Hiperparâmetros iniciais: rank 16, alpha 32, dropout 0,05, atenção e MLP como módulos-alvo. A versão do `vLLM` deve suportar a arquitetura Qwen3.5 e LoRA multimodal sobre modelo quantizado em 8 bits.

## Validação

- `pydantic` para esquema e domínios;
- `validate-docbr` para CPF;
- `rapidfuzz` e `unidecode` para respaldo textual;
- biblioteca padrão `datetime` para datas.

## Componentes removidos na versão 2.0

ConvNeXt-Tiny, BERTimbau e fusão por média ponderada são linhas de base históricas. YOLO foi descartado. PaddleOCR tradicional permanece como linha de base de CER.

## Alertas e saída CSV

- `csv` da biblioteca padrão com `QUOTE_ALL`;
- neutralização própria conforme RN-014, em `visiondoc.csv_seguro` ([ADR-016](../decisions/ADR-016-inventario-e-neutralizacao.md));
- `filelock` para concorrência;
- `pandas` para consolidação;
- `ftfy`, `unicodedata` e `regex` para normalização;
- `pandera` ou `pydantic` para validação de esquema.

## Configuração

*(Definida em 2026-11-21)* Limiares e parâmetros calibráveis ficam em `config/pipeline.yaml`, versionado no repositório e validado com `pydantic` na inicialização; a versão da configuração compõe `versao_pipeline`.

## Componentes transversais

- Prefect ou Apache Airflow para lotes;
- Celery ou Ray para paralelismo;
- Docker e Kubernetes em infraestrutura própria;
- GPU quando necessária à inferência ou treino.
