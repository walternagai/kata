"""Testes para kata.judge — verificação adversarial (fable-judge)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kata.judge import (
    JudgeFraud,
    JudgeResult,
    LanguageProbes,
    _changed_files,
    _empty_test_bodies,
    _ignored_code_files,
    _is_test_file,
    _normaliza_task,
    _oversized_untracked,
    _run_git_diff,
    _unreadable_test_files,
    _untracked_diff,
    collect_claims,
    collect_unverifiable_claims,
    hunt_debris,
    hunt_false_completion,
    hunt_scope_creep,
    hunt_spec_betrayal,
    hunt_unauthorized_action,
    hunt_weakened_checks,
    is_debris_file,
    is_kata_bookkeeping,
    judge_task,
    probes_for,
    record_baseline_ref,
)
from kata.verify import VerifyResult, is_inspectable

# Raiz do repo — os testes de sincronia entre judge.py e o prompt da fase leem
# os dois arquivos direto da fonte (R11-2).
REPO = Path(__file__).resolve().parent.parent


class TestJudgeResult:
    """Verifica o dataclass JudgeResult."""

    def test_default_values(self) -> None:
        r = JudgeResult()
        assert r.verdict == "VERIFIED"
        assert r.claims == []
        assert r.caveats == []
        assert r.frauds == []
        assert r.re_ran_checks == {}
        assert r.details == {}

    def test_with_values(self) -> None:
        f = JudgeFraud(type="debris", severity="low", description="debug print")
        r = JudgeResult(
            verdict="REFUTED",
            claims=["ruff passou"],
            caveats=["1 fraude"],
            frauds=[f],
            re_ran_checks={"ruff": False},
            details={"changed_files": 3},
        )
        assert r.verdict == "REFUTED"
        assert "ruff passou" in r.claims
        assert r.frauds[0].type == "debris"


class TestJudgeFraud:
    """Verifica o dataclass JudgeFraud."""

    def test_default_evidence_empty(self) -> None:
        f = JudgeFraud(type="x", severity="low", description="y")
        assert f.evidence == ""

    def test_all_fields(self) -> None:
        f = JudgeFraud(
            type="scope_creep",
            severity="high",
            description="extra files",
            evidence="unexpected.py",
        )
        assert f.type == "scope_creep"
        assert f.severity == "high"
        assert f.evidence == "unexpected.py"


class TestCollectClaims:
    """Testa extração de claims do YAML da tarefa."""

    def test_no_verify_section(self) -> None:
        claims = collect_claims({})
        assert claims == []

    def test_all_claims_present(self) -> None:
        data = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "coverage_pct": 95.0,
                "success_criteria_met": True,
            },
            "surgical": {"files": [{"path": "a.py", "necessary": True}]},
            "intent": {"all_agree": True},
        }
        claims = collect_claims(data)
        assert len(claims) == 5
        assert any("ruff" in c for c in claims)
        assert any("testes" in c for c in claims)
        assert any("coverage" in c for c in claims)
        assert any("intenção" in c for c in claims)
        assert any("arquivo" in c for c in claims)
        # O critério de sucesso não é re-executável, então não entra aqui.
        assert not any("critério" in c for c in claims)
        assert collect_unverifiable_claims(data) == ["critério de sucesso satisfeito"]

    def test_unverifiable_claims_empty_when_criterion_not_met(self) -> None:
        assert collect_unverifiable_claims({"verify": {"success_criteria_met": False}}) == []
        assert collect_unverifiable_claims({}) == []

    def test_partial_claims(self) -> None:
        data = {"verify": {"ruff_clean": True}}
        claims = collect_claims(data)
        assert len(claims) == 1
        assert "ruff" in claims[0]

    def test_optional_sections_empty(self) -> None:
        data = {"verify": {"ruff_clean": True}, "surgical": {}, "intent": {}}
        claims = collect_claims(data)
        assert len(claims) == 1

    def test_coverage_with_pct_in_claim(self) -> None:
        data = {"verify": {"coverage_pass": True, "coverage_pct": 87.3}}
        claims = collect_claims(data)
        assert any("87.3" in c for c in claims)

    def test_no_coverage_pct_fallback(self) -> None:
        data = {"verify": {"coverage_pass": True}}
        claims = collect_claims(data)
        assert any("?" in c for c in claims)

    def test_surgical_no_necessary(self) -> None:
        data = {"surgical": {"files": [{"path": "x.py", "necessary": False}]}}
        claims = collect_claims(data)
        assert not any("arquivo" in c for c in claims)

    def test_intent_not_all_agree(self) -> None:
        data = {"intent": {"all_agree": False}}
        claims = collect_claims(data)
        assert not any("intenção" in c for c in claims)


class TestHuntWeakenedChecks:
    """Testa caça a verificações enfraquecidas."""

    def test_no_diff_no_frauds(self) -> None:
        frauds = hunt_weakened_checks("")
        assert frauds == []

    def test_non_test_file_ignored(self) -> None:
        diff = """
diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1 @@
-assert True
+print("ok")
"""
        frauds = hunt_weakened_checks(diff)
        assert frauds == []

    def test_assert_true_removed_from_test(self) -> None:
        diff = """
diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1 +1 @@
-def test_foo():
+def test_foo():
-    assert True
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        # Duas linhas suspeitas, dois achados: a asserção que saiu e o `pass` que
        # entrou. São observações distintas sobre a mesma mudança, cada uma com
        # sua evidência — a contagem é de linhas suspeitas, não de padrões casados.
        assert len(frauds) == 2
        assert {f.description.split(": ", 1)[1] for f in frauds} == {
            "assert True (sempre passa se True for literal)",
            "corpo de teste substituído por pass",
        }
        assert all(f.severity == "high" for f in frauds)

    def test_assert_false_removed(self) -> None:
        diff = """
diff --git a/tests/test_bar.py b/tests/test_bar.py
--- a/tests/test_bar.py
+++ b/tests/test_bar.py
@@ -1 +1 @@
-    assert False
+    assert result is None
"""
        frauds = hunt_weakened_checks(diff)
        assert any("assert False" in f.description for f in frauds)

    def test_assert_true_comparacao_real_nao_e_neutralizacao(self) -> None:
        """R10-9: `assert True == x` é asserção real — o padrão só pode casar
        a forma no-op (assert True como statement inteiro)."""
        diff = _diff_modificado(
            "tests/test_foo.py",
            "+    assert True == result.is_valid()",
        )
        assert hunt_weakened_checks(diff) == []

    def test_assert_true_noop_adicionado_e_suspeito(self) -> None:
        diff = _diff_modificado("tests/test_foo.py", "+    assert True")
        frauds = hunt_weakened_checks(diff)
        assert any("neutralizar" in f.description for f in frauds)

    def test_pytest_skip_condicional_legitimo_nao_e_fraude(self) -> None:
        """R10-8: skip condicional é uso legítimo — o padrão só acusa o skip
        como única instrução da linha."""
        diff = _diff_modificado(
            "tests/test_foo.py",
            '+    if not HAS_DEPS: pytest.skip("deps ausentes")',
        )
        assert hunt_weakened_checks(diff) == []

    def test_pytest_skip_comentado_nao_e_fraude(self) -> None:
        """Linha comentada não desativa teste nenhum."""
        diff = _diff_modificado("tests/test_foo.py", '+    # pytest.skip("flaky")')
        assert hunt_weakened_checks(diff) == []

    def test_pytest_skip_como_instrucao_unica_e_suspeito(self) -> None:
        diff = _diff_modificado("tests/test_foo.py", '+    pytest.skip("motivo")')
        frauds = hunt_weakened_checks(diff)
        assert any("pytest.skip" in f.description for f in frauds)

    def test_commented_line(self) -> None:
        diff = """
diff --git a/tests/test_baz.py b/tests/test_baz.py
--- a/tests/test_baz.py
+++ b/tests/test_baz.py
@@ -1 +1 @@
-    assert result == 42
+#    assert result == 42
"""
        frauds = hunt_weakened_checks(diff)
        assert any("comentário" in f.description for f in frauds)

    def test_pass_replaces_body(self) -> None:
        diff = """
diff --git a/tests/test_qux.py b/tests/test_qux.py
--- a/tests/test_qux.py
+++ b/tests/test_qux.py
@@ -1 +1 @@
-    assert result == expected
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        assert any("pass" in f.description for f in frauds)

    def test_noqa_added(self) -> None:
        diff = """
