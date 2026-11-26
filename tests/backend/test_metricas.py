import pytest

from visiondoc.avaliacao.metricas import (
    CLASSES_TIPO,
    INDEFINIDO,
    NAO_LOCALIZADO,
    avaliar_classificacao,
    avaliar_extracao,
    calibracao,
    curva_cobertura,
    parear_documentos,
    por_recorte,
)

REF = ["rg", "rg", "rg", "cnh", "cnh", "cpf", "outros", "outros"]
PRED = ["rg", "rg", "cnh", "cnh", INDEFINIDO, "cpf", "rg", "outros"]


def test_acuracia_e_f1_macro_sobre_aceitos_com_cobertura():
    r = avaliar_classificacao(REF, PRED, CLASSES_TIPO, n_bootstrap=0)
    assert r.total == 8 and r.aceitos == 7
    assert r.cobertura == pytest.approx(7 / 8)
    assert r.acuracia == pytest.approx(5 / 7)
    assert r.f1_macro == pytest.approx(0.75)
    rg = r.por_classe["rg"]
    assert (rg.precisao, rg.revocacao, rg.f1, rg.suporte) == pytest.approx((2 / 3, 2 / 3, 2 / 3, 3))
    assert r.por_classe["outros"].revocacao == pytest.approx(0.5)


def test_matriz_de_confusao_com_coluna_indefinido():
    r = avaliar_classificacao(REF, PRED, CLASSES_TIPO, n_bootstrap=0)
    assert r.colunas == [*CLASSES_TIPO, INDEFINIDO, NAO_LOCALIZADO]
    linha_cnh = r.matriz[CLASSES_TIPO.index("cnh")]
    assert linha_cnh[CLASSES_TIPO.index("cnh")] == 1 and linha_cnh[-2] == 1
    normalizada = r.matriz_normalizada[CLASSES_TIPO.index("cnh")]
    assert normalizada[CLASSES_TIPO.index("cnh")] == pytest.approx(0.5)
    assert r.rejeicoes_por_classe["cnh"] == 1


def test_analise_das_confusoes():
    r = avaliar_classificacao(REF, PRED, CLASSES_TIPO, n_bootstrap=0)
    assert set(r.pares_confundidos) == {("rg", "cnh", 1), ("outros", "rg", 1)}
    assert r.confusoes_de_outros == {"rg": 1}


def test_intervalo_de_confianca_por_bootstrap_contem_a_estimativa():
    r = avaliar_classificacao(REF * 10, PRED * 10, CLASSES_TIPO, n_bootstrap=200, semente=1)
    inferior, superior = r.ic_acuracia
    assert inferior <= r.acuracia <= superior
    assert r.ic_f1_macro[0] <= r.f1_macro <= r.ic_f1_macro[1]


def test_pareamento_por_iou_registra_nao_localizados_e_espurios():
    referencias = [((0, 0, 100, 100), "rg"), ((200, 0, 300, 100), "cpf")]
    previstos = [((5, 5, 100, 100), "rg"), ((500, 500, 600, 600), "cnh")]
    pares, espurios = parear_documentos(referencias, previstos, limiar_iou=0.5)
    assert pares == [("rg", "rg"), ("cpf", NAO_LOCALIZADO)]
    assert espurios == ["cnh"]
    r = avaliar_classificacao(
        [a for a, _ in pares], [b for _, b in pares], CLASSES_TIPO, n_bootstrap=0, espurios=espurios
    )
    assert r.acuracia == pytest.approx(0.5)
    assert r.espurios == {"cnh": 1}


def test_recortes_por_dataset():
    datasets = ["bid"] * 4 + ["br-doc"] * 4
    recortes = por_recorte(REF, PRED, datasets, CLASSES_TIPO, n_bootstrap=0)
    assert set(recortes) == {"agregado", "bid", "br-doc"}
    assert recortes["bid"].total == 4


def test_curva_de_cobertura_e_calibracao():
    ref = ["rg", "rg", "cnh", "cpf"]
    bruta = ["rg", "cnh", "cnh", "cpf"]
    confianca = [0.9, 0.4, 0.8, 0.6]
    curva = curva_cobertura(ref, bruta, confianca, [0.0, 0.5, 0.85])
    assert curva[0] == pytest.approx((0.0, 1.0, 0.75))
    assert curva[1] == pytest.approx((0.5, 0.75, 1.0))
    assert curva[2] == pytest.approx((0.85, 0.25, 1.0))
    perfeita = calibracao([True, True], [1.0, 1.0], n_faixas=10)
    assert perfeita.ece == pytest.approx(0.0)
    assert len(perfeita.faixas) == 10


def test_extracao_mede_um_menos_cer_e_acerto_exato():
    referencias = [{"nome": "FULANO", "cpf": "123.456.789-09"}, {"nome": "BELTRANO", "cpf": None}]
    previstos = [{"nome": "FULAN0", "cpf": "123.456.789-09"}, {"nome": "BELTRANO", "cpf": "1"}]
    r = avaliar_extracao(referencias, previstos)
    assert r.precisao_caracteres == pytest.approx(1 - 1 / (6 + 14 + 8))
    assert r.por_campo["nome"].acerto_exato == pytest.approx(0.5)
    assert r.por_campo["cpf"].precisao == pytest.approx(0.5)
    assert r.por_campo["cpf"].revocacao == pytest.approx(1.0)
