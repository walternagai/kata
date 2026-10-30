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

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from kata import __version__

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

# Diretório dos subagentes dentro do config dir do frontend. Fonte única: o
# `install.py` copia e o `--doctor` confere. Enquanto o literal vivia nos dois
# módulos, renomear um sem o outro fazia o doctor procurar no lugar errado, e
# cada um tinha seu próprio teste — nenhum pegava a divergência (revisão
# completa 2026-10, B8).
SUBAGENTES_DIR = "agents"

# Skills de domain adapters. Diferente das fases, elas são opcionais: o ciclo
# não reprova se estiverem ausentes, porque uma tarefa coding não precisa delas.
# O doctor as lista como aviso, e o orquestrador só as carrega quando o domínio
# da tarefa não é coding.
# Nome do marcador gravado pelo `kata --install` ao lado de cada item. Fica
# aqui (e não só no install.py) porque o doctor o lê: enquanto o literal vivia
# num módulo só, quem lia usava string própria.
MARKER_DIR = ".kata-managed"

DOMAIN_SKILLS: tuple[str, ...] = ("kata-devops", "kata-data-analysis", "kata-research", "kata-docs")

# Skills de fase opcionais: geradas e instaladas, mas fora do preflight
# obrigatório. `kata-agile` é um orquestrador ALTERNATIVO — quem roda o ciclo
# completo nunca precisa dela. Entrar em PHASE_SKILLS tornaria a skill
# obrigatória e reprovaria o `--doctor` de toda instalação existente até um
# `make reinstall`, que é justamente o alarme de "instalação parcial" que o
# doctor usa para acusar risco real.
OPTIONAL_PHASES: tuple[str, ...] = ("kata-agile",)


@dataclass(frozen=True)
class Frontend:
    """Onde um frontend procura suas skills."""

    nome: str
    env_var: str
    default: str
    # O orquestrador do Claude Code é uma skill como as outras; o do OpenCode
    # é um agente, e mora em outro diretório.
    orquestrador_e_skill: bool
    # Subagentes opcionais instalados ao lado das skills, por nome de arquivo
    # em `agents/`. Vazio no Claude Code, onde o revisor adversarial é o
    # `/advisor` nativo — não há arquivo nosso para instalar.
    subagentes: tuple[str, ...] = ()

    def config_dir(self) -> Path:
        return Path(os.environ.get(self.env_var) or Path.home() / self.default)

    def esperadas(self) -> tuple[str, ...]:
        if self.orquestrador_e_skill:
            return (ORCHESTRATOR_SKILL, *PHASE_SKILLS)
        return PHASE_SKILLS

    def domain_skills_esperadas(self) -> tuple[str, ...]:
        return DOMAIN_SKILLS


