"""Instala as skills empacotadas a partir do wheel, sem exigir clone do repo.

Os scripts `scripts/install*.sh` criam symlinks apontando para o checkout —
que não existe para quem instalou via `pipx install kata-dev`. Este módulo
copia o gerado embarcado em `src/kata/assets/` para `~/.config/opencode` ou
`~/.claude`, com as mesmas travas dos instaladores shell: nada que o Kata
não criou é sobrescrito sem `--force`, e o uninstall remove só o que criou.

A prova de "criado pelo Kata" é um marcador `.kata-managed` dentro de cada
diretório de skill (e ao lado do arquivo do agente). O marcador guarda a
versão e os hashes dos arquivos instalados: reinstalar por cima de conteúdo
intacto é upgrade seguro; se o usuário editou um arquivo gerenciado, o hash
não confere e o install recusa — a menos de `force=True`, que guarda o
original em `<nome>.bak`. O uninstall também preserva conteúdo com drift.

`kata --install` (Python) e `scripts/install.ps1` (PowerShell) são caminhos
de instalação separados, com registros de posse próprios; desinstale pelo
mesmo caminho que instalou.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from kata import __version__
from kata.skills import FRONTENDS, SUBAGENTES_DIR, Frontend

MARKER = ".kata-managed"
# O marcador de um arquivo avulso nomeia o arquivo que ele protege: o
# `--uninstall` só apaga o que o Kata instalou, e um diretório pode abrigar
# vários arquivos com donos diferentes.
AGENT_FILE = "kata.md"
AGENT_DIR = "agent"
ADVISOR_FILE = "kata-advisor.md"
# Subagente do OpenCode (OpenCode V2 procura em `agents/`). O Claude Code não
# recebe este arquivo: o advisor lá é o `/advisor` nativo. O nome do diretório
# vem de `skills.py`, que é quem descreve o layout do frontend e quem o doctor
# consulta — um só literal para os dois (B8).
ADVISOR_DIR = SUBAGENTES_DIR


def _marcador(arquivo: str) -> str:
    return f"{MARKER}-{arquivo}"


AGENT_MARKER = _marcador(AGENT_FILE)
ADVISOR_MARKER = _marcador(ADVISOR_FILE)


FRONTENDS_VALIDOS: tuple[str, ...] = tuple(f.nome for f in FRONTENDS)


@dataclass
class InstallReport:
    """Resultado de um install/uninstall, para o CLI imprimir."""

    frontend: str
    instaladas: list[str] = field(default_factory=list)
    removidas: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    recusadas: list[str] = field(default_factory=list)
    preservadas: list[str] = field(default_factory=list)
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


def _origens(frontend: Frontend) -> tuple[Path, Path | None, Path | None]:
    """Diretórios de origem (skills, agent?, agents?) dentro do pacote embarcado."""
    raiz = bundled_root()
    if frontend.nome == "opencode":
        return (
            raiz / "opencode" / "skills",
            raiz / "opencode" / AGENT_DIR,
            raiz / "opencode" / ADVISOR_DIR,
        )
    return raiz / "claude-code" / "skills", None, None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes_dir(root: Path) -> dict[str, str]:
    """Hashes dos arquivos de um diretório, relativos à raiz, sem o marcador."""
    return {
        str(p.relative_to(root)): _sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != MARKER
    }


def _hashes_file(path: Path) -> dict[str, str]:
    return {path.name: _sha256(path)}


def _ler_marcador(marcador: Path) -> dict[str, str] | None:
    """Hashes gravados no marcador; None para marcador legado (texto puro)."""
    if not marcador.is_file():
        return None
    try:
        data = json.loads(marcador.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    files = data.get("files") if isinstance(data, dict) else None
    return files if isinstance(files, dict) else None


def _conteudo_bate(destino: Path, marcador: Path, *, is_dir: bool) -> bool:
    """True se o conteúdo atual bate com os hashes que o Kata gravou."""
    files = _ler_marcador(marcador)
    if files is None:
        # Marcador legado (texto puro): posse sem hash. Mantém o comportamento
        # anterior — não há como distinguir edição de upgrade.
        return True
    if is_dir:
        return _hashes_dir(destino) == files
    return destino.is_file() and _hashes_file(destino) == files


def _estado_skill(destino: Path) -> str:
    if not destino.exists():
        return "missing"
    marcador = destino / MARKER
    if not marcador.is_file():
        return "foreign"
    return "ours" if _conteudo_bate(destino, marcador, is_dir=True) else "drifted"


def _e_link_nosso(destino: Path, origem: Path) -> bool:
    """True quando o destino é symlink cujo alvo tem o MESMO conteúdo do embarcado.

    É o estado que os instaladores shell deixam (`make install` /
    `make install-claude-code`): symlinks para o checkout. Sem isto,
    `kata --install` recusava o link criado pelo próprio projeto e a migração
    para cópia deixava instalação mista (13 cópias + 1 link, exit 1).

    Um link assim não guarda conteúdo do usuário — adotá-lo e substituí-lo
    pela cópia não perde nada. É o mesmo critério por conteúdo que
    `_e_nosso_arquivo` já usa: funciona sem o checkout, onde comparar caminhos
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


def _estado_arquivo(marcador: Path, destino: Path) -> str:
    if not destino.exists():
        return "missing"
    if not marcador.is_file():
        return "foreign"
    files = _ler_marcador(marcador)
    if files is None:
        return "ours"  # marcador legado: posse sem hash
    return "ours" if destino.is_file() and _hashes_file(destino) == files else "drifted"


