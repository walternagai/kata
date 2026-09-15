"""Testes do install empacotado (`kata --install`, sem clone do repo).

Os instaladores shell criam symlinks para o checkout; quem instala via
`pipx install kata-dev` não tem checkout — o `kata.install` copia o gerado
embarcado em `src/kata/assets/`. Cada teste usa um CONFIG_DIR temporário.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kata import install as bundled

REPO = Path(__file__).resolve().parent.parent


def _skills_embarcadas(frontend: str) -> list[str]:
    sub = "opencode/skills" if frontend == "opencode" else "claude-code/skills"
    raiz = bundled.bundled_root() / sub
    return sorted(p.name for p in raiz.iterdir() if p.is_dir())


def test_assets_embarcados_espelham_o_repo() -> None:
    """O build gera nos dois destinos com conteúdo idêntico."""
    for rel in (
        "opencode/skills/kata-fit/SKILL.md",
        "claude-code/skills/kata-fit/SKILL.md",
        "opencode/agent/kata.md",
        "claude-code/skills/kata/SKILL.md",
    ):
        assert (bundled.bundled_root() / rel).is_file(), f"asset ausente: {rel}"
        assert (bundled.bundled_root() / rel).read_bytes() == (REPO / rel).read_bytes()


def test_install_opencode_copia_skills_e_agente(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    report = bundled.install_frontend("opencode")

    assert report.ok, report.recusadas or report.erros
    assert sorted(report.instaladas) == sorted([*_skills_embarcadas("opencode"), "agent/kata.md"])
    for nome in _skills_embarcadas("opencode"):
        destino = tmp_path / "skills" / nome
        assert (destino / "SKILL.md").is_file()
        assert (destino / bundled.MARKER).is_file()
    assert (tmp_path / "agent" / "kata.md").is_file()
    assert (tmp_path / "agent" / bundled.AGENT_MARKER).is_file()


def test_install_claude_code_nao_tem_agente(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    report = bundled.install_frontend("claude-code")

    assert report.ok, report.recusadas or report.erros
    assert "agent/kata.md" not in report.instaladas
    assert not (tmp_path / "agent").exists()


def test_install_e_idempotente(tmp_path, monkeypatch) -> None:
    """Reinstalar por cima do nosso conteúdo é upgrade, não erro."""
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    assert bundled.install_frontend("opencode").ok
    segundo = bundled.install_frontend("opencode")
    assert segundo.ok, segundo.recusadas or segundo.erros
    assert not segundo.backups


def test_recusa_personalizacao_sem_force(tmp_path, monkeypatch) -> None:
    """Diretório do usuário nunca é apagado sem --force."""
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    alvo = tmp_path / "skills" / "kata-fit"
    alvo.mkdir(parents=True)
    (alvo / "SKILL.md").write_text("customização do usuário", encoding="utf-8")

    report = bundled.install_frontend("opencode")

    assert not report.ok
    assert (alvo / "SKILL.md").read_text(encoding="utf-8") == "customização do usuário"
    assert not (alvo / bundled.MARKER).exists()


def test_force_guarda_backup_e_instala(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    alvo = tmp_path / "skills" / "kata-fit"
    alvo.mkdir(parents=True)
    (alvo / "SKILL.md").write_text("customização do usuário", encoding="utf-8")

    report = bundled.install_frontend("opencode", force=True)

    assert report.ok, report.recusadas or report.erros
    assert report.backups == [str(tmp_path / "skills" / "kata-fit.bak")]
    assert (tmp_path / "skills" / "kata-fit.bak" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == "customização do usuário"
    assert (alvo / bundled.MARKER).is_file()


def test_uninstall_remove_so_o_que_criou(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    estranho = tmp_path / "skills" / "minha-skill"
    estranho.mkdir(parents=True)
    (estranho / "SKILL.md").write_text("do usuário", encoding="utf-8")

    assert bundled.install_frontend("opencode").ok
    report = bundled.uninstall_frontend("opencode")

    assert report.ok
    assert (estranho / "SKILL.md").read_text(encoding="utf-8") == "do usuário"
    assert not (tmp_path / "skills" / "kata-fit").exists()
    assert not (tmp_path / "agent" / "kata.md").exists()


def test_run_install_all_e_uninstall(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))

    reports, code = bundled.run_install("all")
    assert code == 0
    assert [r.frontend for r in reports] == ["opencode", "claude-code"]

    reports, code = bundled.run_uninstall("all")
    assert code == 0
    assert not (tmp_path / "oc" / "skills" / "kata-fit").exists()
    assert not (tmp_path / "cc" / "skills" / "kata-fit").exists()


def test_frontend_desconhecido_e_erro() -> None:
    with pytest.raises(ValueError, match="frontend desconhecido"):
        bundled.install_frontend("cursor")
