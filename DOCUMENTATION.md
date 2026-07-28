# Kata Documentation

Technical reference for Kata (型), the Python CLI and OpenCode agent that
guides software changes through a disciplined development cycle.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [CLI](#cli)
- [Development cycle](#development-cycle)
- [Task files](#task-files)
- [Python API](#python-api)
- [OpenCode integration](#opencode-integration)
- [Testing and evaluation](#testing-and-evaluation)
- [Compatibility and limitations](#compatibility-and-limitations)

## Overview

Kata combines the Karpathy Development Cycle with gates inspired by [The Fable
Method](https://github.com/Sahir619/fable-method). It is designed to make the
following evidence explicit before a task is considered complete:

- what problem is being solved;
- which assumptions and alternatives were considered;
- whether the change is minimal and in scope;
- whether code, tests, and specification agree;
- whether lint, tests, coverage, and the success criterion pass; and
- whether the final report contains the required evidence.

The normal flow is:

```text
FIT -> THINK -> SIMPLIFY -> INTENT -> SURGICAL -> VERIFY -> ARTIFACT -> REPORT
                                                                            |
                                                                       JUDGE (optional)
```

Kata is the tool itself, not a framework that must be embedded in the project
being changed. It stores task evidence in `.kata/` at the target project's
root.

## Architecture

```text
src/kata/
├── cli.py       CLI, task persistence, cycle orchestration, and reports
├── fit.py       Diff measurement and triviality gate
├── verify.py    Ruff, pytest, coverage, and pattern search
├── judge.py     Adversarial verification and fraud detection
├── __init__.py  Package version
└── __main__.py python -m kata entry point

opencode/
├── agent/kata.md                 OpenCode @kata agent definition
└── skills/kata-*/SKILL.md        Phase-specific operating instructions

tests/                            Unit tests for the Python implementation
eval/                             Adversarial trap scenarios
scripts/install.sh                OpenCode symlink installer
```

### Module responsibilities

#### `kata.cli`

`cli.main()` parses arguments and selects one of the supported modes. The CLI
also owns task-file creation, YAML/JSON serialization, interactive prompts,
phase orchestration, report formatting, and exit codes.

#### `kata.fit`

`diff_stats()` inspects unstaged changes first and staged changes second.
`is_trivial()` returns true for at most one changed file and fewer than ten
changed lines.

#### `kata.verify`

The verification layer provides independent functions for Ruff, pytest,
coverage, and project-wide regular-expression searches. `run_all()` executes
Ruff and pytest, then runs coverage only when pytest succeeds.

#### `kata.judge`

The optional judge treats the task file as a collection of claims, compares
those claims with the Git diff, re-runs claimed checks, and searches for six
fraud categories: weakened checks, false completion, scope creep, unauthorized
actions, specification betrayal, and debris.

## Installation

### Python package

Kata requires Python 3.11 or newer. Install the package and development
dependencies with:

```bash
pip install -e '.[dev]'
```

The package exposes both entry points:

```bash
kata --version
python3 -m kata --version
```

### OpenCode agent

Install the agent and skills through symlinks:

```bash
make install
```

The installer uses `$OPENCODE_CONFIG_DIR` when set, otherwise
`~/.config/opencode`. Restart OpenCode after installation and use `@kata`.

To remove the installed symlinks:

```bash
make uninstall
```

Because the installer creates symlinks, edits to files under `opencode/` are
visible without reinstalling. Use `make reinstall` after adding new installable
agent or skill entries.

## CLI

### Modes

| Command | Description |
|---|---|
| `kata` | Select or create a task and run the complete interactive cycle |
| `kata --init TASK` | Create a task file from the default template |
| `kata --task TASK` | Resume a specific task |
| `kata --plan [--task TASK]` | Run FIT and THINK, save the plan, and stop |
| `kata --check-only` | Run Ruff, pytest, and coverage without task interaction |
| `kata --report --task TASK` | Regenerate the outcome-first report |
| `kata --judge --task TASK` | Run adversarial verification |
| `kata --version` | Print the package version |

The `--plan`, `--check-only`, `--judge`, and `--report` combinations are
validated by the CLI. In particular, `--plan` and `--check-only` cannot be
used together, and `--judge` cannot be combined with either one.

### Verification options

| Option | Default | Purpose |
|---|---|---|
| `--ruff-paths PATH ...` | `src/ tests/` | Paths passed to Ruff |
| `--test-paths PATH ...` | `tests/` | Paths passed to pytest |
| `--ignore PATH ...` | none | Paths excluded from pytest |
| `--cov-source VALUE` | `src` | Coverage source passed to pytest-cov |
| `--gate PERCENT` | `70` | Minimum coverage percentage |

Example for a project with a different layout:

```bash
kata --check-only \
  --ruff-paths app tests \
  --test-paths tests/unit \
  --cov-source app \
  --gate 80
```

### Exit codes

- `0`: the requested operation passed;
- `1`: the cycle, report status, or judge verdict failed;
- `2`: invalid CLI arguments, as produced by `argparse`.

## Development cycle

### FIT

Measures the current Git diff and classifies the task. Interactive mode offers
`code-loop`, `plan-first`, `question`, `research`, and `inference` routes. A
trivial task is at most one changed file and fewer than ten changed lines.

### THINK

Records the exact problem, assumptions, alternatives, and unknowns before
implementation. In non-interactive mode, defaults are recorded and the phase
is skipped operationally.

### SIMPLIFY

Checks that the solution is minimal, contains no single-use abstractions, and
does not add speculative configuration.

### INTENT

Compares what the code does, what the checks expect, and what the specification
says. The authority order for conflicts is:

```text
user statement > specification/README > tests > current code
```

### SURGICAL

Reviews every changed file and records whether it is necessary. It also checks
that removed imports are clean and that the diff has no unrelated scope.

### VERIFY

Runs the objective checks in this order:

1. `ruff check`;
2. pytest;
3. pytest-cov with `--cov-fail-under`;
4. the task's success criterion.

Coverage is short-circuited when pytest fails. A task is `approved` only when
all checks and the success criterion pass; otherwise it is `rejected`.

### ARTIFACT

Checks whether evidence lines are due and present:

| Line | Trigger |
|---|---|
| `INTENT` | Behavior changed |
| `AUTH` | An irreversible external action was taken |
| `PENDING` | Documentation prescribes a follow-up that was not taken |
| `TWINS` | A defect was fixed and recurring patterns should be searched |

### REPORT

Prints the outcome first, followed by the problem, changed files, verification
results, caveats, and any due artifact lines. Reports can be regenerated with
`--report` without re-running the cycle.

### JUDGE

The judge is opt-in. It re-runs claimed checks and returns:

| Verdict | Meaning |
|---|---|
| `VERIFIED` | No fraud was detected |
| `VERIFIED WITH CAVEATS` | Only medium- or low-severity findings were detected |
| `REFUTED` | At least one high-severity finding was detected |

## Task files

Task files live under `.kata/` and normally use YAML when PyYAML is installed.
The CLI falls back to JSON and changes the extension to `.json` when PyYAML is
unavailable.

Create one with:

```bash
kata --init improve-parser
```

The core schema is:

```yaml
task: improve-parser
status: draft
fit:
  trivial: false
  route: code-loop
  reason: ""
think:
  problem: ""
  assumptions: []
  alternatives: []
  unknowns: ""
  answered: false
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
intent:
  code_does: ""
  check_expects: ""
  spec_says: ""
  all_agree: true
  answered: false
surgical:
  files: []
  removed_imports_clean: true
verify:
  ruff_clean: null
  tests_pass: null
  coverage_pct: null
  coverage_pass: null
  success_criteria_met: null
auth:
  action_taken: false
  authorized: false
pending:
  action: ""
  documented: false
twins:
  searched: false
  pattern: ""
  result: ""
```

Task selection uses the current Git branch when possible. Slashes and
underscores are normalized to hyphens; for example, `feature/parser_fix`
becomes `feature-parser-fix`.

## Python API

The implementation is intentionally modular so its checks can be tested or
reused independently.

### `kata.fit`

```python
diff_stats(cwd: Path | None = None) -> tuple[list[str], int]
is_trivial(files: list[str], lines: int) -> bool
```

### `kata.verify`

```python
run_ruff(paths=None, cwd=None) -> VerifyResult
run_pytest(testpaths=None, ignore=None, cwd=None, extra_args=None) -> VerifyResult
run_coverage(source="src", testpaths=None, ignore=None, gate=70.0, cwd=None)
search_pattern(pattern, paths=None, cwd=None) -> SearchResult
run_all(ruff_paths=None, test_paths=None, ignore=None, cov_source="src", gate=70.0, cwd=None)
```

`VerifyResult` contains `ok`, captured `output`, and a `details` dictionary.
`SearchResult` contains the searched pattern, `SearchMatch` objects, and the
number of files containing matches.

### `kata.judge`

```python
collect_claims(task_data) -> list[str]
hunt_weakened_checks(diff) -> list[JudgeFraud]
hunt_false_completion(task_data, verify_results) -> list[JudgeFraud]
hunt_scope_creep(task_data, changed) -> list[JudgeFraud]
hunt_unauthorized_action(task_data) -> list[JudgeFraud]
hunt_spec_betrayal(task_data) -> list[JudgeFraud]
hunt_debris(diff, changed) -> list[JudgeFraud]
judge_task(task_data, cwd=None, ...) -> JudgeResult
```

`JudgeResult` contains the verdict, extracted claims, caveats, fraud findings,
re-executed checks, and metadata.

## OpenCode integration

The OpenCode agent definition is `opencode/agent/kata.md`. It maps each cycle
phase to a dedicated skill and defines the expected use of OpenCode tools:

- `read` and `grep` for evidence;
- `question` for decisions that require user input;
- `bash` for Git and verification commands;
- `edit` or `write` for surgical changes and task persistence.

The repository contains skills for FIT, THINK, SIMPLIFY, INTENT, SURGICAL,
VERIFY, ARTIFACT, REPORT, and JUDGE. The installer currently creates symlinks
for the four core implementation skills listed in `scripts/install.sh`:
`kata-think`, `kata-simplify`, `kata-surgical`, and `kata-verify`.

## Testing and evaluation

Run the standard checks in the recommended order:

```bash
make lint
make test
```

Other development targets are:

```bash
make format
make install
make uninstall
make clean
```

Tests mock the subprocess wrapper rather than invoking Ruff, pytest, or ripgrep
for most unit cases. This keeps the unit suite deterministic while preserving
coverage for command construction and result parsing.

Adversarial evaluation scenarios live under `eval/scenarios/`. Run them with:

```bash
python3 eval/run_traps.py
```

Each scenario contains a fixture project and a `ground_truth.yaml` describing
the verdict and frauds that the judge must find. See
[`eval/README.md`](eval/README.md) for the scenario schema.

## Compatibility and limitations

- The `.kata/<task>.yaml` schema is compatible with the `.karpathy/` schema used
  by mushin. A symbolic link can preserve access to legacy tasks:
  `ln -s .karpathy .kata`.
- The CLI assumes Git is available for diff and branch detection. It continues
  with reduced task detection when branch lookup fails.
- In non-interactive mode, FIT, THINK, SIMPLIFY, INTENT, and SURGICAL use
  defaults; `--check-only` is the intended CI entry point.
- Coverage percentage extraction expects a standard pytest-cov `TOTAL` line.
  If it cannot parse that line, the reported percentage is `0.0`.
- The current installer does not symlink every skill directory. If an OpenCode
  environment needs the ARTIFACT, REPORT, FIT, INTENT, or JUDGE skills directly,
  install those links explicitly or extend `scripts/install.sh`.

## License

Kata is released under the MIT License.
