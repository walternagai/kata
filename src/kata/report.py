"""I/O de relatório e auditoria do CLI kata (S7-refactor).

Extraído de cli.py para dar um home aos blocos REPORT/AUDIT/DOCTOR sem mudar
comportamento: `_print_header`, `_print_judge_verdict`, `_format_*_line`,
`_AUDIT_RISKS`, `_AUDIT_CONTENT_KEY`, `_audit_task`, `_print_audit` e
`_print_doctor`. O cli.py re-exporta estes nomes (`from kata.report import
...`) para que os testes que patcham `kata.cli._print_header` etc. continuem
a funcionar.

`_step_report` fica no cli.py de propósito: ele depende de `_secao` e
`_detect_scratch_files`, que vivem no cli (e mover tudo criaria import
circular). O que este módulo contém é puro I/O, sem dependência do cli.
"""

from __future__ import annotations

from typing import Any

from kata.judge import JudgeResult
from kata.skills import InstallStatus, doctor_domain


def _print_header(text: str) -> None:
    width = 60
    print()
    print("┌" + "─" * (width - 2) + "┐")
    for line in text.split("\n"):
        print(f"│ {line:<{width - 3}}│")
    print("└" + "─" * (width - 2) + "┘")
    print()


# As chaves de verificação são papéis, mas carregam nome de ferramenta Python
# por serem o mesmo vocabulário que o schema da tarefa persiste (`ruff_clean`,
# `tests_pass`). Renomear o schema é migração à parte; exibir o papel não é, e
# "✅ ruff" num projeto JS é ruído que confunde quem lê o veredito.
_ROLE_LABELS = {"ruff": "lint", "pytest": "teste", "coverage": "coverage"}


def _print_judge_verdict(result: JudgeResult) -> None:
    """Imprime o veredito do juiz adversarial."""
    verdict_icon = {
        "VERIFIED": "✅",
        "VERIFIED WITH CAVEATS": "⚠️",
        "UNVERIFIABLE": "❓",
        "REFUTED": "❌",
    }
    icon = verdict_icon.get(result.verdict, "❓")
    print(f"\n{icon}  VEREDITO: {result.verdict}")
    print()

    if result.claims:
        print("  Claims verificadas:")
        for c in result.claims:
            print(f"    • {c}")
        print()

    if result.unverifiable_claims:
        print("  Claims aceitas sem verificação (não re-executáveis):")
        for c in result.unverifiable_claims:
            print(f"    • {c}")
        print()

    if result.frauds:
        print("  Fraudes encontradas:")
        for f in result.frauds:
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(f"    {sev_icon.get(f.severity, '⚪')} [{f.severity}] {f.type}")
            print(f"       {f.description}")
            if f.evidence:
                print(f"       → {f.evidence}")
        print()

    if result.blind_spots:
        print("  Pontos cegos (o juiz não conseguiu observar):")
        for b in result.blind_spots:
            print(f"    ❓ {b}")
        print()

    if result.caveats:
        print("  Ressalvas:")
        for c in result.caveats:
            print(f"    • {c}")
        print()

    if result.re_ran_checks:
        print("  Re-execução:")
        for check, ok in result.re_ran_checks.items():
            status = "✅" if ok else "❌"
            print(f"    {status} {_ROLE_LABELS.get(check, check)}")
        print()

    print("─" * 58)
    print(f"\n{icon}  KATA JUDGE — {result.verdict}")
    print()


def _format_intent_line(intent: dict[str, Any]) -> str:
    """Formata a linha INTENT no formato fable."""
    code = intent.get("code_does", "")
    check = intent.get("check_expects", "")
    spec = intent.get("spec_says", "")
    if code or check or spec:
        return f"INTENT: code does {code}; check expects {check}; spec says {spec}"
    return ""


def _format_auth_line(auth: dict[str, Any]) -> str:
    """Formata a linha AUTH no formato fable."""
    if auth.get("authorized") and auth.get("quote"):
        return f'AUTH: user said "{auth["quote"]}"'
    return ""


def _format_pending_line(pending: dict[str, Any]) -> str:
    """Formata a linha PENDING no formato fable."""
    if pending.get("documented") and pending.get("action"):
        return f"PENDING: {pending['action']} - awaiting your authorization"
    return ""


def _format_twins_line(twins: dict[str, Any]) -> str:
    """Formata a linha TWINS no formato fable."""
    if twins.get("searched") and twins.get("pattern"):
        found = twins.get("result", "none")
        files = twins.get("files_count", 0)
        matches = twins.get("matches_count", 0)
        detail = f" ({files} file(s), {matches} occurrence(s))" if files else ""
        return f"TWINS: searched {twins['pattern']} - found {found}{detail}"
    return ""


