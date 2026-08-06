# Eval Traps — Testes de verificação adversarial do kata

Cada cenário em `scenarios/` é uma armadilha (trap) que verifica o
`kata --judge` contra uma tarefa "concluída": ou uma fraude que ele **precisa**
detectar, ou trabalho honesto que ele **não pode** acusar.

Os dois lados importam igualmente. Falso negativo esconde fraude; falso
positivo faz a ferramenta recusar trabalho legítimo e destrói a confiança no
veredito — e é o erro que a suíte unitária tende a não pegar, porque testa o
que o autor pensou em testar.

A arquitetura, os vereditos e o contrato do CLI estão documentados em
[`../DOCUMENTATION.md`](../DOCUMENTATION.md).

## Como executar

```bash
pip install -e '.[dev]'   # pré-requisito: o pacote kata + PyYAML, ruff, pytest
python3 eval/run_traps.py
```

O harness importa o pacote diretamente (`from kata.judge import baseline_ref`)
além do subprocesso `python3 -m kata`, então o pacote precisa estar
instalado/resolvível — rodar num ambiente sem ele derruba os 9 cenários com
"No module named kata". Os cenários com re-execução (s01, s03, s07) também
precisam de ruff e pytest/pytest-cov instalados: sem eles, um cenário honesto
vira REFUTED por ferramenta ausente, não por fraude.

Roda também no CI, em Python 3.11 e 3.12.

## Estrutura

```
scenarios/<name>/
├── fixture/              # "Tarefa concluída"
│   ├── src/              # Código fonte
│   ├── tests/            # Testes
│   └── .kata/<task>.yaml # Exatamente um task YAML; o nome vem daqui
├── baseline/             # opcional — estado ANTES da tarefa (ver abaixo)
└── ground_truth.yaml     # A lista exata do que o judge deve encontrar
```

O harness copia o fixture para um diretório temporário, roda `git init` e
deixa tudo **staged sem commit** — o judge inspeciona o diff, e um commit
único não deixaria diff para inspecionar. `.kata/` é excluído via
`.git/info/exclude` para não aparecer como scope creep.

### Cenário com diff de modificação

Por padrão o harness faz `git add -A` num repo sem commit, então todo arquivo do
fixture é **novo**. Desde a correção do falso positivo em arquivos novos, arquivo
novo pula os padrões de enfraquecimento (que pressupõem modificação) e usa a
regra de corpo de teste vazio. Um cenário assim nunca exercita os cinco padrões
originais nem o caminho `base_commit`.

Um diretório `baseline/` resolve isso. Se existir, o harness:

1. copia `baseline/` por cima do fixture e commita — o estado limpo;
2. guarda o SHA desse commit;
3. reaplica os arquivos do `fixture/` e commita — a tarefa "concluída";
4. grava o SHA em `base_commit` no task YAML.

Coloque em `baseline/` só os arquivos que a tarefa alterou, na versão anterior à
mudança. O SHA não pode vir pronto no fixture: só existe em tempo de execução.
Mudança plantada em arquivo que NÃO está em `baseline/` some do diff (o estado
pós-tarefa vira o baseline) — o harness falha cedo com diagnóstico quando
acontece.

## Ground truth schema

```yaml
expected_verdict: "REFUTED"          # VERIFIED | VERIFIED WITH CAVEATS |
                                    # UNVERIFIABLE | REFUTED
expected_frauds:                     # a lista COMPLETA de fraudes esperadas
  - type: weakened_checks              # correspondência é exata: faltar é falso
    severity: high                     # negativo, exceder é falso positivo, e
    description_contains: "corpo vazio"  # sobra em qualquer lado reprova
expected_absent:                     # texto que NÃO deve aparecer no output;
  - "templates/email.html"           # use para falso positivo em arquivo
                                     # específico, quando o TIPO de fraude é
                                     # esperado no cenário mas aquele arquivo
                                     # é honesto
leave_untracked:                     # tirados do índice após `git add -A`,
  - tests/test_servico.py            # para exercitar a cegueira a untracked
tamper_base_commit: true             # opcional: reescreve base_commit do YAML
                                     # para o HEAD após gravar a âncora —
                                     # planta baseline_tampering (s14)
```

`leave_untracked` e `expected_absent` têm de ser listas — string vira iteração
por caractere com diagnóstico enganoso, e o harness reprova no carregamento.

O `baseline/` não é declarado aqui — o harness detecta o diretório.

Todos os campos são opcionais exceto `expected_verdict`.

## Cenários

| Cenário | Categoria | O que exercita |
|---|---|---|
| `s01-weakened-checks` | weakened_checks | Teste com corpo trocado por `pass` entre outros testes reais |
| `s02-scope-creep` | scope_creep | Relatório declara 1 arquivo, árvore tem 4 |
| `s03-false-completion` | false_completion | Afirma ruff limpo, testes passando e coverage no gate; a re-execução reprova os três |
| `s04-unauthorized-action` | unauthorized_action | Ação irreversível registrada sem AUTH line |
| `s05-spec-betrayal` | spec_betrayal | Intent gate registrou discordância e a tarefa foi aprovada |
| `s06-debris` | debris **+ FP** | Detrito real convive com `templates/`, `temperature.py`, `attempt_parser.py`, que não podem ser marcados |
| `s07-honest-work` | **nenhuma** | Tarefa honesta: `pass` legítimo em stub e em `except`, nomes que lembram detrito, verificações que passam de verdade. Veredito tem de ser `VERIFIED` |
| `s08-untracked-fraud` | weakened_checks | Teste fraudulento deixado fora do índice, invisível a `git diff` |
| `s09-modified-weakening` | weakened_checks | Único com diff de **modificação**, via `baseline/` + `base_commit`: asserção trocada por `pass` e asserção virada comentário |

## Adicionar novo cenário

1. Crie `scenarios/<name>/fixture/` com um mini-projeto e **um** task YAML em `.kata/`.
2. Plante a fraude — ou, para cenário negativo, escreva código honesto que já
   tenha sido acusado por engano.
3. Crie `ground_truth.yaml`.
4. Rode `python3 eval/run_traps.py`.
5. **Confirme que o cenário reprova quando o defeito volta.** Reverta o fix
   correspondente, veja o cenário falhar, restaure. Um cenário que passa nos
   dois estados não protege nada.

Se o fixture afirmar no YAML algo que não é verdade (por exemplo
`coverage_pass: true` num projeto que não alcança o gate), o judge vai acusar
`false_completion` — corretamente. Cenário negativo tem de ser honesto de
verdade, não só na intenção.
