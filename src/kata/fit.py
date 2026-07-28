"""Fit gate — classificação e roteamento de tarefas antes do THINK.

Implementa os conceitos de triviality gate e fit gate do fable-method:
1. Identificar tarefas triviais (<=1 arquivo, <10 linhas, sem busca)
2. Classificar a rota da tarefa (code-loop, plan-first, question, research, inference)

Referência: The Fable Method (https://github.com/Sahir619/fable-method),
Karpathy Development Cycle (https://github.com/karpathy).
"""

from __future__ import annotations

import re
from pathlib import Path

from kata.verify import _run


def diff_stats(cwd: Path | None = None) -> tuple[list[str], int]:
    """Analisa o diff git atual e retorna (lista de arquivos, linhas totais).

    Tenta diff unstaged primeiro; se vazio, tenta staged.

    Args:
        cwd: Diretório de execução. Default: CWD atual.

    Returns:
        Tupla (lista de paths de arquivos alterados, total de linhas alteradas).
    """
    result = _run(["git", "diff", "--name-only"], cwd=cwd)
    files_text = result.stdout.strip()
    cmd_stat = ["git", "diff", "--stat"]

    if not files_text:
        result = _run(["git", "diff", "--cached", "--name-only"], cwd=cwd)
        files_text = result.stdout.strip()
        cmd_stat = ["git", "diff", "--cached", "--stat"]

    files = [f for f in files_text.split("\n") if f.strip()]

    result = _run(cmd_stat, cwd=cwd)
    total_lines = 0
    for line in result.stdout.split("\n"):
        m = re.search(r"\|\s*(\d+)", line)
        if m:
            total_lines += int(m.group(1))

    return files, total_lines


def is_trivial(files: list[str], lines: int) -> bool:
    """Retorna True se a tarefa é trivial: <=1 arquivo e <10 linhas.

    Corresponde ao triviality gate do fable-method.
    """
    return len(files) <= 1 and lines < 10