diff --git a/tests/test_noqa.py b/tests/test_noqa.py
--- a/tests/test_noqa.py
+++ b/tests/test_noqa.py
@@ -1 +1 @@
+import os  # noqa: F401
"""
        frauds = hunt_weakened_checks(diff)
        assert any("noqa" in f.description for f in frauds)

    def test_one_fraud_per_line_when_two_patterns_match(self) -> None:
        """Uma linha que casa dois padrões (comentário + noqa) conta uma vez.

        Antes, cada padrão casado emitia uma fraude e o par comentário+noqa
        virava 2 fraudes para 1 mudança — inflando o caveat "N fraude(s) de
        alta severidade". A contagem mede linhas suspeitas, não padrões
        casados: o mesmo princípio do H1 para debris.

        A linha é montada por concatenação de propósito: o judge varre o diff
        da própria tarefa e acusaria "noqa adicionado" se o texto completo
        estivesse literal no arquivo de teste.
        """
        linha_suspeita = "#    assert result == 42  #" + " noqa: E501"
        diff = f"""
diff --git a/tests/test_comentada.py b/tests/test_comentada.py
--- a/tests/test_comentada.py
+++ b/tests/test_comentada.py
@@ -1 +1 @@
-    assert result == 42
+{linha_suspeita}
"""
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        # O padrão mais específico vence: a linha virou comentário.
        assert "comentário" in frauds[0].description
        assert "noqa" not in frauds[0].description

    def test_multiple_frauds(self) -> None:
        diff = """
diff --git a/tests/test_a.py b/tests/test_a.py
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1 +1 @@
-    assert True
+    pass
diff --git a/tests/test_b.py b/tests/test_b.py
--- a/tests/test_b.py
+++ b/tests/test_b.py
@@ -1 +1 @@
-    assert False
+    pass
"""
        frauds = hunt_weakened_checks(diff)
        # Dois arquivos, dois enfraquecimentos, duas linhas suspeitas cada.
        assert len(frauds) == 4
        assert {f.description.split(":", 1)[0] for f in frauds} == {
            "tests/test_a.py",
            "tests/test_b.py",
        }


class TestHuntFalseCompletion:
    """Testa caça a falsa conclusão."""

    def test_no_claims_no_frauds(self) -> None:
        frauds = hunt_false_completion({}, {})
        assert frauds == []

    def test_ruff_claimed_passes_rerun_fails(self) -> None:
        task = {"verify": {"ruff_clean": True}}
        results = {"ruff": VerifyResult(ok=False, output="error")}
        frauds = hunt_false_completion(task, results)
        assert len(frauds) == 1
        assert "ruff" in frauds[0].description

    def test_all_claims_match_rerun(self) -> None:
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
            }
        }
        results = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True),
        }
        frauds = hunt_false_completion(task, results)
        assert frauds == []

    def test_partial_results_only_checks_rerun(self) -> None:
        task = {"verify": {"tests_pass": True}}
        results = {"pytest": VerifyResult(ok=False)}
        frauds = hunt_false_completion(task, results)
        assert len(frauds) == 1

    def test_checks_not_in_results_skipped(self) -> None:
        task = {"verify": {"ruff_clean": True, "tests_pass": True}}
        results = {"ruff": VerifyResult(ok=True)}
        frauds = hunt_false_completion(task, results)
        # pytest not in results, so only ruff is checked
        assert len(frauds) == 0

    def test_empty_verify_no_frauds(self) -> None:
        frauds = hunt_false_completion({"verify": {}}, {"ruff": VerifyResult(ok=False)})
        assert frauds == []


class TestHuntScopeCreep:
    """Testa caça a escopo extra."""

    def test_no_changes_no_frauds(self) -> None:
        frauds = hunt_scope_creep({}, [])
        assert frauds == []

    def test_all_changes_declared(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py"])
        assert frauds == []

    def test_extra_file_detected(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py", "b.py"])
        assert len(frauds) == 1
        assert "b.py" in frauds[0].evidence

    def test_multiple_extra_files(self) -> None:
        task = {"surgical": {"files": [{"path": "a.py", "necessary": True}]}}
        frauds = hunt_scope_creep(task, ["a.py", "b.py", "c.py", "d.py"])
        assert len(frauds) == 1
        # More than 2 extra files → high severity
        assert frauds[0].severity == "high"

    def test_no_surgical_section(self) -> None:
        frauds = hunt_scope_creep({}, ["a.py", "b.py"])
        assert len(frauds) == 1
        assert frauds[0].severity == "medium"

    def test_only_non_necessary_files_declared(self) -> None:
        task = {"surgical": {"files": [{"path": "b.py", "necessary": False}]}}
        frauds = hunt_scope_creep(task, ["a.py"])
        assert len(frauds) == 1


class TestHuntUnauthorizedAction:
    """Testa caça a ação não autorizada."""

    def test_no_artifact_no_fraud(self) -> None:
        frauds = hunt_unauthorized_action({})
        assert frauds == []

    def test_auth_owed_and_present(self) -> None:
        task = {"artifact": {"auth_owed": True, "auth_present": True}}
        frauds = hunt_unauthorized_action(task)
        assert frauds == []

    def test_auth_owed_not_present(self) -> None:
        task = {"artifact": {"auth_owed": True, "auth_present": False}}
        frauds = hunt_unauthorized_action(task)
        assert len(frauds) == 1
        assert "AUTH" in frauds[0].description

    def test_auth_not_owed(self) -> None:
        task = {"artifact": {"auth_owed": False}}
        frauds = hunt_unauthorized_action(task)
        assert frauds == []


class TestHuntSpecBetrayal:
    """Testa caça a traição da especificação."""

    def test_no_intent_no_fraud(self) -> None:
        frauds = hunt_spec_betrayal({})
        assert frauds == []

    def test_intent_not_answered(self) -> None:
        task = {"intent": {"answered": False}}
        frauds = hunt_spec_betrayal(task)
        assert frauds == []

    def test_all_agree(self) -> None:
        task = {"intent": {"answered": True, "all_agree": True}}
        frauds = hunt_spec_betrayal(task)
        assert frauds == []

    def test_disagreement_detected(self) -> None:
        task = {
            "intent": {
                "answered": True,
                "all_agree": False,
                "code_does": "retorna None",
                "check_expects": "retorna str",
                "spec_says": "retorna int",
            }
        }
        frauds = hunt_spec_betrayal(task)
        assert len(frauds) == 1
        assert "spec" in frauds[0].description.lower()


class TestHuntDebris:
    """Testa caça a detritos."""

    def test_no_diff_no_frauds(self) -> None:
        frauds = hunt_debris("", [])
        assert frauds == []

    def test_temp_file_detected(self) -> None:
        frauds = hunt_debris("", ["file.tmp"])
        assert len(frauds) == 1
        assert "file.tmp" in frauds[0].description

    def test_bak_file_detected(self) -> None:
        frauds = hunt_debris("", ["main.py.bak"])
        assert len(frauds) == 1

    def test_scratch_file_detected(self) -> None:
        frauds = hunt_debris("", ["scratch/test.py"])
        assert len(frauds) == 1

    def test_debug_print_detected(self) -> None:
        diff = '+    print("debug: value is", x)\n'
        frauds = hunt_debris(diff, [])
        assert any("debug print" in f.description for f in frauds)

    def test_todo_detected(self) -> None:
        diff = "+    # TODO: handle edge case\n"
        frauds = hunt_debris(diff, [])
        assert any("TODO" in f.description for f in frauds)

    def test_console_log_detected(self) -> None:
        diff = '+    console.log("debug", result)\n'
        frauds = hunt_debris(diff, [])
        assert any("console.log" in f.description for f in frauds)

    def test_normal_code_no_frauds(self) -> None:
        diff = "+    return result\n+    x = calc(value)\n"
        frauds = hunt_debris(diff, ["src/main.py"])
        assert frauds == []

    def test_multiple_debris_types(self) -> None:
        diff = '+    print("debug")\n+    # TODO: fix later\n'
        frauds = hunt_debris(diff, ["scratch/out.txt"])
        # Três: o arquivo scratch/, o debug print e o TODO. O comentário antigo
        # dizia "at least 3" e a asserção admitia 2 — discordavam.
        assert len(frauds) == 3

    def test_temp_filename_without_extension_detected(self) -> None:
        frauds = hunt_debris("", ["temp.py"])
        assert len(frauds) == 1
        assert "temp.py" in frauds[0].description

    def test_temp_file_with_number_detected(self) -> None:
        frauds = hunt_debris("", ["scratch/temp2"])
        # Uma só, apesar de o path casar dois padrões de detrito: is_debris_file
        # é predicado, não contador (fix do H1).
        assert len(frauds) == 1

    def test_temp_as_separated_segment_detected(self) -> None:
        frauds = hunt_debris("", ["my_temp_file.py"])
        assert len(frauds) == 1

    def test_templates_directory_not_flagged(self) -> None:
        frauds = hunt_debris("", ["templates/email.html"])
        assert frauds == []

    def test_attempt_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["attempt_parser.py"])
        assert frauds == []

    def test_temperature_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["src/temperature.py"])
        assert frauds == []

    def test_scratchpad_filename_not_flagged(self) -> None:
        """R10-2: 'scratch' como substring marcava scratchpad.py e
        descratch.py — a mesma família de FP que 'temp' já tinha resolvido.
        O segmento isolado (`scratch_`, `scratch/`) continua sendo detrito."""
        assert hunt_debris("", ["src/scratchpad.py"]) == []
        assert hunt_debris("", ["descratch.py"]) == []
        assert any(f.type == "debris" for f in hunt_debris("", ["src/scratch_utils.py"]))

    def test_contemporary_filename_not_flagged(self) -> None:
        frauds = hunt_debris("", ["contemporary_utils.py"])
        assert frauds == []


@patch("kata.judge.untracked_files", return_value=[])
@patch("kata.judge._ignored_files", return_value=[])
@patch("kata.judge._changed_files")
@patch("kata.judge._run_git_diff")
@patch("kata.judge.run_all")
class TestJudgeTask:
    """Testa judge_task end-to-end.

    `_ignored_files` é mockado de propósito: o caminho real roda
    `git ls-files --others --ignored` na árvore do repo de desenvolvimento, e
    um ignorado com aparência de código quebraria testes que assertam
    `blind_spots == []` sem ter nada a ver com eles (R10-30).
    """

    def test_sem_claims_e_unverifiable_nao_verified(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """Tarefa que não afirma nenhum check reproduzível não pode sair VERIFIED.

        Este teste afirmava o contrário. O veredito limpo era emitido sem
        que run_all fosse chamado uma única vez — o juiz aprovava por não
        ter procurado.
        """
        mock_diff.return_value = ""
        mock_files.return_value = []
        result = judge_task({})
        assert result.verdict == "UNVERIFIABLE"
        assert result.frauds == []
        assert any("nenhuma verificação re-executada" in b for b in result.blind_spots)
        mock_run_all.assert_not_called()

    def test_verify_nao_mapa_vira_ponto_cego_nao_crash(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """R10-17: `verify: true` no YAML (escrito à mão) crashava o judge
        com AttributeError em collect_claims — vira ponto cego confessado."""
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        result = judge_task({"verify": True})
        assert result.verdict == "UNVERIFIABLE"
        assert any("verify" in b for b in result.blind_spots)
        mock_run_all.assert_not_called()

    def test_verified_all_checks_pass(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True, details={"coverage_pct": 95.0}),
        }
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
            }
        }
        result = judge_task(task)
        assert result.verdict == "VERIFIED"
        # Comparação como conjunto de propósito: a ORDEM das claims é
        # determinística hoje, mas congelá-la aqui faria uma claim nova
        # quebrar o teste sem indicar defeito de comportamento (R10-5).
        assert set(result.claims) == {
            "ruff check limpo (sem erros de lint)",
            "todos os testes passam",
            "coverage ≥ gate (?%)",
        }

    def test_false_completion_refuted(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=False, output="E501 line too long"),
        }
        task = {"verify": {"ruff_clean": True}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "false_completion" for f in result.frauds)

    def test_weakened_checks_refuted(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = """
diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1 +1 @@
-    assert True
+    pass
"""
        mock_files.return_value = ["tests/test_foo.py"]
        mock_run_all.return_value = {}
        result = judge_task({})
        assert result.verdict == "REFUTED"
        assert any(f.type == "weakened_checks" for f in result.frauds)

    def test_scope_creep_caveats(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = ["unexpected.py"]
        mock_run_all.return_value = {}
        task = {"surgical": {"files": [{"path": "expected.py", "necessary": True}]}}
        result = judge_task(task)
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "scope_creep" for f in result.frauds)

    def test_debris_combined_with_pass(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = '+    print("debug")\n'
        mock_files.return_value = ["scratch/out.txt"]
        mock_run_all.return_value = {}
        result = judge_task({})
        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert any(f.type == "debris" for f in result.frauds)

    def test_unauthorized_action_refuted(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"artifact": {"auth_owed": True, "auth_present": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "unauthorized_action" for f in result.frauds)

    def test_spec_betrayal_refuted(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"intent": {"answered": True, "all_agree": False}}
        result = judge_task(task)
        assert result.verdict == "REFUTED"
        assert any(f.type == "spec_betrayal" for f in result.frauds)

    def test_claims_collected(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {
            "verify": {
                "ruff_clean": True,
                "tests_pass": True,
                "coverage_pass": True,
                "success_criteria_met": True,
            }
        }
        result = judge_task(task)
        assert len(result.claims) == 3
        assert result.unverifiable_claims == ["critério de sucesso satisfeito"]
        assert any("sem verificação" in c for c in result.caveats)

    def test_re_ran_checks_populated(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
        }
        task = {"verify": {"ruff_clean": True, "tests_pass": True}}
        result = judge_task(task)
        assert result.re_ran_checks.get("ruff") is True
        assert result.re_ran_checks.get("pytest") is True

    def test_custom_paths_passed_to_run_all(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {"ruff": VerifyResult(ok=True)}
        task = {"verify": {"ruff_clean": True}}
        judge_task(
            task,
            ruff_paths=["app/"],
            test_paths=["tests/unit/"],
            cov_source="app",
            gate=80.0,
        )
        mock_run_all.assert_called_once_with(
            ruff_paths=["app/"],
            test_paths=["tests/unit/"],
            ignore=None,
            cov_source="app",
            gate=80.0,
            cwd=None,
            config=None,
        )


@patch("kata.judge.untracked_files", return_value=[])
class TestRunGitDiff:
    """Testa o helper _run_git_diff."""

    @patch("kata.judge._run")
    def test_git_diff_unstaged(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        from kata.judge import _run_git_diff

        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="diff --git a/a.py b/a.py\n",
            stderr="",
        )
        diff = _run_git_diff()
        assert "diff --git" in diff
        assert mock_run.call_args_list[0][0][0] == ["git", "diff", "HEAD"]

    @patch("kata.judge._run")
    def test_git_diff_staged_fallback(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        from kata.judge import _run_git_diff

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="no HEAD"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/staged.py b/staged.py\n", stderr=""
            ),
        ]
        diff = _run_git_diff()
        assert "staged.py" in diff
        assert mock_run.call_args_list[2][0][0] == ["git", "diff", "--cached"]

    @patch("kata.judge._run")
    def test_base_commit_used_when_it_resolves(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        """Com base_commit válido, compara direto contra ele — mesmo se
        não houver diff local (unstaged/staged), o que é o caso de uma
        tarefa já commitada."""
        from kata.judge import _run_git_diff

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # cat-file
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/f.py b/f.py\n+pass\n", stderr=""
            ),
        ]
        diff = _run_git_diff(base_commit="deadbeef")
        assert "+pass" in diff
        assert mock_run.call_args_list[0][0][0] == ["git", "cat-file", "-e", "deadbeef^{commit}"]
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "deadbeef"]

    @patch("kata.judge._run")
    def test_base_commit_falls_back_when_it_does_not_resolve(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        """base_commit inválido (ex: histórico reescrito) não deve travar
        o judge — cai de volta no diff local."""
        from kata.judge import _run_git_diff

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad revision"),
            subprocess.CompletedProcess(
                args=[], returncode=0, stdout="diff --git a/local.py b/local.py\n", stderr=""
            ),
        ]
        diff = _run_git_diff(base_commit="deadbeef")
        assert "local.py" in diff
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "HEAD"]


@patch("kata.judge.untracked_files", return_value=[])
class TestChangedFiles:
    """Testa o helper _changed_files."""

    @patch("kata.judge._run")
    def test_unstaged_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="a.py\nb.py\n",
            stderr="",
        )
        files = _changed_files()
        assert files == ["a.py", "b.py"]

    @patch("kata.judge._run")
    def test_staged_fallback(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="no HEAD"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="staged.py\n", stderr=""),
        ]
        files = _changed_files()
        assert files == ["staged.py"]

    @patch("kata.judge._run")
    def test_no_changes(self, mock_run: MagicMock, mock_untracked: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        files = _changed_files()
        assert files == []

    @patch("kata.judge._run")
    def test_base_commit_used_when_it_resolves(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),  # cat-file
            subprocess.CompletedProcess(args=[], returncode=0, stdout="committed.py\n", stderr=""),
        ]
        files = _changed_files(base_commit="deadbeef")
        assert files == ["committed.py"]
        assert mock_run.call_args_list[1][0][0] == ["git", "diff", "--name-only", "deadbeef"]

    @patch("kata.judge._run")
    def test_base_commit_falls_back_when_it_does_not_resolve(
        self, mock_run: MagicMock, mock_untracked: MagicMock
    ) -> None:
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad revision"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="local.py\n", stderr=""),
        ]
        files = _changed_files(base_commit="deadbeef")
        assert files == ["local.py"]


class TestJudgeTaskDetectsCommittedFraud:
    """Prova, com um repo git de verdade, que uma fraude já commitada
    (o estado normal de uma tarefa "concluída") só é detectada quando
    base_commit está disponível — sem ele, o judge fica cego."""

    def test_committed_fraud_invisible_without_base_commit(
        self, repo_git, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "tests"
        test_file.mkdir()
        (test_file / "test_foo.py").write_text(
            "def test_foo():\n    assert True\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "clean baseline"], cwd=tmp_path, check=True)

        # fraude: assert vira pass, e a mudança é commitada (tarefa "concluída")
        (test_file / "test_foo.py").write_text("def test_foo():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "weaken test"], cwd=tmp_path, check=True)

        task_data = {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}
        result = judge_task(task_data, cwd=tmp_path)
        assert not any(f.type == "weakened_checks" for f in result.frauds)

    def test_committed_fraud_detected_with_base_commit(
        self, repo_git, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "tests"
        test_file.mkdir()
        (test_file / "test_foo.py").write_text(
            "def test_foo():\n    assert True\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "clean baseline"], cwd=tmp_path, check=True)
        base_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

        (test_file / "test_foo.py").write_text("def test_foo():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "weaken test"], cwd=tmp_path, check=True)

        task_data = {
            "base_commit": base_commit,
            "verify": {},
            "surgical": {},
            "intent": {},
            "artifact": {},
        }
        result = judge_task(task_data, cwd=tmp_path)
        assert any(f.type == "weakened_checks" for f in result.frauds)
        assert result.verdict == "REFUTED"

    def test_baseline_yaml_adulterado_e_refutado(self, repo_git, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        test_file = tmp_path / "tests"
        test_file.mkdir()
        alvo = test_file / "test_foo.py"
        alvo.write_text("def test_foo():\n    assert True\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "clean baseline"], cwd=tmp_path, check=True)
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()
        assert record_baseline_ref("tarefa", base, cwd=tmp_path) is True

        alvo.write_text("def test_foo():\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "weaken test"], cwd=tmp_path, check=True)
        atual = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

        result = judge_task({"task": "tarefa", "base_commit": atual, "verify": {}}, cwd=tmp_path)
        assert result.verdict == "REFUTED"
        assert any(f.type == "baseline_tampering" for f in result.frauds)
        # Observável de verdade (a linha anterior só reafirmava o prefixo que
        # a própria função monta): a âncora gravada se lê de volta (R10-28).
        from kata.judge import _read_baseline_ref

        assert _read_baseline_ref("tarefa", cwd=tmp_path) == base


class TestIsDebrisFile:
    """Regra única de detrito, compartilhada entre JUDGE e CLI."""

    @pytest.mark.parametrize(
        "path",
        ["file.tmp", "main.py.bak", "scratch/test.py", "temp.py", "my_temp_file.py"],
    )
    def test_debris_paths(self, path: str) -> None:
        assert is_debris_file(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "templates/email.html",
            "src/temperature.py",
            "attempt_parser.py",
            "contemporary_utils.py",
            "src/main.py",
        ],
    )
    def test_non_debris_paths(self, path: str) -> None:
        assert is_debris_file(path) is False


class TestNewFilesAreNotWeakenedChecks:
    """Arquivo novo não pode ser acusado de "enfraquecer" nada: não havia o
    que enfraquecer. O sinal correto, para adições, é declarar teste sem
    afirmar nada."""

    def _new_file_diff(self, path: str, body: str) -> str:
        linhas = [f"diff --git a/{path} b/{path}", "new file mode 100644"]
        linhas += [f"+{ln}" for ln in body.splitlines()]
        return "\n".join(linhas)

    def test_legitimate_new_test_file_is_clean(self) -> None:
        """Stub com `pass` e `except ...: pass` ao lado de asserções reais.
        Antes, cada `pass` virava uma fraude de alta severidade."""
        diff = self._new_file_diff(
            "tests/test_novo.py",
            (
                "class Stub:\n"
                "    def close(self):\n"
                "        pass\n"
                "\n"
                "def test_ignora_erro():\n"
                "    try:\n"
                "        Stub().close()\n"
                "    except ValueError:\n"
                "        pass\n"
                "    assert 1 + 1 == 2\n"
            ),
        )
        assert hunt_weakened_checks(diff) == []

    def test_new_test_with_empty_body_is_caught(self) -> None:
        """A proteção não pode sumir junto com o falso positivo: uma função
        de teste cujo corpo inteiro é `pass` é suspeita mesmo em arquivo novo."""
        diff = self._new_file_diff("tests/test_fake.py", ("def test_importante():\n    pass\n"))
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert frauds[0].severity == "high"
        assert "corpo vazio" in frauds[0].description

    def test_empty_body_caught_even_beside_real_tests(self) -> None:
        """O cenário do trap s01: um teste vazio no meio de testes reais."""
        diff = self._new_file_diff(
            "tests/test_calc.py",
            (
                "def test_soma():\n"
                "    assert soma(2, 3) == 5\n"
                "\n"
                "# FRAUDE: assert virou pass\n"
                "def test_bordas():\n"
                "    pass\n"
            ),
        )
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "test_bordas" in frauds[0].evidence

    def test_new_non_test_file_is_ignored(self) -> None:
        diff = self._new_file_diff("src/app.py", "def f():\n    pass\n")
        assert hunt_weakened_checks(diff) == []

    def test_modified_test_file_still_caught(self) -> None:
        """Sem `new file mode`, o arquivo foi modificado: os padrões de
        enfraquecimento continuam valendo integralmente."""
        diff = (
            "diff --git a/tests/test_x.py b/tests/test_x.py\n"
            "--- a/tests/test_x.py\n"
            "+++ b/tests/test_x.py\n"
            "-    assert resultado == 42\n"
            "+    pass\n"
        )
        frauds = hunt_weakened_checks(diff)
        assert any("pass" in f.description for f in frauds)

    def test_test_with_real_body_is_clean(self) -> None:
        diff = self._new_file_diff(
            "tests/test_erro.py",
            ("def test_explode():\n    with pytest.raises(ValueError):\n        parse('x')\n"),
        )
        assert hunt_weakened_checks(diff) == []


class TestUntrackedSizeLimit:
    """Arquivos untracked grandes não podem ser lidos inteiros para a memória."""

    def test_large_file_is_skipped(self, tmp_path) -> None:
        grande = tmp_path / "dados.csv"
        grande.write_text("x,y\n" * 200_000, encoding="utf-8")
        assert grande.stat().st_size > 256 * 1024

        assert _untracked_diff(["dados.csv"], cwd=tmp_path) == ""
        assert _oversized_untracked(["dados.csv"], cwd=tmp_path) == ["dados.csv"]

    def test_small_file_is_inspected(self, tmp_path) -> None:
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")
        diff = _untracked_diff(["novo.py"], cwd=tmp_path)
        assert "new file mode" in diff
        assert "+x = 1" in diff
        assert _oversized_untracked(["novo.py"], cwd=tmp_path) == []

    def test_unreadable_path_is_not_inspectable(self, tmp_path) -> None:
        """stat() falhando não pode derrubar o judge."""
        assert is_inspectable(tmp_path / "nao-existe.py") is False
        assert _oversized_untracked(["nao-existe.py"], cwd=tmp_path) == []

    def test_skipped_file_becomes_a_caveat(self, tmp_path, monkeypatch) -> None:
        """Pular um arquivo em silêncio seria a cegueira que este módulo
        existe para evitar: o que não foi inspecionado tem de ser declarado."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "dados.csv").write_text("x,y\n" * 200_000, encoding="utf-8")

        result = judge_task(
            {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}, cwd=tmp_path
        )
        assert any("não inspecionado" in c and "dados.csv" in c for c in result.caveats)

    def test_comment_between_declaration_and_pass_still_caught(self) -> None:
        """Um comentário entre o `def test_` e o `pass` não deve servir de
        disfarce."""
        diff = "\n".join(
            [
                "diff --git a/tests/test_x.py b/tests/test_x.py",
                "new file mode 100644",
                "+def test_importante():",
                "+    # TODO: escrever depois",
                "+",
                "+    pass",
            ]
        )
        frauds = hunt_weakened_checks(diff)
        assert any("corpo vazio" in f.description for f in frauds)


