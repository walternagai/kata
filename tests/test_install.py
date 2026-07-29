"""Testes dos instaladores shell.

Os instaladores mexem em ~/.claude e ~/.config/opencode — defeito ali tem
consequência fora do repositório, e eram o único código do projeto sem
teste nenhum. Cada teste roda o script de verdade contra um CONFIG_DIR
temporário.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

INSTALADORES = [
    ("scripts/install-claude-code.sh", "CLAUDE_CONFIG_DIR", "claude-code/skills", 11),
    ("scripts/install.sh", "OPENCODE_CONFIG_DIR", "opencode/skills", 10),
]

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None, reason="instaladores .sh exigem bash"
)


def _run(script: str, env_var: str, config_dir: Path, *args: str):
    return subprocess.run(
        ["bash", str(REPO / script), *args],
        cwd=REPO,
        env={"PATH": "/usr/bin:/bin", "HOME": str(config_dir), env_var: str(config_dir)},
        capture_output=True,
        text=True,
    )


def _links(config_dir: Path) -> list[Path]:
    skills = config_dir / "skills"
    if not skills.is_dir():
        return []
    return [p for p in skills.iterdir() if p.is_symlink()]


@pytest.mark.parametrize("script,env_var,_src,n_skills", INSTALADORES)
def test_install_into_clean_dir(script, env_var, _src, n_skills, tmp_path) -> None:
    result = _run(script, env_var, tmp_path)
    assert result.returncode == 0, result.stderr
    assert len(_links(tmp_path)) == n_skills
    assert all(p.resolve().is_dir() for p in _links(tmp_path))


@pytest.mark.parametrize("script,env_var,_src,n_skills", INSTALADORES)
def test_install_is_idempotent(script, env_var, _src, n_skills, tmp_path) -> None:
    _run(script, env_var, tmp_path)
    result = _run(script, env_var, tmp_path)
    assert result.returncode == 0, result.stderr
    assert len(_links(tmp_path)) == n_skills


@pytest.mark.parametrize("script,env_var,_src,_n", INSTALADORES)
def test_refuses_to_touch_a_real_directory(script, env_var, _src, _n, tmp_path) -> None:
    """`ln -sfn` sobre um diretório real cria o link DENTRO dele e o script
    reportava sucesso — a skill não ficava onde a ferramenta procura."""
    alvo = tmp_path / "skills" / "kata-fit"
    alvo.mkdir(parents=True)
    (alvo / "SKILL.md").write_text("customização do usuário", encoding="utf-8")

    result = _run(script, env_var, tmp_path)

    assert result.returncode != 0
    assert "não é symlink" in result.stdout
    assert (alvo / "SKILL.md").read_text(encoding="utf-8") == "customização do usuário"
    assert list(alvo.glob("**/*")) == [alvo / "SKILL.md"]  # nada aninhado
    assert _links(tmp_path) == []  # pré-voo: nenhuma mutação parcial


@pytest.mark.parametrize("script,env_var,_src,_n", INSTALADORES)
def test_refuses_to_overwrite_a_real_file(script, env_var, _src, _n, tmp_path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir(parents=True)
    (skills / "kata-judge").write_text("arquivo do usuário", encoding="utf-8")

    result = _run(script, env_var, tmp_path)

    assert result.returncode != 0
    assert (skills / "kata-judge").read_text(encoding="utf-8") == "arquivo do usuário"


@pytest.mark.parametrize("script,env_var,src,_n", INSTALADORES)
def test_uninstall_removes_only_its_own_links(script, env_var, src, _n, tmp_path) -> None:
    _run(script, env_var, tmp_path)
    assert _links(tmp_path)

    result = _run(script, env_var, tmp_path, "--uninstall")

    assert result.returncode == 0, result.stderr
    assert _links(tmp_path) == []


@pytest.mark.parametrize("script,env_var,src,_n", INSTALADORES)
def test_uninstall_cleans_nested_orphan(script, env_var, src, _n, tmp_path) -> None:
    """Instalações anteriores aninhavam o link dentro do diretório existente.
    O uninstall via 'não é symlink' e deixava o órfão para sempre."""
    alvo = tmp_path / "skills" / "kata-fit"
    alvo.mkdir(parents=True)
    (alvo / "NOTAS.md").write_text("do usuário", encoding="utf-8")
    orfao = alvo / "kata-fit"
    orfao.symlink_to(REPO / src / "kata-fit")

    result = _run(script, env_var, tmp_path, "--uninstall")

    assert result.returncode == 0, result.stderr
    assert not orfao.is_symlink()
    assert (alvo / "NOTAS.md").read_text(encoding="utf-8") == "do usuário"


def test_agent_file_is_not_overwritten(tmp_path) -> None:
    """Só o instalador do OpenCode liga um arquivo (o agente): `ln -sf`
    substituiria o arquivo do usuário sem aviso."""
    agent = tmp_path / "agent"
    agent.mkdir(parents=True)
    (agent / "kata.md").write_text("meu agente", encoding="utf-8")

    result = _run("scripts/install.sh", "OPENCODE_CONFIG_DIR", tmp_path)

    assert result.returncode != 0
    assert (agent / "kata.md").read_text(encoding="utf-8") == "meu agente"
