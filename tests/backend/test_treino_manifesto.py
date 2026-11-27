import json

import pytest

from visiondoc.treino.bid import dividir
from visiondoc.treino.manifesto import listar_manifesto, montar_cache
from visiondoc.treino.preparacao import carregar_preparados


def _fonte(tmp_path, quantidades=None, nome="MANIFESTO.JSONL"):
    quantidades = quantidades or {"cnh": 20, "rg": 20, "outros": 10}
    raiz = tmp_path / "cache"
    (raiz / "imagens").mkdir(parents=True)
    linhas = []
    for tipo, n in quantidades.items():
        for i in range(n):
            imagem = f"imagens/{tipo}-{i:05d}.png"
            (raiz / imagem).write_bytes(b"\x89PNG")
            linhas.append(
                {
                    "id": f"train-{len(linhas):05d}",
                    "particao": "train",
                    "tipo": tipo,
                    "campos": {"nome": "FULANO"},
                    "sem_anotacao": [],
                    "imagem": imagem,
                    "transcricao": "",
                    "inteiro_teor": "",
                    "largura": 457,
                    "altura": 640,
                    "erro": None,
                }
            )
    (raiz / nome).write_text(
        "".join(json.dumps(linha) + "\n" for linha in linhas), encoding="utf-8"
    )
    return raiz


def test_le_manifesto_com_invoice_e_outros_como_invoice(tmp_path):
    imagens, descartes = listar_manifesto(_fonte(tmp_path))
    assert len(imagens) == 50 and not descartes
    assert {i.classe for i in imagens} == {"cnh", "rg", "invoice"}


def test_descarta_erro_e_imagem_ausente_e_recusa_tipo_desconhecido(tmp_path):
    raiz = _fonte(tmp_path, {"cnh": 2, "rg": 2, "invoice": 2})
    arquivo = raiz / "MANIFESTO.JSONL"
    linhas = [json.loads(linha) for linha in arquivo.read_text("utf-8").splitlines()]
    linhas[0]["erro"] = "formato_invalido"
    (raiz / linhas[1]["imagem"]).unlink()
    arquivo.write_text("".join(json.dumps(linha) + "\n" for linha in linhas), "utf-8")
    imagens, descartes = listar_manifesto(raiz)
    assert len(imagens) == 4
    assert descartes == {"erro na preparação": 1, "imagem ausente": 1}
    linhas[2]["tipo"] = "passaporte"
    arquivo.write_text("".join(json.dumps(linha) + "\n" for linha in linhas), "utf-8")
    with pytest.raises(ValueError, match="passaporte"):
        listar_manifesto(raiz)


def test_manifesto_ausente_e_erro(tmp_path):
    with pytest.raises(ValueError, match="MANIFESTO"):
        listar_manifesto(tmp_path)


def test_divide_70_15_15_e_monta_cache_so_de_classificacao(tmp_path):
    imagens, _ = listar_manifesto(_fonte(tmp_path, nome="manifesto.jsonl"))
    divisao = dividir(imagens, semente=42)
    assert {p: len(v) for p, v in divisao.items()} == {"train": 35, "valid": 8, "test": 7}
    itens = montar_cache(divisao, tmp_path / "treino")
    assert len(itens) == 50
    particoes = carregar_preparados(tmp_path / "treino")
    assert {p: len(v) for p, v in particoes.items()} == {"train": 35, "valid": 8, "test": 7}
    cnh = next(i for i in particoes["train"] if i.tipo == "cnh")
    assert set(cnh.sem_anotacao) >= {"nome", "cpf"} and cnh.campos["nome"] is None
    invoice = next(i for i in particoes["test"] if i.tipo == "invoice")
    assert invoice.sem_anotacao == [] and invoice.origem.startswith("imagens/")
    assert (tmp_path / "treino" / invoice.imagem).is_file()  # caminho absoluto na fonte
