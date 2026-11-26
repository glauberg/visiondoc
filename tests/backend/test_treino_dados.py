import json

import httpx
import pytest

from visiondoc.treino.alinhamento import PARTICOES
from visiondoc.treino.dados import baixar_rotulos, gravar_jsonl, montar_exemplos
from visiondoc.treino.esquema import SaidaVLM
from visiondoc.treino.instrucao import INSTRUCAO, TEXTO_USUARIO, hash_instrucao

RG = json.dumps({"nome_completo": "FULANO", "data_nascimento": "1980-05-12"})


def _pasta(tmp_path, nomes):
    for nome in nomes:
        (tmp_path / nome).touch()
    return tmp_path


def _rotulos(**por_split):
    return {s: por_split.get(s, []) for s in PARTICOES}


def test_montar_exemplos_formato(tmp_path):
    pasta = _pasta(tmp_path, ["test-01137.png"])
    exemplos, relatorio = montar_exemplos(pasta, _rotulos(test=[{"type": "rg", "response": RG}]))
    ex = exemplos["test"][0]
    assert ex["id"] == "test-01137" and ex["split"] == "test"
    assert ex["imagem"] == "test-01137.png" and ex["tipo"] == "rg"
    sistema, usuario, assistente = ex["messages"]
    assert sistema == {"role": "system", "content": INSTRUCAO}
    assert usuario == {
        "role": "user",
        "content": [{"type": "image"}, {"type": "text", "text": TEXTO_USUARIO}],
    }
    assert assistente["role"] == "assistant"
    SaidaVLM.model_validate_json(assistente["content"])
    assert relatorio["hash_instrucao"] == hash_instrucao()
    assert relatorio["contagem_por_split"]["test"] == 1


def test_sem_vazamento(tmp_path):
    nomes = ["train-00000.png", "train-00001.png", "valid-01062.png", "test-01137.png"]
    pasta = _pasta(tmp_path, nomes)
    rotulo = {"type": "rg", "response": RG}
    exemplos, _ = montar_exemplos(
        pasta,
        _rotulos(train=[rotulo, rotulo], valid=[rotulo], test=[rotulo]),
    )
    ids = {s: {e["id"] for e in exemplos[s]} for s in exemplos}
    assert ids["train"].isdisjoint(ids["valid"])
    assert ids["train"].isdisjoint(ids["test"])
    assert ids["valid"].isdisjoint(ids["test"])


def test_linha_descartada_e_contada(tmp_path):
    pasta = _pasta(tmp_path, ["train-00000.png", "train-00001.png"])
    rotulos = _rotulos(
        train=[{"type": "rg", "response": "quebrado"}, {"type": "rg", "response": RG}]
    )
    exemplos, relatorio = montar_exemplos(pasta, rotulos)
    assert [e["id"] for e in exemplos["train"]] == ["train-00001"]
    assert relatorio["descartadas"] == 1


def test_data_fora_do_iso_so_conta(tmp_path):
    pasta = _pasta(tmp_path, ["test-01137.png"])
    resposta = json.dumps({"nome_completo": "X", "data_nascimento": "12/05/1980"})
    exemplos, relatorio = montar_exemplos(
        pasta, _rotulos(test=[{"type": "rg", "response": resposta}])
    )
    assert "12/05/1980" in exemplos["test"][0]["messages"][2]["content"]
    assert relatorio["datas_fora_do_padrao_iso"] == 1


def test_gravar_jsonl(tmp_path):
    exemplos = {"train": [{"id": "a", "texto": "ç"}], "valid": [], "test": []}
    gravar_jsonl(exemplos, {"descartadas": 0}, tmp_path / "saida")
    linhas = (tmp_path / "saida" / "train.jsonl").read_text("utf-8").splitlines()
    assert json.loads(linhas[0]) == {"id": "a", "texto": "ç"}
    assert (tmp_path / "saida" / "valid.jsonl").read_text("utf-8") == ""
    assert json.loads((tmp_path / "saida" / "relatorio.json").read_text("utf-8")) == {
        "descartadas": 0
    }


def _cliente(total: int, chamadas: list):
    def tratar(requisicao: httpx.Request) -> httpx.Response:
        params = requisicao.url.params
        offset, tamanho = int(params["offset"]), int(params["length"])
        chamadas.append((offset, tamanho))
        linhas = [
            {"row_idx": i, "row": {"type": "rg", "response": RG, "image": {"src": "x"}}}
            for i in range(offset, min(offset + tamanho, total))
        ]
        return httpx.Response(200, json={"rows": linhas})

    return httpx.Client(transport=httpx.MockTransport(tratar))


def test_baixar_rotulos_pagina_e_guarda_cache(tmp_path, monkeypatch):
    monkeypatch.setitem(PARTICOES, "test", (1137, 250))
    chamadas: list = []
    rotulos = baixar_rotulos("test", tmp_path, cliente=_cliente(250, chamadas))
    assert len(rotulos) == 250
    assert set(rotulos[0]) == {"type", "response"}
    assert [c[0] for c in chamadas] == [0, 100, 200]
    assert (tmp_path / "rotulos-test.json").exists()
    chamadas.clear()
    assert baixar_rotulos("test", tmp_path, cliente=_cliente(250, chamadas)) == rotulos
    assert chamadas == []


def test_baixar_rotulos_contagem_divergente(tmp_path):
    with pytest.raises(ValueError):
        baixar_rotulos("test", tmp_path, cliente=_cliente(80, []))
