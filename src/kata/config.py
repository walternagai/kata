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
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\\s+\\|\\s+([\\d.]+)'
  gate: 80
```

Cada comando aceita string (dividida como o shell dividiria) ou lista já
dividida. Um papel não declarado cai no default Python daquele papel.
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

_ROLES = ("lint", "test", "coverage")


class ConfigError(ValueError):
    """Configuração presente porém inválida.

    É erro, e não default silencioso, de propósito: quem escreveu
    `.kata/config.yaml` quis verificar de um jeito específico. Cair no ruff
    calado faria o kata reportar sucesso de uma verificação que o projeto
    nunca pediu — a mesma classe de mentira que o JUDGE existe para caçar.
    """


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
        return cmd
    if isinstance(value, list):
        if not value:
            raise ConfigError(f"verify.{role}: comando vazio")
        if not all(isinstance(part, str) for part in value):
            raise ConfigError(f"verify.{role}: a lista deve conter só strings")
        return list(value)
    raise ConfigError(f"verify.{role}: esperava string ou lista, veio {type(value).__name__}")


def config_path(cwd: Path | None = None) -> Path | None:
    """Caminho do arquivo de config existente, ou None."""
    base = (cwd or Path.cwd()) / ".kata"
    for nome in ("config.yaml", "config.yml", "config.json"):
        caminho = base / nome
        if caminho.is_file():
            return caminho
    return None


def load_verify_config(cwd: Path | None = None) -> VerifyConfig:
    """Lê `.kata/config.yaml`. Sem arquivo, devolve os defaults Python."""
    caminho = config_path(cwd)
    if caminho is None:
        return VerifyConfig()

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
        return VerifyConfig()
    if not isinstance(dados, dict):
        raise ConfigError(f"{caminho}: esperava um mapa no topo")

    verify = dados.get("verify")
    if verify is None:
        verify = {}
    if not isinstance(verify, dict):
        raise ConfigError(f"{caminho}: `verify` deve ser um mapa")

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
        test=_parse_command(verify.get("test"), "test"),
        coverage=_parse_command(verify.get("coverage"), "coverage"),
        coverage_pattern=pattern,
        gate=float(gate) if gate is not None else None,
    )
