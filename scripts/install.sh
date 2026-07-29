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
# A lista vem do filesystem. Mantê-la escrita à mão aqui significava que
# criar uma skill exigia lembrar de editar 4 instaladores; nada verificava.
SKILLS=()
for _dir in "$KATA_DIR/opencode/skills"/*/; do
    [[ -d "$_dir" ]] || continue
    SKILLS+=("$(basename "$_dir")")
done
if (( ${#SKILLS[@]} == 0 )); then
    echo "Erro: nenhuma skill encontrada em $KATA_DIR/opencode/skills" >&2
    exit 1
fi

ACTION="${1:-install}"

usage() {
    echo "Uso: bash scripts/install.sh [--uninstall]"
    echo ""
    echo "  (sem args)     Instala agente + skills via symlinks"
    echo "  --uninstall    Remove os symlinks"
    exit 1
}

# Só é nosso o que é symlink. Sobre um diretório real, `ln -sfn` cria o link
# DENTRO dele (skills/kata-fit/kata-fit) e reportaria sucesso; sobre um
# arquivo real, `ln -sf` substitui o arquivo do usuário sem aviso.
check_targets() {
    local problema=0
    local alvos=("$CONFIG_DIR/agent/$AGENT_FILE")
    for skill in "${SKILLS[@]}"; do
        alvos+=("$CONFIG_DIR/skills/$skill")
    done
    for alvo in "${alvos[@]}"; do
        if [[ -e "$alvo" && ! -L "$alvo" ]]; then
            echo "  ❌ $alvo já existe e não é symlink"
            problema=1
        fi
    done
    if (( problema )); then
        echo ""
        echo "O instalador não sobrescreve caminhos que não criou."
        echo "Remova ou renomeie os caminhos acima e rode de novo."
        return 1
    fi
}

install() {
    echo "Instalando kata em $CONFIG_DIR..."

    mkdir -p "$CONFIG_DIR/agent" "$CONFIG_DIR/skills"
    check_targets

    # Agente
    ln -sf "$KATA_DIR/opencode/agent/$AGENT_FILE" "$CONFIG_DIR/agent/$AGENT_FILE"
    echo "  ✅ agent/$AGENT_FILE → $KATA_DIR/opencode/agent/$AGENT_FILE"

    # Skills
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
        elif [[ -L "$CONFIG_DIR/skills/$skill/$skill" ]]; then
            # Órfão de instalação anterior, quando `ln -sfn` aninhava o link
            # dentro do diretório existente.
            rm "$CONFIG_DIR/skills/$skill/$skill"
            echo "  ✅ removido link aninhado skills/$skill/$skill (instalação antiga)"
        elif [[ -e "$CONFIG_DIR/skills/$skill" ]]; then
            echo "  ⚠  skills/$skill não é symlink — não foi criado por nós (pulando)"
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
