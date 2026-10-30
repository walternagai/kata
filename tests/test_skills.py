"""Testes de kata.skills — o preflight de instalação.

Instalação parcial é o estado perigoso: o orquestrador tenta carregar a
skill que falta, não consegue, e o modelo improvisa a fase a partir do nome
dela. O YAML sai preenchido e o `--audit` não tem como distinguir isso de
trabalho de verdade.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kata.skills import (
    FRONTENDS,
    ORCHESTRATOR_SKILL,
    PHASE_SKILLS,
    SUBAGENTES_DIR,
    Frontend,
    check_frontend,
    check_optional_phases,
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


class TestSubagenteOpcional:
    """O `kata-advisor` faltando é aviso, nunca reprovação.

    Sem ele o JUDGE roda só o Estágio 1 (mecânico), que continua válido. Se
    a ausência contasse como `parcial`, o doctor reprovaria uma instalação
    que funciona — e o `--doctor` existe para nomear o que quebra de fato.
    """

    def test_advisor_esperado_so_no_opencode(self) -> None:
        assert FRONTENDS[0].subagentes == ("kata-advisor.md",)
        assert FRONTENDS[1].subagentes == ()

    def test_diretorio_dos_subagentes_tem_uma_fonte(self) -> None:
        """B8: o literal morava em skills.py e em install.py.

        Renomear um sem o outro fazia o doctor procurar num diretório e o
        install copiar em outro — cada módulo com seu próprio teste, nenhum
        pegando a divergência.
        """
        from kata import install

        assert install.ADVISOR_DIR == SUBAGENTES_DIR == "agents"

    def test_advisor_faltando_e_avisado_sem_reprovar(self, oc, tmp_path) -> None:
        _instala(tmp_path, PHASE_SKILLS)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")

        e = check_frontend(oc)

        assert e.completo is True
        assert e.parcial is False
        assert e.subagentes_faltando == ["kata-advisor.md"]

    def test_advisor_instalado_limpa_o_aviso(self, oc, tmp_path) -> None:
        _instala(tmp_path, PHASE_SKILLS)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "kata-advisor.md").write_text("sub", encoding="utf-8")

        assert check_frontend(oc).subagentes_faltando == []

    def test_claude_code_nao_tem_subagente_esperado(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        _instala(tmp_path, FRONTENDS[1].esperadas())
        assert check_frontend(FRONTENDS[1]).subagentes_faltando == []


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


class TestModoDeInstalacao:
    """O doctor nomeia COMO as skills estão instaladas: link, cópia ou misto.

    Os dois modos são válidos — link é o fluxo dev, cópia é o do wheel. O que
    precisa de nome é o misto: metade reflete o repo e metade não, e sem isso
    escrito o sintoma ("esta skill não atualiza") começa o diagnóstico do zero.
    """

    def test_tudo_copia_reporta_copia(self, oc, tmp_path) -> None:
        _instala(tmp_path, PHASE_SKILLS)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        e = check_frontend(oc)
        assert e.modo == "copia"
        assert e.copias == list(PHASE_SKILLS)
        assert e.links == []

    def test_tudo_link_reporta_link(self, oc, tmp_path) -> None:
        skills = tmp_path / "skills"
        skills.mkdir(parents=True)
        for nome in PHASE_SKILLS:
            alvo = tmp_path / "fontes" / nome
            alvo.mkdir(parents=True)
            (alvo / "SKILL.md").write_text("skill", encoding="utf-8")
            (skills / nome).symlink_to(alvo, target_is_directory=True)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")
        e = check_frontend(oc)
        assert e.modo == "link"
        assert e.links == list(PHASE_SKILLS)
        assert e.copias == []

    def test_metade_link_metade_copia_reporta_misto(self, oc, tmp_path) -> None:
        metade = list(PHASE_SKILLS)[: len(PHASE_SKILLS) // 2]
        _instala(tmp_path, [s for s in PHASE_SKILLS if s not in metade])
        skills = tmp_path / "skills"
        for nome in metade:
            alvo = tmp_path / "fontes" / nome
            alvo.mkdir(parents=True)
            (alvo / "SKILL.md").write_text("skill", encoding="utf-8")
            (skills / nome).symlink_to(alvo, target_is_directory=True)
        (tmp_path / "agent").mkdir()
        (tmp_path / "agent" / "kata.md").write_text("agent", encoding="utf-8")

        e = check_frontend(oc)

        assert e.modo == "misto"
        assert e.completo is True, "misto é ambíguo, não incompleto"
        assert sorted(e.links) == sorted(metade)
        assert len(e.copias) == len(PHASE_SKILLS) - len(metade)

    def test_nada_instalado_reporta_ausente(self, oc) -> None:
        assert check_frontend(oc).modo == "ausente"

    def test_symlink_quebrado_nao_entra_na_contagem_de_link(self, oc, tmp_path) -> None:
        """Link quebrado já não conta como instalado; não pode contar como modo
        link tampouco, senão um frontend ausente reportaria `link`."""
        _instala(tmp_path, PHASE_SKILLS)
        alvo = tmp_path / "skills" / "kata-fit"
        alvo.rmdir()
        alvo.symlink_to(tmp_path / "nao-existe")
        e = check_frontend(oc)
        assert "kata-fit" not in e.links
        assert e.modo == "copia"


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

    `OPTIONAL_PHASES` entra no conjunto esperado, mas não em `PHASE_SKILLS`:
    fonte sem categoria (obrigatória ou opcional) continua sendo divergência.
    O que a disjunção protege é a categoria, não a existência.
    """
    from kata.skills import OPTIONAL_PHASES

    fontes = {p.stem for p in (REPO / "phases").glob("*.md")}
    esperado = {*PHASE_SKILLS, ORCHESTRATOR_SKILL, *OPTIONAL_PHASES}
    assert fontes == esperado, (
        f"phases/ e kata.skills.PHASE_SKILLS divergem: "
        f"só em phases/ {sorted(fontes - esperado)}, "
        f"só em PHASE_SKILLS {sorted(esperado - fontes)}"
    )
    # Opcional que vaza para a lista obrigatória reprova a instalação de quem
    # não perdeu nada — que é o estado que o doctor existe para acusar.
    assert not (set(PHASE_SKILLS) & set(OPTIONAL_PHASES))


