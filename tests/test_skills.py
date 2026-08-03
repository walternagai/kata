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
        (skills / nome).mkdir()


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


class TestDoctor:
    def test_cobre_todos_os_frontends(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "oc"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cc"))
        estados = doctor()
        assert [e.frontend for e in estados] == ["opencode", "claude-code"]
        assert all(e.ausente for e in estados)


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
