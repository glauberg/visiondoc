import io

import pikepdf
from PIL import Image

from sintetico import jpeg_sintetico, pdf_sintetico


def test_pdf_sintetico_com_conteudo_ativo():
    dados = pdf_sintetico(javascript=True, open_action=True, anexo=True, formulario=True)
    with pikepdf.open(io.BytesIO(dados)) as pdf:
        assert "/OpenAction" in pdf.Root
        assert "/AcroForm" in pdf.Root
        assert len(pdf.attachments) == 1


def test_pdf_sintetico_criptografado():
    dados = pdf_sintetico(senha="segredo-ficticio")
    with pikepdf.open(io.BytesIO(dados), password="segredo-ficticio") as pdf:
        assert pdf.is_encrypted


def test_jpeg_sintetico_com_exif():
    img = Image.open(io.BytesIO(jpeg_sintetico(orientacao_exif=6)))
    assert img.format == "JPEG"
    assert img.getexif()[0x0112] == 6