FRONTENDS: tuple[Frontend, ...] = (
    Frontend(
        "opencode",
        "OPENCODE_CONFIG_DIR",
        ".config/opencode",
        False,
        subagentes=("kata-advisor.md",),
    ),
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
        links: Skills instaladas como symlink (fluxo dev: `make install`).
        copias: Skills instaladas como cópia (fluxo wheel: `kata --install`).
    """

    frontend: str
    config_dir: Path
    instaladas: list[str] = field(default_factory=list)
    faltando: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    copias: list[str] = field(default_factory=list)
    agente_esperado: bool = False
    agente_instalado: bool = True
    subagentes_esperados: tuple[str, ...] = ()
    subagentes_faltando: list[str] = field(default_factory=list)
    # Versões gravadas nos marcadores `.kata-managed` deste frontend. Mais de
    # uma é estado real: instalação feita em releases diferentes.
    versoes: tuple[str, ...] = ()

    @property
    def modo(self) -> str:
        """Como as skills instaladas estão no disco: link, copia, misto, ausente.

        Os dois modos são válidos — link é o fluxo de desenvolvimento (editar
        o repo reflete sem reinstalar), cópia é o do wheel. O que o doctor
        precisa nomear é o **misto**, que é ambíguo: metade reflete o repo e
        metade não, e quem depura uma skill que não atualiza perde tempo até
        descobrir qual é qual.
        """
        if not self.instaladas:
            return "ausente"
        if not self.links:
            return "copia"
        if not self.copias:
            return "link"
        return "misto"

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
    def versao_desatualizada(self) -> bool:
        """Algum item foi instalado por uma versão diferente da que roda.

        A5 da revisão estrutural: o marcador sempre guardou a versão, e o
        doctor nunca a leu — uma cópia da 0.7.4 com o CLI 0.7.5 reportava
        "instalação completa", e o agente rodava as instruções de fase da
        versão antiga. Sem marcador (instalação por link), não há o that
        comparar e não há aviso.
        """
        return any(versao != __version__ for versao in self.versoes)

    @property
    def completo(self) -> bool:
        return (
            bool(self.instaladas)
            and not self.faltando
            and (not self.agente_esperado or self.agente_instalado)
        )


def _versao_do_marcador(marcador: Path) -> str | None:
    """Versão gravada num `.kata-managed`, nos dois formatos que existem.

    O install atual grava JSON (`{"version": ..., "files": ...}`). Instalações
    anteriores deixaram texto puro (`kata-dev 0.7.5`), que o `install.py` já
    reconhece como marcador legado sem hash. Ler só JSON fazia o doctor não
    ver versão nenhuma justamente nas máquinas instaladas há mais tempo —
    inclusive nesta, medido em 2026-10-28: a primeira versão deste código
    devolvia `()` para `~/.config/opencode`.
    """
    try:
        texto = marcador.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        dados = None
    if isinstance(dados, dict):
        versao = dados.get("version")
        return versao.strip() if isinstance(versao, str) and versao.strip() else None
    # Formato legado: `<distribuição> <versão>`.
    partes = texto.split()
    if len(partes) == 2 and re.match(r"^\d+(?:\.\d+)+", partes[1]):
        return partes[1]
    return None


def _versoes_instaladas(config_dir: Path) -> tuple[str, ...]:
    """Versões gravadas nos marcadores `.kata-managed` de um frontend.

    O marcador é por item instalado — `skills/<nome>/.kata-managed` para
    diretório, `<dir>/<arquivo>.kata-managed` para arquivo avulso (o agente e
    o subagente) —, então a leitura varre os três diretórios onde o install
    escreve. Marcador ilegível é ignorado: doctor é diagnóstico, não auditoria
    de JSON.
    """
    versoes: set[str] = set()
    alvos = (config_dir / "skills", config_dir / "agent", config_dir / SUBAGENTES_DIR)
    for base in alvos:
        if not base.is_dir():
            continue
        marcadores = [*base.rglob(f"{MARKER_DIR}"), *base.glob(f"*{MARKER_DIR}")]
        for marcador in marcadores:
            versao = _versao_do_marcador(marcador)
            if versao:
                versoes.add(versao)
    return tuple(sorted(versoes))


def check_frontend(frontend: Frontend) -> InstallStatus:
    """Inspeciona o diretório de skills de um frontend."""
    raiz = frontend.config_dir() / "skills"
    instaladas: list[str] = []
    faltando: list[str] = []
    links: list[str] = []
    copias: list[str] = []
    for nome in frontend.esperadas():
        # Symlink quebrado não conta como instalado: `exists()` segue o link,
        # que é o que o host também vai fazer ao tentar carregar a skill.
        alvo = raiz / nome
        if alvo.exists():
            instaladas.append(nome)
            (links if alvo.is_symlink() else copias).append(nome)
        else:
            faltando.append(nome)
    agente_esperado = not frontend.orquestrador_e_skill
    raiz_config = raiz.parent
    agente_instalado = (raiz_config / "agent" / "kata.md").is_file() if agente_esperado else True
    # Subagente faltando é aviso, nunca reprovação: sem ele o JUDGE cai no
    # Estágio 1 (mecânico), que continua válido — a revisão semântica é o
    # extra. Por isso não entra em `faltando`/`parcial`.
    subagentes_faltando = [
        nome for nome in frontend.subagentes if not (raiz_config / SUBAGENTES_DIR / nome).is_file()
    ]
    return InstallStatus(
        frontend=frontend.nome,
        config_dir=frontend.config_dir(),
        instaladas=instaladas,
        faltando=faltando,
        links=links,
        copias=copias,
        agente_esperado=agente_esperado,
        agente_instalado=agente_instalado,
        subagentes_esperados=frontend.subagentes,
        subagentes_faltando=subagentes_faltando,
        versoes=_versoes_instaladas(frontend.config_dir()),
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


def check_optional_phases(frontend: Frontend) -> list[str]:
    """Skills de fase opcionais que estão faltando no frontend.

    Mesmo contrato de `check_domain_skills`: informa, nunca reprova. Quem não
    tem `kata-agile` instalada roda o `@kata` completo normalmente; a
    instalação parcial de uma fase OBRIGATÓRIA é que é o estado perigoso.
    """
    if check_frontend(frontend).ausente:
        return []
    raiz = frontend.config_dir() / "skills"
    return [nome for nome in OPTIONAL_PHASES if not (raiz / nome).exists()]


def doctor_optional_phases() -> dict[str, list[str]]:
    """Skills de fase opcionais faltando em cada frontend."""
    return {f.nome: check_optional_phases(f) for f in FRONTENDS}


def doctor_domain() -> dict[str, list[str]]:
    """Domain skills opcionais faltando em cada frontend."""
    return {f.nome: check_domain_skills(f) for f in FRONTENDS}
