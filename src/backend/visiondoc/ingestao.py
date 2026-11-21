"""Ingestão: validação, identificação, saneamento e rasterização (T025).

Referências: RN-001, RN-002, RN-018, ADR-001 e ING-SEC-01 a ING-SEC-11.
Nenhum conteúdo recebido é executado. PDF e JPEG são processados em processo
isolado, com tempo máximo; o JPEG é convertido em PDF de uma página sem
reamostragem e segue o fluxo do PDF.
"""

import hashlib
import io
import math
import zlib
from datetime import datetime
from pathlib import Path

import pikepdf
from pikepdf import Dictionary, Name

from visiondoc.configuracao import Configuracao
from visiondoc.fontes import EntradaArquivo
from visiondoc.isolamento import FalhaIsolada, TempoExcedido, executar_isolado
from visiondoc.modelos import (
    ArquivoIngerido,
    ErroIngestao,
    Identificacao,
    ItemAtivo,
    MotivoErro,
    Pagina,
    SegmentoTexto,
)

_LIMITE_NOS = 200_000


class ErroArquivo(Exception):
    def __init__(self, motivo: MotivoErro, detalhe: str) -> None:
        super().__init__(motivo, detalhe)
        self.motivo = motivo
        self.detalhe = detalhe


# --- identificação e formato -------------------------------------------------


