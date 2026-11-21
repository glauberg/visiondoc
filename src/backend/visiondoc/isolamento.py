"""Execução isolada de parsers e decodificadores (ING-SEC-05).

Cada chamada roda em processo próprio (spawn), com tempo máximo e, em POSIX,
limite de memória. O processo é encerrado se o tempo for excedido.
"""

import multiprocessing as mp
import sys
from collections.abc import Callable
from typing import Any


class TempoExcedido(Exception):
    pass


class FalhaIsolada(Exception):
    """Exceção levantada no processo isolado, transportada sem o traceback original."""

    def __init__(self, tipo: str, mensagem: str) -> None:
        super().__init__(f"{tipo}: {mensagem}")
        self.tipo = tipo
        self.mensagem = mensagem


def _limitar_memoria(memoria_gb: float) -> None:
    if sys.platform.startswith("win"):
        return  # sem limite de memória por processo no Windows; tempo continua limitado
    import resource

    limite = int(memoria_gb * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (limite, limite))


def _alvo(conexao, funcao, args, memoria_gb) -> None:
    try:
        _limitar_memoria(memoria_gb)
        conexao.send(("ok", funcao(*args)))
    except BaseException as erro:  # noqa: BLE001
        excecao = erro if _serializavel(erro) else None
        conexao.send(("erro", (type(erro).__name__, str(erro)[:300], excecao)))
    finally:
        conexao.close()


def _serializavel(obj) -> bool:
    import pickle

    try:
        pickle.dumps(obj)
        return True
    except Exception:  # noqa: BLE001
        return False


def executar_isolado(
    funcao: Callable[..., Any], args: tuple, tempo_max_s: float, memoria_gb: float
) -> Any:
    contexto = mp.get_context("spawn")
    receptor, emissor = contexto.Pipe(duplex=False)
    processo = contexto.Process(target=_alvo, args=(emissor, funcao, args, memoria_gb), daemon=True)
    processo.start()
    emissor.close()
    try:
        if not receptor.poll(tempo_max_s):
            raise TempoExcedido(f"tempo máximo de {tempo_max_s}s excedido")
        status, valor = receptor.recv()
    except EOFError as erro:
        raise FalhaIsolada("ProcessoEncerrado", "processo isolado terminou sem resposta") from erro
    finally:
        if processo.is_alive():
            processo.kill()
        processo.join(5)
        receptor.close()
    if status == "ok":
        return valor
    tipo, mensagem, excecao = valor
    if excecao is not None:
        raise excecao
    raise FalhaIsolada(tipo, mensagem)
