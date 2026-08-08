# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Kata (型) is the tool itself, not a project where kata is applied. It implements the cycle
`FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT`
(+ optional `JUDGE`, and `--audit` grades task phases as followed / skipped / faked / degraded),
combining the Karpathy Development Cycle with fit-gate/verification-gate ideas from
[The Fable Method](https://github.com/Sahir619/fable-method).

Two frontends share one Python backend, and both are **generated from a single source in
`phases/`** (11 files: 10 phases + the orchestrator), plus optional domain adapters from `domains/`
(currently `kata-devops`):
- **OpenCode**: `@kata` agent (`opencode/agent/kata.md`) backed by 10 phase skills + the
  `kata-devops` adapter (`opencode/skills/kata-*/`).
- **Claude Code**: `kata` orchestrator skill (`claude-code/skills/kata/SKILL.md`) backed by the same
  10 phase skills + the `kata-devops` adapter (`claude-code/skills/kata-*/`). No subagent — the cycle
  is interactive (asks a question at nearly every phase), so it runs in the main conversation.

Only the orchestration layer differs between frontends; Ruff/pytest/coverage/judge logic always runs
through the `kata` Python package (`src/kata/`).

Full technical reference: [`DOCUMENTATION.md`](DOCUMENTATION.md). Agent-authoring conventions
(this file overlaps with, but is not identical to): [`AGENTS.md`](AGENTS.md).

## Commands

```bash
pip install -e '.[dev]'       # do this first — the suite imports `kata`, and without the
                              # editable install every test file errors with
                              # ModuleNotFoundError before a single assertion runs

make lint && make test        # recommended order before committing
make build-skills             # regenerate opencode/ + claude-code/ from phases/
make check-skills             # fail if the generated files are stale
make lint                     # ruff check src/ tests/ eval/ scripts/
make format                   # ruff format src/ tests/ eval/ scripts/
make format-check             # CI runs this; `ruff check` does not catch format drift
make test                     # pytest tests/ -v --cov=kata --cov=build_skills --cov=run_traps (gate 70%)

python3 -m pytest tests/test_verify.py::TestRunRuff -v      # a single class
python3 -m pytest tests/test_judge.py -k escrituracao -v    # by name fragment

make install                  # symlink @kata agent + skills into ~/.config/opencode/
make uninstall
make reinstall                # after adding NEW skill/agent files (edits alone don't need this)
make install-claude-code      # symlink kata skills into ~/.claude/
make uninstall-claude-code

python3 -m kata --doctor      # are the phase skills installed? (partial install exits 1;
                              # missing domain adapters are optional warnings)
python3 eval/run_traps.py     # adversarial JUDGE trap scenarios (eval/scenarios/)
```

CI (`.github/workflows/ci.yml`, Python 3.11 + 3.12) runs `make lint`, `make format-check`,
`make check-skills`, `make test` and the trap runner — all five must pass. The traps are the
one gate `make test` does not cover: `run_traps.py` shells out to `python3 -m kata` with
`cwd` set to a temp fixture, so a *relative* `PYTHONPATH=src` silently stops resolving there
and all scenarios fail with "No module named kata". Install the package instead.

Installers use symlinks (`$OPENCODE_CONFIG_DIR` / `$CLAUDE_CONFIG_DIR`, defaulting to
`~/.config/opencode` / `~/.claude`), so editing files under `opencode/` or `claude-code/` is visible
immediately without reinstalling — `make reinstall` is only needed for newly added installable files.

The `kata` CLI itself (this tool applied to *other* projects) is invoked as `kata` / `python -m kata`;
see [`DOCUMENTATION.md`](DOCUMENTATION.md#cli) for its modes (`--init`, `--plan`, `--check-only`,
`--judge`, `--report`, `--audit`) and verification flags (`--ruff-paths`, `--test-paths`, `--cov-source`, `--gate`).

## Architecture

```
src/kata/
├── cli.py       CLI, task persistence (.kata/*.yaml), cycle orchestration, reports
├── config.py    .kata/config.yaml — the target project's own lint/test/coverage commands
├── skills.py    PHASE_SKILLS + per-frontend install check (the --doctor preflight)
├── fit.py       diff_stats() / is_trivial() — the fit gate
├── verify.py    run_ruff / run_pytest / run_coverage / run_command / search_pattern / run_all()
├── judge.py     collect_claims() + the fraud hunters (six hunt_*() plus
│                baseline tampering inside judge_task()) + judge_task()
├── __init__.py  package version
└── __main__.py  python -m kata entry point (excluded from coverage)
```

- `fit.py`: `diff_stats()` diffs against `HEAD` first (staged and unstaged in
  one pass), falling back to unstaged, then staged, in a repository without
  commits. `is_trivial()` is true for at most 1 changed file and <10 changed
  lines — this is the triviality gate that lets a task skip straight to VERIFY.
- `config.py`: reads `.kata/config.yaml` in the *target* project — `verify.lint` / `verify.test` /
  `verify.coverage` (string or list), plus `coverage_pattern` and `gate`. A declared role is run
  verbatim; an omitted one falls back to the Python default. Invalid config raises `ConfigError` and
  the CLI exits 1 rather than silently checking something the project never asked for.
- `verify.py`: independent functions per role; `run_all()` runs lint + test, then coverage only if
  the test step passed (short-circuits on failure). `run_command()` executes a declared command and
  judges it by exit code; `run_command_coverage()` extracts the percentage and applies the gate here,
  because `--cov-fail-under` does not exist outside Python. Tests mock `kata.verify._run` (the
  subprocess wrapper) — never invoke real ruff/pytest inside the unit suite.
- `judge.py`: treats a task's `.kata/<task>.yaml` as a set of claims, diffs them against Git reality,
  re-runs claimed checks, and hunts seven fraud categories: weakened checks, false completion, scope
  creep, unauthorized action, spec betrayal, debris, and baseline tampering (the YAML's `base_commit`
  diverging from the Git anchor recorded at task start). Weakening patterns are per-language
  (`_LANGUAGES`: Python, JS/TS, Go, Ruby, Rust, Java/Kotlin); a test in an unlisted language becomes a
  declared blind spot instead of silence. Verdicts: `VERIFIED`, `VERIFIED WITH CAVEATS`
  (medium/low findings only), `UNVERIFIABLE` (no fraud, but nothing could be
  observed — one of six blind spots), `REFUTED` (any high-severity finding).
  Two rules are easy to break by accident:
  - **Kata's own bookkeeping is not the task's work.** `is_kata_bookkeeping()` keeps
    `.kata/*.{yaml,yml,json}` out of the changed-file set and the synthetic untracked diff.
    Counting it made the judge accuse honest work of scope creep — up to `REFUTED` past two
    files — because nothing asks a project to gitignore `.kata/`. The filter is by extension,
    not by directory, so source code kept under `.kata/` stays visible.
  - **A malformed task file must still produce a verdict.** Hand-written YAML is supported and
    nothing validates a schema before judging, so `_normaliza_task()` coerces `verify` /
    `surgical` / `intent` / `artifact`, a non-map top level, and non-map `surgical.files`
    entries into blind spots. Never reach into those sections with a bare `.get()`: a traceback
    exits 1, the same code as `REFUTED`, which makes a broken file look like fraud found.
- Task files live in `.kata/<task>.yaml` at the *target* project's root (not this repo's own root,
  except when kata is being used on itself). Schema is compatible with mushin's `.karpathy/`
  (`ln -s .karpathy .kata` to migrate).
