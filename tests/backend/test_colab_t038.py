import importlib.util
import json

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


def _manifesto(raiz, linhas):
    (raiz / "imagens").mkdir(parents=True, exist_ok=True)
    for linha in linhas:
        if linha.get("imagem"):
            (raiz / linha["imagem"]).write_bytes(b"x")
    (raiz / "MANIFESTO.JSONL").write_text(
        "".join(json.dumps(linha) + "\n" for linha in linhas), encoding="utf-8"
    )


def test_verifica_manifesto(tmp_path):
    linhas = [
        {"tipo": t, "imagem": f"imagens/{k}.png", "transcricao": "x", "erro": None}
        for k, t in enumerate(["cnh", "cnh", "rg", "invoice", "outros"])
    ]
    _manifesto(tmp_path, linhas)
    assert colab.verificar_dataset(tmp_path) == ([], [], {"cnh": 2, "rg": 1, "invoice": 2})
    linhas[0]["erro"] = "formato_invalido"
    linhas[1]["transcricao"] = ""
    _manifesto(tmp_path, linhas)
    problemas, avisos, contagem = colab.verificar_dataset(tmp_path)
    assert problemas == [] and contagem["cnh"] == 1
    assert any("descartadas" in a for a in avisos) and any("transcrição" in a for a in avisos)
    _manifesto(tmp_path, [{"tipo": "rg", "imagem": "imagens/0.png", "erro": None}])
    problemas, _, _ = colab.verificar_dataset(tmp_path)
    assert any("CNH" in p for p in problemas) and any("INVOICE" in p for p in problemas)
    assert colab.verificar_dataset(tmp_path / "inexistente")[0]


def test_padroes_no_drive_e_cache_por_amostra():
    a = colab.argumentos(["--etapa", "tudo", "--por-classe", "20"])
    assert a.dados.as_posix() == "/content/drive/MyDrive/visiondoc/cache"
    assert a.saidas.as_posix() == "/content/drive/MyDrive/visiondoc/logs"
    assert colab.diretorio_cache(a, 42).as_posix() == (
        "/content/drive/MyDrive/visiondoc/treino/cache/br-doc-s42-n20"
    )
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
