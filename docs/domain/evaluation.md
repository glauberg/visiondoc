# Dados e avaliação

## Conjuntos de dados

### BID Dataset

O Brazilian Identity Document Dataset contém imagens sintéticas e informações falsas. Inclui oito classes de frente e verso de CNH, CPF e RG, totalizando 28.800 imagens. É usado no treino e na validação dos classificadores visual e textual.

### br-doc-extraction

O dataset `tech4humans/br-doc-extraction` contém imagem e esquema textual de campos. Não deve ser usado como conjunto independente do BID, pois pode compartilhar origem e causar vazamento.

### Conjunto próprio da JFRN

Quando autorizado, reúne páginas reais anonimizadas de petições iniciais, documentos fora do escopo das classes principais e páginas com vários documentos anotadas com caixas. Esse conjunto é o teste final para medir a distância entre dados sintéticos e realidade.

### Dados sintéticos complementares

- páginas compostas sobre fundos A4;
- injeções sintéticas de texto oculto e instruções;
- degradações de fotocópia, desfoque, compressão, ruído e JPEG;
- caixas conhecidas automaticamente para treino de detecção.

## Cuidados

1. Não usar resultados do BID como substituto do conjunto real.
2. A classe `outros` evita que documentos não suportados sejam forçados para RG, CPF ou CNH.
3. Treino, validação e teste são separados antes de composição ou aumento de dados.
4. Dados reais só são usados com autorização, anonimização adequada e salvaguardas documentadas.

## Métricas

| Componente | Métrica |
|---|---|
| Classificação visual, textual e fusão | F1 macro, acurácia e matriz de confusão |
| Rejeição | Cobertura por acurácia em função do limiar |
| Calibração | Erro de calibração esperado (ECE) |
| Detecção de documentos | mAP@0.5 e mAP@0.5:0.95 |
| OCR | CER e WER |
| Atos maliciosos | Precisão, revocação e falsos positivos por categoria |
| Desempenho | Tempo por página, GPU e memória |

O alvo mínimo é 90% de precisão em nível de caractere em conjunto aprovado, reportado por categoria e condição representativa. Esse limite não é garantia por documento.

## Experimentos

1. Comparar ConvNeXt-Tiny, YOLO-cls e YOLO em detecção.
2. Comparar PaddleOCR, EasyOCR e Tesseract.
3. Fazer ablação de texto, imagem e fusão.
4. Avaliar detecção sobre injeções sintéticas.
5. Executar avaliação final no conjunto real aprovado.
