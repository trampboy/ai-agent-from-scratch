"""P3 — File tools (read / write / list within a workspace)."""

from __future__ import annotations

from typing import Any


def read_file(path: str, **kwargs: Any) -> str:
    raise NotImplementedError("P3: safe read within workspace")


def write_file(path: str, content: str, **kwargs: Any) -> str:
    raise NotImplementedError("P3: safe write within workspace")


def list_files(path: str = ".", **kwargs: Any) -> list:
    raise NotImplementedError("P3: list workspace files")
