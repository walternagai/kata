#!/usr/bin/env bash
# Instala o agente @kata e as 10 skills no OpenCode via symlinks.
#
# Uso:
#   bash scripts/install.sh             # instalar
#   bash scripts/install.sh --uninstall # remover
#   powershell -ExecutionPolicy Bypass -File scripts/install.ps1 # Windows
#
# Os symlinks são criados em ~/.config/opencode/agent/ e ~/.config/opencode/skills/
# apontando para os arquivos neste repositório. Isso permite que mudanças
# no repositório sejam refletidas automaticamente sem reinstalação.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KATA_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"

AGENT_FILE="kata.md"
SKILLS=(
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
    echo "Uso: bash scripts/install.sh [--uninstall]"
    echo ""
    echo "  (sem args)     Instala agente + skills via symlinks"
    echo "  --uninstall    Remove os symlinks"
    exit 1
}

install() {
    echo "Instalando kata em $CONFIG_DIR..."

    # Agente
    mkdir -p "$CONFIG_DIR/agent"
    ln -sf "$KATA_DIR/opencode/agent/$AGENT_FILE" "$CONFIG_DIR/agent/$AGENT_FILE"
    echo "  ✅ agent/$AGENT_FILE → $KATA_DIR/opencode/agent/$AGENT_FILE"

    # Skills
    mkdir -p "$CONFIG_DIR/skills"
    for skill in "${SKILLS[@]}"; do
        ln -sfn "$KATA_DIR/opencode/skills/$skill" "$CONFIG_DIR/skills/$skill"
        echo "  ✅ skills/$skill → $KATA_DIR/opencode/skills/$skill"
    done

    echo ""
    echo "✅ Kata instalado! Reinicie o OpenCode para usar @kata"
}

uninstall() {
    echo "Removendo kata de $CONFIG_DIR..."

    # Agente
    if [[ -L "$CONFIG_DIR/agent/$AGENT_FILE" ]]; then
        rm "$CONFIG_DIR/agent/$AGENT_FILE"
        echo "  ✅ removido agent/$AGENT_FILE"
    else
        echo "  ⚠  agent/$AGENT_FILE não é symlink (pulando)"
    fi

    # Skills
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