# Risco concreto que cada fase faked/skipped cria, no estilo do
# `/fable-method audit` do The Fable Method: cada skip/fake nomeia o que
# deixou de ser observado e o que isso permite que aconteça.
_AUDIT_RISKS: dict[str, str] = {
    "fit": "rota e trivialidade não classificadas por humano — esforço pode ser "
    "desperdiçado em tarefa trivial ou mal roteada",
    "think": "assumptions nunca declaradas — qualquer solução pode atacar o problema errado",
    "simplify": "minimalidade afirmada sem ninguém confrontar o diff com o "
    "pedido — abstrações especulativas podem passar sem revisão",
    "surgical": "cada arquivo declarado necessário sem ninguém conferir — "
    "escopo extra pode entrar sem ser notado",
    "intent": "código, teste e spec podem discordar sem registro — "
    "comportamento muda sem intenção verificada",
    "verify": "sucesso afirmado sem evidência de execução — a tarefa pode "
    "estar aprovada sobre nada",
    "twins": "defeito corrigido sem busca de recorrência — o mesmo padrão "
    "pode se repetir em outros lugares",
    "preflight": "fase(s) executada(s) sem a skill correspondente — as "
    "instruções da fase não foram carregadas, e o que ficou registrado "
    "veio de improviso",
}

# Para cada fase com semântica answered/skipped, a chave cujo conteúdo real
# prova que a fase foi de fato respondida (não preenchida com default).
# simplify/surgical entram no mesmo contrato (R10-22): um bloco `answered:
# true` escrito à mão SEM as chaves de conteúdo é tão faked quanto um THINK
# com problem vazio.
_AUDIT_CONTENT_KEY: dict[str, str] = {
    "fit": "reason",
    "think": "problem",
    "intent": "code_does",
    "simplify": "minimum_code",
    "surgical": "files",
}


def _audit_task(data: dict[str, Any]) -> list[dict[str, str]]:
    """Gradua as fases da tarefa como followed / skipped / faked.

    Inspirado no `/fable-method audit` do Fable Method: cada passo é
    *followed* (observado), *skipped* (pulado com registro) ou *faked*
    (afirmado sem observação). Para cada skip/fake, nomeia o risco concreto
    que criou.

    - followed: fase com `answered: true` e conteúdo real (ex.: think.problem
      não vazio);
    - skipped: fase com `skipped: true` (documentado);
    - faked: fase com `answered: true` mas conteúdo default/vazio (o padrão
      do R7-1) OU verify afirmando sucesso sem evidência correspondente OU
      twins declarando defeito sem busca.

    Fases não iniciadas (nem answered nem skipped) ficam de fora: uma tarefa
    em andamento não tem skip/fake a auditar.
    """
    achados: list[dict[str, str]] = []

    # Tarefa malformada não pode derrubar a graduação com traceback: YAML
    # escrito à mão é entrada suportada e o CLI não valida schema antes de
    # auditar. Uma seção que não é mapa (`surgical: true`) ou uma lista no
    # topo do arquivo davam AttributeError — e traceback sai com código 1, o
    # mesmo de "audit sujo", tornando arquivo quebrado indistinguível de fase
    # fingida (R11-1). Sem seção legível não há o que graduar: lista vazia.
    if not isinstance(data, dict):
        return achados

    def bloco(nome: str) -> dict[str, Any]:
        secao = data.get(nome)
        return secao if isinstance(secao, dict) else {}

    # Preflight primeiro: se as instruções de uma fase não foram sequer
    # carregadas, o que as outras graduações leem foi escrito sem elas.
    faltando = bloco("preflight").get("skills_missing") or []
    if faltando:
        achados.append(
            {
                "fase": "preflight",
                "status": "degraded",
                "risco": f"{_AUDIT_RISKS['preflight']} — faltou: {', '.join(faltando)}",
            }
        )

    for fase in ("fit", "think", "intent"):
        secao = bloco(fase)
        if secao.get("skipped"):
            achados.append({"fase": fase, "status": "skipped", "risco": _AUDIT_RISKS[fase]})
            continue
        if not secao.get("answered"):
            continue
        if str(secao.get(_AUDIT_CONTENT_KEY[fase], "")).strip():
            achados.append({"fase": fase, "status": "followed", "risco": ""})
        else:
            achados.append({"fase": fase, "status": "faked", "risco": _AUDIT_RISKS[fase]})

    for fase in ("simplify", "surgical"):
        secao = bloco(fase)
        if secao.get("skipped"):
            achados.append({"fase": fase, "status": "skipped", "risco": _AUDIT_RISKS[fase]})
            continue
        if not secao.get("answered"):
            continue
        if _AUDIT_CONTENT_KEY[fase] in secao:
            achados.append({"fase": fase, "status": "followed", "risco": ""})
        else:
            achados.append({"fase": fase, "status": "faked", "risco": _AUDIT_RISKS[fase]})

    verify = bloco("verify")
    evidencias = [verify.get(chave) for chave in ("ruff_clean", "tests_pass", "coverage_pass")]
    if verify.get("success_criteria_met") and not any(evidencias):
        achados.append({"fase": "verify", "status": "faked", "risco": _AUDIT_RISKS["verify"]})
    elif any(evidencias):
        achados.append({"fase": "verify", "status": "followed", "risco": ""})

    twins = bloco("twins")
    if twins.get("defect_fixed") and not twins.get("searched"):
        achados.append({"fase": "twins", "status": "faked", "risco": _AUDIT_RISKS["twins"]})
    elif twins.get("searched"):
        achados.append({"fase": "twins", "status": "followed", "risco": ""})

    return achados


