"""Gerador de arquivos sintéticos para testes (T024).

Todos os conteúdos são fictícios. Nenhum documento real é usado; os arquivos
são gerados em memória ou em diretórios temporários dos testes.
"""

import io

import pikepdf
from pikepdf import Array, Dictionary, Name, String
from PIL import Image, ImageDraw, ImageFont

LINHAS_RG = [
    "REPUBLICA FEDERATIVA DO BRASIL",
    "CARTEIRA DE IDENTIDADE",
    "REGISTRO GERAL 0000000",
    "NOME FULANO DE TAL",
    "DATA DE NASCIMENTO 12/05/1980",
]


def _escapar(texto: str) -> bytes:
    bruto = texto.encode("latin-1", errors="replace")
    return bruto.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _conteudo(linhas: list[str], texto_oculto: str | None, fonte_oculta: float) -> bytes:
    partes = [b"BT /F1 18 Tf 72 760 Td 22 TL"]
    for linha in linhas:
        partes.append(b"(" + _escapar(linha) + b") Tj T*")
    partes.append(b"ET")
    if texto_oculto:
        partes.append(
            b"BT 3 Tr /F1 "
            + str(fonte_oculta).encode()
            + b" Tf 72 120 Td ("
            + _escapar(texto_oculto)
            + b") Tj ET"
        )
    return b"\n".join(partes)


def pdf_sintetico(
    linhas: list[str] | None = None,
    *,
    paginas: int = 1,
    javascript: bool = False,
    open_action: bool = False,
    launch: bool = False,
    anexo: bool = False,
    formulario: bool = False,
    texto_oculto: str | None = None,
    fonte_oculta: float = 0.5,
    senha: str | None = None,
) -> bytes:
    linhas = LINHAS_RG if linhas is None else linhas
    pdf = pikepdf.new()
    fonte = pdf.make_indirect(
        Dictionary(
            Type=Name.Font,
            Subtype=Name.Type1,
            BaseFont=Name.Helvetica,
            Encoding=Name.WinAnsiEncoding,
        )
    )
    for _ in range(paginas):
        pagina = pdf.add_blank_page(page_size=(595, 842))
        pagina.Resources = Dictionary(Font=Dictionary(F1=fonte))
        pagina.Contents = pdf.make_stream(_conteudo(linhas, texto_oculto, fonte_oculta))
        if launch:
            pagina.AA = Dictionary(O=Dictionary(S=Name.Launch, F=String("calc.exe")))
    if javascript:
        acao = pdf.make_indirect(Dictionary(S=Name.JavaScript, JS=String("app.alert(1)")))
        pdf.Root.Names = Dictionary(JavaScript=Dictionary(Names=Array([String("js"), acao])))
    if open_action:
        pdf.Root.OpenAction = Dictionary(S=Name.JavaScript, JS=String("app.alert(2)"))
    if formulario:
        pdf.Root.AcroForm = Dictionary(Fields=Array())
    if anexo:
        pdf.attachments["anexo.txt"] = pikepdf.AttachedFileSpec(pdf, b"conteudo ficticio")
    saida = io.BytesIO()
    if senha:
        pdf.save(saida, encryption=pikepdf.Encryption(owner=senha, user=senha))
    else:
        pdf.save(saida)
    return saida.getvalue()


def imagem_cartao(
    linhas: list[str] | None = None, largura: int = 1200, altura: int = 800
) -> Image.Image:
    linhas = LINHAS_RG if linhas is None else linhas
    img = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(img)
    desenho.rectangle((40, 40, largura - 40, altura - 40), outline="black", width=4)
    try:
        fonte = ImageFont.load_default(size=40)
    except TypeError:
        fonte = ImageFont.load_default()
    y = 80
    for linha in linhas:
        desenho.text((80, y), linha, fill="black", font=fonte)
        y += 60
    return img


def jpeg_sintetico(
    largura: int = 1200,
    altura: int = 800,
    *,
    orientacao_exif: int | None = None,
    qualidade: int = 90,
) -> bytes:
    img = imagem_cartao(largura=largura, altura=altura)
    saida = io.BytesIO()
    if orientacao_exif is not None:
        exif = Image.Exif()
        exif[0x0112] = orientacao_exif
        exif[0x010F] = "Fabricante ficticio"
        img.save(saida, "JPEG", quality=qualidade, exif=exif)
    else:
        img.save(saida, "JPEG", quality=qualidade)
    return saida.getvalue()
