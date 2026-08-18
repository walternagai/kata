"""Quais skills o ciclo precisa, e se elas estão instaladas.

O orquestrador não é auto-contido: em cada fase ele carrega a skill
correspondente e segue as instruções dela. Quando uma skill não está
instalada, a chamada falha e o orquestrador fica sem instrução nenhuma para
aquela fase — e o modelo improvisa a partir do nome. O resultado é um
`.kata/<task>.yaml` com a seção preenchida e nada por trás: exatamente a
"fase fingida" que `kata --audit` existe para caçar, só que produzida pelo
ferramental e não pelo agente.

Este módulo dá o preflight que faltava: a lista canônica do que o ciclo
precisa, e onde procurar por isso em cada frontend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# As skills de fase do ciclo. São 10 skills para 9 fases + JUDGE + QUESTION:
# o ciclo real tem 9 fases (FIT, THINK, SIMPLIFY, INTENT, SURGICAL, VERIFY,
# TWIN CHECK, ARTIFACT, REPORT) e o TWIN CHECK vive no orquestrador — JUDGE
# e QUESTION são skills próprias fora das 9 (K-27). A ordem é a do ciclo,
# não alfabética, porque é assim que aparecem no relatório do doctor e é
# assim que quem lê espera encontrá-las.
PHASE_SKILLS: tuple[str, ...] = (
    "kata-fit",
    "kata-think",
    "kata-simplify",
    "kata-intent",
    "kata-surgical",
    "kata-verify",
    "kata-artifact",
    "kata-report",
    "kata-judge",
    "kata-question",
)

ORCHESTRATOR_SKILL = "kata"

# Skills de domain adapters. Diferente das fases, elas são opcionais: o ciclo
# não reprova se estiverem ausentes, porque uma tarefa coding não precisa delas.
# O doctor as lista como aviso, e o orquestrador só as carrega quando o domínio
# da tarefa não é coding.
DOMAIN_SKILLS: tuple[str, ...] = ("kata-devops",)


@dataclass(frozen=True)
class Frontend:
    """Onde um frontend procura suas skills."""

    nome: str
    env_var: str
    default: str
    # O orquestrador do Claude Code é uma skill como as outras; o do OpenCode
    # é um agente, e mora em outro diretório.
    orquestrador_e_skill: bool

    def config_dir(self) -> Path:
        return Path(os.environ.get(self.env_var) or Path.home() / self.default)

    def esperadas(self) -> tuple[str, ...]:
        if self.orquestrador_e_skill:
            return (ORCHESTRATOR_SKILL, *PHASE_SKILLS)
        return PHASE_SKILLS

    def domain_skills_esperadas(self) -> tuple[str, ...]:
        return DOMAIN_SKILLS


FRONTENDS: tuple[Frontend, ...] = (
    Frontend("opencode", "OPENCODE_CONFIG_DIR", ".config/opencode", False),
    Frontend("claude-code", "CLAUDE_CONFIG_DIR", ".claude", True),
)


@dataclass
class InstallStatus:
    """O que um frontend tem instalado.

    Attributes:
        frontend: Nome do frontend.
        config_dir: Diretório inspecionado.
        instaladas: Skills encontradas.
        faltando: Skills esperadas que não estão lá.
    """

    frontend: str
    config_dir: Path
    instaladas: list[str] = field(default_factory=list)
    faltando: list[str] = field(default_factory=list)
    agente_esperado: bool = False
    agente_instalado: bool = True

    @property
    def ausente(self) -> bool:
        """Nenhuma skill instalada — o frontend simplesmente não é usado."""
        return not self.instaladas and (not self.agente_esperado or not self.agente_instalado)

    @property
    def parcial(self) -> bool:
        """Algumas instaladas e outras não.

        É este o estado perigoso, e não o `ausente`. Quem nunca instalou o
        OpenCode não perde nada; quem tem 9 das 10 skills roda o ciclo e
        perde uma fase sem ser avisado.

        `agente_instalado` é True por omissão quando o frontend não espera
        agente (claude-code) — a primeira conjunção tem de exigir
        `agente_esperado` também, senão um claude-code nunca instalado
        reportaria `parcial` junto de `ausente` (R10-14).
        """
        return (bool(self.instaladas) or (self.agente_esperado and self.agente_instalado)) and (
            bool(self.faltando) or (self.agente_esperado and not self.agente_instalado)
        )

    @property
    def completo(self) -> bool:
        return (
            bool(self.instaladas)
            and not self.faltando
            and (not self.agente_esperado or self.agente_instalado)
        )


def check_frontend(frontend: Frontend) -> InstallStatus:
    """Inspeciona o diretório de skills de um frontend."""
    raiz = frontend.config_dir() / "skills"
    instaladas: list[str] = []
    faltando: list[str] = []
    for nome in frontend.esperadas():
        # Symlink quebrado não conta como instalado: `exists()` segue o link,
        # que é o que o host também vai fazer ao tentar carregar a skill.
        if (raiz / nome).exists():
            instaladas.append(nome)
        else:
            faltando.append(nome)
    agente_esperado = not frontend.orquestrador_e_skill
    agente_instalado = (raiz.parent / "agent" / "kata.md").is_file() if agente_esperado else True
    return InstallStatus(
        frontend=frontend.nome,
        config_dir=frontend.config_dir(),
        instaladas=instaladas,
        faltando=faltando,
        agente_esperado=agente_esperado,
        agente_instalado=agente_instalado,
    )


def check_domain_skills(frontend: Frontend) -> list[str]:
    """Lista domain skills opcionais que estão faltando no frontend.

    Diferente de `check_frontend`, esta função nunca reprova: ela só informa
    que o adapter de um domínio não está disponível. Uma tarefa `coding`
    continua funcionando normalmente.

    Frontend nunca instalado não gera aviso: sem nem as skills de fase, não
    faz sentido acusar a falta de um adapter opcional (R10-15) — o mesmo
    tratamento que o preflight de fases dá ao ausente.
    """
    if check_frontend(frontend).ausente:
        return []
    raiz = frontend.config_dir() / "skills"
    return [nome for nome in frontend.domain_skills_esperadas() if not (raiz / nome).exists()]


def doctor() -> list[InstallStatus]:
    """Estado de instalação de todos os frontends conhecidos."""
    return [check_frontend(f) for f in FRONTENDS]


def doctor_domain() -> dict[str, list[str]]:
    """Domain skills opcionais faltando em cada frontend."""
    return {f.nome: check_domain_skills(f) for f in FRONTENDS}