class TestJudgeSeesUntrackedFiles:
    """Prova, com um repo git de verdade, que um arquivo novo ainda não
    rastreado não é invisível ao JUDGE. `git diff` — inclusive contra
    base_commit — não enxerga untracked, então uma fraude podia entrar
    inteira num arquivo nunca adicionado ao índice."""

    def test_untracked_file_listed_as_changed(self, repo_git, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        assert _changed_files(cwd=tmp_path) == ["novo.py"]

    def test_untracked_content_reaches_the_diff(self, repo_git, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "novo.py").write_text("x = 1\n", encoding="utf-8")

        diff = _run_git_diff(cwd=tmp_path)
        assert "diff --git a/novo.py b/novo.py" in diff
        assert "+x = 1" in diff

    def test_untracked_weakened_test_is_caught(self, repo_git, tmp_path, monkeypatch) -> None:
        """O caso que motiva a correção: um teste inteiro escrito com o
        corpo trocado por `pass`, deixado untracked, era invisível."""
        monkeypatch.chdir(tmp_path)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_fake.py").write_text(
            "def test_importante():\n    pass\n", encoding="utf-8"
        )

        task_data = {"verify": {}, "surgical": {}, "intent": {}, "artifact": {}}
        result = judge_task(task_data, cwd=tmp_path)

        assert any(f.type == "weakened_checks" for f in result.frauds)
        assert result.verdict == "REFUTED"

    def test_untracked_binary_file_does_not_break_the_diff(
        self, repo_git, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00binary")

        diff = _run_git_diff(cwd=tmp_path)
        assert "blob.bin" not in diff
        assert _changed_files(cwd=tmp_path) == ["blob.bin"]


class TestUnreadableTestFiles:
    """`_unreadable_test_files` reconhece teste pelo nome, em qualquer linguagem."""

    @pytest.mark.parametrize(
        "path",
        [
            "src/Calculadora.test.php",
            "Tests/soma_test.swift",
            "test/calculo_test.exs",
            "spec/widget_spec.dart",
        ],
    )
    def test_linguagem_sem_sondas_e_ilegivel(self, path: str) -> None:
        """Linguagem fora de _LANGUAGES continua sendo confessada."""
        assert _unreadable_test_files([path]) == [path]

    @pytest.mark.parametrize(
        "path",
        [
            "src/calculadora.test.js",
            "app/Widget.spec.ts",
            "internal/soma_test.go",
            "spec/models/user_spec.rb",
            "src/calculo_test.rs",
            "src/CalculoTest.java",
        ],
    )
    def test_linguagem_com_sondas_deixa_de_ser_ponto_cego(self, path: str) -> None:
        """A confissão encolhe sozinha conforme _LANGUAGES cresce.

        Estas eram ilegíveis quando os padrões eram só sintaxe Python; passar
        a conhecê-las é o ponto do item — e a lista de pontos cegos é derivada
        de _LANGUAGES, não mantida à mão em paralelo.
        """
        assert _unreadable_test_files([path]) == []

    @pytest.mark.parametrize(
        "path",
        [
            "tests/test_calculadora.py",
            "src/soma_test.py",
            "kata/verify.py",
        ],
    )
    def test_python_e_codigo_comum_nao_entram(self, path: str) -> None:
        assert _unreadable_test_files([path]) == []

    @pytest.mark.parametrize(
        "path",
        [
            "tests/fixtures/dados.json",
            "templates/base.html",
            "src/temperature.py",
            "src/latest.js",
            "src/contest.go",
            "src/attempt_parser.rb",
        ],
    )
    def test_nao_confunde_fixture_nem_substring(self, path: str) -> None:
        """Uma ressalva que aparece em todo projeto é uma ressalva que ninguém lê.

        `latest`, `contest` e `templates` são a mesma família de falso
        positivo que _DEBRIS_FILE_PATTERNS já teve de resolver para "temp".
        """
        assert _unreadable_test_files([path]) == []

    def test_arquivo_sob_tests_sem_nome_de_teste_nao_e_ponto_cego(self) -> None:
        """R10-12: morar em tests/ não basta — README e fixture de dados não
        são testes ilegíveis; o reconhecimento é por convenção de nome."""
        assert _unreadable_test_files(["tests/README.md", "tests/fixtures/data.csv"]) == []

    def test_nome_de_teste_mas_sufixo_de_dado_nao_e_ponto_cego(self) -> None:
        """test_data.csv tem nome de teste mas é dado — sufixos não-executáveis
        nunca entram na confissão."""
        assert (
            _unreadable_test_files(
                ["tests/test_data.csv", "tests/test_notes.md", "spec/test_fixture.png"]
            )
            == []
        )


class TestIgnoredCodeFiles:
    """`_ignored_code_files` filtra o que o judge não declara como ponto cego."""

    def test_kata_dir_proprio_da_ferramenta_e_ruido(self) -> None:
        """R10-11: tarefa com nome de teste (test-foo, foo_test) mora em
        .kata/ — sem excluir o diretório, o judge da própria tarefa listaria
        o YAML dela como ponto cego e viraria UNVERIFIABLE sempre."""
        assert _ignored_code_files([".kata/test-task.yaml", ".kata/foo_test.yaml"]) == []

    def test_build_dirs_de_outras_linguagens_sao_ruido(self) -> None:
        """R10-16: target/ (Rust) e vendor/ (Go) ignorados não são código a
        revisar — sem eles, todo judge de projeto Rust/Go declararia ponto
        cego e bloquearia VERIFIED."""
        assert (
            _ignored_code_files(["target/debug/deps/bar-123.rs", "vendor/github.com/x/y/z.go"])
            == []
        )

    def test_ignorado_com_aparencia_de_codigo_fora_de_ruido_continua_listado(self) -> None:
        """O filtro não pode virar silêncio: ignorado com cara de código, fora
        dos diretórios de ruído, continua sendo ponto cego declarado."""
        assert _ignored_code_files(["scratch/gen_parser.py"]) == ["scratch/gen_parser.py"]


@patch("kata.judge.untracked_files", return_value=[])
@patch("kata.judge._ignored_files", return_value=[])
@patch("kata.judge._changed_files")
@patch("kata.judge._run_git_diff")
@patch("kata.judge.run_all")
class TestBlindSpots:
    """O juiz confessa o que não conseguiu observar, e o veredito reflete isso.

    `_ignored_files` mockado pelo mesmo motivo do TestJudgeTask (R10-30): o
    caminho real lê o git do repo de desenvolvimento.
    """

    def test_teste_ilegivel_derruba_o_verified_limpo(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """Repositório poliglota: os checks rodam e passam, e mesmo assim há
        no diff um teste de linguagem que hunt_weakened_checks não lê."""
        mock_diff.return_value = ""
        mock_files.return_value = ["src/soma.php", "src/soma.test.php"]
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
        }
        task = {
            "verify": {"ruff_clean": True, "tests_pass": True},
            "surgical": {
                "files": [
                    {"path": "src/soma.php", "necessary": True},
                    {"path": "src/soma.test.php", "necessary": True},
                ]
            },
        }
        result = judge_task(task)

        assert result.verdict == "UNVERIFIABLE"
        assert result.re_ran_checks == {"ruff": True, "pytest": True}
        assert any("src/soma.test.php" in b for b in result.blind_spots)

    def test_checks_reexecutados_e_tudo_python_sai_verified(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """O caminho honesto continua VERIFIED — a correção não pode
        transformar trabalho verificado em suspeita."""
        mock_diff.return_value = ""
        mock_files.return_value = ["src/soma.py", "tests/test_soma.py"]
        mock_run_all.return_value = {
            "ruff": VerifyResult(ok=True),
            "pytest": VerifyResult(ok=True),
            "coverage": VerifyResult(ok=True),
        }
        task = {
            "verify": {"ruff_clean": True, "tests_pass": True, "coverage_pass": True},
            "surgical": {
                "files": [
                    {"path": "src/soma.py", "necessary": True},
                    {"path": "tests/test_soma.py", "necessary": True},
                ]
            },
        }
        result = judge_task(task)

        assert result.verdict == "VERIFIED"
        assert result.blind_spots == []

    def test_fraude_grave_vence_o_ponto_cego(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        """UNVERIFIABLE não pode mascarar REFUTED: quando o juiz achou fraude,
        ele achou — o ponto cego é sobre o resto."""
        mock_diff.return_value = ""
        mock_files.return_value = []
        mock_run_all.return_value = {}
        task = {"intent": {"answered": True, "all_agree": False}}
        result = judge_task(task)

        assert result.verdict == "REFUTED"
        assert result.blind_spots != []

    def test_fraude_leve_vence_o_ponto_cego(
        self,
        mock_run_all: MagicMock,
        mock_diff: MagicMock,
        mock_files: MagicMock,
        mock_ignored_files: MagicMock,
        mock_untracked: MagicMock,
    ) -> None:
        mock_diff.return_value = ""
        mock_files.return_value = ["scratch/saida.tmp"]
        mock_run_all.return_value = {}
        result = judge_task({})

        assert result.verdict == "VERIFIED WITH CAVEATS"
        assert result.blind_spots != []


def _diff_modificado(path: str, *linhas: str) -> str:
    """Diff de arquivo modificado (sem `new file mode`)."""
    cabecalho = f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@"
    return "\n".join([cabecalho, *linhas])


def _diff_novo(path: str, *linhas: str) -> str:
    """Diff de arquivo novo, como o git o emite."""
    cabecalho = f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}"
    return "\n".join([cabecalho, *linhas])


class TestProbesPorLinguagem:
    """A tabela _LANGUAGES é o que torna o hunter agnóstico de linguagem."""

    def test_extensao_conhecida_tem_sondas(self) -> None:
        assert probes_for("src/a.js") is not None
        assert probes_for("src/a.go") is not None
        assert probes_for("src/a.py") is not None

    def test_extensao_desconhecida_nao_tem(self) -> None:
        assert probes_for("src/a.php") is None
        assert probes_for("src/a") is None

    def test_variantes_de_js_compartilham_as_mesmas_sondas(self) -> None:
        base = probes_for("a.js")
        for ext in (".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
            assert probes_for(f"a{ext}") is base


class TestHuntWeakenedChecksPoliglota:
    """O mesmo hunter, agora aplicando a sintaxe certa a cada linguagem."""

    def test_js_expect_removido(self) -> None:
        diff = _diff_modificado(
            "src/soma.test.js",
            "-  expect(soma(1, 2)).toBe(3);",
            "+  // nada",
        )
        frauds = hunt_weakened_checks(diff)
        assert any("expect() removida" in f.description for f in frauds)
        assert all(f.severity == "high" for f in frauds)

    def test_js_teste_desativado_com_skip(self) -> None:
        diff = _diff_modificado("src/soma.test.js", "+  it.skip('soma', () => {")
        assert any(".skip" in f.description for f in hunt_weakened_checks(diff))

    def test_js_eslint_disable(self) -> None:
        diff = _diff_modificado("src/soma.test.js", "+  // eslint-disable-next-line")
        assert any("eslint-disable" in f.description for f in hunt_weakened_checks(diff))

    def test_ts_ignore_suprime_checagem(self) -> None:
        diff = _diff_modificado("app/widget.spec.ts", "+  // @ts-ignore")
        assert any("tipo suprimida" in f.description for f in hunt_weakened_checks(diff))

    def test_go_t_error_removido(self) -> None:
        diff = _diff_modificado(
            "internal/soma_test.go",
            '-\t\tt.Errorf("esperava %d", esperado)',
            "+\t\treturn",
        )
        assert any("t.Error" in f.description for f in hunt_weakened_checks(diff))

    def test_go_t_skip_adicionado(self) -> None:
        diff = _diff_modificado("internal/soma_test.go", '+\tt.Skip("flaky")')
        assert any("t.Skip" in f.description for f in hunt_weakened_checks(diff))

    def test_ruby_xit(self) -> None:
        diff = _diff_modificado("spec/soma_spec.rb", "+  xit 'soma' do")
        assert any("xit" in f.description for f in hunt_weakened_checks(diff))

    def test_rust_ignore(self) -> None:
        diff = _diff_modificado("src/soma_test.rs", "+    #[ignore]")
        assert any("#[ignore]" in f.description for f in hunt_weakened_checks(diff))

    def test_java_disabled(self) -> None:
        diff = _diff_modificado("src/SomaTest.java", "+    @Disabled")
        assert any("@Disabled" in f.description for f in hunt_weakened_checks(diff))

    def test_linguagem_sem_sondas_nao_gera_fraude(self) -> None:
        """Silêncio aqui é declarado como ponto cego em judge_task, e não
        confundido com ausência de fraude."""
        diff = _diff_modificado("src/soma.test.php", "-  $this->assertEquals(3, $r);")
        assert hunt_weakened_checks(diff) == []

    def test_padroes_de_python_nao_vazam_para_outra_linguagem(self) -> None:
        """`pass` é corpo esvaziado em Python e identificador comum alhures.

        Enquanto os padrões eram uma constante só, aplicada a todo arquivo,
        esta linha viraria fraude de alta severidade num teste Go.
        """
        diff = _diff_modificado("internal/soma_test.go", "+\tpass := true")
        assert hunt_weakened_checks(diff) == []


class TestCorpoVazioPorLinguagem:
    """Teste novo que não faz nada, em arquivo novo, onde tudo é linha '+'."""

    def test_python_corpo_pass(self) -> None:
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            "+    pass",
        )
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_js_corpo_vazio_multilinha(self) -> None:
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => {",
            "+});",
        )
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_js_corpo_vazio_na_mesma_linha(self) -> None:
        diff = _diff_novo("src/soma.test.js", "+it('soma', () => {});")
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_go_corpo_vazio(self) -> None:
        diff = _diff_novo(
            "internal/soma_test.go",
            "+func TestSoma(t *testing.T) {",
            "+}",
        )
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_js_com_corpo_de_verdade_nao_acusa(self) -> None:
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => {",
            "+  expect(soma(1, 2)).toBe(3);",
            "+});",
        )
        assert hunt_weakened_checks(diff) == []

    def test_comentario_entre_declaracao_e_corpo_e_pulado(self) -> None:
        """A sintaxe de comentário muda por linguagem — em JS é `//`, e com o
        `#` de Python a linha não seria pulada e o teste vazio escaparia."""
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => {",
            "+  // TODO: escrever",
            "+});",
        )
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_python_pass_com_noqa_inline_e_corpo_vazio(self) -> None:
        """R9-6: `pass  # noqa` é a fraude mais comum — o corpo vazio
        'documentado' por comentário inline. Antes escapava porque a linha
        não casava `skippable` nem o `empty_body` antigo."""
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            "+    pass  # noqa: F401",
        )
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "corpo vazio" in frauds[0].description

    def test_js_corpo_vazio_na_mesma_linha_com_comentario(self) -> None:
        """R9-6: corpo vazio com comentário inline na mesma linha — o
        padrão antigo de fechamento inline não casava o comentario."""
        diff = _diff_novo("src/soma.test.js", "+it('soma', () => { /* TODO */ });")
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "corpo vazio" in frauds[0].description

    def test_js_com_corpo_de_verdade_com_comentario_nao_acusa(self) -> None:
        """O inline com comentário NÃO pode virar falso positivo quando há
        corpo de verdade."""
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => { /* verifica */ expect(soma(1, 2)).toBe(3); });",
        )
        assert hunt_weakened_checks(diff) == []

    def test_js_corpo_de_verdade_uma_linha_com_literal_nao_acusa(self) -> None:
        """R10-7: teste honesto de uma linha com object literal não pode ser
        "corpo vazio" — o padrão antigo casava o par de chaves interno
        (`{}`) e acusava fraude high."""
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => { const r = {}; expect(r).toBeDefined(); });",
        )
        assert hunt_weakened_checks(diff) == []

    def test_go_corpo_de_verdade_uma_linha_com_literal_nao_acusa(self) -> None:
        diff = _diff_novo(
            "internal/soma_test.go",
            "+func TestSoma(t *testing.T) { m := map[string]int{}; t.Log(m) }",
        )
        assert hunt_weakened_checks(diff) == []

    def test_python_assert_true_no_corpo_em_arquivo_novo(self) -> None:
        """R10-10: `assert True` como corpo de teste NOVO é no-op — os
        padrões `weakened` só rodavam em arquivo modificado e a fraude mais
        comum (teste novo que não verifica nada) escapava."""
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            "+    assert True",
        )
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "assert True" in frauds[0].description

    def test_python_assert_true_com_comentario_em_arquivo_novo(self) -> None:
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            "+    assert True  # sempre passa",
        )
        assert any("assert True" in f.description for f in hunt_weakened_checks(diff))

    def test_python_pytest_skip_em_arquivo_novo(self) -> None:
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            '+    pytest.skip("flaky")',
        )
        assert any("pytest.skip" in f.description for f in hunt_weakened_checks(diff))

    def test_python_skip_condicional_em_arquivo_novo_nao_acusa(self) -> None:
        """Skip condicional é uso legítimo mesmo em arquivo novo — o mesmo
        cuidado do R10-8 aplicado ao corpo."""
        diff = _diff_novo(
            "tests/test_soma.py",
            "+def test_soma():",
            '+    if not HAS_DEPS: pytest.skip("deps ausentes")',
        )
        assert hunt_weakened_checks(diff) == []

    def test_python_corpo_vazio_na_mesma_linha(self) -> None:
        """P1-3: `def test_x(): pass` de uma linha — Python não tinha
        empty_inline e o corpo vazio escapava."""
        diff = _diff_novo("tests/test_soma.py", "+def test_soma(): pass")
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_python_print_pass_na_mesma_linha_nao_acusa(self) -> None:
        """`print("pass")` termina a linha com `pass` entre aspas — não é
        corpo vazio, e o empty_inline não pode casar."""
        diff = _diff_novo("tests/test_soma.py", '+def test_soma(): print("pass")')
        assert hunt_weakened_checks(diff) == []

    def test_js_skip_em_arquivo_novo(self) -> None:
        """P1-1: `it.skip` em arquivo novo — a declaração nem era varrida
        (test_declaration só casava `it(`)."""
        diff = _diff_novo("src/soma.test.js", "+it.skip('soma', () => {});")
        frauds = hunt_weakened_checks(diff)
        assert len(frauds) == 1
        assert "desativado" in frauds[0].description

    def test_js_xit_em_arquivo_novo(self) -> None:
        diff = _diff_novo("src/soma.test.js", "+xit('soma', () => {});")
        assert any("desativado" in f.description for f in hunt_weakened_checks(diff))

    def test_js_skip_com_corpo_de_verdade_em_arquivo_novo(self) -> None:
        """O corpo não importa: um teste `.skip` é desativado inteiro."""
        diff = _diff_novo(
            "src/soma.test.js",
            "+it.skip('soma', () => { expect(soma(1, 2)).toBe(3); });",
        )
        assert any("desativado" in f.description for f in hunt_weakened_checks(diff))

    def test_js_comentario_em_bloco_entre_declaracao_e_corpo(self) -> None:
        """P1-2: `/* */` como única linha do corpo escapava — skippable só
        casava `//`. A classe do R9-6, em forma de comentário de bloco."""
        diff = _diff_novo(
            "src/soma.test.js",
            "+it('soma', () => {",
            "+  /* TODO: escrever */",
            "+});",
        )
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_go_t_skip_em_arquivo_novo(self) -> None:
        diff = _diff_novo(
            "internal/soma_test.go",
            "+func TestSoma(t *testing.T) {",
            '+\tt.Skip("flaky")',
            "+}",
        )
        assert any("t.Skip" in f.description for f in hunt_weakened_checks(diff))

    def test_go_t_skip_condicional_em_arquivo_novo_nao_acusa(self) -> None:
        diff = _diff_novo(
            "internal/soma_test.go",
            "+func TestSoma(t *testing.T) {",
            '+	if !hasDeps { t.Skip("no deps") }',
            "+}",
        )
        assert hunt_weakened_checks(diff) == []

    def test_ruby_corpo_vazio_inline(self) -> None:
        """P1-3: Ruby sem empty_inline — `it 'x' { }` de uma linha escapava."""
        diff = _diff_novo("spec/soma_spec.rb", "+it 'soma' { }")
        assert any("corpo vazio" in f.description for f in hunt_weakened_checks(diff))

    def test_ruby_xit_em_arquivo_novo(self) -> None:
        diff = _diff_novo("spec/soma_spec.rb", "+xit 'soma' do", "+end")
        assert any("desativado" in f.description for f in hunt_weakened_checks(diff))


