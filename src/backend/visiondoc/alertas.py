"""Gravação de `alertas_AAAA-MM-DD.csv` (T030).

Referências: contrato docs/contracts/alertas-csv.md 2.1, RN-012 a RN-015,
RN-017, ADR-006 e Q-11. A gravação nunca interrompe o documento: falha imediata
mantém o alerta em memória para regravação ao fim do lote; se a regravação
falhar, usa-se o arquivo de contingência; se este também falhar, o lote termina
com erro, e o log não contém conteúdo documental.
"""

import csv
import logging
import uuid
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from filelock import FileLock

from visiondoc.csv_seguro import formatar_caixa, preparar_texto
from visiondoc.modelos import Caixa, Identificacao, Ocorrencia

log = logging.getLogger(__name__)

COLUNAS = [
    "id_alerta",
    "id_registro",
    "id_processo",
    "arquivo",
    "hash_arquivo",
    "pagina",
    "bbox",
    "data_hora",
    "etapa",
    "categoria",
    "severidade",
    "regra_ou_modelo",
    "escore",
    "campo",
    "evidencia",
    "localizacao_evidencia",
    "mascarado",
    "tipo_documento_previsto",
    "versao_pipeline",
]
_MASCARADO = {True: "sim", False: "nao", None: None}


class FalhaGravacaoAlertas(Exception):
    def __init__(self, quantidade: int) -> None:
        super().__init__(f"{quantidade} alerta(s) não gravado(s)")
        self.quantidade = quantidade


def registro_de_ocorrencia(
    oc: Ocorrencia,
    identificacao: Identificacao,
    id_registro: str,
    bbox_documento: Caixa | None,
    tipo_documento: str,
    versao_pipeline: str,
) -> dict:
    localizacao = formatar_caixa(oc.localizacao_original) or oc.localizacao_evidencia
    return {
        "id_alerta": str(uuid.uuid4()),
        "id_registro": id_registro,
        "id_processo": identificacao.id_processo,
        "arquivo": identificacao.nome_arquivo,
        "hash_arquivo": identificacao.hash_arquivo,
        "pagina": oc.pagina,
        "bbox": formatar_caixa(bbox_documento),
        "data_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
        "etapa": oc.etapa,
        "categoria": str(oc.categoria),
        "severidade": str(oc.severidade),
        "regra_ou_modelo": oc.regra_ou_modelo,
        "escore": oc.escore,
        "campo": oc.campo,
        "evidencia": oc.evidencia,
        "localizacao_evidencia": localizacao,
        "mascarado": _MASCARADO[oc.mascarado],
        "tipo_documento_previsto": tipo_documento,
        "versao_pipeline": versao_pipeline,
    }


class GravadorAlertas:
    def __init__(
        self,
        diretorio_saida: str | Path,
        diretorio_contingencia: str | Path,
        id_lote: str,
        evidencia_max: int = 500,
        hoje: Callable[[], date] = date.today,
    ) -> None:
        self.diretorio_saida = Path(diretorio_saida)
        self.diretorio_contingencia = Path(diretorio_contingencia)
        self.id_lote = id_lote
        self.evidencia_max = evidencia_max
        self._hoje = hoje
        self._pendentes: list[dict] = []

    @property
    def pendentes(self) -> int:
        return len(self._pendentes)

    def _arquivo_diario(self) -> Path:
        return self.diretorio_saida / f"alertas_{self._hoje():%Y-%m-%d}.csv"

    def _celula(self, coluna: str, valor):
        if valor is None or isinstance(valor, (int, float)):
            return "" if valor is None else valor
        limite = self.evidencia_max if coluna == "evidencia" else None
        return preparar_texto(str(valor), limite)

    def _gravar(self, caminho: Path, registros: list[dict]) -> None:
        if not caminho.parent.is_dir():
            raise FileNotFoundError("diretório de saída indisponível")
        with FileLock(str(caminho) + ".lock"):
            novo = not caminho.exists() or caminho.stat().st_size == 0
            with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
                escritor = csv.writer(arquivo, quoting=csv.QUOTE_NONNUMERIC)
                if novo:
                    escritor.writerow(COLUNAS)
                for registro in registros:
                    escritor.writerow([self._celula(c, registro[c]) for c in COLUNAS])

    def registrar(self, registro: dict) -> bool:
        """Grava imediatamente; em falha, mantém em memória. Nunca levanta exceção de E/S."""
        try:
            self._gravar(self._arquivo_diario(), [registro])
            return True
        except OSError:
            self._pendentes.append(registro)
            return False

    def finalizar_lote(self) -> None:
        if not self._pendentes:
            return
        quantidade = len(self._pendentes)
        try:
            self._gravar(self._arquivo_diario(), self._pendentes)
            self._pendentes.clear()
            return
        except OSError:
            pass
        contingencia = self.diretorio_contingencia / f"alertas_pendentes_{self.id_lote}.csv"
        try:
            self._gravar(contingencia, self._pendentes)
            log.warning(
                "%d alerta(s) do lote %s gravados em contingência", quantidade, self.id_lote
            )
            self._pendentes.clear()
        except OSError as erro:
            log.error(
                "%d alerta(s) do lote %s não gravados: %s",
                quantidade,
                self.id_lote,
                type(erro).__name__,
            )
            raise FalhaGravacaoAlertas(quantidade) from erro
