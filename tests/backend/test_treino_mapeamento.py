import json

import pytest

from visiondoc.treino.exemplos import montar_resposta, rotular_tokens
from visiondoc.treino.mapeamento import CAMPOS_CONTRATO, mapear_linha

ESQUEMA_RG = "### Esquema JSON: " + json.dumps(
    {
        "nome_completo": {},
        "registro_geral": {},
        "filiacao_pai": {},
        "filiacao_mae": {},
        "local_nascimento": {},
        "data_nascimento": {},
        "cpf": {},
        "data_expedicao": {},
    }
)


def _rg(**resposta):
    base = {
        "nome_completo": "fulano  de tal",
        "registro_geral": "0000000",
        "filiacao_pai": "BELTRANO DE TAL",
        "filiacao_mae": "CICRANA DE TAL",
        "local_nascimento": "NATAL-RN",
        "data_nascimento": "12/05/1980",
        "cpf": "12345678909",
        "data_expedicao": "2015-03-02",
    }
    base.update(resposta)
    return {"type": "rg", "schema": ESQUEMA_RG, "response": json.dumps(base)}


def test_mapeia_rg_para_o_contrato_normalizando_formatos():
    m = mapear_linha(_rg())
    assert m.tipo == "rg"
    assert m.campos["nome"] == "FULANO DE TAL"
    assert m.campos["numero_documento"] == "0000000"
    assert m.campos["cpf"] == "123.456.789-09"
    assert m.campos["data_nascimento"] == "1980-05-12"
    assert m.campos["data_emissao"] == "2015-03-02"
    assert m.campos["naturalidade"] == "NATAL-RN"
    assert m.campos["filiacao"] == ["BELTRANO DE TAL", "CICRANA DE TAL"]
    assert set(m.campos) == set(CAMPOS_CONTRATO)


def test_campos_pertinentes_nao_anotados_ficam_fora_da_perda():
    m = mapear_linha(_rg())
    assert "orgao_emissor" in m.sem_anotacao  # pertinente ao RG, ausente do esquema
    assert "doc_origem" in m.sem_anotacao
    assert m.campos["data_validade"] is None  # não pertinente ao RG: null conhecido
    assert "data_validade" not in m.sem_anotacao


def test_data_invalida_fica_sem_anotacao():
    m = mapear_linha(_rg(data_nascimento="31/02/1980"))
    assert m.campos["data_nascimento"] is None
    assert "data_nascimento" in m.sem_anotacao


def test_cnh_usa_numero_de_registro_e_categoria():
    linha = {
        "type": "cnh",
        "schema": "### Esquema JSON: "
        + json.dumps(
            {
                "nome": {},
                "num_registro": {},
                "categoria_habilitacao": {},
                "data_validade": {},
                "doc_identidade": {},
            }
        ),
        "response": json.dumps(
            {
                "nome": "Fulano",
                "num_registro": "123",
                "categoria_habilitacao": "AB",
                "data_validade": "01/01/2030",
                "doc_identidade": "x",
            }
        ),
    }
    m = mapear_linha(linha)
    assert (m.tipo, m.campos["numero_documento"], m.campos["categoria_habilitacao"]) == (
        "cnh",
        "123",
        "AB",
    )
    assert m.campos["data_validade"] == "2030-01-01"
    assert m.campos["naturalidade"] is None and "naturalidade" not in m.sem_anotacao


def test_nota_fiscal_vira_outros_sem_campos():
    m = mapear_linha(
        {
            "type": "invoice",
            "schema": "### Esquema JSON: {}",
            "response": json.dumps({"company": "x", "total": 1.0}),
        }
    )
    assert m.tipo == "outros"
    assert all(v is None or v == [] for v in m.campos.values())
    assert m.sem_anotacao == set()


def test_tipo_desconhecido_e_rejeitado():
    with pytest.raises(ValueError):
        mapear_linha({"type": "passaporte", "schema": "", "response": "{}"})


def test_resposta_tem_todas_as_chaves_e_marca_trechos_sem_perda():
    m = mapear_linha(_rg())
    texto, trechos = montar_resposta(m.tipo, m.campos, m.sem_anotacao, "frente", [0, 0, 1000, 1000])
    dados = json.loads(texto)
    doc = dados["documentos"][0]
    assert doc["tipo"] == "rg" and doc["bbox"] == [0, 0, 1000, 1000]
    assert set(doc["campos"]) == set(CAMPOS_CONTRATO)
    ignorados = [texto[a:b] for a, b in trechos]
    assert ignorados == ["null", "null"]  # orgao_emissor e doc_origem
    posicao = texto.index('"orgao_emissor": ') + len('"orgao_emissor": ')
    assert (posicao, posicao + 4) in trechos


def test_rotula_tokens_sobrepostos_aos_trechos_sem_perda():
    offsets = [(0, 3), (3, 7), (7, 11), (11, 12)]
    ids = [10, 11, 12, 13]
    assert rotular_tokens(ids, offsets, [(4, 9)]) == [10, -100, -100, 13]
