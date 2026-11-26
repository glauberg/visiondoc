from pathlib import Path

import pytest

from visiondoc.treino.alinhamento import PARTICOES, linha_do_arquivo, verificar_pasta


def test_particoes():
    assert PARTICOES == {"train": (0, 1062), "valid": (1062, 75), "test": (1137, 81)}


def test_linha_do_arquivo():
    assert linha_do_arquivo("train-00000.png") == ("train", 0)
    assert linha_do_arquivo("train-01061.png") == ("train", 1061)
    assert linha_do_arquivo("valid-01062.png") == ("valid", 0)
    assert linha_do_arquivo("test-01137.png") == ("test", 0)
    assert linha_do_arquivo("test-01217.png") == ("test", 80)


@pytest.mark.parametrize("nome", ["test-00005.png", "train-01100.png", "test-01218.png"])
def test_prefixo_nao_bate(nome):
    with pytest.raises(ValueError):
        linha_do_arquivo(nome)


def _pasta_completa(pasta: Path) -> None:
    for split, (inicio, quantidade) in PARTICOES.items():
        for i in range(inicio, inicio + quantidade):
            (pasta / f"{split}-{i:05d}.png").touch()


def test_verificar_pasta_completa_passa(tmp_path):
    _pasta_completa(tmp_path)
    verificar_pasta(tmp_path)


def test_verificar_pasta_sem_arquivo_levanta(tmp_path):
    _pasta_completa(tmp_path)
    (tmp_path / "valid-01100.png").unlink()
    with pytest.raises(ValueError):
        verificar_pasta(tmp_path)


def test_verificar_pasta_com_arquivo_estranho_levanta(tmp_path):
    _pasta_completa(tmp_path)
    (tmp_path / "lixo.png").touch()
    with pytest.raises(ValueError):
        verificar_pasta(tmp_path)
