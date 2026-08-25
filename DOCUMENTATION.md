# Kata Documentation

Technical reference for Kata (型): a Python CLI, an OpenCode agent, and a set
of Claude Code skills that all guide software changes through the same
disciplined development cycle.

## Contents

- [Overview](#overview)
- [Specific uses](#specific-uses)
- [Architecture](#architecture)
- [Installation](#installation)
- [CLI](#cli)
  - [Project configuration](#project-configuration)
- [Development cycle](#development-cycle)
- [Task files](#task-files)
- [Python API](#python-api)
- [OpenCode integration](#opencode-integration)
- [Claude Code integration](#claude-code-integration)
- [Testing and evaluation](#testing-and-evaluation)
- [Editing the prompts](#editing-the-prompts)
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
FIT -> THINK -> SIMPLIFY -> INTENT -> SURGICAL -> VERIFY -> TWIN CHECK -> ARTIFACT -> REPORT
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

## Specific uses

Kata is a quality gate for software changes, not a project template. It fits
the following situations:

- **Before committing**: run the full cycle to force evidence for the change —
  problem, assumptions, minimality, intent agreement, and passing lint, tests,
  and coverage — instead of committing on a "it works" impression.
- **Bug fixes**: the cycle is adversarial about defects. INTENT catches
  code/test/specification conflicts, and TWIN CHECK searches the project for
  the same defect pattern elsewhere, recording even a negative result.
- **Small code-loop tasks**: the FIT gate measures the diff and routes trivial
  changes (one file, fewer than ten lines) directly, without planning ceremony.
- **Planning before implementation**: `kata --plan` runs FIT and THINK, saves
  the plan with assumptions and unknowns, and stops — the plan can be reviewed
  or handed off before a single line changes.
- **Documentation-only changes**: docs-only tasks are recognized and are not
  asked the INTENT question, keeping the gate silent where no behavior changed.
- **Adversarial verification of finished work**: `kata --judge` re-runs every
  claimed check and hunts seven fraud categories (weakened checks, false
  completion, scope creep, unauthorized actions, specification betrayal,
  debris, and baseline tampering — the YAML's `base_commit` diverging from the
  Git anchor recorded when the task started) before a merge or hand-over.
- **Auditing tasks after the fact**: `kata --audit` grades each phase of a
  completed task as followed, skipped, or faked, and names the concrete risk
  each skip or fake created — useful for review queues and hand-overs.
- **Continuous integration**: `kata --check-only` runs Ruff, pytest, and
  coverage with the coverage gate, non-interactively, as a CI entry point.
- **Unsticking a fix-verify loop**: after 3 failed verification attempts the
  task is handed back to the user with what was tried, the real output, and
  the current hypothesis, instead of looping forever.
- **Migrating legacy mushin tasks**: `.kata/` is schema-compatible with
  `.karpathy/`, so existing tasks keep working through a symbolic link.

## Architecture

```text
src/kata/
├── cli.py       CLI, task persistence, cycle orchestration, and reports
├── config.py    `.kata/config.yaml` — the target project's own check commands
├── skills.py    Which phase skills the cycle needs, and whether they are installed
├── fit.py       Diff measurement and triviality gate
├── verify.py    Lint, test, coverage, and pattern search
├── judge.py     Adversarial verification and fraud detection
├── __init__.py  Package version
└── __main__.py python -m kata entry point

phases/                           SINGLE SOURCE for every frontend prompt
├── kata.md                       The orchestrator
└── kata-*.md                     The 10 phase skills (9 phases + JUDGE + QUESTION)

opencode/                         GENERATED — do not edit by hand
├── agent/kata.md                 OpenCode @kata agent definition
└── skills/kata-*/SKILL.md        Phase-specific operating instructions

claude-code/                      GENERATED — do not edit by hand
└── skills/kata-*/SKILL.md        kata orchestrator skill + the same 10
                                   phase-specific skills + the kata-devops
                                   domain adapter

tests/                            Unit tests for the Python implementation
eval/                             Adversarial trap scenarios
scripts/build_skills.py           Renders phases/ into both frontends
scripts/install.sh                OpenCode symlink installer
scripts/install-claude-code.sh    Claude Code symlink installer
```

### Module responsibilities

#### `kata.cli`

`cli.main()` parses arguments and selects one of the supported modes. The CLI
also owns task-file creation, YAML/JSON serialization, interactive prompts,
phase orchestration, report formatting, and exit codes.

#### `kata.fit`

`diff_stats()` diffs against `HEAD` first (staged and unstaged in one pass),
falling back to unstaged, then staged, in a repository without commits.
`is_trivial()` returns true for at most one changed file and fewer than ten
changed lines.

#### `kata.verify`

The verification layer provides independent functions for Ruff, pytest,
coverage, and project-wide regular-expression searches. `run_all()` executes
Ruff and pytest, then runs coverage only when pytest succeeds.

#### `kata.judge`

The optional judge treats the task file as a collection of claims, compares
those claims with the Git diff, re-runs claimed checks, and searches for seven
fraud categories: weakened checks, false completion, scope creep, unauthorized
actions, specification betrayal, debris, and baseline tampering.

Kata's own bookkeeping (`.kata/*.yaml`, `.kata/config.yaml`) is excluded from
the changed-file set: the tool creates those files, the task's author does not,
and counting them accused honest work of scope creep — up to `REFUTED` past two
files, since `--init` touches no `.gitignore` and nothing asks a project to
ignore `.kata/`. The exclusion is by extension, not by directory, so source
code someone keeps under `.kata/` stays visible to the judge.

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

To run or install the CLI without touching the current environment, use
`pipx` or `uv` (both isolate the package and its bin in their own venv;
no editable install needed):

```bash
# One-off run — nothing installed permanently (CI/headless friendly)
pipx run --spec . kata --version
uv tool run --from . kata --version

# Permanent install — creates a `kata` bin on the runner's PATH
pipx install .
uv tool install . --force
```

All routes share the same `kata.cli:main` entry point from
`pyproject.toml`; `pip`, `pipx` and `uv` only deliver the binary
differently.

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

Install the `kata` skill, its 10 phase skills, and the `kata-devops` domain
adapter into Claude Code, also through symlinks:

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
| `kata --init TASK` | Create a task file and run FIT + THINK (interactive in a terminal, defaults headless) |
| `kata --task TASK` | Resume a specific task |
| `kata --plan [--task TASK]` | Run FIT and THINK, save the plan, and stop |
| `kata --check-only` | Run Ruff, pytest, and coverage without task interaction |
| `kata --report --task TASK` | Regenerate the outcome-first report |
| `kata --judge --task TASK` | Run adversarial verification |
| `kata --audit [--task TASK]` | Grade the task phases as followed / skipped / faked / degraded, with the concrete risk of each (fable-method audit) |
| `kata --doctor` | Check whether the phase skills are installed in each frontend (missing domain adapters are optional warnings) |
| `kata --version` | Print the package version |

The `--plan`, `--check-only`, `--judge`, `--report`, and `--audit`
combinations are validated by the CLI. In particular, `--plan` and
`--check-only` cannot be used together, `--judge` cannot be combined with
either one, and `--audit` is mutually exclusive with `--init`, `--plan`,
`--check-only`, `--judge`, and `--report`.

### Verification options

| Option | Default | Purpose |
|---|---|---|
| `--ruff-paths PATH ...` | `src/ tests/` | Paths passed to Ruff |
| `--test-paths PATH ...` | `tests/` | Paths passed to pytest |
| `--ignore PATH ...` | none | Paths excluded from pytest |
| `--cov-source VALUE` | auto-detected | Coverage source passed to pytest-cov: read from `[tool.coverage.run] source` in `pyproject.toml`, falling back to `src` |
| `--gate PERCENT` | `verify.gate`, else `70` | Minimum coverage percentage |

These flags configure the **built-in Python defaults**. A role declared in
`.kata/config.yaml` is run verbatim, so the path flags for that role no
longer apply — see [Project configuration](#project-configuration).

Example for a project with a different layout:

```bash
kata --check-only \
  --ruff-paths app tests \
  --test-paths tests/unit \
  --cov-source app \
  --gate 80
```

### Project configuration

Kata does not assume the project it verifies is a Python project. Whoever knows
how to check a repository is the repository, so the commands live in
`.kata/config.yaml` (or `.kata/config.json` where PyYAML is unavailable), next
to the task files:

```yaml
verify:
  lint: npx eslint src tests
  test: npx vitest run
  coverage: npx vitest run --coverage
  coverage_pattern: 'All files\s+\|\s+([\d.]+)'
  gate: 80
```

| Key | Meaning |
|---|---|
| `lint` / `test` / `coverage` | Command for that role, as a string (split the way a shell would) or an already-split list |
| `coverage_pattern` | Regex whose first group is the coverage percentage. Default reads the `TOTAL` line pytest-cov prints |
| `gate` | Minimum coverage percentage. A `--gate` flag overrides it |

Every key is optional. A role that is not declared falls back to the Python
default for that role (`ruff` / `pytest` / `pytest-cov`) and keeps obeying the
path flags, so a project can replace only its linter and keep pytest. With no
file at all, behaviour is identical to before the option existed.

A declared role is run verbatim and judged by its exit code, the one contract
every lint and test tool honours. Coverage is the exception: the built-in path
delegates the gate to `--cov-fail-under`, which does not exist outside Python,
so a declared coverage command has its percentage extracted with
`coverage_pattern` and compared here. **If the pattern matches nothing, the
check fails** rather than recording 0.0% as a pass — "could not measure" is not
"measured and passed".

A config file that exists but is invalid **aborts with exit code 1**. Falling
back to ruff silently would report the success of a check the project never
asked for, which is the class of lie the judge exists to hunt.

Commands are executed with a 300-second timeout, but without sandboxing. Treat
`.kata/config.yaml` as trusted project configuration. The task name `config` is
reserved for this file and cannot be used as a task name.

### Exit codes

- `0`: the requested operation passed;
- `1`: the cycle or report status failed, the audit found fakes/skips/degraded
  phases (or the audited task does not exist), the judge returned `REFUTED`,
  or `--doctor` found a partial install;
- `2`: invalid CLI arguments, as produced by `argparse`.

`VERIFIED WITH CAVEATS` and `UNVERIFIABLE` both exit `0`. The judge did verify the task and approved
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
implementation. It also records the **done criterion** (Fable Step 1): what
"ready" means and how it will be verified, declared *before* the evidence
exists. The VERIFY phase confronts this declared criterion with the final
result, and the report displays it. In non-interactive mode, defaults are
recorded and the phase is skipped operationally.

Investigation is bounded (Fable Step 5): after 2 consecutive lookups with no
result, the agent stops searching and asks the user instead of continuing to
dig.

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

1. lint;
2. test;
3. coverage against the gate;
4. the task's success criterion, confronted with the `done` criterion
   declared in THINK.

Each of the first three runs the command declared in `.kata/config.yaml` for
that role, or the Python default (`ruff check`, pytest, pytest-cov with
`--cov-fail-under`) when the role is not declared.

Coverage is short-circuited when the test step fails. A task is `approved` only when
all checks and the success criterion pass; otherwise it is `rejected`.

The phase enforces a **hard bound** (Fable Step 5): `verify.attempts` counts
how many times VERIFY ran (persisted in the task file). After 3 failed
attempts, `verify.hand_back` becomes `true` and the task is handed back to
the user with what was tried, the real output, and the current hypothesis —
instead of looping fix-verify forever.

### TWIN CHECK

Runs after VERIFY and before ARTIFACT, and only for an approved task. When a
defect has been fixed, the same pattern often exists elsewhere; the step asks
whether one was, searches the project for the pattern, and records the answer
in `twins`. Recording a negative answer is part of the point — it is what
distinguishes "no defect" from "not checked".

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

Prints the outcome first, followed by the problem, the `done` criterion
declared in THINK, changed files, verification results, caveats, and any due
artifact lines. Reports can be regenerated with `--report` without re-running
the cycle. A rejected task whose `verify.hand_back` is `true` reports the
hand-back explicitly with the number of failed attempts, instead of a generic
"rejected" that invites yet another fix-verify cycle.

### AUDIT

The audit mode (`kata --audit [--task TASK]`) grades each phase of a task as:

- **followed**: the phase has `answered: true` and real content (e.g.
  `think.problem` is not empty);
- **skipped**: the phase has `skipped: true` (documented);
- **faked**: the phase has `answered: true` but default/empty content — the
  R7-1 pattern (for SIMPLIFY/SURGICAL, `answered: true` without the content
  keys at all is equally faked) — or VERIFY claims success without
  corresponding evidence, or TWINS declares a defect without a search;
- **degraded**: `preflight.skills_missing` is not empty — one or more phases
  ran without their own skill loaded, so whatever the other grades read was
  written without those instructions.

For each skip/fake, the audit names the concrete risk it created (e.g.
"THINK faked → assumptions never declared; any solution may attack the wrong
problem"). It is the kata's equivalent of the fable-method's `/fable-method
audit`, and catches phases that were filled in without being observed.

### Preflight

The orchestrator is not self-contained: at each phase it loads the matching
skill and follows its instructions. When a skill is not installed, the call
fails, the orchestrator has no instructions for that phase, and the model
improvises from the phase name. The result is a task file with the section
filled in and nothing behind it — precisely the faked phase the audit exists
to catch, except produced by the tooling rather than by the agent, and
invisible in the output.

`kata --doctor` reports, per frontend, which of the expected skills are
present under `$OPENCODE_CONFIG_DIR/skills` and `$CLAUDE_CONFIG_DIR/skills`
(defaulting to `~/.config/opencode` and `~/.claude`). A broken symlink does
not count as installed, because `exists()` follows the link and so does the
host when it tries to load the skill.

**A partial install is what fails, not an absent one.** Exit code `1` is
reserved for a frontend that has some skills but not all: someone who never
installed a frontend loses nothing, while someone with 9 of the 10 phase skills
runs the whole cycle and silently loses a phase. With no frontend installed
at all, `--doctor` says so and exits `0` — the `kata` CLI works without any.

Domain adapters are optional and never fail `--doctor`: a missing `kata-devops`
is reported as a hint (installable with `make reinstall` /
`make reinstall-claude-code`) because a `coding` task does not need it.

When a skill fails to load mid-cycle, the orchestrator is instructed not to
improvise: it falls back to a per-phase minimum contract documented in the
orchestrator itself, records the skill name in `preflight.skills_missing`,
and discloses it in the report. VERIFY and JUDGE degrade best, because their
logic lives in the Python package rather than in the skill text.

### JUDGE

The judge is opt-in. It re-runs claimed checks and returns:

| Verdict | Meaning |
|---|---|
| `VERIFIED` | No fraud was detected, and the judge was able to look |
| `VERIFIED WITH CAVEATS` | Only medium- or low-severity findings were detected |
| `UNVERIFIABLE` | No fraud, but the judge could observe nothing (see blind spots) |
| `REFUTED` | At least one high-severity finding was detected |

A **blind spot** is the judge admitting what it could not observe — not an
accusation, since not having looked is evidence of neither fraud nor honesty.
Six are detected: the report claims no check the judge knows how to re-run,
the diff touches a test file in a language the judge has no probes for, an
ignored source/test candidate is outside Git's diff, a `base_commit` declared
in the YAML has no independent `refs/kata/base/<hash>` anchor, a baseline
no longer resolves in the repository history, or a section of the task file
is not a map (`surgical: true` in hand-written YAML, or a list at the top of
the file). A baseline that resolves but is not an ancestor of the current
`HEAD` is a high-severity `baseline_tampering` finding rather than a blind
spot.

Hand-written task files are supported input and the CLI validates no schema
before judging, so an unreadable section is confessed and the verdict still
comes out. It used to be an `AttributeError`, and a traceback exits 1 — the
same code as `REFUTED` — which made a malformed file indistinguishable from
fraud found for anything reading the exit code.

The first blind spot is disarmed by declaring the project's commands in
`.kata/config.yaml`. The second knows Python, JS/TS, Go, Ruby, Rust,
Java/Kotlin, C#, PHP and Swift; a
`.exs` test is still confessed rather than passed over
in silence. With no fraud at all, any blind spot yields `UNVERIFIABLE`
instead of `VERIFIED`: "I could not look" must never be reported as "all
clear". With fraud present, the fraud decides the verdict and the blind
spots are still listed.

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
schema_version: 1    # CR-014/S5: version of the task-file schema. --init
                     # writes it; readers tolerate absence (legacy files
                     # are treated as version 1). Bump when a mandatory
                     # change lands, and fail loudly instead of .get().
task: improve-parser
status: draft
domain: coding    # coding | devops | data-analysis | research | docs
                  # default is coding; other domains load a domain adapter
done: ""    # Fable Step 1: done criterion declared in THINK, before the
            # evidence; VERIFY confronts it and the report displays it
base_commit: ""    # HEAD captured when the task started; lets JUDGE diff
                    # against it even after the task has been committed.
                    # The CLI also stores an independent Git ref anchor.
approved_commit: ""  # R14: HEAD at the moment of approval. JUDGE diffs
                    # base_commit..approved_commit instead of base_commit..HEAD,
                    # so files changed by LATER tasks don't count as
                    # "undeclared" for this one. Absent in legacy tasks
                    # (approved before this round) — they keep diffing to HEAD.
                    #
                    # P-1 (0.6.0): legacy tasks WITHOUT approved_commit are
                    # expected to come back REFUTED for structural scope
                    # creep when later tasks touched undeclared files — the
                    # judge diffs base_commit..HEAD and has no way to know
                    # where the task ended. This is a documented limitation,
                    # not a regression: re-approving a legacy task (running
                    # VERIFY again) records approved_commit and restores
                    # VERIFIED.
fit:
  trivial: false
  route: code-loop
  reason: ""
  answered: false
  skipped: false
think:
  problem: ""
  assumptions: []
  alternatives: []
  unknowns: ""
  answered: false
  skipped: false      # filled with defaults, nobody answered
simplify:
  minimum_code: true
  no_single_use_abstractions: true
  no_speculative_config: true
  notes: ""             # optional SIMPLIFY observations (only when filled)
  answered: false       # true when the phase was completed; false when it was
                        # filled with defaults because nobody answered
  skipped: false        # true only in non-interactive mode
intent:
  code_does: ""
  check_expects: ""
  spec_says: ""
  all_agree: true
  conflict_resolution: ""  # how the code/test/spec conflict was resolved
                        # (only when all_agree is false)
  answered: false
  skipped: false
surgical:
  files: []
  removed_imports_clean: true
  answered: false       # same convention as simplify
  skipped: false        # true only in non-interactive mode
verify:
  ruff_clean: null
  tests_pass: null
  coverage_pct: null
  coverage_pass: null
  success_criteria_met: null
  attempts: 0          # Fable Step 5: VERIFY run counter; after 3 failed
                       # attempts the task is handed back
  hand_back: false     # true after 3 failed attempts — task handed back to
                       # the user with what was tried, the real output, and
                       # the current hypothesis
auth:
  action_taken: false
  authorized: false
  action: ""
  quote: ""           # without it the AUTH line is never emitted
pending:
  action: ""
  documented: false
twins:
  searched: false
  pattern: ""
  result: ""
  defect_fixed: false   # the signal the TWINS gate reads
  matches_count: 0
  files_count: 0
  fix_applied: false
preflight:
  skills_missing: []    # phase skills that failed to load in this run;
                        # a phase run without its own instructions is
                        # degraded, not followed
artifact:
  intent_owed: false
  intent_present: false
  auth_owed: false
  auth_present: false
  pending_owed: false
  pending_present: false
  twins_owed: false
  twins_present: false
```

`twins.defect_fixed` is what the TWINS gate consults. It is written by the
TWIN CHECK step, and recording a `false` matters as much as a `true`: without
it the gate cannot tell "no defect was fixed" from "nobody checked".

Task selection uses the current Git branch when possible. Slashes and
underscores are normalized to hyphens; for example, `feature/parser_fix`
becomes `feature-parser-fix`.

## Domain Adapters

Domain adapters extend the cycle to non-coding tasks without changing the
underlying pipeline. A task declares its domain in `.kata/<task>.yaml`
(`domain: devops`, for example); the orchestrator loads the adapter via
`{{LOAD_DOMAIN}}` after FIT and applies its domain-specific evidence set and
fraud table.

Adapters are optional: a missing adapter does not fail `--doctor` or stop the
cycle, because the default domain is `coding` and most tasks do not need an
adapter. When a domain adapter is missing for a non-coding task, the
orchestrator records the skill name in `preflight.skills_missing` and falls
back to the adapter's minimal contract.

New adapters follow `domains/TEMPLATE.md` and are generated to both frontends
by `make build-skills`. Each adapter defines:

- **Domain scope**: what the adapter covers and explicitly does not cover
- **Evidence**: files and state to inspect before acting
- **Authority**: who decides correctness in the domain
- **Verify by observation**: how to confirm an action actually worked
- **Fraud table**: domain-specific frauds to hunt
- **Minimum evidence set (binding)**: checklist that must be completed before
  acting
- **FIT routes by shape**: which route each task shape should take
- **Red lines**: actions never allowed without documented human authorization

The only adapter shipped today is `kata-devops` (Docker, Docker Compose,
Terraform, Nginx, GitHub Actions, deploys and healthchecks). Adapters for
`data-analysis`, `research` and `docs` are planned.

## Python API

The implementation is intentionally modular so its checks can be tested or
reused independently.

### `kata.fit`

```python
diff_stats(cwd: Path | None = None) -> tuple[list[str], int]
untracked_stats(cwd: Path | None = None) -> tuple[list[str], int]
is_trivial(files: list[str], lines: int) -> bool
TRIVIAL_MAX_LINES: int
```

### `kata.verify`

```python
run_ruff(paths=None, cwd=None) -> VerifyResult
run_pytest(testpaths=None, ignore=None, cwd=None, extra_args=None) -> VerifyResult
run_coverage(source="src", testpaths=None, ignore=None, gate=70.0, cwd=None)
run_command(cmd: list[str], cwd=None) -> VerifyResult
run_command_coverage(cmd, pattern=DEFAULT_COVERAGE_PATTERN, gate=70.0, cwd=None)
search_pattern(pattern, paths=None, cwd=None) -> SearchResult
run_all(ruff_paths=None, test_paths=None, ignore=None, cov_source="src", gate=70.0, cwd=None, config=None)

untracked_files(cwd=None) -> list[str]
is_inspectable(path: Path) -> bool
MAX_UNTRACKED_FILE_BYTES: int
```

`untracked_files` and `is_inspectable` are shared Git helpers rather than
checks. `git diff` in any form is blind to files that never entered the index,
so both `kata.fit` and `kata.judge` need the first; the second is the single
size limit above which a file cannot be read whole. What each does when the
limit is exceeded differs on purpose: the judge skips the file and reports a
caveat, while fit counts it as exceeding the triviality threshold, because
treating "could not read" as "no lines changed" is what made the triviality
gate call a new 200-line module trivial.

`VerifyResult` contains `ok`, captured `output`, and a `details` dictionary.
`SearchResult` contains the searched pattern, `SearchMatch` objects, and the
number of files containing matches.

### `kata.config`

```python
load_verify_config(cwd=None) -> VerifyConfig
config_path(cwd=None) -> Path | None
VerifyConfig(lint, test, coverage, coverage_pattern, gate)
ConfigError
DEFAULT_COVERAGE_PATTERN: str
DEFAULT_GATE: float
```

`VerifyConfig.customizado` is true when the project declared at least one role.
`None` in a role means "not declared", which is what keeps the fallback to the
Python default distinguishable from an explicit choice.

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
caveats, fraud findings, re-executed checks, blind spots, and metadata.

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

The repository contains the same 11 phase/domain skills as the OpenCode side
(`claude-code/skills/kata-*/SKILL.md` — the 10 phase skills — 9 phases +
JUDGE + QUESTION — plus the `kata-devops`
domain adapter), plus the `kata` skill itself.
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
the verdict and the frauds the judge must find. Twelve scenarios (s01–s06,
s08–s11, s14, s18) plant a fraud the judge must catch; `s07`, `s15`, `s16`
and `s17` are entirely honest tasks that must come back `VERIFIED`, `s12`/`s13`
expect `UNVERIFIABLE` (blind spots, no fraud), and `s19` expects
`UNVERIFIABLE` for the Git-ignored code blind spot. `s06` doubles as a guard
against refusing legitimate work, planting real debris beside files whose
names merely look like debris, and `s14` plants `baseline_tampering` (the
harness rewrites `base_commit` in the YAML after recording the Git anchor).
A judge that refuses legitimate work is as broken as one that misses fraud,
and unit tests are poor at catching it, because they test what the author
thought to test. `s17` exercises `approved_commit` end to end (a later task
touches an undeclared file after the approval — it must not count as scope
creep), `s18` plants JS frauds that only the language probes can see, and
`s19` plants a Git-ignored test via the harness's local exclude.

`s15` exists because the other eighteen scenarios structurally could not
catch its defect: the harness excluded `.kata/` from Git in every fixture,
so the task's own file was invisible and the judge counting it as scope
creep survived ten review rounds — including `s07`, whose whole job is
catching false positives. A scenario now opts into the real environment
with `kata_visivel: true`.

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

## Editing the prompts

The files under `opencode/` and `claude-code/` are **generated**. Edit
`phases/<name>.md` and run `make build-skills`; committing the regenerated
files is part of the change. `tests/test_skills_build.py` fails when they are
stale, so the drift cannot pass CI unnoticed.

Each phase used to exist as two hand-maintained copies. The discipline failed:
the copies accumulated 395 divergent lines, and part of that was an improvement
applied to one frontend and forgotten in the other — the ARTIFACT phase had a
"Ferramentas" section only in Claude Code, and the OpenCode orchestrator never
received the corrected step numbering or the `base_commit` instruction. Today
93% of the source is shared and the remaining 7% is declared difference.

### The frontend contract

A frontend is defined by three things, declared in `FRONTENDS` in
`scripts/build_skills.py` and checked by `validate_frontends()`:

| Part | What it is |
|---|---|
| `roles` | How the host names each of `REQUIRED_ROLES`: `LOAD_PHASE`, `LOAD_DOMAIN`, `ASK`, `RUN`, `READ`, `WRITE`, `EDIT`, `SEARCH`, `LIST_FILES` |
| `identity` | How the frontend presents itself — its name, the invocation prefix, whether it is an agent or a skill |
| `capabilities` | What the host can do beyond the roles: `closed_choice_ask`, `task_tracker` |

They are **roles**, not tool names: `RUN` means "run a command", not "bash".
While the variable was called `BASH`, the contract read as if it were bound to
a particular shell, which is exactly what kata claims not to be.

The template language has three constructs:

| Construct | Purpose |
|---|---|
| `{{RUN}}`, `{{READ}}`, `{{ASK}}`, `{{LOAD_PHASE}}`, … | How this host names that role. An undeclared variable is a build error, never literal text |
| `<!--if:CAP-->` / `<!--ifnot:CAP-->` … | A block that depends on a host **capability**. An unknown capability is a build error — a typo here would delete the block from every frontend in silence |
| `<!--only:FRONTEND-->` … | A block for a named frontend (comma-separated). For genuine **identity** only |

**Prefer capability blocks.** Almost all conditional content in this repository
exists because the asking tool is closed-choice, not because the frontend is
called Claude Code. Writing such a block as `only:claude-code` forces a third
host of the same shape to be added to each block by hand — the duplication of
the previous section, returning through another door. `only:` is right for
frontmatter, the title, and the invocation prefix, and little else.

Rewriting shared prose into two blocks to avoid a small wording difference
re-creates by hand the drift this exists to prevent.

**`question` is a trap.** The route `question` is a `fit.route` value and is
spelled the same in every frontend; only the *asking tool* becomes `{{ASK}}`.
Confusing them makes a frontend instruct `route: AskUserQuestion`, which the CLI
does not accept. `tests/test_skills_build.py` checks this specifically.

Adding a frontend means adding one entry to `FRONTENDS`: its role vocabulary,
its identity, its capabilities, and where its files go. No phase content has to
be rewritten — `test_um_frontend_novo_e_so_uma_entrada_na_tabela` proves it by
rendering the whole tree for a host that does not exist in the repository, so a
source that had quietly coupled itself to a real frontend would fail there.

## Compatibility and limitations

- The `.kata/<task>.yaml` schema is compatible with the `.karpathy/` schema used
  by mushin. A symbolic link can preserve access to legacy tasks:
  `ln -s .karpathy .kata`.
- The CLI assumes Git is available for diff and branch detection. It continues
  with reduced task detection when branch lookup fails.
- In non-interactive mode, FIT, THINK, SIMPLIFY, INTENT, and SURGICAL use
  defaults; `--check-only` is the intended CI entry point.
- Coverage percentage extraction expects a standard pytest-cov `TOTAL` line.
  If it cannot parse that line, the check **fails** — "could not measure" is
  not "measured and passed", and reporting `0.0` as approved produced YAML
  that contradicted itself (R10-32).

## License

Kata is released under the MIT License.
