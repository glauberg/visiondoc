import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from visiondoc.treino.esquema import SaidaVLM
from visiondoc.treino.instrucao import INSTRUCAO, TEXTO_USUARIO, hash_instrucao

POC = Path(__file__).parents[2] / "infrastructure" / "poc-t020" / "poc_vllm.py"


def _instrucao_da_poc() -> str:
    arvore = ast.parse(POC.read_text("utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id == "INSTRUCAO" for alvo in no.targets
        ):
            return ast.literal_eval(no.value)
    raise AssertionError("INSTRUCAO não encontrada em poc_vllm.py")


def test_instrucao_igual_a_da_poc():
    assert INSTRUCAO == _instrucao_da_poc()


def test_texto_do_usuario_fixo():
    assert TEXTO_USUARIO == "Analise a imagem."


def test_hash_instrucao_estavel():
    assert len(hash_instrucao()) == 64
    assert hash_instrucao() == hash_instrucao()


def test_esquema_aceita_chaves_omitidas():
    saida = SaidaVLM.model_validate_json(
        '{"documentos":[{"tipo":"rg","bbox":[0,0,1000,1000],"campos":{}}]}'
    )
    assert saida.documentos[0].tipo == "rg"
    with pytest.raises(ValidationError):
        SaidaVLM.model_validate_json(
            '{"documentos":[{"tipo":"indefinido","bbox":[0,0,1,1],"campos":{}}]}'
        )
