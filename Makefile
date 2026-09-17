.PHONY: install uninstall reinstall install-claude-code uninstall-claude-code reinstall-claude-code build-skills check-skills skills-stats test lint format format-check paper clean

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
	python3 -m pytest tests/ -v --cov --cov-report=term-missing

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
