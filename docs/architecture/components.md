# Componentes tecnológicos

Linguagem de implementação: Python. Esta lista define candidatos e técnicas; decisões estruturais permanecem nos ADRs.

## Ingestão e saneamento

| Função | Componente |
|---|---|
| Validação e reescrita PDF | `pikepdf` |
| Rasterização e texto nativo | `pypdfium2` |
| Antivírus conhecido | ClamAV via `clamd` |
| Hash | `hashlib`/SHA-256 |

`PyMuPDF` é alternativa preterida por licença AGPL-3.0.

## Pré-processamento

- PaddleOCR para orientação e desretificação;
- OpenCV para inclinação, perspectiva, CLAHE, ruído e redimensionamento;
- scikit-image para Sauvola;
- Pillow como apoio ao processamento de imagens.

Saídas: imagem colorida normalizada e imagem binarizada.

## Classificação visual

- ConvNeXt-Tiny via `timm` ou `torchvision`;
- YOLO26/YOLO11 via Ultralytics em modo classificação ou detecção;
- Albumentations para aumento;
- Grad-CAM para explicabilidade;
- CVAT ou Label Studio para anotação;
- PyTorch como framework.

YOLO e modelos treinados por Ultralytics têm licença AGPL-3.0; uso em produção exige ADR específico e solução licenciada ou Enterprise.

## OCR

- PaddleOCR como principal;
- EasyOCR como alternativa;
- Tesseract com português como linha de base.

## Classificação textual e fusão

- BERTimbau ajustado via Hugging Face Transformers;
- temperature scaling com scikit-learn ou PyTorch;
- média ponderada no código próprio;
- MLflow para experimentos;
- ONNX Runtime para inferência, quando adequado.

## Detecção de atos maliciosos

- `pdfid`, `yara-python` e regras próprias para conteúdo ativo;
- comparação de texto nativo e OCR com `rapidfuzz`, `regex` e `unicodedata`;
- Prompt Guard 2, llm-guard ou classificador ajustado a partir de BERTimbau;
- divergência visual/textual por código próprio.

## Alertas e saída CSV

- `csv` da biblioteca padrão com `QUOTE_ALL`;
- `defusedcsv` para neutralização;
- `filelock` para concorrência;
- `pandas` para consolidação;
- `ftfy`, `unicodedata` e `regex` para normalização;
- `pandera` ou `pydantic` para validação de esquema.

## Componentes transversais

- Prefect ou Apache Airflow para lotes;
- Celery ou Ray para paralelismo;
- Docker e Kubernetes em infraestrutura própria;
- GPU quando necessária à inferência ou treino.
