"""Fixtures compartilhadas da suíte.

repo_git: repo git real com um commit inicial — o estado que os caminhos
staged/committed precisam para serem exercitados. Helper único no lugar das
cópias de _repo/_make_repo em quatro arquivos de teste (R10-29), que já
tinham divergido (email, nome, arquivo base, mensagem de commit).
"""

from __future__ import annotations

import subprocess

import pytest


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
