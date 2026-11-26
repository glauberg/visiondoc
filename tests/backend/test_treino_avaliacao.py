import json

import pytest

from visiondoc.treino.avaliacao import (
    avaliar_itens,
    confianca_do_tipo,
    interpretar_resposta,
    tem_respaldo,
)
from visiondoc.treino.configuracao import carregar_config_treino
from visiondoc.treino.exemplos import montar_resposta, montar_sequencia
from visiondoc.treino.mapeamento import CAMPOS_CONTRATO
from visiondoc.treino.preparacao import ItemPreparado


def _campos(**valores):
    campos = {c: None for c in CAMPOS_CONTRATO}
    campos["filiacao"] = []
    campos.update(valores)
    return campos


def _resposta(tipo, **valores):
    return montar_resposta(tipo, _campos(**valores), set(), None, [0, 0, 1000, 1000])[0]


def _item(i, tipo, **valores):
    return ItemPreparado(
        f"test-{i:05d}",
        "test",
        tipo,
        _campos(**valores),
        [],
        f"imagens/{i}.png",
        "x",
        "NOME FULANO DE TAL\n12/05/1980",
        640,
        400,
    )


def test_interpreta_resposta_valida_e_rejeita_chave_faltando():
    tipo, campos, valido = interpretar_resposta(_resposta("rg", nome="FULANO DE TAL"))
    assert (tipo, campos["nome"], valido) == ("rg", "FULANO DE TAL", True)
    incompleta = json.loads(_resposta("rg"))
    del incompleta["documentos"][0]["campos"]["cpf"]
    assert interpretar_resposta(json.dumps(incompleta)) == (None, None, False)
    assert interpretar_resposta("não é json") == (None, None, False)


def test_confianca_e_o_produto_dos_tokens_do_rotulo():
    tokens = ['{"documentos": [{"', "tipo", '": "', "cn", "h", '", "face']
    probs = [1.0, 1.0, 1.0, 0.9, 0.5, 1.0]
    assert confianca_do_tipo(tokens, probs) == pytest.approx(0.45)
    assert confianca_do_tipo(["{}"], [1.0]) is None


def test_respaldo_normaliza_texto_cpf_e_datas():
    transcricao = "NOME FULANO DE TAL\nCPF 123.456.789-09\nNASC 12/05/1980"
    assert tem_respaldo("FULANO DE TAL", transcricao, 90)
    assert tem_respaldo("12345678909", transcricao, 90)
    assert tem_respaldo("1980-05-12", transcricao, 90)
    assert not tem_respaldo("BELTRANO SILVA", transcricao, 90)


def test_sequencia_de_treino_ignora_prompt_e_campos_sem_anotacao():
    ids, rotulos = montar_sequencia([1, 2, 3], [10, 11, 12], [(0, 2), (2, 6), (6, 8)], [(3, 5)])
    assert ids == [1, 2, 3, 10, 11, 12]
    assert rotulos == [-100, -100, -100, 10, -100, 12]


def test_avalia_itens_com_rejeicao_extracao_e_respaldo():
    cfg = carregar_config_treino("config/treino.yaml")
    itens = [
        _item(0, "rg", nome="FULANO DE TAL", data_nascimento="1980-05-12"),
        _item(1, "cnh", nome="FULANO DE TAL"),
        _item(2, "outros"),
    ]
    respostas = {
        "test-00000": (_resposta("rg", nome="FULANO DE TAL", data_nascimento="1980-05-12"), 0.95),
        "test-00001": (_resposta("rg", nome="BELTRANO"), 0.40),  # rejeitado
        "test-00002": ("lixo", None),  # JSON inválido
    }

    def gerar(item):
        texto, conf = respostas[item.id]
        tokens = ['{"documentos": [{"tipo": "', "rg", '"'] if conf else ["lixo"]
        probs = [1.0, conf, 1.0] if conf else [1.0]
        return texto, tokens, probs, 2.0

    avaliacao, inferencia = avaliar_itens(gerar, itens, cfg, tempo_carga_s=10.0)
    r = avaliacao.classificacao["tipo"]["agregado"]
    assert r.total == 3 and r.aceitos == 1 and r.acuracia == 1.0
    assert inferencia.taxa_json_valido == pytest.approx(2 / 3)
    assert inferencia.tempos_pagina_s == [2.0, 2.0, 2.0]
    extracao = avaliacao.extracao["br-doc-extraction"]
    assert extracao.por_campo["nome"].acerto_exato == pytest.approx(0.5)
    # respostas válidas preenchem 3 campos; BELTRANO não aparece na transcrição
    assert avaliacao.taxa_campos_sem_respaldo == pytest.approx(1 / 3)
