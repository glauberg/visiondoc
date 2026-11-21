import pytest

from visiondoc.csv_seguro import formatar_caixa, higienizar, neutralizar, preparar_texto


@pytest.mark.parametrize("valor", ["=SOMA(A1)", "+1", "-2", "@x", "\tA", "\rB"])
def test_neutraliza_prefixos_de_formula(valor):
    assert neutralizar(valor) == "'" + valor


def test_nao_altera_texto_comum():
    assert neutralizar("FULANO") == "FULANO"


def test_higieniza_controle_e_invisiveis_e_normaliza_nfc():
    assert higienizar("Jose\u0301\u200b\x07 SILVA") == "José SILVA"


def test_preserva_quebras_somente_quando_pedido():
    assert higienizar("A\nB") == "A B"
    assert higienizar("A\r\nB", preservar_quebras=True) == "A\nB"


def test_preparar_texto_higieniza_neutraliza_e_trunca():
    texto = preparar_texto("\u200b=1+1" + "x" * 600, limite=500)
    assert texto.startswith("'=1+1")
    assert len(texto) == 500


def test_formata_caixa():
    assert formatar_caixa((1, 2, 3, 4)) == "1;2;3;4"
    assert formatar_caixa(None) is None