class TestIsTestFilePoliglota:
    """Sem reconhecer o arquivo como teste, dar sondas ao juiz não bastaria."""

    @pytest.mark.parametrize(
        "path",
        [
            "tests/test_a.py",
            "test/a_test.go",
            "spec/a_spec.rb",
            "src/__tests__/a.js",
            "src/a.test.js",
            "app/widget.spec.ts",
            "pkg/internal/tests/helper.py",
        ],
    )
    def test_reconhece(self, path: str) -> None:
        assert _is_test_file(path) is True

    @pytest.mark.parametrize(
        "path",
        ["src/main.py", "templates/base.html", "src/latest.js", "src/contest.go"],
    )
    def test_nao_confunde(self, path: str) -> None:
        assert _is_test_file(path) is False


class TestEmptyTestBodiesSemSondas:
    """Linguagem com `weakened` mas sem sondas de corpo vazio não é varrida.

    O silêncio é estreito e deliberado: os padrões de modificação daquela
    linguagem continuam valendo, e só a varredura de arquivo novo é pulada.
    """

    def test_sem_declaracao_nao_varre(self) -> None:
        probes = LanguageProbes(weakened=((r"^-.*assert", "x"),))
        assert _empty_test_bodies(["+func TestA() {", "+}"], probes) == []


