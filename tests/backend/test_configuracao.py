from pathlib import Path

import pytest
from pydantic import ValidationError

from visiondoc import __version__
from visiondoc.configuracao import carregar_configuracao, versao_pipeline

RAIZ = Path(__file__).resolve().parents[2]


def test_carrega_configuracao_versionada_do_repositorio():
    cfg = carregar_configuracao(RAIZ / "config" / "pipeline.yaml")
    assert cfg.limites.tamanho_max_bytes == 2_000_000
    assert cfg.rasterizacao.dpi == 300
    assert cfg.deteccao.injecao_limiar_alto == 0.9


def test_versao_pipeline_inclui_versao_da_configuracao():
    cfg = carregar_configuracao(RAIZ / "config" / "pipeline.yaml")
    assert versao_pipeline(cfg) == f"{__version__}+cfg.{cfg.versao}"


def test_rejeita_chave_desconhecida(tmp_path):
    original = (RAIZ / "config" / "pipeline.yaml").read_text(encoding="utf-8")
    arquivo = tmp_path / "pipeline.yaml"
    arquivo.write_text(original + "\nchave_inexistente: 1\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        carregar_configuracao(arquivo)


def test_rejeita_limiar_intermediario_maior_que_alto(tmp_path):
    original = (RAIZ / "config" / "pipeline.yaml").read_text(encoding="utf-8")
    arquivo = tmp_path / "pipeline.yaml"
    arquivo.write_text(
        original.replace("injecao_limiar_intermediario: 0.5", "injecao_limiar_intermediario: 0.95"),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        carregar_configuracao(arquivo)
