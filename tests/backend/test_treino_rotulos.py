import json

from visiondoc.treino.esquema import SaidaVLM
from visiondoc.treino.rotulos import converter_rotulo, serializar_alvo


def _campos(saida: SaidaVLM):
    return saida.documentos[0].campos


def test_cnh_com_chaves_alternativas():
    resposta = json.dumps(
        {
            "titular": "A B",
            "doc_identidade": "123",
            "cpf": "386.468.821-36",
            "data_nascimento": "1986-08-18",
            "categoria_habilitacao": "AB",
        }
    )
    saida = converter_rotulo("cnh", resposta)
    assert saida.documentos[0].tipo == "cnh"
    assert _campos(saida).nome == "A B"
    assert _campos(saida).numero_documento == "123"
    assert _campos(saida).categoria_habilitacao == "AB"
    assert "data_validade" not in _campos(saida).model_fields_set


def test_rg_mapeia_expedicao_para_emissao():
    resposta = json.dumps(
        {
            "nome_completo": "X",
            "registro_geral": "94.055.743-5",
            "data_expedicao": "1975-11-02",
            "naturalidade": "FREI PAULO-SE",
        }
    )
    saida = converter_rotulo("rg", resposta)
    assert _campos(saida).data_emissao == "1975-11-02"
    assert _campos(saida).numero_documento == "94.055.743-5"
    assert _campos(saida).naturalidade == "FREI PAULO-SE"


def test_invoice_vira_outros():
    saida = converter_rotulo("invoice", json.dumps({"company": "ACME", "total": "10"}))
    assert saida.documentos[0].tipo == "outros"
    assert '"campos":{}' in serializar_alvo(saida)


def test_vazio_vira_null():
    saida = converter_rotulo("rg", json.dumps({"nome_completo": "X", "orgao_emissor": ""}))
    assert _campos(saida).orgao_emissor is None
    assert "orgao_emissor" in _campos(saida).model_fields_set


def test_sinonimo_vazio_nao_sobrescreve():
    a = converter_rotulo("cnh", json.dumps({"nome": "", "nome_completo": "A B"}))
    b = converter_rotulo("cnh", json.dumps({"nome_completo": "", "nome": "C D"}))
    assert _campos(a).nome == "A B"
    assert _campos(b).nome == "C D"


def test_filiacao():
    so_pai = converter_rotulo("rg", json.dumps({"filiacao_pai": "P", "filiacao_mae": ""}))
    so_mae = converter_rotulo("rg", json.dumps({"filiacao_pai": "", "filiacao_mae": "M"}))
    ambos = converter_rotulo("rg", json.dumps({"filiacao_pai": "P", "filiacao_mae": "M"}))
    nenhum = converter_rotulo("rg", json.dumps({"filiacao_pai": "", "filiacao_mae": ""}))
    assert _campos(so_pai).filiacao == ["P"]
    assert _campos(so_mae).filiacao == ["M"]
    assert _campos(ambos).filiacao == ["P", "M"]
    assert '"filiacao"' not in serializar_alvo(nenhum)
    assert '""' not in serializar_alvo(so_pai)


def test_descartes():
    assert converter_rotulo("cnh", "não é json") is None
    assert converter_rotulo("cnh", "[1,2]") is None
    assert converter_rotulo("passaporte", "{}") is None


def test_alvo_fixo():
    nome = 'JOÃO "ZÉ"'
    saida = converter_rotulo("rg", json.dumps({"nome_completo": nome}))
    alvo = serializar_alvo(saida)
    documento = json.loads(alvo)["documentos"][0]
    assert documento["bbox"] == [0, 0, 1000, 1000]
    assert "face" in documento and documento["face"] is None
    assert documento["campos"]["nome"] == nome
    SaidaVLM.model_validate_json(alvo)