class TestEscrituracaoDoKata:
    """R11-3: `.kata/<task>.yaml` é escrituração da ferramenta, não trabalho.

    O arquivo é criado pelo kata e é untracked em qualquer projeto que não
    tenha ignorado `.kata/` — e nada no kata pede isso. Contá-lo fazia o juiz
    acusar trabalho honesto de scope creep.
    """

    @pytest.mark.parametrize(
        "path",
        [
            ".kata/minha-tarefa.yaml",
            ".kata/minha-tarefa.yml",
            ".kata/config.yaml",
            ".kata/tarefa.json",
            "sub/projeto/.kata/t.yaml",
        ],
    )
    def test_reconhece_escrituracao(self, path: str) -> None:
        assert is_kata_bookkeeping(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "src/kata/judge.py",
            "src/config.yaml",
            "katalogo.yaml",
            "docs/.katalog/x.yaml",
            ".kata/script.py",
        ],
    )
    def test_nao_engole_codigo(self, path: str) -> None:
        """Filtra a escrituração, não o diretório: código guardado sob
        `.kata/` continua visível ao juiz, e `.kata` como substring de outro
        nome não conta — a mesma família de falso positivo do "temp"."""
        assert is_kata_bookkeeping(path) is False


class TestJudgeComKataVisivelAoGit:
    """R11-3 ponta a ponta, no ambiente exato em que o defeito vivia.

    Este repositório tem `/.kata/` no .gitignore e o harness de traps escreve
    `.kata/` no .git/info/exclude de todo fixture — por isso nem a suíte nem
    os 14 cenários conseguiam ver a classe. Aqui `.kata/` fica VISÍVEL ao git,
    que é o estado de qualquer projeto que rode `kata --init` sem ignorar nada.
    """

    def _tarefa(self, repo, declarados: list[str]) -> dict:
        (repo / ".kata").mkdir(exist_ok=True)
        (repo / ".kata" / "t.yaml").write_text("task: t\n", encoding="utf-8")
        return {
            "task": "t",
            "surgical": {"files": [{"path": p, "necessary": True} for p in declarados]},
        }

    def test_arquivo_da_propria_tarefa_nao_e_scope_creep(self, repo_git) -> None:
        (repo_git / "base.txt").write_text("mudou\n", encoding="utf-8")
        data = self._tarefa(repo_git, ["base.txt"])

        resultado = judge_task(data, cwd=repo_git)

        assert [f for f in resultado.frauds if f.type == "scope_creep"] == []
        assert ".kata" not in str(resultado.frauds)

    def test_arquivo_novo_de_verdade_continua_sendo_pego(self, repo_git) -> None:
        """Guarda contra filtrar demais: o filtro é da escrituração, e um
        arquivo não declarado de verdade tem de continuar acusado."""
        (repo_git / "base.txt").write_text("mudou\n", encoding="utf-8")
        (repo_git / "extra.py").write_text("x = 1\n", encoding="utf-8")
        data = self._tarefa(repo_git, ["base.txt"])

        resultado = judge_task(data, cwd=repo_git)

        creep = [f for f in resultado.frauds if f.type == "scope_creep"]
        assert len(creep) == 1
        assert "extra.py" in creep[0].evidence
        assert ".kata" not in creep[0].evidence


