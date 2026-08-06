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
    ("scripts/install-claude-code.sh", "CLAUDE_CONFIG_DIR", "claude-code/skills"),
    ("scripts/install.sh", "OPENCODE_CONFIG_DIR", "opencode/skills"),
]


def _skills_no_repo(src: str) -> list[str]:
    """Quantas skills existem de fato. O teste não repete a lista: ela já
    viveu em cópias demais."""
    return sorted(p.name for p in (REPO / src).iterdir() if p.is_dir())


pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="instaladores .sh exigem bash")


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


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_install_into_clean_dir(script, env_var, src, tmp_path) -> None:
    result = _run(script, env_var, tmp_path)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in _links(tmp_path)) == _skills_no_repo(src)
    assert all(p.resolve().is_dir() for p in _links(tmp_path))


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_install_is_idempotent(script, env_var, src, tmp_path) -> None:
    _run(script, env_var, tmp_path)
    result = _run(script, env_var, tmp_path)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in _links(tmp_path)) == _skills_no_repo(src)


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_refuses_to_touch_a_real_directory(script, env_var, src, tmp_path) -> None:
    """`ln -sfn` sobre um diretório real cria o link DENTRO dele e o script
    reportava sucesso — a skill não ficava onde a ferramenta procura."""
    alvo = tmp_path / "skills" / "kata-fit"
    alvo.mkdir(parents=True)
    (alvo / "SKILL.md").write_text("customização do usuário", encoding="utf-8")

    result = _run(script, env_var, tmp_path)

    assert result.returncode != 0
    assert "não foi criado pelo Kata" in result.stdout
    assert (alvo / "SKILL.md").read_text(encoding="utf-8") == "customização do usuário"
    assert list(alvo.glob("**/*")) == [alvo / "SKILL.md"]  # nada aninhado
    assert _links(tmp_path) == []  # pré-voo: nenhuma mutação parcial


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_refuses_to_overwrite_a_real_file(script, env_var, src, tmp_path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir(parents=True)
    (skills / "kata-judge").write_text("arquivo do usuário", encoding="utf-8")

    result = _run(script, env_var, tmp_path)

    assert result.returncode != 0
    assert (skills / "kata-judge").read_text(encoding="utf-8") == "arquivo do usuário"


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_refuses_to_replace_foreign_symlink(script, env_var, src, tmp_path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir(parents=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    alvo = skills / "kata-judge"
    alvo.symlink_to(foreign, target_is_directory=True)

    result = _run(script, env_var, tmp_path)

    assert result.returncode != 0
    assert alvo.is_symlink()
    assert alvo.resolve() == foreign


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_uninstall_removes_only_its_own_links(script, env_var, src, tmp_path) -> None:
    _run(script, env_var, tmp_path)
    assert _links(tmp_path)

    result = _run(script, env_var, tmp_path, "--uninstall")

    assert result.returncode == 0, result.stderr
    assert _links(tmp_path) == []


@pytest.mark.parametrize("script,env_var,src", INSTALADORES)
def test_uninstall_cleans_nested_orphan(script, env_var, src, tmp_path) -> None:
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
