import importlib.util

import pytest

from conftest import RAIZ

_spec = importlib.util.spec_from_file_location(
    "t038_colab", RAIZ / "infrastructure" / "colab" / "t038_colab.py"
)
colab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(colab)


def test_le_gpu_do_nvidia_smi():
    gpu = colab.ler_gpu("NVIDIA L4, 23034, 8.9, 580.82.07\n")
    assert gpu == colab.Gpu("NVIDIA L4", 22.49, 8.9, "580.82.07")


def test_aceita_gpu_com_bfloat16():
    problemas, avisos = colab.avaliar_condicoes(
        colab.Gpu("NVIDIA L4", 22.5, 8.9, "x"), espaco_livre_gb=80, drive_montado=True
    )
    assert problemas == [] and avisos == []


def test_recusa_ausencia_de_gpu_e_t4():
    problemas, _ = colab.avaliar_condicoes(None, 80, True)
    assert any("GPU" in p for p in problemas)
    problemas, _ = colab.avaliar_condicoes(colab.Gpu("Tesla T4", 15.0, 7.5, "x"), 80, True)
    assert any("bfloat16" in p for p in problemas)


def test_avisa_drive_desmontado_e_pouco_disco():
    problemas, avisos = colab.avaliar_condicoes(colab.Gpu("A100", 40.0, 8.0, "x"), 10, False)
    assert any("espaço" in p for p in problemas)
    assert any("Drive" in a for a in avisos)


def test_argumentos_padrao_e_limites():
    a = colab.argumentos(["--etapa", "tudo", "--limite-treino", "20", "--limite-teste", "10"])
    assert (a.etapa, a.limite_treino, a.limite_teste, a.zero_shot) == ("tudo", 20, 10, True)
    with pytest.raises(SystemExit):
        colab.argumentos(["--etapa", "inexistente"])


def test_subetapa_repassa_as_opcoes():
    a = colab.argumentos(["--etapa", "tudo", "--limite-treino", "20", "--sem-zero-shot"])
    opcoes = colab.opcoes_da_subetapa(a, "treinar")
    assert opcoes[:2] == ["--etapa", "treinar"]
    assert colab.argumentos(opcoes).limite_treino == 20
    assert colab.argumentos(opcoes).zero_shot is False
