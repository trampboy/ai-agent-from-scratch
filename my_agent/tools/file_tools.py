"""P3 — File tools (read / write / list within a workspace)."""

from __future__ import annotations

from typing import Any
import os

def read_file(path: str, start_line: int = 1, end_line: int = -1) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    if not os.path.isfile(path):
        # 不是文件，而是目录
        raise IsADirectoryError(f"Not a file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        start_idx = max(0, start_line - 1)
        end_idx = len(lines) if end_line == -1 else min(len(lines), end_line)
        selected = lines[start_idx:end_idx]
        result = []
        for i, line in enumerate(selected, start=start_line):
            result.append(f"{i:4d}: {line.rstrip()}")
        return "\n".join(result)
    except Exception as e:
        raise ValueError(f"Error reading file: {e}")


def write_file(path: str, content: str, **kwargs: Any) -> str:
    if os.path.isdir(path):
        raise IsADirectoryError(f"Not a file: {path}")
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"File written successfully: {path}"
    except Exception as e:
        raise ValueError(f"Error writing file: {e}")


def list_files(path: str = ".", **kwargs: Any) -> list:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Not a directory: {path}")
    try:
        files = []
        for name in os.listdir(path):
            if name.startswith("."):
                continue
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                files.append(f"{name}/")  # 目录以 / 结尾
            elif os.path.isfile(full_path):
                files.append(name)
        return files
    except Exception as e:
        raise ValueError(f"Error listing files: {e}")
