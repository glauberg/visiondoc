"""Detecção de conteúdo ativo, texto oculto e injeção de prompt (T028).

Referências: RN-009, RN-010, ADR-012, MAL-SEC-01 a MAL-SEC-08 e Q-19/Q-21.
A detecção nunca interrompe o documento. Falha ou indisponibilidade de um
detector gera a ocorrência `falha_deteccao`, nunca uma ausência silenciosa.
Nenhum texto analisado é executado ou tratado como instrução.
"""

import io
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rapidfuzz import fuzz

from visiondoc.configuracao import Configuracao
from visiondoc.modelos import (
    ArquivoIngerido,
    Categoria,
    ItemAtivo,
    Ocorrencia,
    Pagina,
    Severidade,
)
from visiondoc.preprocessamento import PaginaNormalizada
from visiondoc.transcricao import Transcricao

# --- utilidades ----------------------------------------------------------------


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _normalizar(texto: str) -> str:
    return " ".join(_sem_acentos(texto).upper().split())


def _escapar_invisiveis(texto: str) -> str:
    return "".join(f"\\u{ord(c):04x}" if unicodedata.category(c) == "Cf" else c for c in texto)


def _presenca(trecho: str, texto: str) -> float:
    """Quanto `trecho` aparece em `texto` (0 a 100).

    `partial_ratio` usa sempre a menor cadeia como agulha; se o texto for mais
    curto que o trecho, a comparação passa a ser da cadeia inteira.
    """
    if not texto:
        return 0.0
    if len(texto) < len(trecho):
        return fuzz.ratio(trecho, texto)
    return fuzz.partial_ratio(trecho, texto)


def _falha(detector: str, motivo: str, pagina: int | None = None) -> Ocorrencia:
    return Ocorrencia(
        Categoria.FALHA_DETECCAO,
        Severidade.MEDIA,
        detector,
        f"detector indisponível ou com falha: {motivo}",
        pagina=pagina,
    )


# --- conteúdo ativo --------------------------------------------------------------


def detectar_conteudo_ativo(inventario: list[ItemAtivo]) -> list[Ocorrencia]:
    """Itens executáveis têm severidade alta; os demais, média (calibrável)."""
    return [
        Ocorrencia(
            Categoria.CONTEUDO_ATIVO,
            Severidade.ALTA if item.executavel else Severidade.MEDIA,
            f"inventario:{item.tipo}",
            f"{item.tipo} em {item.objeto}",
            localizacao_evidencia=item.objeto,
        )
        for item in inventario
    ]


def detectar_yara(dados: bytes, regras: str | Path) -> list[Ocorrencia]:
    try:
        import yara

        compiladas = yara.compile(filepath=str(regras))
        correspondencias = compiladas.match(data=dados, timeout=60)
    except Exception as erro:  # noqa: BLE001
        return [_falha("yara", type(erro).__name__)]
    ocorrencias = []
    for c in correspondencias:
        executavel = bool(c.meta.get("executavel", False))
        ocorrencias.append(
            Ocorrencia(
                Categoria.CONTEUDO_ATIVO,
                Severidade.ALTA if executavel else Severidade.MEDIA,
                f"yara:{c.rule}",
                f"regra YARA {c.rule}",
            )
        )
    return ocorrencias


class Verificador(Protocol):
    def verificar(self, dados: bytes) -> str | None:
        """Nome da assinatura encontrada, ou None."""


class VerificadorClamAV:
    def __init__(self, host: str, porta: int, tempo_s: float = 30) -> None:
        self.host, self.porta, self.tempo_s = host, porta, tempo_s

    def verificar(self, dados: bytes) -> str | None:
        import clamd

        cliente = clamd.ClamdNetworkSocket(self.host, self.porta, timeout=self.tempo_s)
        status, assinatura = cliente.instream(io.BytesIO(dados))["stream"]
        if status == "FOUND":
            return assinatura
        if status == "OK":
            return None
        raise RuntimeError(f"resposta inesperada do ClamAV: {status}")


def detectar_clamav(dados: bytes, verificador: Verificador) -> list[Ocorrencia]:
    try:
        assinatura = verificador.verificar(dados)
    except Exception as erro:  # noqa: BLE001
        return [_falha("clamav", type(erro).__name__)]
    if assinatura is None:
        return []
    return [
        Ocorrencia(
            Categoria.CONTEUDO_ATIVO,
            Severidade.ALTA,
            f"clamav:{assinatura}",
            f"assinatura {assinatura}",
        )
    ]


