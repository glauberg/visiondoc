"""Página sintética com um RG fictício para a prova de conceito T020.

Todos os dados são fictícios. Nenhum documento real é usado.
"""

from PIL import Image, ImageDraw, ImageFont

LINHAS = [
    "REPÚBLICA FEDERATIVA DO BRASIL",
    "CARTEIRA DE IDENTIDADE",
    "REGISTRO GERAL 0000000",
    "NOME FULANO DE TAL",
    "FILIAÇÃO BELTRANO DE TAL",
    "CICRANA DE TAL",
    "NATURALIDADE NATAL-RN",
    "DATA DE NASCIMENTO 12/05/1980",
    "DATA DE EXPEDIÇÃO 02/03/2015",
    "CPF 123.456.789-09",
    "SSP/RN",
]

TRANSCRICAO = "\n".join(LINHAS)

# Página A4 a 150 DPI; o lado maior é limitado antes do envio ao VLM.
LARGURA, ALTURA = 1240, 1754
CARTAO = (120, 200, 1120, 900)


def _fonte(tamanho: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def gerar_pagina(lado_maximo: int = 1280) -> Image.Image:
    pagina = Image.new("RGB", (LARGURA, ALTURA), "white")
    desenho = ImageDraw.Draw(pagina)
    desenho.rectangle(CARTAO, outline="black", width=4, fill=(235, 242, 230))
    fonte = _fonte(36)
    x, y = CARTAO[0] + 40, CARTAO[1] + 40
    for linha in LINHAS:
        desenho.text((x, y), linha, fill="black", font=fonte)
        y += 56
    pagina.thumbnail((lado_maximo, lado_maximo))
    return pagina


if __name__ == "__main__":
    gerar_pagina().save("pagina-sintetica.jpg", "JPEG", quality=90)
    print("pagina-sintetica.jpg gerada")
