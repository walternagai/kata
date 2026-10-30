# Publicando uma versão (`kata-dev` no PyPI)

> Processo verificado nas releases 0.7.3 e 0.7.4. É manual de propósito: o
> upload é irreversível e não pertence a um job que roda sozinho a cada push.

## Antes de começar

| Requisito | Como conferir |
|---|---|
| `build` e `twine` instalados | `python3 -m build --version` · `python3 -m twine --version` |
| Token do PyPI em `~/.pypirc` com `username = __token__` | `test -f ~/.pypirc` (nunca imprima o conteúdo) |
| Árvore limpa e CI verde no commit que vai ser publicado | `git status` · `make lint format-check check-skills test` · `make package` |

O pacote se chama **`kata-dev`** no PyPI; o comando e o repositório continuam
`kata`.

## 1. Escolha o número — não tem volta

O PyPI **rejeita re-upload da mesma versão**. Errar o número não tem rollback:
sobra `yank` (esconde a versão, não a substitui) e publicar a seguinte.

Convenção a partir da 0.9.0: **feature visível sobe *minor*** (0.8.x → 0.9.0);
correção, ajuste de texto e refactor sem comportamento novo sobem *patch*.
A 0.9.0 é o primeiro caso — o `kata-agile` muda como o ciclo é aberto, e um
número de patch esconderia isso de quem lê "o que mudou".

Antes disso a convenção era outra: mudança aditiva sem quebra era *patch*, e
`v0.7.0 → v0.7.1` publicou o `install.py` inteiro assim. O histórico anterior
não foi reescrito; ele só não serve mais de regra.

## 2. Bump nos dois lugares

O número vive em `pyproject.toml` (`[project] version`) e em
`src/kata/__init__.py` (`__version__`). `tests/test_cli.py::test_version_matches_pyproject`
reprova se divergirem.

O `CHANGELOG.md` entra no mesmo passo: a seção da versão nova sai de "Não
publicado" para `## X.Y.Z — AAAA-MM-DD`, e `test_changelog_menciona_a_versao_atual`
reprova se a versão publicada não tiver seção. O changelog é escrito para quem
usa o CLI, o agente ou as skills — o `git log` continua sendo a trilha técnica.

```bash
# pyproject.toml:7            version = "X.Y.Z"
# src/kata/__init__.py:9     __version__ = "X.Y.Z"
# CHANGELOG.md               ## X.Y.Z — AAAA-MM-DD
python3 -m kata --version    # confirma no binário
```

## 3. Gate completo, já com o bump

```bash
make lint && make format-check && make check-skills && make test
python3 eval/run_traps.py
make package
```

`make package` apaga `dist/` velho, constrói wheel + sdist, roda `twine check`
e confere os dois artefatos: no wheel, os módulos essenciais, os assets das
skills e a versão; no sdist, os arquivos de raiz que ele precisa levar
(`CHANGELOG.md`, `README.md`, `LICENSE`, `MANIFEST.in`). É o mesmo alvo que o
job `package` do CI roda.

Artefato de release anterior em `dist/` é a armadilha clássica: sem apagar, o
wheel velho sobe junto.

## 4. Commit de release, tag e push

```bash
git add -A
git commit -m "release: kata-dev X.Y.Z — <o que muda em uma linha>"
git tag -a vX.Y.Z -m "kata-dev X.Y.Z no PyPI: <resumo>"
git push origin main
git push origin vX.Y.Z
```

A tag é **anotada** (`-a`), como em todas as anteriores.

## 5. Upload

```bash
python3 -m twine upload dist/kata_dev-X.Y.Z-py3-none-any.whl dist/kata_dev-X.Y.Z.tar.gz
```

> **Não use `uv publish`.** Na 0.7.3 ele falhou porque não lê `~/.pypirc` e
> tentou *trusted publishing* sem OIDC. `twine` funciona e é o que as releases
> anteriores usaram.

## 6. Verifique o que está publicado — não o que você enviou

```bash
# a versão virou a "latest"?
curl -s https://pypi.org/pypi/kata-dev/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"

# o sha256 do que está no ar é o do arquivo local?
curl -s https://pypi.org/pypi/kata-dev/X.Y.Z/json | python3 -c "
import sys, json
for f in json.load(sys.stdin)['urls']: print(f['filename'], f['digests']['sha256'])
"
sha256sum dist/kata_dev-X.Y.Z*

# instala do zero, sem cache, e exercita o recurso novo
python3 -m venv /tmp/v && /tmp/v/bin/pip install --no-cache-dir kata-dev==X.Y.Z
/tmp/v/bin/kata --version
```

**O JSON do PyPI pode servir a versão anterior por alguns segundos** depois do
upload — é cache do CDN, não falha. Reconsulte com `?cb=$RANDOM` antes de
concluir que não subiu.

## 7. Se o pacote estiver errado

Não há como reenviar o mesmo número. Caminhos:

1. `twine yank` (ou "Yank" na página do projeto) para esconder a versão;
2. corrigir, subir o número e publicar;
3. as versões já instaladas continuam instaladas — `yank` não as remove.

Por isso o passo 3 existe: o `make package` pega o defeito antes do upload.