# --- texto oculto ----------------------------------------------------------------


def detectar_texto_oculto(
    pagina: Pagina, normalizada: PaginaNormalizada, transcricao: Transcricao, cfg: Configuracao
) -> list[Ocorrencia]:
    limiar = cfg.deteccao.texto_oculto_partial_ratio
    fonte_minima = cfg.deteccao.fonte_minima_pt
    transcrito = _normalizar(transcricao.inteiro_teor)
    t = normalizada.transformacao
    ocorrencias = []

    for seg in pagina.texto_nativo:
        texto = _normalizar(seg.texto)
        if len(texto.replace(" ", "")) < 3:
            continue
        if seg.tamanho_fonte is not None and seg.tamanho_fonte < fonte_minima:
            regra, escore = "rn-009:fonte_minima", None
        else:
            razao = _presenca(texto, transcrito)
            if razao >= limiar:
                continue
            regra, escore = "rn-009:divergencia_nativo_transcricao", round(razao / 100, 4)
        ocorrencias.append(
            Ocorrencia(
                Categoria.TEXTO_OCULTO,
                Severidade.MEDIA,
                regra,
                seg.texto,
                pagina=pagina.numero,
                escore=escore,
                localizacao=t.para_normalizada(seg.caixa),
                localizacao_original=seg.caixa,
            )
        )

    for linha in transcricao.linhas:
        if any(unicodedata.category(c) == "Cf" for c in linha.texto):
            ocorrencias.append(
                Ocorrencia(
                    Categoria.TEXTO_OCULTO,
                    Severidade.MEDIA,
                    "rn-009:caracteres_invisiveis",
                    _escapar_invisiveis(linha.texto),
                    pagina=pagina.numero,
                    localizacao=linha.caixa,
                    localizacao_original=t.para_original(linha.caixa),
                )
            )
    return ocorrencias


# --- injeção de prompt -------------------------------------------------------------

_PADROES_INJECAO = {
    "ignorar_instrucoes": r"\bIGNOR(E|AR|EM)\b.{0,40}\bINSTRUC",
    "desconsiderar": r"\bDESCONSIDER(E|AR|EM)\b.{0,40}\b(INSTRUC|REGRA|ANTERIOR)",
    "papel_do_modelo": r"\b(VOCE|VC)\b.{0,15}\b(E|SERA|DEVE SER)\b.{0,30}\b(ASSISTENTE|MODELO|IA)\b",
    "classificar_como": r"\bCLASSIFI(QUE|CAR|CA)\b.{0,40}\bCOMO\b.{0,20}\b(CNH|RG|CPF|OUTROS)\b",
    "responder_apenas": r"\bRESPONDA\b.{0,20}\b(APENAS|SOMENTE)\b",
    "prompt_do_sistema": r"\b(PROMPT|INSTRUCAO|INSTRUCOES) (DE|DO) SISTEMA\b",
    "aja_como": r"\bAJA COMO\b",
    "novas_instrucoes": r"\bNOVAS? INSTRUC",
    "ignore_instructions": r"\bIGNORE\b.{0,30}\b(PREVIOUS|PRIOR|ABOVE|ALL)\b.{0,20}\bINSTRUCTIONS?\b",
    "disregard": r"\bDISREGARD\b.{0,40}\b(INSTRUCTIONS?|RULES)\b",
    "you_are_now": r"\bYOU ARE NOW\b",
    "system_prompt": r"\bSYSTEM PROMPT\b",
    "act_as": r"\bACT AS\b",
    "new_instructions": r"\bNEW INSTRUCTIONS?\b",
}
_PADROES_COMPILADOS = {nome: re.compile(p) for nome, p in _PADROES_INJECAO.items()}


class ClassificadorInjecao(Protocol):
    nome: str

    def escore(self, texto: str) -> float: ...