- `skills.py`: `PHASE_SKILLS` is the canonical list the cycle needs. `--doctor` checks each frontend's
  config dir; a **partial** install exits 1 (a missing skill makes the orchestrator improvise the phase),
  an absent one does not. A phase run without its skill is recorded in `preflight.skills_missing` and
  graded `degraded` by `--audit`.
- Exit codes: `0` pass, `1` cycle/report/judge failure, audit fakes/skips/degraded, or a partial install
  found by `--doctor`; `2` invalid CLI args (argparse).

### Adding or changing a phase skill

**Edit `phases/kata-<phase>.md` — never the files under `opencode/` or `claude-code/`.** Those are
generated by `scripts/build_skills.py`; run `make build-skills` and commit the result.
`tests/test_skills_build.py` fails if they drift.

In the source, `{{RUN}}` / `{{READ}}` / `{{ASK}}` / `{{LOAD_PHASE}}` … expand to how the host names
each **role** in `REQUIRED_ROLES` (an undeclared variable is a build error). Conditional content uses
`<!--if:CAP-->` / `<!--ifnot:CAP-->` for host **capabilities** — prefer these — and
`<!--only:FRONTEND-->` only for genuine identity (frontmatter, title, invocation prefix).
`validate_frontends()` rejects a frontend that misses a role, declares one outside the contract, or
names an unknown capability.

