# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Kata (型) is the tool itself, not a project where kata is applied. It implements the cycle
`FIT → THINK → SIMPLIFY → INTENT → SURGICAL → VERIFY → TWIN CHECK → ARTIFACT → REPORT`
(+ optional `JUDGE`, and `--audit` grades task phases as followed / skipped / faked),
combining the Karpathy Development Cycle with fit-gate/verification-gate ideas from
[The Fable Method](https://github.com/Sahir619/fable-method).

Two frontends share one Python backend:
- **OpenCode**: `@kata` agent (`opencode/agent/kata.md`) backed by 10 phase skills (`opencode/skills/kata-*/`).
- **Claude Code**: `kata` orchestrator skill (`claude-code/skills/kata/SKILL.md`) backed by the same
  10 phase skills ported 1:1 (`claude-code/skills/kata-*/`). No subagent — the cycle is interactive
  (asks a question at nearly every phase), so it runs in the main conversation.

Only the orchestration layer differs between frontends; Ruff/pytest/coverage/judge logic always runs
through the `kata` Python package (`src/kata/`).

Full technical reference: [`DOCUMENTATION.md`](DOCUMENTATION.md). Agent-authoring conventions
(this file overlaps with, but is not identical to): [`AGENTS.md`](AGENTS.md).

## Commands

```bash
make lint && make test        # recommended order before committing
make lint                     # ruff check src/ tests/
make format                   # ruff format src/ tests/
make test                     # pytest tests/ -v --cov=kata --cov-report=term-missing (gate 70%)

python3 -m pytest tests/test_verify.py::TestRunRuff -v   # run a single test

make install                  # symlink @kata agent + skills into ~/.config/opencode/
make uninstall
make reinstall                # after adding NEW skill/agent files (edits alone don't need this)
make install-claude-code      # symlink kata skills into ~/.claude/
make uninstall-claude-code

python3 eval/run_traps.py     # adversarial JUDGE trap scenarios (eval/scenarios/)
```

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
├── fit.py       diff_stats() / is_trivial() — the fit gate
├── verify.py    run_ruff / run_pytest / run_coverage / search_pattern / run_all()
├── judge.py     collect_claims() + six hunt_*() fraud detectors + judge_task()
├── __init__.py  package version
└── __main__.py  python -m kata entry point (excluded from coverage)
```

- `fit.py`: `diff_stats()` inspects unstaged changes first, then staged. `is_trivial()` is true for
  at most 1 changed file and <10 changed lines — this is the triviality gate that lets a task skip
  straight to VERIFY.
- `verify.py`: independent functions per tool; `run_all()` runs Ruff + pytest, then coverage only if
  pytest passed (short-circuits on failure). Tests mock `kata.verify._run` (the subprocess wrapper) —
  never invoke real ruff/pytest inside the unit suite.
- `judge.py`: treats a task's `.kata/<task>.yaml` as a set of claims, diffs them against Git reality,
  re-runs claimed checks, and hunts six fraud categories: weakened checks, false completion, scope
  creep, unauthorized action, spec betrayal, debris. Verdicts: `VERIFIED`, `VERIFIED WITH CAVEATS`
  (medium/low findings only), `UNVERIFIABLE` (no fraud, but nothing could be
  observed — nothing re-run, or tests in a language it has no patterns for),
  `REFUTED` (any high-severity finding).
- Task files live in `.kata/<task>.yaml` at the *target* project's root (not this repo's own root,
  except when kata is being used on itself). Schema is compatible with mushin's `.karpathy/`
  (`ln -s .karpathy .kata` to migrate).
- Exit codes: `0` pass, `1` cycle/report/judge failure or audit fakes/skips, `2` invalid CLI args (argparse).

### Adding or changing a phase skill

A phase exists in triplicate and all three must stay in sync when its behavior changes:
`opencode/skills/kata-<phase>/SKILL.md`, `claude-code/skills/kata-<phase>/SKILL.md`, and — for
phases with objective logic (FIT, VERIFY, JUDGE) — the corresponding function in `src/kata/*.py`.

## Conventions (from AGENTS.md)

- `from __future__ import annotations` at the top of every module.
- Docstrings/comments in Portuguese (BR); identifiers (code) in English.
- Type hints on all functions; imports ordered stdlib → third-party → local, alphabetical per group.
- `snake_case` functions/variables, `PascalCase` classes.
- No `print()` in library code — only in direct CLI output. Use `logging` or `rich.console.Console`.
- Ruff: `line-length=100`, `target-version=py311`, rules `E/F/W/I/UP/B`.
- Coverage: `pyproject.toml` omits only `__main__.py` — `cli.py` is measured. Gate is `fail_under = 70`.
