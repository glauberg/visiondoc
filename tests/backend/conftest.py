from pathlib import Path

import pytest

from visiondoc.configuracao import carregar_configuracao

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def cfg():
    return carregar_configuracao(RAIZ / "config" / "pipeline.yaml")


def alterar(cfg, secao: str, **valores):
    """Cópia da configuração com valores alterados em uma seção."""
    nova_secao = getattr(cfg, secao).model_copy(update=valores)
    return cfg.model_copy(update={secao: nova_secao})