Watch out for `question`: the **route** `question` is a `fit.route` value and reads the same in both
frontends; only the *asking tool* becomes `{{ASK}}`.

Phases with objective logic (FIT, VERIFY, JUDGE) also live in `src/kata/*.py` — a behaviour change
there must accompany the source.

## Review rounds and the `Rn-m` markers

Comments across `src/`, `scripts/`, `eval/` and `phases/` cite findings like `R10-8` or
`R11-3` — finding *m* of review round *n*. They are the reason a guard exists, and they are
load-bearing: most of the odd-looking specificity in the fraud patterns is a false positive
some round reproduced. Read the marker before "simplifying" the code around it.

Rounds come in pairs of task files under `.kata/`, which is gitignored at the repo root
(`/.kata/`, anchored so `eval/scenarios/*/fixture/.kata/` stays tracked as fixture data):

- `code-review-round-N.yaml` — diagnosis only, `fit.route: question`, no code changes. Findings
  go in `question.findings`, each tagged `RN-m`, with severity and a reproduction.
- `fix-round-N.yaml` — the `code-loop` task that implements them.

Two habits that round 11 showed matter:

- **Reproduce before reporting.** A finding carries `[R]` (executed) or `[E]` (static). A
  hypothesis that did not reproduce is written down as a verified false alarm so the next
  round does not reopen it.
- **Prove a new test fails without its fix.** `eval/README.md` requires it for scenarios, and
  it applies to unit tests too: revert the fix, watch the test go red, restore. The suite is
  full of guards against *false positives*, and a test that passes in both states protects
  nothing.

## Testing conventions

- Unit tests mock `kata.verify._run` — never invoke real ruff/pytest inside the suite.
- Tests needing a real repository use the shared `repo_git` fixture (`tests/conftest.py`),
  not a private `git init` helper.
- `tests/test_skills_build.py` guards the generated frontends: it fails on drift from
  `phases/` and on an installable skill with no source (`make check-skills` catches only the
  first).
- Eval scenarios live in `eval/scenarios/<name>/` with `fixture/` (exactly one task YAML in
  `.kata/`) and `ground_truth.yaml`. The harness git-excludes `.kata/` by default; a scenario
  that needs the real environment — where the task file is visible to Git — sets
  `kata_visivel: true`. An optional `baseline/` gives the scenario a modification diff and a
  `base_commit`.

## Conventions (from AGENTS.md)

- `from __future__ import annotations` at the top of every module.
- Docstrings/comments in Portuguese (BR); identifiers (code) in English.
- Type hints on all functions; imports ordered stdlib → third-party → local, alphabetical per group.
- `snake_case` functions/variables, `PascalCase` classes.
- No `print()` in library code — only in direct CLI output. Use `logging` or `rich.console.Console`.
- Ruff: `line-length=100`, `target-version=py311`, rules `E/F/W/I/UP/B`.
- Coverage: `pyproject.toml` omits only `tests/*` and `__main__.py` — `cli.py` is measured, and
  `source` includes `build_skills`/`run_traps` so a regression in the skill builder or the trap
  harness drops the gate. Gate is `fail_under = 70`.
