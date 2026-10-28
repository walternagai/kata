"""Configuração do projeto alvo — quais comandos verificam este repositório.

O kata nasceu presumindo ruff + pytest + coverage. A presunção estava no lugar
errado: quem sabe verificar um projeto é o projeto, não a ferramenta. Sem
isto, num repositório que não é Python o VERIFY não tinha o que rodar e o
JUDGE não re-executava nada — e `UNVERIFIABLE` (ver `kata.judge`) era a única
resposta honesta que sobrava.

O arquivo é `.kata/config.yaml` (ou `.kata/config.json` onde não houver
PyYAML), ao lado dos arquivos de tarefa. Ausente, os defaults reproduzem
exatamente o comportamento anterior — nenhum projeto Python existente muda.

```yaml
verify:
  lint: npx eslint src tests
  typecheck: npx tsc --noEmit
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\\s+\\|\\s+([\\d.]+)'
  gate: 80
```

Cada comando aceita string (dividida como o shell dividiria) ou lista já
dividida. Um papel não declarado cai no default Python daquele papel —
exceto `typecheck`, que não tem default: não existe verificador de tipos
universal, e inventar um faria o kata reportar como verificada uma checagem
que o projeto nunca pediu.

Chave desconhecida em `verify` é erro, não default silencioso: alguém que
escreve `typecheck` num kata antigo acreditava ter declarado o gate de tipos.
Ignorar a chave fazia o ciclo aprovar sem nunca tê-lo rodado — a mesma classe
de mentira que o `ConfigError` acima existe para impedir.
"""

from __future__ import annotations

import json
import math
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# Percentual na linha TOTAL do `coverage report` — o formato que pytest-cov
# emite. É o default porque é o que o kata sempre leu; projetos com outro
# formato declaram o seu em `verify.coverage_pattern`.
DEFAULT_COVERAGE_PATTERN = r"^TOTAL\s+.*?(\d+(?:\.\d+)?)%"

DEFAULT_GATE = 70.0

# Papéis de verificação. `typecheck` não tem default Python: quem declara, roda.
_ROLES = ("lint", "typecheck", "test", "coverage")

# O que pode aparecer dentro de `verify`. Qualquer outra chave é erro nomeado
# (ver o docstring do módulo): antes, `verify.typecheck` num kata que não
# conhecia o papel era lido, descartado e o VERIFY aprovava sem ele.
_VERIFY_KEYS = frozenset({*_ROLES, "coverage_pattern", "gate"})

# Operadores que só existem num shell. `verify._run` executa SEM shell, então
# `npm run check && npm run test:db` chegava ao processo como seis argumentos
# e o npm os repassava ao script: exit 0, tier 2 nunca executado. Rejeitar no
# carregamento troca um verde silencioso por um erro que diz o que fazer.
# A saída legítima é um script do projeto (`npm run check:all`) ou um shell
# explícito (`bash -c "..."`), que não é token solto e continua aceito.
_SHELL_OPERATORS = frozenset({"&&", "||", "|", ";", "&", ">", ">>", "<", "<<"})


class ConfigError(ValueError):
    """Configuração presente porém inválida.

    É erro, e não default silencioso, de propósito: quem escreveu
    `.kata/config.yaml` quis verificar de um jeito específico. Cair no ruff
    calado faria o kata reportar sucesso de uma verificação que o projeto
    nunca pediu — a mesma classe de mentira que o JUDGE existe para caçar.
    """


@dataclass(frozen=True)
class AdvisorConfig:
    """Configuração do subagente advisor declarada em .kata/config.yaml.

    Permite que o projeto especifique o modelo mais robusto ou nível de
    thinking para a revisão adversarial semântica (Estágio 2 do JUDGE).
    """

    enabled: bool = True
    model: str | None = None
    effort: str | None = None
    skip_trivial: bool = True


