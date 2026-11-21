"""Lote de processamento e descarte de intermediários (ING-SEC-11)."""

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Self


class Lote:
    """Contexto de uma execução. Apaga o diretório de intermediários ao sair, mesmo em falha."""

    def __init__(self, base: str | Path | None = None) -> None:
        self.id = str(uuid.uuid4())
        self._base = Path(base) if base else None
        self.diretorio_trabalho: Path | None = None

    def __enter__(self) -> Self:
        self.diretorio_trabalho = Path(
            tempfile.mkdtemp(prefix=f"visiondoc-{self.id}-", dir=self._base)
        )
        return self

    def __exit__(self, *_exc) -> bool:
        if self.diretorio_trabalho is not None:
            shutil.rmtree(self.diretorio_trabalho, ignore_errors=True)
        return False