def _e_nosso_arquivo(marcador: Path, destino: Path, origem: Path) -> bool:
    if marcador.is_file():
        files = _ler_marcador(marcador)
        if files is None:
            return True  # marcador legado: posse sem hash
        return destino.is_file() and _hashes_file(destino) == files
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


def _escrever_marcador(destino: Path, marcador: Path | None = None, *, is_dir: bool = True) -> None:
    """Grava versão e hashes do conteúdo recém-instalado."""
    alvo = marcador or (destino / MARKER)
    payload = {
        "version": __version__,
        "kind": "dir" if is_dir else "file",
        "files": _hashes_dir(destino) if is_dir else _hashes_file(destino),
    }
    alvo.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _instalar_arquivo(
    origem: Path,
    destino_dir: Path,
    report: InstallReport,
    force: bool,
) -> bool:
    """Copia um arquivo avulso do pacote e grava o marcador ao lado.

    Devolve False quando recusou — conteúdo do usuário e sem `force`. O
    chamador decide se a recusa interrompe: do agente orquestrador sim (sem
    ele o ciclo não existe); do subagente, não (sem ele o JUDGE degrada para
    a verificação mecânica, que continua válida).
    """
    if not origem.is_file():
        return True
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origem.name
    marcador = destino_dir / _marcador(origem.name)
    if destino.is_symlink() or destino.exists():
        estado = _estado_arquivo(marcador, destino)
        if destino.is_symlink() and _e_link_nosso(destino, origem):
            destino.unlink()
        elif (
            not marcador.is_file()
            and destino.is_file()
            and destino.read_bytes() == origem.read_bytes()
        ):
            destino.unlink()
        elif estado == "ours":
            destino.unlink()
        elif estado == "drifted":
            if force:
                report.backups.append(str(_backup(destino)))
            else:
                report.recusadas.append(
                    f"{destino} tem alterações do usuário "
                    "(use --force para guardar .bak e substituir)"
                )
                return False
        elif force:
            report.backups.append(str(_backup(destino)))
        else:
            report.recusadas.append(
                f"{destino} já existe e não foi criado pelo Kata "
                "(use --force para guardar .bak e substituir)"
            )
            return False
    shutil.copy2(origem, destino)
    _escrever_marcador(destino, marcador, is_dir=False)
    report.instaladas.append(f"{destino_dir.name}/{origem.name}")
    return True


def _remover_arquivo(destino_dir: Path, origem: Path, report: InstallReport) -> None:
    """Remove um arquivo avulso instalado pelo Kata; drift e terceiros ficam."""
    destino = destino_dir / origem.name
    marcador = destino_dir / _marcador(origem.name)
    if not destino.exists() and not marcador.is_file():
        return
    if not _e_nosso_arquivo(marcador, destino, origem):
        report.preservadas.append(f"{destino} tem alterações do usuário; preservado")
        return
    if destino.is_symlink() or destino.is_file():
        destino.unlink()
        report.removidas.append(f"{destino_dir.name}/{origem.name}")
    if marcador.is_file():
        marcador.unlink()


def install_frontend(nome: str, force: bool = False) -> InstallReport:
    """Copia skills + agente (+ subagentes, no OpenCode) para o config dir."""
    frontend = _frontend(nome)
    report = InstallReport(frontend=nome)
    skills_src, agent_src, agents_src = _origens(frontend)
    if not skills_src.is_dir():
        report.erros.append(f"assets não encontrados em {skills_src}")
        return report

    config = frontend.config_dir()
    skills_dir = config / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    for origem in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        destino = skills_dir / origem.name
        estado = _estado_skill(destino)
        if destino.is_symlink() and _e_link_nosso(destino, origem):
            destino.unlink()
        elif estado == "ours":
            if destino.is_symlink():
                destino.unlink()
            else:
                shutil.rmtree(destino)
        elif estado == "drifted":
            if force:
                report.backups.append(str(_backup(destino)))
            else:
                report.recusadas.append(
                    f"{destino} tem alterações do usuário "
                    "(use --force para guardar .bak e substituir)"
                )
                continue
        elif estado == "foreign":
            if force:
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
        if not _instalar_arquivo(agent_src / AGENT_FILE, config / AGENT_DIR, report, force):
            return report
        if agents_src is not None:
            _instalar_arquivo(agents_src / ADVISOR_FILE, config / ADVISOR_DIR, report, force)

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
    skills_src, agent_src, agents_src = _origens(frontend)

    if skills_dir.is_dir():
        for filho in sorted(skills_dir.iterdir()):
            if not (filho.is_dir() or filho.is_symlink()):
                continue
            estado = _estado_skill(filho)
            if estado == "ours":
                if filho.is_symlink():
                    filho.unlink()
                else:
                    shutil.rmtree(filho)
                report.removidas.append(filho.name)
            elif estado == "drifted":
                report.preservadas.append(f"{filho} tem alterações do usuário; preservado")
        _limpar_bak_de_link(skills_dir, skills_src, report)

    if agent_src is not None:
        agent_dir = config / AGENT_DIR
        _remover_arquivo(agent_dir, agent_src / AGENT_FILE, report)
        _limpar_bak_de_link(agent_dir, agent_src, report)

    if agents_src is not None:
        advisor_dir = config / ADVISOR_DIR
        _remover_arquivo(advisor_dir, agents_src / ADVISOR_FILE, report)
        _limpar_bak_de_link(advisor_dir, agents_src, report)

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
    "ADVISOR_FILE",
    "ADVISOR_MARKER",
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