@dataclass(frozen=True)
class VerifyConfig:
    """Comandos de verificação declarados pelo projeto alvo.

    `None` em um papel significa "não declarado": o papel cai no default
    Python e continua obedecendo às flags de caminho (`--ruff-paths`,
    `--test-paths`, `--cov-source`). Um papel declarado é usado verbatim, e
    as flags de caminho daquele papel deixam de valer — o projeto já disse
    o comando inteiro.
    """

    lint: list[str] | None = None
    # `typecheck` fica sem default de propósito: ao contrário de ruff e
    # pytest, não existe verificador de tipos universal. Papel não declarado
    # simplesmente não roda — e não entra como True no YAML.
    typecheck: list[str] | None = None
    test: list[str] | None = None
    coverage: list[str] | None = None
    coverage_pattern: str = DEFAULT_COVERAGE_PATTERN
    gate: float | None = None

    @property
    def customizado(self) -> bool:
        """Algum papel foi declarado pelo projeto."""
        return any(getattr(self, role) is not None for role in _ROLES)


def _parse_command(value: Any, role: str) -> list[str] | None:
    """Aceita string ("npx eslint src") ou lista (["npx", "eslint", "src"]).

    K-09: aspas não fechadas ("npx eslint 'src") levantam ValueError do
    shlex — antes escapavam do `except ConfigError` do main e viravam
    traceback. Config ilegível é erro nomeado, nunca traceback (mesma
    doutrina do docstring de ConfigError).

    Operador de shell virado token é erro nomeado. O comando é executado sem
    shell (`verify._run`), então `a && b` não encadeia: o segundo vira
    argumento do primeiro. No npm isso devolve exit 0 com o primeiro script
    só — verde que esconde a metade não executada.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            cmd = shlex.split(value)
        except ValueError as exc:
            raise ConfigError(f"verify.{role}: comando inválido ({exc})") from exc
        if not cmd:
            raise ConfigError(f"verify.{role}: comando vazio")
        return _reject_shell_operators(cmd, role)
    if isinstance(value, list):
        if not value:
            raise ConfigError(f"verify.{role}: comando vazio")
        if not all(isinstance(part, str) for part in value):
            raise ConfigError(f"verify.{role}: a lista deve conter só strings")
        return _reject_shell_operators(list(value), role)
    raise ConfigError(f"verify.{role}: esperava string ou lista, veio {type(value).__name__}")


def _reject_shell_operators(cmd: list[str], role: str) -> list[str]:
    """Recusa operador de shell como token solto no comando.

    Token solto é a assinatura do encadeamento acidental. Um operador dentro
    de um token com espaços (`bash -c "npm ci && npm test"`) é shell
    explícito e continua válido — ali quem interpreta é o bash, não o kata.
    """
    for token in cmd:
        if token in _SHELL_OPERATORS:
            raise ConfigError(
                f"verify.{role}: `{token}` não é interpretado — o kata executa o comando "
                "sem shell, e o que vem depois vira argumento do primeiro. Declare um "
                "script do projeto (`npm run check:all`) ou um shell explícito "
                '(`bash -c "comando1 && comando2"`).'
            )
    return cmd


def config_path(cwd: Path | None = None) -> Path | None:
    """Caminho do arquivo de config existente, ou None."""
    base = (cwd or Path.cwd()) / ".kata"
    for nome in ("config.yaml", "config.yml", "config.json"):
        caminho = base / nome
        if caminho.is_file():
            return caminho
    return None


def _load_raw_config(cwd: Path | None = None) -> tuple[Path | None, dict[str, Any] | None]:
    """Lê o arquivo de config existente (.kata/config.yaml / json) e retorna (caminho, dados)."""
    caminho = config_path(cwd)
    if caminho is None:
        return None, None

    texto = ""
    try:
        texto = caminho.read_text(encoding="utf-8")
        if caminho.suffix == ".json" or not _HAS_YAML:
            dados = json.loads(texto)
        else:
            dados = yaml.safe_load(texto)
    except Exception as exc:
        # YAML, JSON e OSError levantam exceções de famílias diferentes; o
        # que importa é que config ilegível vire erro nomeado, nunca default
        # silencioso. O read_text fora do try deixava OSError (permissão,
        # diretório quebrado) escapar como traceback (K-09).
        raise ConfigError(f"{caminho}: não foi possível ler ({exc})") from exc

    if dados is None:
        return caminho, None
    if not isinstance(dados, dict):
        raise ConfigError(f"{caminho}: esperava um mapa no topo")
    return caminho, dados


def load_verify_config(cwd: Path | None = None) -> VerifyConfig:
    """Lê `.kata/config.yaml`. Sem arquivo, devolve os defaults Python."""
    caminho, dados = _load_raw_config(cwd)
    if caminho is None or dados is None:
        return VerifyConfig()

    verify = dados.get("verify")
    if verify is None:
        verify = {}
    if not isinstance(verify, dict):
        raise ConfigError(f"{caminho}: `verify` deve ser um mapa")

    desconhecidas = sorted(str(k) for k in verify if str(k) not in _VERIFY_KEYS)
    if desconhecidas:
        raise ConfigError(
            f"{caminho}: chave(s) desconhecida(s) em `verify`: {', '.join(desconhecidas)} "
            f"(conhecidas: {', '.join(sorted(_VERIFY_KEYS))})"
        )

    gate = verify.get("gate")
    if gate is not None and (isinstance(gate, bool) or not isinstance(gate, (int, float))):
        raise ConfigError(f"{caminho}: `verify.gate` deve ser número")
    if gate is not None and (not math.isfinite(float(gate)) or not 0 <= gate <= 100):
        raise ConfigError(f"{caminho}: `verify.gate` deve estar entre 0 e 100")

    pattern = verify.get("coverage_pattern", DEFAULT_COVERAGE_PATTERN)
    if not isinstance(pattern, str):
        raise ConfigError(f"{caminho}: `verify.coverage_pattern` deve ser string")
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ConfigError(f"{caminho}: `verify.coverage_pattern` inválido ({exc})") from exc
    # O percentual é extraído do grupo 1; um padrão válido sem grupo faz
    # run_command_coverage casar sem conseguir medir (R10-1). Erro nomeado no
    # carregamento, não crash em tempo de verificação.
    if compiled.groups < 1:
        raise ConfigError(
            f"{caminho}: `verify.coverage_pattern` deve ter ao menos um grupo "
            "de captura para o percentual"
        )

    return VerifyConfig(
        lint=_parse_command(verify.get("lint"), "lint"),
        typecheck=_parse_command(verify.get("typecheck"), "typecheck"),
        test=_parse_command(verify.get("test"), "test"),
        coverage=_parse_command(verify.get("coverage"), "coverage"),
        coverage_pattern=pattern,
        gate=float(gate) if gate is not None else None,
    )


def load_advisor_config(cwd: Path | None = None) -> AdvisorConfig:
    """Lê a seção `advisor` de `.kata/config.yaml`. Sem arquivo ou seção, devolve defaults."""
    caminho, dados = _load_raw_config(cwd)
    if caminho is None or dados is None:
        return AdvisorConfig()

    advisor = dados.get("advisor")
    if advisor is None:
        return AdvisorConfig()
    if not isinstance(advisor, dict):
        raise ConfigError(f"{caminho}: `advisor` deve ser um mapa")

    enabled = advisor.get("enabled", True)
    if isinstance(enabled, str):
        if enabled.lower() in ("true", "auto", "always"):
            enabled = True
        elif enabled.lower() in ("false", "never"):
            enabled = False
        else:
            raise ConfigError(
                f"{caminho}: `advisor.enabled` deve ser booleano ou auto/always/never"
            )
    elif not isinstance(enabled, bool):
        raise ConfigError(f"{caminho}: `advisor.enabled` deve ser booleano")

    model = advisor.get("model")
    if model is not None and not isinstance(model, str):
        raise ConfigError(f"{caminho}: `advisor.model` deve ser string")
    if isinstance(model, str) and not model.strip():
        model = None

    effort = advisor.get("effort")
    if effort is not None and not isinstance(effort, str):
        raise ConfigError(f"{caminho}: `advisor.effort` deve ser string")

    skip_trivial = advisor.get("skip_trivial", True)
    if not isinstance(skip_trivial, bool):
        raise ConfigError(f"{caminho}: `advisor.skip_trivial` deve ser booleano")

    return AdvisorConfig(
        enabled=enabled,
        model=model,
        effort=effort,
        skip_trivial=skip_trivial,
    )