class TestNormalizaTask:
    """R11-1: YAML malformado vira ponto cego confessado, nunca traceback."""

    def test_topo_que_nao_e_mapa(self) -> None:
        data, avisos = _normaliza_task(["isto", "e uma lista"])
        assert data == {}
        assert any("topo do arquivo" in a for a in avisos)

    @pytest.mark.parametrize("secao", ["verify", "surgical", "intent", "artifact"])
    def test_secao_que_nao_e_mapa(self, secao: str) -> None:
        data, avisos = _normaliza_task({"task": "t", secao: True})
        assert data[secao] == {}
        assert any(secao in a for a in avisos)

    def test_files_com_strings_no_lugar_de_mapas(self) -> None:
        data, avisos = _normaliza_task({"surgical": {"files": ["a.py", {"path": "b.py"}]}})
        assert data["surgical"]["files"] == [{"path": "b.py"}]
        assert any("não são mapas" in a for a in avisos)

    def test_files_que_nao_e_lista(self) -> None:
        data, avisos = _normaliza_task({"surgical": {"files": "a.py"}})
        assert data["surgical"]["files"] == []
        assert any("não é uma lista" in a for a in avisos)

    def test_tarefa_bem_formada_nao_gera_aviso(self) -> None:
        original = {
            "task": "t",
            "verify": {"tests_pass": True},
            "surgical": {"files": [{"path": "a.py", "necessary": True}]},
            "intent": {"all_agree": True},
        }
        data, avisos = _normaliza_task(original)
        assert avisos == []
        assert data["verify"] == {"tests_pass": True}
        assert data["surgical"]["files"] == [{"path": "a.py", "necessary": True}]


