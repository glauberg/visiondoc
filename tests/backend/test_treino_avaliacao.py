import pytest

from visiondoc.treino.avaliacao import (
    CLASSES,
    acerto_por_campo,
    acuracia_tipo,
    f1_macro,
    matriz_confusao,
)


def test_classes():
    assert CLASSES == ("cnh", "rg", "outros")


def test_acuracia_e_matriz():
    reais = ["cnh", "cnh", "rg", "outros"]
    previstos = ["cnh", "rg", "rg", "outros"]
    assert acuracia_tipo(previstos, reais) == 0.75
    assert matriz_confusao(previstos, reais) == [[1, 1, 0], [0, 1, 0], [0, 0, 1]]


def test_rotulo_fora_das_classes_conta_como_outros():
    assert matriz_confusao(["invoice"], ["outros"]) == [[0, 0, 0], [0, 0, 0], [0, 0, 1]]


def test_f1_macro_perfeito_e_ignora_classe_ausente():
    assert f1_macro(["cnh", "rg"], ["cnh", "rg"]) == 1.0


def test_f1_macro_imperfeito():
    reais = ["cnh", "cnh", "rg", "rg"]
    previstos = ["cnh", "rg", "rg", "rg"]
    # cnh: p=1, r=0,5 -> 2/3; rg: p=2/3, r=1 -> 0,8
    assert f1_macro(previstos, reais) == pytest.approx((2 / 3 + 0.8) / 2)


def test_listas_vazias():
    assert acuracia_tipo([], []) == 0.0
    assert f1_macro([], []) == 0.0


def test_acerto_por_campo():
    real = {"nome": "ANA", "cpf": "111", "filiacao": ["P", "M"], "orgao_emissor": None}
    previsto = {
        "nome": "  ANA ",
        "cpf": "112",
        "filiacao": ["P", "M"],
        "data_validade": "2020-01-01",
        "naturalidade": None,
    }
    resultado = acerto_por_campo(previsto, real)
    assert resultado["rotulados"] == {
        "nome": True,
        "cpf": False,
        "filiacao": True,
        "orgao_emissor": True,
    }
    assert resultado["extras"] == ["data_validade"]
