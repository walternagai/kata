"""Testes de kata.skills — o preflight de instalação.

Instalação parcial é o estado perigoso: o orquestrador tenta carregar a
skill que falta, não consegue, e o modelo improvisa a fase a partir do nome
dela. O YAML sai preenchido e o `--audit` não tem como distinguir isso de
trabalho de verdade.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kata.skills import (
    FRONTENDS,
    ORCHESTRATOR_SKILL,
    PHASE_SKILLS,
    Frontend,
    check_frontend,
    doctor,
)

REPO = Path(__file__).resolve().parent.parent


def _instala(config_dir: Path, nomes) -> None:
    skills = config_dir / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    for nome in nomes:
        alvo = skills / nome
        if alvo.is_symlink() or alvo.is_file():
            alvo.unlink()
        elif alvo.exists():
            alvo.rmdir()
        alvo.mkdir()


@pytest.fixture
def oc(tmp_path, monkeypatch) -> Frontend:
    monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path))
    return FRONTENDS[0]


class TestCheckFrontend:
    def test_nada_instalado_e_ausente(self, oc, tmp_path) -> None:
        e = check_frontend(oc)
        assert e.ausente is True
        assert e.parcial is False
        assert e.completo is False
        assert set(e.faltando) == set(PHASE_SKILLS)

    def test_tudo_instalado_e_completo(self, oc, tmp_path) -> None:
        _instala(tmp_path, PHASE_SKILLS)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        e = check_frontend(oc)
        assert e.completo is True
        assert e.parcial is False
        assert e.faltando == []

    def test_faltando_uma_e_parcial(self, oc, tmp_path) -> None:
        """O caso que motiva o módulo: 9 de 10 roda e perde uma fase calado."""
        _instala(tmp_path, [s for s in PHASE_SKILLS if s != "kata-simplify"])
        e = check_frontend(oc)
        assert e.parcial is True
        assert e.completo is False
        assert e.ausente is False
        assert e.faltando == ["kata-simplify"]

    def test_symlink_quebrado_nao_conta_como_instalado(self, oc, tmp_path) -> None:
        """`exists()` segue o link — que é o que o host também faz ao carregar.

        Um link apontando para um diretório removido é exatamente o estado que
        um `git clean` ou um repo movido de lugar produz.
        """
        _instala(tmp_path, PHASE_SKILLS)
        alvo = tmp_path / "skills" / "kata-fit"
        alvo.rmdir()
        alvo.symlink_to(tmp_path / "nao-existe")
        e = check_frontend(oc)
        assert e.faltando == ["kata-fit"]
        assert e.parcial is True

    def test_claude_code_espera_tambem_o_orquestrador(self, tmp_path, monkeypatch) -> None:
        """No Claude Code o orquestrador é uma skill; no OpenCode é um agente."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cc = FRONTENDS[1]
        assert ORCHESTRATOR_SKILL in cc.esperadas()
        assert ORCHESTRATOR_SKILL not in FRONTENDS[0].esperadas()

        _instala(tmp_path, PHASE_SKILLS)
        assert check_frontend(cc).faltando == [ORCHESTRATOR_SKILL]

    def test_config_dir_respeita_a_variavel_de_ambiente(self, oc, tmp_path) -> None:
        assert check_frontend(oc).config_dir == tmp_path

    def test_claude_code_nunca_instalado_nao_e_parcial(self, tmp_path, monkeypatch) -> None:
        """R10-14: `agente_instalado` é True por omissão para claude-code —
        sem exigir `agente_esperado`, um frontend nunca instalado reportava
        `parcial` junto de `ausente`, contradizendo o docstring."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        cc = FRONTENDS[1]
        e = check_frontend(cc)
        assert e.ausente is True
        assert e.parcial is False
        assert e.completo is False


class TestDoctor:
    def test_cobre_todos_os_frontends(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
        estados = doctor()
        assert [e.frontend for e in estados] == ["opencode", "claude-code"]
        assert all(e.ausente for e in estados)

    def test_doctor_domain_avisa_quando_frontend_instalado_sem_domain_adapter(
        self, tmp_path, monkeypatch
    ) -> None:
        """CR-012: quando o frontend está instalado mas falta o domain adapter,
        doctor_domain lista o adapter faltando.
        """
        from kata.skills import DOMAIN_SKILLS, doctor_domain

        oc_dir = tmp_path / "oc"
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(oc_dir))
        _instala(oc_dir, PHASE_SKILLS)
        (oc_dir / "agent").mkdir()
        (oc_dir / "agent" / "kata.md").write_text("agent", encoding="utf-8")

        faltando = doctor_domain()
        assert faltando["opencode"] == list(DOMAIN_SKILLS)

    def test_doctor_domain_ignora_domain_adapter_quando_frontend_nao_instalado(
        self, tmp_path, monkeypatch
    ) -> None:
        """CR-012: se o frontend está ausente, não faz sentido exigir adapter."""
        from kata.skills import doctor_domain

        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        faltando = doctor_domain()
        assert faltando["opencode"] == []


class TestSecurity:
    def test_symlink_para_fora_do_repo_nao_conta_como_instalado(self, oc, tmp_path) -> None:
        """CR-012: symlink quebrado ou apontando para fora do config_dir não
        deve ser considerado uma skill instalada (segurança)."""
        _instala(tmp_path, ["kata-fit"])
        alvo = tmp_path / "skills" / "kata-fit"
        if alvo.is_symlink() or alvo.is_file():
            alvo.unlink()
        elif alvo.is_dir():
            alvo.rmdir()
        alvo.symlink_to("/tmp/nao-existe-no-sistema")
        e = check_frontend(oc)
        assert "kata-fit" in e.faltando

    def test_skill_instalada_sem_SKILL_md_ainda_conta(self, oc, tmp_path) -> None:
        """CR-012: check_frontend só verifica existência do diretório; o host
        é quem valida o SKILL.md. Diretório vazio conta como instalado."""
        _instala(tmp_path, ["kata-fit"])
        e = check_frontend(oc)
        assert "kata-fit" not in e.faltando


class TestClaudeCodeOrchestrator:
    def test_com_orquestrador_e_completo(self, tmp_path, monkeypatch) -> None:
        """CR-012: caminho feliz do claude-code com todas as fases + orquestrador."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        _instala(tmp_path, (*PHASE_SKILLS, ORCHESTRATOR_SKILL))
        cc = FRONTENDS[1]
        e = check_frontend(cc)
        assert e.completo is True
        assert e.parcial is False
        assert e.faltando == []

    def test_sem_orquestrador_e_parcial(self, tmp_path, monkeypatch) -> None:
        """CR-012: claude-code com fases mas sem orquestrador é parcial."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        _instala(tmp_path, PHASE_SKILLS)  # sem ORCHESTRATOR_SKILL
        cc = FRONTENDS[1]
        e = check_frontend(cc)
        assert e.completo is False
        assert e.parcial is True
        assert ORCHESTRATOR_SKILL in e.faltando


class TestDomainAdapter:
    def test_frontend_completo_incluindo_domain_adapter(self, oc, tmp_path) -> None:
        """CR-012: check_frontend completo quando o domain adapter também existe."""
        from kata.skills import DOMAIN_SKILLS

        _instala(tmp_path, (*PHASE_SKILLS, *DOMAIN_SKILLS))
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        e = check_frontend(oc)
        assert e.completo is True
        assert e.faltando == []

    def test_skill_orfa_nao_reprova_frontend(self, oc, tmp_path) -> None:
        """CR-012: diretório extra em skills/ que não está na lista canônica
        não faz o frontend ser parcial nem completo — é ignorado.
        """
        _instala(tmp_path, PHASE_SKILLS)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        (tmp_path / "skills" / "kata-fantasma").mkdir()
        e = check_frontend(oc)
        assert e.completo is True
        assert "kata-fantasma" not in e.faltando


def test_a_lista_canonica_bate_com_as_fontes_em_phases() -> None:
    """Duas listas do mesmo conjunto podem divergir; esta impede.

    `scripts/build_skills.py` deriva as skills do filesystem (`phases/*.md`),
    mas o pacote instalado não tem `phases/` e precisa da lista escrita. Uma
    fase nova em phases/ sem entrada aqui sai do preflight — e volta a ser
    possível rodar o ciclo sem ela e não ser avisado.
    """
    fontes = {p.stem for p in (REPO / "phases").glob("*.md")}
    esperado = {*PHASE_SKILLS, ORCHESTRATOR_SKILL}
    assert fontes == esperado, (
        f"phases/ e kata.skills.PHASE_SKILLS divergem: "
        f"só em phases/ {sorted(fontes - esperado)}, "
        f"só em PHASE_SKILLS {sorted(esperado - fontes)}"
    )