def _print_audit(achados: list[dict[str, str]]) -> None:
    """Imprime a graduação followed/skipped/faked com os riscos concretos."""
    icones = {"followed": "✅", "skipped": "⏭️", "faked": "❌", "degraded": "⚠️"}
    if not achados:
        print("  (nenhuma fase iniciada — tarefa em andamento)")
        print()
        return
    for a in achados:
        print(f"  {icones.get(a['status'], '•')} {a['fase'].upper()}: {a['status']}")
        if a["risco"]:
            print(f"     ⚠ {a['risco']}")
    print()
    fakes = [a for a in achados if a["status"] == "faked"]
    skips = [a for a in achados if a["status"] == "skipped"]
    degradadas = [a for a in achados if a["status"] == "degraded"]
    if fakes or skips or degradadas:
        resumo = f"{len(fakes)} fake(s) e {len(skips)} skip(s)"
        if degradadas:
            resumo += f", {len(degradadas)} degradada(s)"
        print(f"  ⚠  Audit encontrou {resumo}.")
    else:
        print("  ✅  Audit limpo — todas as fases foram seguidas.")


def _print_doctor(estados: list[InstallStatus]) -> int:
    """Imprime o estado de instalação. Devolve o exit code.

    Instalação **parcial** é o que reprova, e não a ausente: quem nunca
    instalou um frontend não perde nada, mas quem tem 9 das 10 skills roda o
    ciclo inteiro e perde uma fase sem ser avisado — o orquestrador tenta
    carregar a que falta, falha, e o modelo improvisa a fase a partir do
    nome dela.
    """
    parciais = 0
    for e in estados:
        if e.completo:
            print(f"  ✅ {e.frontend}: {len(e.instaladas)} skill(s) em {e.config_dir}")
        elif e.ausente:
            print(f"  •  {e.frontend}: não instalado ({e.config_dir})")
        else:
            parciais += 1
            print(f"  ❌ {e.frontend}: instalação PARCIAL em {e.config_dir}")
            faltando = list(e.faltando)
            if e.agente_esperado and not e.agente_instalado:
                faltando.append("agent/kata.md")
            print(f"     {len(e.instaladas)} instalada(s), faltando: {', '.join(faltando)}")
    print()

    # Domain skills são opcionais: avisar, mas não reprovar.
    domain_missing = doctor_domain()
    domain_warnings = 0
    for frontend, faltando in domain_missing.items():
        if faltando:
            domain_warnings += 1
            print(f"  ℹ️  {frontend}: domain skills opcionais faltando: {', '.join(faltando)}")
    if domain_warnings:
        print("     Domain adapters só são necessárias quando a tarefa usa um")
        print("     domínio diferente de coding. Instale com `make reinstall` /")
        print("     `make reinstall-claude-code` se for usar devops/data-analysis/etc.")
        print()

    if parciais:
        print(f"  ⚠  {parciais} frontend(s) com instalação parcial.")
        print("     O ciclo vai tentar carregar a skill que falta, não conseguir,")
        print("     e improvisar a fase — que é o que o --audit chama de fase fingida.")
        print("     Rode `make reinstall` / `make reinstall-claude-code`.")
    elif all(e.ausente for e in estados):
        print("  ⚠  Nenhum frontend instalado. Rode `make install` ou")
        print("     `make install-claude-code`. O CLI `kata` funciona sem isso.")
    else:
        print("  ✅  Instalação completa.")
    print()
    return 1 if parciais else 0
