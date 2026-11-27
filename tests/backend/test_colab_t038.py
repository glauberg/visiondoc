import importlib.util

import pytest

from conftest import RAIZ

_spec = importlib.util.spec_from_file_location(
    "t038_colab", RAIZ / "infrastructure" / "colab" / "t038_colab.py"
)
colab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(colab)

L4 = colab.Gpu("NVIDIA L4", 22.5, 8.9, "x")


def test_le_gpu_do_nvidia_smi():
    gpu = colab.ler_gpu("NVIDIA L4, 23034, 8.9, 580.82.07\n")
    assert gpu == colab.Gpu("NVIDIA L4", 22.49, 8.9, "580.82.07")


def test_aceita_gpu_com_bfloat16():
    assert colab.avaliar_condicoes(
        L4, espaco_livre_gb=80, drive_montado=True, versao_python=(3, 13)
    ) == ([], [])


def test_recusa_ausencia_de_gpu_e_t4():
    problemas, _ = colab.avaliar_condicoes(None, 80, True, (3, 12))
    assert any("GPU" in p for p in problemas)
    problemas, _ = colab.avaliar_condicoes(colab.Gpu("Tesla T4", 15.0, 7.5, "x"), 80, True, (3, 12))
    assert any("bfloat16" in p for p in problemas)


def test_recusa_drive_desmontado_e_pouco_disco():
    problemas, _ = colab.avaliar_condicoes(colab.Gpu("A100", 40.0, 8.0, "x"), 10, False, (3, 12))
    assert any("espaço" in p for p in problemas)
    assert any("Drive" in p for p in problemas)


def test_aceita_python_312_e_313_e_recusa_outros():
    for versao in ((3, 12), (3, 13)):
        assert colab.avaliar_condicoes(L4, 80, True, versao)[0] == []
    problemas, _ = colab.avaliar_condicoes(L4, 80, True, (3, 14))
    assert any("Python 3.14" in p for p in problemas)


def test_verifica_subpastas_do_bid(tmp_path):
    for pasta, n in (("CNH", 2), ("rg", 1), ("Cpf", 3)):
        (tmp_path / pasta).mkdir()
        for i in range(n):
            (tmp_path / pasta / f"{i}.JPG").write_bytes(b"x")
    assert colab.verificar_dataset(tmp_path) == ([], {"cnh": 2, "cpf": 3, "rg": 1})
    (tmp_path / "Outros").mkdir()
    problemas, _ = colab.verificar_dataset(tmp_path)
    assert any("Outros" in p for p in problemas)
    assert colab.verificar_dataset(tmp_path / "inexistente")[0]


def test_padroes_no_drive_e_cache_por_amostra():
    a = colab.argumentos(["--etapa", "tudo", "--por-classe", "20"])
    assert a.dados.as_posix() == "/content/drive/MyDrive/visiondoc/BID-Dataset"
    assert a.saidas.as_posix() == "/content/drive/MyDrive/visiondoc/logs"
    assert colab.diretorio_cache(a, 42).name == "bid-s42-n20"
    with pytest.raises(SystemExit):
        colab.argumentos(["--etapa", "inexistente"])


def test_subetapa_repassa_as_opcoes():
    a = colab.argumentos(
        ["--etapa", "tudo", "--por-classe", "5", "--limite-treino", "20", "--sem-zero-shot"]
    )
    opcoes = colab.opcoes_da_subetapa(a, "treinar")
    assert opcoes[:2] == ["--etapa", "treinar"]
    b = colab.argumentos(opcoes)
    assert (b.por_classe, b.limite_treino, b.zero_shot, b.saidas) == (5, 20, False, a.saidas)
