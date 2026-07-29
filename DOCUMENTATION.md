# Kata Documentation

Technical reference for Kata (型): a Python CLI, an OpenCode agent, and a set
of Claude Code skills that all guide software changes through the same
disciplined development cycle.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [CLI](#cli)
- [Development cycle](#development-cycle)
- [Task files](#task-files)
- [Python API](#python-api)
- [OpenCode integration](#opencode-integration)
- [Claude Code integration](#claude-code-integration)
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

Two frontends share the same Python backend and cycle logic:

- **OpenCode**: a single `@kata` agent (`opencode/agent/kata.md`) that
  orchestrates the cycle, backed by 10 phase-specific skills.
- **Claude Code**: a `kata` skill (`claude-code/skills/kata/SKILL.md`) that
  plays the same orchestration role, backed by the same 10 phase-specific
  skills ported to Claude Code's tool set. See
  [Claude Code integration](#claude-code-integration).

Only the orchestration/interaction layer differs between the two — the
verification and fraud-hunting logic (Ruff, pytest, coverage, judge) always
runs through the `kata` Python package.

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

claude-code/
└── skills/kata-*/SKILL.md        kata orchestrator skill + the same 10
                                   phase-specific skills, ported to Claude Code

tests/                            Unit tests for the Python implementation
eval/                             Adversarial trap scenarios
scripts/install.sh                OpenCode symlink installer
scripts/install-claude-code.sh    Claude Code symlink installer
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

On Windows, run the native PowerShell installer from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install.ps1
```

Use `-Copy` if symbolic links or junctions are unavailable, and
`-Uninstall` to remove the installed agent and skills. The PowerShell
installer also honors `OPENCODE_CONFIG_DIR` and otherwise uses
`~/.config/opencode`.

To remove the installed symlinks:

```bash
make uninstall
```

Because the installer creates symlinks, edits to files under `opencode/` are
visible without reinstalling. Use `make reinstall` after adding new installable
agent or skill entries.

### Claude Code skills

Install the `kata` skill and its 10 phase skills into Claude Code, also
through symlinks:

```bash
make install-claude-code
```

The installer uses `$CLAUDE_CONFIG_DIR` when set, otherwise `~/.claude`. Use
the `kata` skill afterward (e.g. `/kata`, or describe the task and let Claude
Code invoke it by description).

On Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-claude-code.ps1
```

Same `-Copy` / `-Uninstall` flags as the OpenCode PowerShell installer.

```bash
make uninstall-claude-code
```

Unlike the OpenCode `@kata` agent, the Claude Code version ships as skills
only — no subagent. The cycle asks a question at nearly every phase, which
fits the main conversation better than an isolated subagent that only
reports a summary at the end.

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
| `--cov-source VALUE` | auto-detected | Coverage source passed to pytest-cov: read from `[tool.coverage.run] source` in `pyproject.toml`, falling back to `src` |
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
- `1`: the cycle or report status failed, or the judge returned `REFUTED`;
- `2`: invalid CLI arguments, as produced by `argparse`.

`VERIFIED WITH CAVEATS` exits `0`. The judge did verify the task and approved
it with low- or medium-severity notes; treating that as a failure would equate
a caveat with a high-severity fraud and push callers to ignore the exit code.
Read the printed caveats to decide whether they matter for your workflow.

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

`INTENT` is due when SURGICAL declared at least one changed file that is not
documentation, so a docs-only task is not asked what its code does. `TWINS`
is due when a defect was actually declared fixed — either the intent gate
recorded a conflict, or the TWIN CHECK recorded that a defect was corrected.
Passing lint, tests and coverage is the normal state of a finished task, not
evidence that a defect was fixed; a gate that fires on every task is noise.

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

Claims are reported in two groups. Lint, tests, coverage, surgical scope and
intent alignment are confronted with the repository and listed as verified.
The success criterion is not: it is a subjective confirmation the user gives
during VERIFY, and no command reproduces it. It is listed separately as
accepted without verification, and it adds a caveat. Presenting it as
verified would be exactly the fraud the judge exists to hunt.

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
base_commit: ""    # HEAD captured when the task started; lets JUDGE diff
                    # against it even after the task has been committed
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
collect_unverifiable_claims(task_data) -> list[str]
hunt_weakened_checks(diff) -> list[JudgeFraud]
hunt_false_completion(task_data, verify_results) -> list[JudgeFraud]
hunt_scope_creep(task_data, changed) -> list[JudgeFraud]
hunt_unauthorized_action(task_data) -> list[JudgeFraud]
hunt_spec_betrayal(task_data) -> list[JudgeFraud]
hunt_debris(diff, changed) -> list[JudgeFraud]
judge_task(task_data, cwd=None, ...) -> JudgeResult
```

`JudgeResult` contains the verdict, verified claims, unverifiable claims,
caveats, fraud findings, re-executed checks, and metadata.

## OpenCode integration

The OpenCode agent definition is `opencode/agent/kata.md`. It maps each cycle
phase to a dedicated skill and defines the expected use of OpenCode tools:

- `read` and `grep` for evidence;
- `question` for decisions that require user input;
- `bash` for Git and verification commands;
- `edit` or `write` for surgical changes and task persistence.

The repository contains skills for FIT, QUESTION, THINK, SIMPLIFY, INTENT,
SURGICAL, VERIFY, ARTIFACT, REPORT, and JUDGE. `scripts/install.sh` symlinks
all 10 of them under `$CONFIG_DIR/skills/`, plus the `@kata` agent itself
under `$CONFIG_DIR/agent/`.

## Claude Code integration

The Claude Code orchestrator is `claude-code/skills/kata/SKILL.md`. It plays
the same role as the OpenCode `@kata` agent, mapped onto Claude Code's tool
set instead of OpenCode's:

- `Read` and `Grep`/`Glob` for evidence;
- free text or `AskUserQuestion` for decisions that require user input — see
  `claude-code/skills/kata-question/SKILL.md` for which one to use where,
  since Claude Code has no single dedicated free-text question tool the way
  OpenCode does;
- `Bash` for Git and verification commands;
- `Edit` or `Write` for surgical changes and task persistence.

The repository contains the same 10 phase skills as the OpenCode side
(`claude-code/skills/kata-*/SKILL.md`), plus the `kata` skill itself.
`scripts/install-claude-code.sh` symlinks every directory it finds under
`claude-code/skills/` into `$CLAUDE_CONFIG_DIR/skills/`.

The two ports carry the same procedure, not the same text. Each phase names
the tools of its own host — `question` against `AskUserQuestion`, `read`
against `Read`, `bash` against `Bash` — so the files differ by roughly one
to seventy lines depending on how much of the phase is tool-driven. When a
phase's behaviour changes, both files and, for phases with objective logic,
`src/kata/` have to change together.

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
make install-claude-code
make uninstall-claude-code
make clean
```

Tests mock the subprocess wrapper rather than invoking Ruff, pytest, or ripgrep
for most unit cases. This keeps the unit suite deterministic while preserving
coverage for command construction and result parsing.

The tests that exercise the judge against Git are a deliberate exception: they
build a real repository under `tmp_path` and invoke `git`. Blindness to
committed or untracked changes cannot be reproduced against a mock, because the
mock is precisely what would hide it.

Adversarial evaluation scenarios live under `eval/scenarios/`. Run them with:

```bash
python3 eval/run_traps.py
```

Each scenario contains a fixture project and a `ground_truth.yaml` describing
the verdict and the frauds the judge must find. Eight scenarios cover the six
fraud categories, plus two that exist to catch the opposite failure: `s06`
plants real debris beside files whose names merely look like debris, and `s07`
is an entirely honest task that must come back `VERIFIED`. A judge that
refuses legitimate work is as broken as one that misses fraud, and unit tests
are poor at catching it, because they test what the author thought to test.

See [`eval/README.md`](eval/README.md) for the scenario schema and for the
rule that a new scenario must be shown to fail when its defect is
reintroduced.

### Continuous integration

`.github/workflows/ci.yml` runs `make lint`, `make test` and the trap runner
on Python 3.11 and 3.12, for every push to `main` and every pull request. It
invokes the Makefile rather than restating the commands, so what is verified
locally and what is verified remotely cannot drift apart. The coverage gate
comes from `[tool.coverage.report] fail_under` in `pyproject.toml`, so
`make test` enforces it without the workflow having to repeat the threshold.

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

## License

Kata is released under the MIT License.