class TestVersoesInstaladas:
    """A5: o `.kata-managed` guarda a versão; o doctor passou a lê-la."""

    def _marcador(self, caminho, versao) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps({"version": versao, "kind": "dir"}), encoding="utf-8")

    def test_le_marcador_de_diretorio_e_de_arquivo(self, tmp_path) -> None:
        from kata.skills import _versoes_instaladas

        self._marcador(tmp_path / "skills" / "kata-fit" / ".kata-managed", "0.7.4")
        self._marcador(tmp_path / "agent" / "kata.md.kata-managed", "0.7.5")

        assert _versoes_instaladas(tmp_path) == ("0.7.4", "0.7.5")

    def test_versao_repetida_aparece_uma_vez(self, tmp_path) -> None:
        from kata.skills import _versoes_instaladas

        self._marcador(tmp_path / "skills" / "a" / ".kata-managed", "0.7.5")
        self._marcador(tmp_path / "skills" / "b" / ".kata-managed", "0.7.5")

        assert _versoes_instaladas(tmp_path) == ("0.7.5",)

    def test_marcador_ilegivel_e_ignorado(self, tmp_path) -> None:
        from kata.skills import _versoes_instaladas

        self._marcador(tmp_path / "skills" / "a" / ".kata-managed", "0.7.5")
        (tmp_path / "skills" / "b").mkdir(parents=True)
        (tmp_path / "skills" / "b" / ".kata-managed").write_text("{nao json", encoding="utf-8")

        assert _versoes_instaladas(tmp_path) == ("0.7.5",)

    def test_marcador_legado_em_texto_puro(self, tmp_path) -> None:
        """Formato anterior ao JSON: `<distribuição> <versão>`.

        Medido na máquina do autor em 2026-10-28: `~/.config/opencode` tinha
        `kata-dev 0.7.5` em texto puro, e a leitura só-JSON devolvia `()` —
        o doctor não veria versão nenhuma justamente onde a instalação é mais
        antiga.
        """
        from kata.skills import _versoes_instaladas

        (tmp_path / "skills" / "kata-fit").mkdir(parents=True)
        (tmp_path / "skills" / "kata-fit" / ".kata-managed").write_text(
            "kata-dev 0.7.4\n", encoding="utf-8"
        )
        assert _versoes_instaladas(tmp_path) == ("0.7.4",)

    def test_marcador_em_texto_sem_versao_e_ignorado(self, tmp_path) -> None:
        from kata.skills import _versoes_instaladas

        (tmp_path / "skills" / "a").mkdir(parents=True)
        (tmp_path / "skills" / "a" / ".kata-managed").write_text("lixo", encoding="utf-8")
        assert _versoes_instaladas(tmp_path) == ()

    def test_sem_marcador_nao_ha_versao(self, tmp_path) -> None:
        """Instalação por link não grava marcador: nada a comparar."""
        from kata.skills import _versoes_instaladas

        (tmp_path / "skills" / "kata-fit").mkdir(parents=True)
        assert _versoes_instaladas(tmp_path) == ()

    def test_versao_desatualizada_so_com_diferenca(self) -> None:
        import kata
        from kata.skills import InstallStatus

        atual = InstallStatus(frontend="x", config_dir=Path("/x"), versoes=(kata.__version__,))
        velha = InstallStatus(frontend="x", config_dir=Path("/x"), versoes=("0.0.1",))
        mista = InstallStatus(
            frontend="x", config_dir=Path("/x"), versoes=("0.0.1", kata.__version__)
        )
        vazia = InstallStatus(frontend="x", config_dir=Path("/x"))

        assert atual.versao_desatualizada is False
        assert velha.versao_desatualizada is True
        assert mista.versao_desatualizada is True
        assert vazia.versao_desatualizada is False