def identificar(entrada: EntradaArquivo, dados: bytes) -> Identificacao:
    return Identificacao(
        id_processo=entrada.id_processo,
        nome_arquivo=entrada.nome_arquivo,
        hash_arquivo=hashlib.sha256(dados).hexdigest(),
        data_hora=datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def detectar_formato(dados: bytes) -> str | None:
    """Formato real pelo conteúdo, não pela extensão."""
    if dados.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if dados[:1024].find(b"%PDF-") != -1:
        return "pdf"
    return None


# --- inventário e saneamento de PDF --------------------------------------------


def _rotulo(caminho: str, obj) -> str:
    num, ger = getattr(obj, "objgen", (0, 0))
    return f"{caminho} (obj {num} {ger})" if num else caminho


def _inventariar_pdf(pdf: pikepdf.Pdf) -> list[ItemAtivo]:
    itens: dict[tuple[str, str], ItemAtivo] = {}

    def registrar(tipo: str, objeto: str, executavel: bool) -> None:
        itens.setdefault((tipo, objeto), ItemAtivo(tipo, objeto, executavel))

    vistos: set[tuple[int, int]] = set()
    pilha = [("/Root", pdf.Root)]
    nos = 0
    while pilha and nos < _LIMITE_NOS:
        caminho, obj = pilha.pop()
        nos += 1
        try:
            objgen = obj.objgen
        except Exception:  # noqa: BLE001
            objgen = (0, 0)
        if objgen != (0, 0):
            if objgen in vistos:
                continue
            vistos.add(objgen)
        if isinstance(obj, pikepdf.Stream):
            obj = obj.stream_dict
        if isinstance(obj, pikepdf.Dictionary):
            acao = obj.get("/S")
            if acao == Name.JavaScript or "/JS" in obj:
                registrar("javascript", _rotulo(caminho, obj), True)
            if acao == Name.Launch:
                registrar("launch", _rotulo(caminho, obj), True)
            if "/OpenAction" in obj:
                registrar("acao_automatica", f"{caminho}/OpenAction", True)
            if "/AA" in obj:
                registrar("acao_automatica", f"{caminho}/AA", True)
            if obj.get("/Type") == Name.EmbeddedFile or (
                obj.get("/Type") == Name.Filespec and "/EF" in obj
            ):
                registrar("arquivo_embutido", _rotulo(caminho, obj), False)
            if obj.get("/Subtype") == Name.RichMedia:
                registrar("rich_media", _rotulo(caminho, obj), True)
            if caminho == "/Root" and "/AcroForm" in obj:
                registrar("formulario", "/Root/AcroForm", False)
            for chave in obj:
                if chave == "/Parent":
                    continue
                pilha.append((f"{caminho}/{chave.lstrip('/')}", obj[chave]))
        elif isinstance(obj, pikepdf.Array):
            for i, valor in enumerate(obj):
                pilha.append((f"{caminho}[{i}]", valor))
    return sorted(itens.values(), key=lambda item: (item.tipo, item.objeto))


def _abrir_pdf(dados: bytes) -> pikepdf.Pdf:
    try:
        pdf = pikepdf.open(io.BytesIO(dados))
    except pikepdf.PasswordError as erro:
        raise ErroArquivo(MotivoErro.ARQUIVO_ILEGIVEL, "PDF criptografado") from erro
    except Exception as erro:
        raise ErroArquivo(MotivoErro.ARQUIVO_ILEGIVEL, "PDF corrompido") from erro
    if pdf.is_encrypted:
        pdf.close()
        raise ErroArquivo(MotivoErro.ARQUIVO_ILEGIVEL, "PDF criptografado")
    return pdf


def inventariar(dados: bytes) -> list[ItemAtivo]:
    with _abrir_pdf(dados) as pdf:
        return _inventariar_pdf(pdf)


def sanear(dados: bytes) -> bytes:
    """Remove conteúdo ativo por reescrita; o conteúdo visual vem das páginas rasterizadas."""
    with _abrir_pdf(dados) as pdf:
        raiz = pdf.Root
        for chave in ("/OpenAction", "/AA", "/AcroForm", "/Outlines", "/AF"):
            if chave in raiz:
                del raiz[chave]
        if "/Names" in raiz:
            for chave in ("/JavaScript", "/EmbeddedFiles"):
                if chave in raiz.Names:
                    del raiz.Names[chave]
        for pagina in pdf.pages:
            for chave in ("/AA", "/Annots", "/AF"):
                if chave in pagina.obj:
                    del pagina.obj[chave]
        saida = io.BytesIO()
        pdf.save(saida)
        return saida.getvalue()


# --- conversão de JPEG ---------------------------------------------------------


def _jpeg_para_pdf(dados: bytes, cfg: Configuracao) -> tuple[bytes, int | None]:
    from PIL import Image

    lado_max = cfg.limites.lado_max_px
    Image.MAX_IMAGE_PIXELS = lado_max * lado_max
    try:
        imagem = Image.open(io.BytesIO(dados))
        largura, altura = imagem.size
        if max(largura, altura) > lado_max:
            raise ErroArquivo(MotivoErro.TAMANHO_EXCEDIDO, "dimensão acima do limite")
        orientacao = imagem.getexif().get(0x0112)
        rgb = imagem.convert("RGB").tobytes()  # pixels apenas; metadados descartados
    except ErroArquivo:
        raise
    except Image.DecompressionBombError as erro:
        raise ErroArquivo(MotivoErro.TAMANHO_EXCEDIDO, "dimensão acima do limite") from erro
    except Exception as erro:
        raise ErroArquivo(MotivoErro.ARQUIVO_ILEGIVEL, "JPEG ilegível") from erro

    dpi = cfg.rasterizacao.dpi
    largura_pt, altura_pt = largura * 72 / dpi, altura * 72 / dpi
    pdf = pikepdf.new()
    pagina = pdf.add_blank_page(page_size=(largura_pt, altura_pt))
    figura = pikepdf.Stream(pdf, zlib.compress(rgb))
    figura.Type = Name.XObject
    figura.Subtype = Name.Image
    figura.Width, figura.Height = largura, altura
    figura.ColorSpace = Name.DeviceRGB
    figura.BitsPerComponent = 8
    figura.Filter = Name.FlateDecode
    pagina.Resources = Dictionary(XObject=Dictionary(Im0=figura))
    pagina.Contents = pdf.make_stream(f"q {largura_pt} 0 0 {altura_pt} 0 0 cm /Im0 Do Q".encode())
    saida = io.BytesIO()
    pdf.save(saida)
    return saida.getvalue(), orientacao


# --- texto nativo e rasterização ----------------------------------------------


def _texto_nativo(pagina_pdfium, altura_pt: float, escala: float) -> list[SegmentoTexto]:
    import pypdfium2.raw as pdfium_c

    textpage = pagina_pdfium.get_textpage()
    try:
        caracteres = []
        for i in range(textpage.count_chars()):
            esq, inf, dir_, sup = textpage.get_charbox(i)
            caracteres.append(
                ((esq + dir_) / 2, (inf + sup) / 2, pdfium_c.FPDFText_GetFontSize(textpage.raw, i))
            )
        segmentos = []
        for i in range(textpage.count_rects()):
            esq, inf, dir_, sup = textpage.get_rect(i)
            texto = textpage.get_text_bounded(esq, inf, dir_, sup).strip()
            if not texto:
                continue
            tamanhos = [t for x, y, t in caracteres if esq <= x <= dir_ and inf <= y <= sup]
            caixa = (
                int(esq * escala),
                int((altura_pt - sup) * escala),
                math.ceil(dir_ * escala),
                math.ceil((altura_pt - inf) * escala),
            )
            segmentos.append(SegmentoTexto(texto, caixa, min(tamanhos) if tamanhos else None))
        return segmentos
    finally:
        textpage.close()


def _processar(formato: str, dados: bytes, diretorio: str, prefixo: str, cfg: Configuracao):
    """Executado no processo isolado. Devolve (páginas, inventário, orientação EXIF)."""
    import pypdfium2 as pdfium

    orientacao = None
    if formato == "jpeg":
        dados, orientacao = _jpeg_para_pdf(dados, cfg)

    with _abrir_pdf(dados) as pdf:
        if len(pdf.pages) > cfg.limites.paginas_max:
            raise ErroArquivo(MotivoErro.TAMANHO_EXCEDIDO, "páginas acima do limite")
        inventario = _inventariar_pdf(pdf)
    saneado = sanear(dados)
    if inventariar(saneado):
        raise ErroArquivo(MotivoErro.FALHA_PROCESSAMENTO, "saneamento incompleto")

    escala = cfg.rasterizacao.dpi / 72
    paginas = []
    documento = pdfium.PdfDocument(saneado)
    try:
        for indice in range(len(documento)):
            pagina = documento[indice]
            largura_pt, altura_pt = pagina.get_size()
            if max(largura_pt, altura_pt) * escala > cfg.limites.lado_max_px:
                raise ErroArquivo(MotivoErro.TAMANHO_EXCEDIDO, "dimensão acima do limite")
            texto = _texto_nativo(pagina, altura_pt, escala) if formato == "pdf" else []
            imagem = pagina.render(scale=escala).to_pil().convert("RGB")
            destino = Path(diretorio) / f"{prefixo}-p{indice + 1:03d}.png"
            imagem.save(destino, "PNG")
            paginas.append(Pagina(indice + 1, destino, imagem.width, imagem.height, texto))
            pagina.close()
    finally:
        documento.close()
    return paginas, inventario, orientacao


def ingerir(
    entrada: EntradaArquivo, diretorio_trabalho: Path, cfg: Configuracao
) -> ArquivoIngerido | ErroIngestao:
    dados = entrada.caminho.read_bytes()
    identificacao = identificar(entrada, dados)

    def erro(motivo: MotivoErro, detalhe: str) -> ErroIngestao:
        return ErroIngestao(identificacao, motivo, detalhe)

    if len(dados) >= cfg.limites.tamanho_max_bytes:
        return erro(MotivoErro.TAMANHO_EXCEDIDO, "arquivo com tamanho igual ou acima do limite")
    formato = detectar_formato(dados)
    if formato is None:
        return erro(MotivoErro.FORMATO_NAO_SUPORTADO, "formato real não é PDF nem JPEG")

    try:
        paginas, inventario, orientacao = executar_isolado(
            _processar,
            (formato, dados, str(diretorio_trabalho), identificacao.hash_arquivo[:16], cfg),
            cfg.limites.tempo_max_s,
            cfg.limites.memoria_max_gb,
        )
    except ErroArquivo as falha:
        return erro(falha.motivo, falha.detalhe)
    except TempoExcedido:
        return erro(MotivoErro.FALHA_PROCESSAMENTO, "tempo máximo de ingestão excedido")
    except (FalhaIsolada, MemoryError) as falha:
        return erro(
            MotivoErro.FALHA_PROCESSAMENTO, f"falha no processo isolado: {type(falha).__name__}"
        )
    return ArquivoIngerido(identificacao, entrada.caminho, formato, paginas, inventario, orientacao)
