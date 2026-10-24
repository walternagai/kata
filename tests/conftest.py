"""Fixtures compartilhadas da suíte.

repo_git: repo git real com um commit inicial — o estado que os caminhos
staged/committed precisam para serem exercitados. Helper único no lugar das
cópias de _repo/_make_repo em quatro arquivos de teste (R10-29), que já
tinham divergido (email, nome, arquivo base, mensagem de commit).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import kata

REPO = Path(__file__).resolve().parent.parent
KATA_SRC = (REPO / "src").resolve()


def pytest_configure(config: pytest.Config) -> None:
    """A suíte mede o checkout, nunca um kata instalado em site-packages.

    `make test` define PYTHONPATH para src/; quem roda pytest direto precisa
    do editable install. Sem esta guarda, um `pip install kata-dev` no venv
    faz 981 testes passarem contra outra cópia e o coverage nem lista
    src/kata (revisão de 2026-10-23, M1).
    """
    arquivo = Path(kata.__file__).resolve()
    if not arquivo.is_relative_to(KATA_SRC):
        raise pytest.UsageError(
            f"os testes importaram kata de {arquivo}, fora de {KATA_SRC}. "
            "Use `make test` ou instale com `pip install -e '.[dev]'`."
        )


@pytest.fixture
def repo_git(tmp_path):
    """Repo git real com um arquivo base commitado e identidade configurada."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=tmp_path, check=True)
    return tmp_path
