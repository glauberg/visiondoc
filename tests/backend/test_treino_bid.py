import csv

import pytest

from visiondoc.treino.bid import amostrar, dividir, exemplos_bid, gravar_particoes_csv, listar_bid
from visiondoc.treino.mapeamento import PERTINENTES, mapear_classe


def _bid(tmp_path, quantidades=None):
    quantidades = quantidades or {"CNH": 20, "RG": 20, "CPF": 10}
    raiz = tmp_path / "BID-Dataset"
    for pasta, n in quantidades.items():
        (raiz / pasta).mkdir(parents=True)
        for i in range(n):
            (raiz / pasta / f"{i:05d}.jpg").write_bytes(b"\xff\xd8\xff")
    return raiz


def test_lista_imagens_com_a_subpasta_como_classe(tmp_path):
    raiz = _bid(tmp_path)
    (raiz / "CNH" / "leia-me.txt").write_text("x")
    (raiz / "RG" / "maiuscula.JPEG").write_bytes(b"\xff\xd8\xff")
    arquivos = listar_bid(raiz)
    assert len(arquivos) == 51
    assert {a.classe for a in arquivos} == {"cnh", "rg", "cpf"}
    assert arquivos[0].relativo == "CNH/00000.jpg"


def test_subpasta_desconhecida_e_erro(tmp_path):
    raiz = _bid(tmp_path)
    (raiz / "Passaporte").mkdir()
    with pytest.raises(ValueError, match="Passaporte"):
        listar_bid(raiz)


def test_divide_70_15_15_por_classe_de_forma_reproduzivel(tmp_path):
    arquivos = listar_bid(_bid(tmp_path))
    divisao = dividir(arquivos, semente=42)
    contagem = {
        p: {c: sum(a.classe == c for a in v) for c in ("cnh", "rg", "cpf")}
        for p, v in divisao.items()
    }
    assert contagem == {
        "train": {"cnh": 14, "rg": 14, "cpf": 7},
        "valid": {"cnh": 3, "rg": 3, "cpf": 2},
        "test": {"cnh": 3, "rg": 3, "cpf": 1},
    }
    todos = [a.relativo for v in divisao.values() for a in v]
    assert len(todos) == len(set(todos)) == 50
    assert dividir(arquivos, semente=42) == divisao
    assert dividir(arquivos, semente=7) != divisao


def test_grava_csv_das_particoes(tmp_path):
    divisao = dividir(listar_bid(_bid(tmp_path)), semente=42)
    caminho = gravar_particoes_csv(divisao, tmp_path / "logs")
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == 50
    assert set(linhas[0]) == {"particao", "classe", "arquivo"}


def test_amostra_por_classe_e_exemplos_so_de_classificacao(tmp_path):
    divisao = amostrar(dividir(listar_bid(_bid(tmp_path)), semente=42), 2)
    assert {p: len(v) for p, v in divisao.items()} == {"train": 6, "valid": 6, "test": 5}
    exemplo = next(iter(exemplos_bid(divisao)))
    assert exemplo.particao == "train" and exemplo.origem.endswith(".jpg")
    assert exemplo.mapeada.sem_anotacao == PERTINENTES[exemplo.mapeada.tipo]


def test_mapear_classe_deixa_todos_os_campos_fora_da_perda():
    m = mapear_classe("cpf")
    assert m.tipo == "cpf" and m.sem_anotacao == {"nome", "cpf", "data_nascimento"}
    assert all(v is None or v == [] for v in m.campos.values())
