---
name: kata-judge
description: Fase JUDGE do ciclo Karpathy (kata). Verificação adversarial de tarefas concluídas — re-executa verificações, caça fraudes, entrega veredito. Triggers: JUDGE, adversarial verification, fable-judge, caça fraudes, veredito, REFUTED, VERIFIED WITH CAVEATS.
---
<!-- Gerado por scripts/build_skills.py a partir de phases/kata-judge.md. Não edite aqui. -->

# Skill: kata-judge

Fase 6 do Karpathy Development Cycle — **JUDGE** (adversarial verification).

Inspirado no **fable-judge** do [The Fable Method](https://github.com/Sahir619/fable-method),
que trata um relatório como um conjunto de claims e não acredita em nada
que não observou.

## Objetivo

Verificar adversarialmente uma tarefa concluída:

1. **Collect claims** — extrair do YAML o que o relatório diz que foi feito
2. **Establish ground truth** — diff contra o estado real do código, desde
   `base_commit` (o HEAD registrado no início da tarefa, na fase FIT) se
   disponível. O CLI confere se ele resolve, é ancestral do HEAD e coincide
   com a âncora independente em `refs/kata/base/<hash>`; divergência é
   `baseline_tampering`. Sem âncora, o resultado não pode ser VERIFIED. Sem
   baseline, usa diff local contra HEAD e declara os pontos cegos observáveis.
3. **Re-run every claimed verification** — executar de novo e comparar
4. **Hunt frauds** — 8 categorias
5. **Confess blind spots** — registrar o que não teve como observar
6. **Deliver verdict** — VERIFIED / VERIFIED WITH CAVEATS / UNVERIFIABLE / REFUTED

## Execução

Via `bash`:

```bash
python -m kata --task <name> --judge
```

Ou para tarefa detectada por branch:

```bash
python -m kata --judge
```

## As 8 Fraudes

| # | Fraude | Descrição | Severidade |
|---|--------|-----------|------------|
| 1 | **Weakened checks** | Asserts removidos ou relaxados em arquivos de teste, linhas comentadas, `pass` substituindo corpo de teste, `noqa` adicionado | 🔴 alta |
| 2 | **False completion** | Relatório afirma que verificação passou, mas re-execução mostra falha | 🔴 alta |
| 3 | **Scope creep** | Arquivos alterados que não foram declarados como necessários na fase SURGICAL. **Exceção (S2/CR-002):** quando `fit.trivial=true` e `surgical.files=[]`, SURGICAL foi pulado legitimamente pelo triviality gate — não há o que declarar e a fraude não se aplica. `fit.trivial=false` com `surgical.files=[]` continua acusando: a ausência é ilegitima (SURGICAL pulado sem motivo). | 🟡 média/alta |
| 4 | **Unauthorized action** | Ação externa (push, deploy) realizada sem AUTH line documentada | 🔴 alta |
| 5 | **Spec betrayal** | O INTENT registrou que código, teste e spec discordam (`all_agree: false`) e a tarefa foi aprovada sem `conflict_resolution`. **Exceção:** discordância com resolução registrada (texto não vazio) é o INTENT funcionando — o fluxo normal de um bug fix — e não é fraude; a resolução é listada entre as claims aceitas sem verificação. | 🔴 alta |
| 6 | **Debris** | Arquivos temporários (`.tmp`, `.bak`), debug prints, TODOs, lixo | 🟢 baixa |
| 7 | **Baseline tampering** | `base_commit` do YAML diverge da âncora `refs/kata/base/<hash>` registrada no início, a âncora foi movida depois de criada (o reflog dela aponta para mais de um commit), ou o baseline não é ancestral do HEAD — mover o baseline encolhe o diff que o juiz examina. Apagar e recriar a âncora apaga o reflog e escapa localmente: no CI, use `--trusted-base <ref>` para tirar o piso de uma ref que o agente não move | 🔴 alta |
| 8 | **Triviality claim** | `fit.trivial=true` sem arquivos declarados no SURGICAL desliga o scope creep por decisão do triviality gate — o juiz mede se a alegação se sustenta. A tolerância é **grosseira** de propósito: só acusa a partir de 100 linhas adicionadas ou 10 arquivos, porque o S2/CR-002 declarou legítimos os 3 arquivos pequenos do cenário s16, e o alvo deste hunter é o commit de 16 mil linhas aprovado como trivial. Com arquivos declarados, o scope creep compara normalmente. Sem teto de diff conhecido (`approved_commit` ou base confiável), o excesso vira **ressalva** em vez de fraude: pode ser trabalho de task posterior | 🟡 média/alta |

### Evidência da execução

O arquivo da tarefa carrega `kata_version`, `verify.gate_used`,
`verify.commands` e `verify.ran_at`. O juiz confronta versão e gate com os
seus e, quando divergem, **não** acusa fraude: registra ressalva. "Aprovado
sob a versão 0.7.5 e reexecutado sob 0.8.0" e "aprovado com `--gate 38` e
reexecutado com o gate 70" são verdades diferentes que, sem esses campos,
sairiam idênticas no relatório.

A escrituração do próprio kata (`.kata/*.yaml`, `.kata/config.yaml`) não conta
como arquivo alterado: ela é criada pela ferramenta, não pelo autor da tarefa,
e contá-la acusava trabalho honesto de scope creep (R11-3).

## Vereditos

| Veredito | Condição |
|----------|----------|
| **VERIFIED** | Nenhuma fraude encontrada, e o juiz teve como procurar |
| **VERIFIED WITH CAVEATS** | Fraudes de média/baixa severidade, nenhuma alta |
| **UNVERIFIABLE** | Nenhuma fraude, mas o juiz não teve como observar |
| **REFUTED** | Pelo menos uma fraude de alta severidade |

### Pontos cegos

Um ponto cego é o juiz confessando o que não conseguiu observar. Não é
acusação: não ter observado não é evidência de fraude nem de honestidade.
Oito disparam hoje:

1. **Nenhuma verificação re-executada** — o relatório não afirma nenhum
   check (`ruff_clean`, `typecheck_clean`, `tests_pass`, `coverage_pass`) que o juiz saiba
   reproduzir, então nada é re-executado. Declarar os comandos do projeto em
   `.kata/config.yaml` é o que desarma este ponto cego.
2. **Teste em linguagem sem sondas** — o juiz conhece a sintaxe de Python,
   JS/TS, Go, Ruby, Rust, Java/Kotlin, C#, PHP e Swift. Um teste fora dessa
   lista (`.exs`…) não pode ser lido, e o juiz diz isso em vez de calar.
3. **Código/teste ignorado pelo Git** — candidatos relevantes sob `.gitignore`
   não entram no diff e são listados como ponto cego.
4. **Seção da tarefa ilegível** — `verify`, `surgical`, `intent` ou `artifact`
   que não sejam mapas (YAML escrito à mão), ou uma lista no topo do arquivo.
   O que não pôde ser lido é confessado e o veredito sai; antes, o judge
   morria com traceback e o código de saída ficava igual ao de REFUTED (R11-1).
5. **Baseline sem âncora independente** — o YAML declara `base_commit` mas não
   há `refs/kata/base/<hash>` para confrontá-lo. A âncora é local ao clone: um
   clone novo de tarefa antiga cai aqui, e isso é ponto cego, não fraude.
6. **Baseline não resolve mais** — o commit declarado sumiu do histórico
   (rebase, poda), então não há de onde diffar.
7. **Janela de diff vazia** — `approved_commit` coincide com `base_commit` e o
   trabalho foi commitado depois dele: não há como separá-lo de tasks
   posteriores. Se o HEAD ainda está no `base_commit`, nada foi commitado e o
   juiz difa contra a árvore de trabalho, sem ponto cego (artigo JSERD §6.4).
8. **Base confiável sem merge-base** — `judge_task(..., trusted_base=...)`
   recebeu uma ref que não resolve ou não tem merge-base com o HEAD (clone raso);
   a janela veio do YAML, que o agente controla. A CLI não chega aqui: nesse
   caso ela sai 1 sem julgar. Com a base confiável resolvida, a âncora ausente
   (o clone do CI não a traz) e um `base_commit` fora do histórico não viram
   ponto cego.

Não havendo fraude nenhuma, qualquer ponto cego faz o veredito ser
**UNVERIFIABLE** em vez de VERIFIED: "não consegui olhar" não pode ser
reportado como "está tudo certo". Havendo fraude, ela manda no veredito e
os pontos cegos continuam listados.

O exit code de UNVERIFIABLE é `0` — o juiz não encontrou nada errado,
apenas não teve como olhar. Quem quiser barrar no CI lê o veredito.

## Resultado no CLI

```
  Claims verificadas:
    • ruff check limpo (sem erros de lint)
    • todos os testes passam
    • coverage ≥ gate (95.0%)

  Claims aceitas sem verificação (não re-executáveis):
    • critério de sucesso satisfeito

  Fraudes encontradas:
    🔴 [high] false_completion
       ruff re-executado falhou, mas relatório afirma que passou
       → relatório: ruff_clean=True → reality: ruff falhou
    🟡 [medium] scope_creep
       2 arquivo(s) alterado(s) não declarado(s) como necessários
       → extra_a.py, extra_b.py

  Pontos cegos (o juiz não conseguiu observar):
    ❓ 1 arquivo(s) de teste sem padrão de enfraquecimento para a linguagem: src/soma.test.js

  Re-execução:
    ✅ ruff
    ❌ pytest

──────────────────────────────────────────────────────────

❌  KATA JUDGE — REFUTED
```

## Verificação em Dois Estágios

A verificação adversarial do Kata opera em dois estágios complementares:

### Estágio 1: Verificação Mecânica (Determinística)

Executa o CLI Python (`python -m kata --task <name> --judge` via `bash`).
Ele re-executa linters e testes, varre o diff e a AST contra as 8 fraudes
sintáticas e confessa pontos cegos. Se o veredito mecânico for REFUTED ou
houver falha de execução, o ciclo para imediatamente — a tarefa é reprovada
sem necessidade de revisão semântica adicional.

### Estágio 2: Verificação Semântica Adversarial

Roda só quando o Estágio 1 aprovou e a tarefa não é trivial
(`fit.trivial == false`). Ele cobre o que regex, AST e linters não alcançam:

- Testes tautológicos ou superficiais que passam nos checks mas não testam a regra real;
- Desvios sutis de especificação ou intenção do usuário;
- Complexidade acidental que violou o minimalismo (YAGNI);
- Edge cases e riscos de concorrência ou quebra de contratos.

**O Kata não exige um modelo de IA específico para isso**, nem pressupõe
que o revisor seja mais capaz do que quem escreveu o diff. O Estágio 2 é um
procedimento com saída em formato fixo; quem o executa depende do que existe
no ambiente:

| Situação | Quem executa o Estágio 2 |
|---|---|
| Host com revisor adversarial próprio | o revisor do host (subagente ou comando) |
| Sem revisor, com humano no loop | o usuário, pelo checklist abaixo |
| Sem revisor e sem humano | o Estágio 2 não roda — registre em `caveats` do veredito |

#### Checklist executável (independente de modelo)

Todo revisor — humano, subagente do host ou outro — responde os quatro itens
no mesmo formato. Nenhum item pede julgamento sem âncora: cada um se ancora em
`arquivo:linha` ou em uma frase citada.

1. **Tautologia**: para cada teste novo ou alterado no diff, descreva o que
   deixaria de falhar se a implementação fosse removida ou a asserção
   invertida. Se nada falharia, o teste é tautológico. Saída: `arquivo:linha`
   do teste + comportamento que ele deveria pegar.
2. **Desvio de spec**: cite a frase da especificação, do pedido do usuário ou
   do docstring, e a linha do diff que a implementa. Saída: as duas citações +
   concorda / diverge.
3. **YAGNI**: liste cada símbolo novo (função, classe, parâmetro, chave de
   config) e o caller real que o usa. Sem caller, é achado. Saída:
   `arquivo:linha` do símbolo + caller, ou "sem caller".
4. **Contrato e borda**: nomeie uma entrada que o código não trata (vazio,
   `None`, caminho inexistente, concorrência) e o que acontece. Saída: a
   entrada + o efeito observado ou esperado.

Item sem problema se escreve "sem achado". Item que não pôde ser checado se
escreve "não verificado" e entra em `caveats` — nunca em "sem achado". Um
Estágio 2 inteiro "não verificado" não produz VERIFIED.

**Configuração (.kata/config.yaml):**
Se o projeto declarar a seção `advisor:`, suas diretrizes são obedecidas.
Todas as chaves são opcionais e descrevem o **host**, não um fornecedor:

```yaml
advisor:
  enabled: true                        # true | false | auto | never
  model: "<provedor>/<modelo>#<variante>"  # opcional; o Kata só repassa a string
  effort: "high"                       # nível de esforço/thinking do host, se ele tiver
  skip_trivial: true                   # bypass automático se fit.trivial == true
```

O CLI não interpreta `model` nem `effort`: valida que são strings e deixa a
escolha para o host. Um projeto sem `advisor:` roda o Estágio 2 pelo
checklist acima, sem perda de contrato.

**No OpenCode:**
Acione o subagente `kata-advisor` (armazenado em `.opencode/agents/kata-advisor.md`
ou `~/.config/opencode/agents/kata-advisor.md`). Se `advisor.model` estiver
configurado em `.kata/config.yaml`, passe-o explicitamente no parâmetro `model`
da ferramenta `subagent`. O subagente opera em modo *read-only* (`edit: deny`,
`shell: deny`) e retorna seu veredito semântico (VERIFIED / CAVEATS / REFUTED)
seguindo o checklist acima. Se o subagente não estiver instalado, execute o
checklist na conversa principal.

## Registro no YAML

O CLI Python não persiste o resultado do judge de volta no arquivo de
tarefa — `--judge` é uma verificação stateless, re-executada a cada chamada.
Se o agente decidir registrar o veredito em `.kata/<task>.yaml` (via
`write`/`edit`), use a chave `judge`:

```yaml
judge:
  verdict: "REFUTED"           # VERIFIED | VERIFIED WITH CAVEATS |
                               # UNVERIFIABLE | REFUTED
  frauds:
    - type: false_completion
      severity: high
      description: "ruff re-executado falhou, mas relatório afirma que passou"
  caveats:
    - "1 fraude(s) de alta severidade"
  judged_at: "2026-07-28"      # data (ou commit) em que o judge rodou
```

## Modo Automático

O judge executa automaticamente como fase extra ao final do ciclo se
desejado, mas por padrão é um modo separado (`--judge`) que o usuário
invoca explicitamente para verificar uma tarefa já concluída.

## Princípios

- **O diff é a verdade; o relatório não é**: acredite no que o git mostra, não no que o YAML diz
- **Re-execute sempre**: toda claim de verificação deve ser re-executada, nunca assumida
- **Fraude de alta severidade = REFUTED**: uma só já invalida o ciclo
- **Caveats honestos**: se algo não pôde ser verificado, diga exatamente isso
- **Não observar não é aprovar**: sem nada observado, o veredito é
  UNVERIFIABLE, nunca VERIFIED
