#!/usr/bin/env bash
# Instala a skill @kata e as 10 skills de fase no Claude Code via symlinks.
#
# Uso:
#   bash scripts/install-claude-code.sh             # instalar
#   bash scripts/install-claude-code.sh --uninstall  # remover
#   powershell -ExecutionPolicy Bypass -File scripts/install-claude-code.ps1 # Windows
#
# Os symlinks são criados em ~/.claude/skills/ apontando para os arquivos
# neste repositório. Isso permite que mudanças no repositório sejam
# refletidas automaticamente sem reinstalação.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KATA_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

SKILLS=(
    kata
    kata-fit
    kata-question
    kata-think
    kata-simplify
    kata-intent
    kata-surgical
    kata-verify
    kata-artifact
    kata-report
    kata-judge
)

ACTION="${1:-install}"

usage() {
    echo "Uso: bash scripts/install-claude-code.sh [--uninstall]"
    echo ""
    echo "  (sem args)     Instala a skill kata + skills de fase via symlinks"
    echo "  --uninstall    Remove os symlinks"
    exit 1
}

install() {
    echo "Instalando kata em $CONFIG_DIR/skills..."

    mkdir -p "$CONFIG_DIR/skills"
    for skill in "${SKILLS[@]}"; do
        ln -sfn "$KATA_DIR/claude-code/skills/$skill" "$CONFIG_DIR/skills/$skill"
        echo "  ✅ skills/$skill → $KATA_DIR/claude-code/skills/$skill"
    done

    echo ""
    echo "✅ Kata instalado! Use a skill kata (ex: /kata ou 'use a skill kata') no Claude Code."
}

uninstall() {
    echo "Removendo kata de $CONFIG_DIR/skills..."

    for skill in "${SKILLS[@]}"; do
        if [[ -L "$CONFIG_DIR/skills/$skill" ]]; then
            rm "$CONFIG_DIR/skills/$skill"
            echo "  ✅ removido skills/$skill"
        else
            echo "  ⚠  skills/$skill não é symlink (pulando)"
        fi
    done

    echo ""
    echo "✅ Kata removido."
}

case "$ACTION" in
    install)
        install
        ;;
    --uninstall|uninstall)
        uninstall
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Erro: argumento desconhecido '$ACTION'"
        usage
        ;;
esac
