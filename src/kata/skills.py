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

# As 10 fases. A ordem é a do ciclo, não alfabética, porque é assim que
# aparecem no relatório do doctor e é assim que quem lê espera encontrá-las.
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

    @property
    def ausente(self) -> bool:
        """Nenhuma skill instalada — o frontend simplesmente não é usado."""
        return not self.instaladas

    @property
    def parcial(self) -> bool:
        """Algumas instaladas e outras não.

        É este o estado perigoso, e não o `ausente`. Quem nunca instalou o
        OpenCode não perde nada; quem tem 9 das 10 skills roda o ciclo e
        perde uma fase sem ser avisado.
        """
        return bool(self.instaladas) and bool(self.faltando)

    @property
    def completo(self) -> bool:
        return bool(self.instaladas) and not self.faltando


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
    return InstallStatus(
        frontend=frontend.nome,
        config_dir=frontend.config_dir(),
        instaladas=instaladas,
        faltando=faltando,
    )


def doctor() -> list[InstallStatus]:
    """Estado de instalação de todos os frontends conhecidos."""
    return [check_frontend(f) for f in FRONTENDS]
