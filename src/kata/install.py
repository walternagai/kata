"""Instala as skills empacotadas a partir do wheel, sem exigir clone do repo.

Os scripts `scripts/install*.sh` criam symlinks apontando para o checkout —
que não existe para quem instalou via `pipx install kata-dev`. Este módulo
copia o gerado embarcado em `src/kata/assets/` para `~/.config/opencode` ou
`~/.claude`, com as mesmas travas dos instaladores shell: nada que o Kata
não criou é sobrescrito sem `--force`, e o uninstall remove só o que criou.

A prova de "criado pelo Kata" é um marcador `.kata-managed` dentro de cada
diretório de skill (e ao lado do arquivo do agente): reinstalar por cima de
conteúdo nosso é upgrade seguro; por cima de personalização do usuário,
recusa — a menos de `force=True`, que guarda o original em `<nome>.bak`.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from kata import __version__
from kata.skills import FRONTENDS, Frontend

MARKER = ".kata-managed"
AGENT_MARKER = ".kata-managed-kata.md"

FRONTENDS_VALIDOS: tuple[str, ...] = tuple(f.nome for f in FRONTENDS)


@dataclass
class InstallReport:
    """Resultado de um install/uninstall, para o CLI imprimir."""

    frontend: str
    instaladas: list[str] = field(default_factory=list)
    removidas: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    recusadas: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.erros and not self.recusadas


def bundled_root() -> Path:
    """Raiz dos assets embarcados (`src/kata/assets/` no wheel ou no repo)."""
    try:
        raiz = resources.files("kata") / "assets"
        if raiz.is_dir():
            return Path(str(raiz))
    except (ModuleNotFoundError, TypeError, OSError):
        pass
    return Path(__file__).resolve().parent / "assets"


def _frontend(nome: str) -> Frontend:
    for f in FRONTENDS:
        if f.nome == nome:
            return f
    raise ValueError(f"frontend desconhecido: {nome!r} (use: {', '.join(FRONTENDS_VALIDOS)})")


def _origens(frontend: Frontend) -> tuple[Path, Path | None]:
    """Diretórios de origem (skills, agent?) dentro do pacote embarcado."""
    raiz = bundled_root()
    if frontend.nome == "opencode":
        return raiz / "opencode" / "skills", raiz / "opencode" / "agent"
    return raiz / "claude-code" / "skills", None


def _e_nosso_skill(destino: Path) -> bool:
    return (destino / MARKER).is_file()


def _e_link_nosso(destino: Path, origem: Path) -> bool:
    """True quando o destino é symlink cujo alvo tem o MESMO conteúdo do embarcado.

    É o estado que os instaladores shell deixam (`make install` /
    `make install-claude-code`): symlinks para o checkout. Sem isto,
    `kata --install` recusava o link criado pelo próprio projeto e a migração
    para cópia deixava instalação mista (13 cópias + 1 link, exit 1).

    Um link assim não guarda conteúdo do usuário — adotá-lo e substituí-lo
    pela cópia não perde nada. É o mesmo critério por conteúdo que
    `_e_nosso_agent` já usa: funciona sem o checkout, onde comparar caminhos
    com a fonte não seria possível. Vale para diretório de skill (compara
    `SKILL.md`) e para o arquivo do agente (compara o arquivo).
    """
    if not destino.is_symlink() or not destino.exists():
        return False
    alvo = destino.resolve()
    if alvo.is_dir() != origem.is_dir():
        return False
    if alvo.is_dir():
        a, b = alvo / "SKILL.md", origem / "SKILL.md"
    else:
        a, b = alvo, origem
    return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()


def _e_nosso_agent(marcador: Path, destino: Path, origem: Path) -> bool:
    if marcador.is_file():
        return True
    # Sem marcador mas conteúdo idêntico ao embarcado: intacto, é nosso.
    return destino.is_file() and destino.read_bytes() == origem.read_bytes()


def _backup(caminho: Path) -> Path:
    """Move o existente para `<nome>.bak`, removendo backup anterior."""
    backup = caminho.with_name(caminho.name + ".bak")
    if backup.exists():
        if backup.is_dir() and not backup.is_symlink():
            shutil.rmtree(backup)
        else:
            backup.unlink()
    caminho.rename(backup)
    return backup


def _escrever_marcador(destino: Path) -> None:
    (destino / MARKER).write_text(f"kata-dev {__version__}\n", encoding="utf-8")


def install_frontend(nome: str, force: bool = False) -> InstallReport:
    """Copia skills (+ agente, no OpenCode) do pacote para o config dir."""
    frontend = _frontend(nome)
    report = InstallReport(frontend=nome)
    skills_src, agent_src = _origens(frontend)
    if not skills_src.is_dir():
        report.erros.append(f"assets não encontrados em {skills_src}")
        return report

    config = frontend.config_dir()
    skills_dir = config / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    for origem in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        destino = skills_dir / origem.name
        if destino.is_symlink() or destino.exists():
            if _e_nosso_skill(destino) or _e_link_nosso(destino, origem):
                if destino.is_symlink():
                    destino.unlink()
                else:
                    shutil.rmtree(destino)
            elif force:
                report.backups.append(str(_backup(destino)))
            else:
                report.recusadas.append(
                    f"{destino} já existe e não foi criado pelo Kata "
                    "(use --force para guardar .bak e substituir)"
                )
                continue
        shutil.copytree(origem, destino)
        _escrever_marcador(destino)
        report.instaladas.append(origem.name)

    if agent_src is not None:
        origem_agent = agent_src / "kata.md"
        agent_dir = config / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        destino_agent = agent_dir / "kata.md"
        marcador = agent_dir / AGENT_MARKER
        if destino_agent.is_symlink() or destino_agent.exists():
            if _e_nosso_agent(marcador, destino_agent, origem_agent):
                destino_agent.unlink()
            elif force:
                report.backups.append(str(_backup(destino_agent)))
            else:
                report.recusadas.append(
                    f"{destino_agent} já existe e não foi criado pelo Kata "
                    "(use --force para guardar .bak e substituir)"
                )
                return report
        shutil.copy2(origem_agent, destino_agent)
        marcador.write_text(f"kata-dev {__version__}\n", encoding="utf-8")
        report.instaladas.append("agent/kata.md")

    return report


def _limpar_bak_de_link(dir_pai: Path, origem: Path, report: InstallReport) -> None:
    """Remove `<nome>.bak` que seja symlink NOSSO, deixado por `--force` antigo.

    Quando o `--force` era a única via para migrar um link dos instaladores
    shell, o original ia para `.bak` — que continuava sendo um symlink para o
    checkout. O uninstall não o removia (só apaga diretórios com marcador), e
    ele ficava para sempre.

    Só remove symlink cujo alvo tem o mesmo conteúdo do embarcado. Um `.bak`
    de conteúdo real do usuário — diretório ou arquivo — é preservado.
    """
    if not dir_pai.is_dir():
        return
    for bak in sorted(dir_pai.glob("*.bak")):
        nome_original = bak.name.removesuffix(".bak")
        if _e_link_nosso(bak, origem / nome_original):
            bak.unlink()
            report.removidas.append(bak.name)


def uninstall_frontend(nome: str) -> InstallReport:
    """Remove só o que o install copiou; personalização do usuário fica."""
    frontend = _frontend(nome)
    report = InstallReport(frontend=nome)
    config = frontend.config_dir()
    skills_dir = config / "skills"
    skills_src, agent_src = _origens(frontend)

    if skills_dir.is_dir():
        for filho in sorted(skills_dir.iterdir()):
            if filho.is_dir() and _e_nosso_skill(filho):
                shutil.rmtree(filho)
                report.removidas.append(filho.name)
        _limpar_bak_de_link(skills_dir, skills_src, report)

    if frontend.nome == "opencode":
        agent_dir = config / "agent"
        destino_agent = agent_dir / "kata.md"
        marcador = agent_dir / AGENT_MARKER
        origem_agent = agent_src / "kata.md" if agent_src else None
        if marcador.is_file() or (
            origem_agent is not None
            and origem_agent.is_file()
            and _e_nosso_agent(marcador, destino_agent, origem_agent)
        ):
            if destino_agent.is_symlink() or destino_agent.is_file():
                destino_agent.unlink()
                report.removidas.append("agent/kata.md")
            if marcador.is_file():
                marcador.unlink()
        if agent_src is not None:
            _limpar_bak_de_link(agent_dir, agent_src, report)

    return report


def config_dir_de(nome: str) -> Path:
    """Diretório de destino de um frontend (respeita *_CONFIG_DIR)."""
    return _frontend(nome).config_dir()


def _resolver_nomes(selecao: str | None) -> list[str]:
    if selecao in (None, "all"):
        return list(FRONTENDS_VALIDOS)
    return [selecao]


def run_install(selecao: str | None, force: bool = False) -> tuple[list[InstallReport], int]:
    """Executa o install para a seleção; retorna (reports, exit_code)."""
    reports = [install_frontend(nome, force=force) for nome in _resolver_nomes(selecao)]
    code = 0 if all(r.ok for r in reports) else 1
    return reports, code


def run_uninstall(selecao: str | None) -> tuple[list[InstallReport], int]:
    """Executa o uninstall para a seleção; retorna (reports, exit_code)."""
    reports = [uninstall_frontend(nome) for nome in _resolver_nomes(selecao)]
    code = 0 if all(r.ok for r in reports) else 1
    return reports, code


__all__ = [
    "AGENT_MARKER",
    "FRONTENDS_VALIDOS",
    "MARKER",
    "InstallReport",
    "bundled_root",
    "config_dir_de",
    "install_frontend",
    "run_install",
    "run_uninstall",
    "uninstall_frontend",
]