class DetectorInjecaoLLMGuard:
    """Scanner PromptInjection do llm-guard (extra `modelos`); não verificado neste ambiente."""

    def __init__(self) -> None:
        from importlib.metadata import version

        from llm_guard.input_scanners import PromptInjection
        from llm_guard.input_scanners.prompt_injection import MatchType

        self.nome = f"llm_guard:prompt_injection@{version('llm-guard')}"
        self._scanner = PromptInjection(threshold=0.5, match_type=MatchType.FULL)

    def escore(self, texto: str) -> float:
        _, _, risco = self._scanner.scan(texto)
        return max(0.0, min(1.0, float(risco)))


def _padrao(texto: str) -> str | None:
    normalizado = _normalizar(texto)
    for nome, padrao in _PADROES_COMPILADOS.items():
        if padrao.search(normalizado):
            return nome
    return None


def detectar_injecao(
    pagina: Pagina,
    normalizada: PaginaNormalizada,
    transcricao: Transcricao,
    classificador: ClassificadorInjecao | None,
    cfg: Configuracao,
) -> list[Ocorrencia]:
    alto = cfg.deteccao.injecao_limiar_alto
    intermediario = cfg.deteccao.injecao_limiar_intermediario
    t = normalizada.transformacao
    ocorrencias: list[Ocorrencia] = []
    if classificador is None:
        ocorrencias.append(
            _falha("injecao:classificador", "classificador não instalado", pagina.numero)
        )

    trechos = [
        (linha.texto, linha.caixa, t.para_original(linha.caixa)) for linha in transcricao.linhas
    ]
    trechos += [
        (seg.texto, t.para_normalizada(seg.caixa), seg.caixa) for seg in pagina.texto_nativo
    ]

    for texto, caixa, original in trechos:
        escore = None
        if classificador is not None:
            try:
                escore = float(classificador.escore(texto))
            except Exception as erro:  # noqa: BLE001
                ocorrencias.append(_falha(classificador.nome, type(erro).__name__, pagina.numero))
                classificador = None
        padrao = _padrao(texto)
        if escore is not None and escore >= alto:
            severidade, regra = Severidade.ALTA, classificador.nome
        elif escore is not None and escore >= intermediario:
            severidade, regra = Severidade.MEDIA, classificador.nome
        elif padrao:
            severidade, regra = Severidade.BAIXA, f"regex:{padrao}"  # padrão isolado
        else:
            continue
        ocorrencias.append(
            Ocorrencia(
                Categoria.INJECAO_PROMPT,
                severidade,
                regra,
                texto,
                pagina=pagina.numero,
                escore=escore,
                localizacao=caixa,
                localizacao_original=original,
            )
        )
    return ocorrencias


# --- orquestração ----------------------------------------------------------------


@dataclass
class Detectores:
    classificador_injecao: ClassificadorInjecao | None
    clamav: Verificador | None

    @classmethod
    def padrao(cls, cfg: Configuracao) -> "Detectores":
        try:
            classificador = DetectorInjecaoLLMGuard()
        except Exception:  # noqa: BLE001  (extra `modelos` ausente)
            classificador = None
        clamav = cfg.deteccao.clamav
        verificador = VerificadorClamAV(clamav.host, clamav.porta) if clamav.habilitado else None
        return cls(classificador, verificador)


def detectar(
    arquivo: ArquivoIngerido,
    normalizadas: list[PaginaNormalizada],
    transcricoes: list[Transcricao],
    detectores: Detectores,
    cfg: Configuracao,
    regras_yara: str | Path,
) -> list[Ocorrencia]:
    ocorrencias = detectar_conteudo_ativo(arquivo.inventario)
    dados = Path(arquivo.caminho_original).read_bytes()
    ocorrencias += detectar_yara(dados, regras_yara)
    if detectores.clamav is not None:
        ocorrencias += detectar_clamav(dados, detectores.clamav)
    for pagina, normalizada, transcricao in zip(arquivo.paginas, normalizadas, transcricoes):
        try:
            ocorrencias += detectar_texto_oculto(pagina, normalizada, transcricao, cfg)
        except Exception as erro:  # noqa: BLE001
            ocorrencias.append(_falha("texto_oculto", type(erro).__name__, pagina.numero))
        try:
            ocorrencias += detectar_injecao(
                pagina, normalizada, transcricao, detectores.classificador_injecao, cfg
            )
        except Exception as erro:  # noqa: BLE001
            ocorrencias.append(_falha("injecao", type(erro).__name__, pagina.numero))
    return ocorrencias