class TestOptionalPhases:
    """`kata-agile` é orquestrador alternativo: instalá-lo é opcional.

    Entrar em PHASE_SKILLS tornaria a skill obrigatória e reprovaria o
    `--doctor` de toda instalação existente até um `make reinstall` — o
    alarme de "instalação parcial" passaria a tocar para quem não perdeu
    nada.
    """

    def _com_agente(self, raiz: Path, nomes) -> None:
        _instala(raiz, nomes)
        (raiz / "agent").mkdir(exist_ok=True)
        (raiz / "agent" / "kata.md").write_text("agent", encoding="utf-8")

    def test_kata_agile_fora_do_preflight_obrigatorio(self, oc, tmp_path) -> None:
        from kata.skills import OPTIONAL_PHASES

        assert "kata-agile" in OPTIONAL_PHASES
        assert "kata-agile" not in PHASE_SKILLS

    def test_instalacao_sem_kata_agile_continua_completa(self, oc, tmp_path) -> None:
        self._com_agente(tmp_path, PHASE_SKILLS)
        e = check_frontend(oc)
        assert e.completo is True
        assert e.parcial is False
        assert "kata-agile" not in e.faltando

    def test_kata_agile_faltando_vira_aviso(self, oc, tmp_path) -> None:
        self._com_agente(tmp_path, PHASE_SKILLS)
        assert check_optional_phases(oc) == ["kata-agile"]

    def test_kata_agile_instalada_sem_aviso(self, oc, tmp_path) -> None:
        self._com_agente(tmp_path, (*PHASE_SKILLS, "kata-agile"))
        assert check_optional_phases(oc) == []

    def test_frontend_ausente_nao_avisa(self, oc) -> None:
        """Sem nem as fases, acusar a falta de uma opcional é ruído (R10-15)."""
        assert check_optional_phases(oc) == []
