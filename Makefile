.PHONY: install uninstall reinstall install-claude-code uninstall-claude-code reinstall-claude-code build-skills check-skills skills-stats test eval check package lint format format-check paper clean

# === Instalação do agente + skills no OpenCode ===

install:
	bash scripts/install.sh

uninstall:
	bash scripts/install.sh --uninstall

reinstall: uninstall install

# === Instalação das skills no Claude Code ===

install-claude-code:
	bash scripts/install-claude-code.sh

uninstall-claude-code:
	bash scripts/install-claude-code.sh --uninstall

reinstall-claude-code: uninstall-claude-code install-claude-code

# === Skills: fonte única em phases/, frontends gerados ===

build-skills:
	python3 scripts/build_skills.py

check-skills:
	python3 scripts/build_skills.py --check

skills-stats:
	python3 scripts/build_skills.py --stats

# === Artigo JSERD ===
# Exige TeX Live com xelatex e bibtex; o alvo não entra no CI, que não tem
# LaTeX instalado. Verifica o log (erros novos, referências indefinidas,
# convergência das passadas) em vez do exit do xelatex, que sai 1 pelo
# microtype em XeTeX mesmo gerando o PDF completo.
#
# O script mora ao lado do paper.tex (paper/jserd/), não em scripts/: ele
# resolve tudo a partir da própria localização, então funciona da raiz, de
# dentro da pasta e de qualquer diretório.

paper:
	bash paper/jserd/compile-paper.sh

# === Desenvolvimento ===

test:
	PYTHONPATH="$(CURDIR)/src" python3 -m pytest tests/ -v --cov --cov-report=term-missing

# Os traps provam que o JUDGE ainda caça as fraudes plantadas — e que não
# acusa trabalho honesto. O CI já rodava o script direto; local, ninguém
# rodava, e foi assim que ele ficou 0/23 desde 0b31c07 sem que `make test`
# reclamasse (achado A2 da revisão estrutural de 2026-10). Com alvo próprio,
# `make check` alcança o mesmo conjunto que o CI.
#
# `PYTHONPATH` porque `run_traps.py` chama `python3 -m kata` em subprocesso: sem
# ele, o `-m` resolve o pacote INSTALADO, não a árvore. Medido em 2026-10-30:
# com 0.8.1 no site-packages e a árvore em 0.9.1, o alvo acusou `25/26` num
# cenário que o código da árvore já passava. O CI não sofre (faz `pip install
# -e`), quem roda local sim — e o alarme falso ensina a ignorar o alvo.
eval:
	PYTHONPATH="$(CURDIR)/src" python3 eval/run_traps.py

# O conjunto que o CI verifica, num comando. Cada passo é o mesmo alvo que o
# workflow chama: o que é verde local não pode ser vermelho remoto.
check: lint format-check check-skills test eval

# Constrói e confere o artefato que vai para o PyPI. Os testes leem a árvore de
# fontes; sem este alvo, um package-data quebrado só aparecia no release.
# Requer `build` e `twine` (o CI instala; local: pip install build twine).
package:
	rm -rf build dist/*.whl dist/*.tar.gz
	python3 -m build
	python3 -m twine check dist/*
	python3 scripts/check_package.py

lint:
	python3 -m ruff check src/ tests/ eval/ scripts/

format:
	ruff format src/ tests/ eval/ scripts/

# R9-8/R10-6: o lint (ruff check) não vê drift de formatação; o CI só passou
# a reprovar quando este alvo entrou nele.
format-check:
	python3 -m ruff format --check src/ tests/ eval/ scripts/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
