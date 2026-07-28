.PHONY: install uninstall reinstall install-claude-code uninstall-claude-code reinstall-claude-code test lint format clean

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

# === Desenvolvimento ===

test:
	python3 -m pytest tests/ -v --cov=kata --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
