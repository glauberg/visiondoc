import pytest

from visiondoc.fontes import listar_entradas
from visiondoc.lote import Lote


def test_lista_arquivos_do_dataset_com_identificador_sintetico(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "sub" / "a.pdf").write_bytes(b"y")
    entradas = listar_entradas(tmp_path, "bid")
    assert [e.id_processo for e in entradas] == ["bid:b.jpg", "bid:sub/a.pdf"]
    assert entradas[0].nome_arquivo == "b.jpg"


def test_rejeita_nome_de_dataset_invalido(tmp_path):
    with pytest.raises(ValueError):
        listar_entradas(tmp_path, "BID com espaco")


def test_lote_apaga_intermediarios_ao_final(tmp_path):
    with Lote(base=tmp_path) as lote:
        intermediario = lote.diretorio_trabalho / "pagina.png"
        intermediario.write_bytes(b"x")
        diretorio = lote.diretorio_trabalho
    assert not diretorio.exists()
    assert len(lote.id) == 36


def test_lote_apaga_intermediarios_mesmo_com_falha(tmp_path):
    with pytest.raises(RuntimeError), Lote(base=tmp_path) as lote:
        (lote.diretorio_trabalho / "x.txt").write_text("x")
        raise RuntimeError("falha")
    assert not lote.diretorio_trabalho.exists()