@patch("kata.judge._ignored_files", return_value=[])
@patch("kata.judge.untracked_files", return_value=[])
@patch("kata.judge._changed_files", return_value=[])
@patch("kata.judge._run_git_diff", return_value="")
class TestJudgeTaskTarefaMalformada:
    """R11-1 ponta a ponta: o veredito sai, e o exit code deixa de mentir.

    Traceback saía com código 1 — o mesmo de REFUTED —, então arquivo
    quebrado era indistinguível de fraude encontrada para quem lê o CI.
    """

    @pytest.mark.parametrize("secao", ["verify", "surgical", "intent", "artifact"])
    def test_secao_nao_mapa_entrega_veredito(
        self,
        mock_diff: MagicMock,
        mock_changed: MagicMock,
        mock_untracked: MagicMock,
        mock_ignored: MagicMock,
        secao: str,
    ) -> None:
        resultado = judge_task({"task": "t", secao: True})

        assert resultado.verdict == "UNVERIFIABLE"
        assert any(secao in p for p in resultado.blind_spots)
        assert resultado.frauds == []

    def test_topo_nao_mapa_entrega_veredito(
        self,
        mock_diff: MagicMock,
        mock_changed: MagicMock,
        mock_untracked: MagicMock,
        mock_ignored: MagicMock,
    ) -> None:
        resultado = judge_task(["isto", "e uma lista"])

        assert resultado.verdict == "UNVERIFIABLE"
        assert any("topo do arquivo" in p for p in resultado.blind_spots)


class TestPromptDaFaseBateComOsHunters:
    """R11-2: a tabela de fraudes do prompt é o que o agente lê.

    O prompt declarava 6 fraudes e 3 pontos cegos contra 7 e 6 implementados,
    e `make check-skills` passava — o gerado estava fiel a uma fonte errada.
    Este teste deriva a verdade de judge.py, então a tabela não pode envelhecer
    de novo em silêncio.

    CR-001 (S1): estendido para varrer também `phases/kata.md` (orquestrador) —
    antes só `kata-judge.md` era coberto, e o drift voltou exatamente na fonte
    que o agente lê primeiro.
    """

    def _emitidos(self) -> set[str]:
        fonte = (REPO / "src" / "kata" / "judge.py").read_text(encoding="utf-8")
        return set(re.findall(r'type="(\w+)"', fonte))

    def test_toda_fraude_emitida_aparece_no_prompt(self) -> None:
        prompt = (REPO / "phases" / "kata-judge.md").read_text(encoding="utf-8").lower()
        faltando = sorted(t for t in self._emitidos() if t.replace("_", " ") not in prompt)
        assert not faltando, (
            f"judge.py emite fraudes que phases/kata-judge.md não documenta: {faltando}. "
            "Atualize a tabela e rode `make build-skills`."
        )

    def test_a_contagem_declarada_bate_com_a_implementacao(self) -> None:
        prompt = (REPO / "phases" / "kata-judge.md").read_text(encoding="utf-8")
        declarada = re.search(r"##\s+As\s+(\d+)\s+Fraudes", prompt)
        assert declarada is not None, "phases/kata-judge.md perdeu o título 'As N Fraudes'"
        assert int(declarada.group(1)) == len(self._emitidos()), (
            f"o prompt declara {declarada.group(1)} fraudes e judge.py emite "
            f"{len(self._emitidos())}"
        )

    def test_a_contagem_no_orquestrador_bate_com_a_implementacao(self) -> None:
        """CR-001: phases/kata.md (fonte do agente/skill do orquestrador) também
        precisa refletir a contagem real de fraudes. Sem este teste, o drift
        '6 tipos de fraude' voltou em kata.md sem ser pego pela suíte.
        """
        prompt = (REPO / "phases" / "kata.md").read_text(encoding="utf-8")
        n_emitidos = len(self._emitidos())
        declarado = re.search(r"ca[çc]a\s+(\d+)\s+tipos?\s+de\s+fraude", prompt)
        assert declarado is not None, (
            "phases/kata.md perdeu a frase 'caça N tipos de fraude' na seção JUDGE"
        )
        assert int(declarado.group(1)) == n_emitidos, (
            f"phases/kata.md declara {declarado.group(1)} tipos de fraude e judge.py "
            f"emite {n_emitidos}. Atualize kata.md e rode `make build-skills`."
        )

    def test_pkg_init_declara_9_fases(self) -> None:
        """CR-003: src/kata/__init__.py docstring tem que mencionar '9 fases'.

        O ciclo tem 9 fases (FIT, THINK, SIMPLIFY, INTENT, SURGICAL, VERIFY,
        TWIN CHECK, ARTIFACT, REPORT) — TWIN CHECK é a 7ª, omitida por
        contagens que dizem '8 fases'. Antes deste teste ninguém pegou.
        """
        init = (REPO / "src" / "kata" / "__init__.py").read_text(encoding="utf-8")
        assert "9 fases" in init or "nove fases" in init, (
            "src/kata/__init__.py docstring deveria dizer '9 fases' (o ciclo tem 9 "
            "incluindo TWIN CHECK); atualmente diz outra coisa. Atualize."
        )
        assert "8 fases" not in init and "oito fases" not in init, (
            "src/kata/__init__.py docstring ainda menciona '8 fases' — drift com "
            "o resto do repo (README, AGENTS, phases, frontends gerados)."
        )
