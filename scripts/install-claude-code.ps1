[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Copy
)

$ErrorActionPreference = "Stop"

$kataRoot = Split-Path -Parent $PSScriptRoot
$configRoot = if ($env:CLAUDE_CONFIG_DIR) {
    $env:CLAUDE_CONFIG_DIR
} else {
    Join-Path $HOME ".claude"
}

# A lista vem do filesystem — ver comentário equivalente nos scripts .sh.
$skillsRoot = Join-Path $kataRoot "claude-code/skills"
$skills = Get-ChildItem -Directory -Path $skillsRoot | Select-Object -ExpandProperty Name | Sort-Object
if ($skills.Count -eq 0) { throw "Nenhuma skill encontrada em $skillsRoot" }

# Marcador gravado dentro de cada diretório que o modo -Copy cria, para que a
# desinstalação saiba o que é dela. Sem isso não há como distinguir uma cópia
# nossa de um diretório do próprio usuário com o mesmo nome.
$managedMarker = ".kata-managed"

function Test-ManagedPath([string]$Path) {
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $true }                                    # não existe: livre
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { return $true }  # link nosso
    if ($item -isnot [IO.DirectoryInfo]) { return $false }                   # arquivo do usuário
    return Test-Path -LiteralPath (Join-Path $Path $managedMarker)           # cópia nossa
}

# Remove apenas o que o instalador criou. A versão anterior fazia
# `Remove-Item -Recurse` em qualquer coisa que estivesse no destino,
# apagando sem aviso um diretório do usuário — inclusive no -Uninstall.
function Remove-ManagedPath([string]$Path) {
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -eq $item) { return }
    if (-not (Test-ManagedPath $Path)) {
        Write-Warning "'$Path' não foi criado pelo instalador. Preservado — remova à mão se quiser."
        return
    }
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Remove-Item -Force -LiteralPath $Path
    } else {
        Remove-Item -Force -Recurse -LiteralPath $Path
    }
}

function Install-Entry([string]$Source, [string]$Target, [bool]$IsDirectory) {
    if (-not (Test-ManagedPath $Target)) {
        throw "'$Target' já existe e não foi criado pelo instalador. Remova ou renomeie e rode de novo."
    }
    Remove-ManagedPath $Target
    $parent = Split-Path -Parent $Target
    New-Item -ItemType Directory -Force -Path $parent | Out-Null

    if (-not $Copy) {
        try {
            $linkType = if ($IsDirectory) { "Junction" } else { "SymbolicLink" }
            New-Item -ItemType $linkType -Path $Target -Target $Source | Out-Null
            return "link"
        } catch {
            Write-Warning "Não foi possível criar link para '$Target'. Usando cópia."
        }
    }

    if ($IsDirectory) {
        Copy-Item -Recurse -Force -Path $Source -Destination $Target
        New-Item -ItemType File -Force -Path (Join-Path $Target $managedMarker) | Out-Null
    } else {
        Copy-Item -Force -Path $Source -Destination $Target
    }
    return "copy"
}

if ($Uninstall) {
    Write-Host "Removendo kata de $configRoot/skills..."
    foreach ($skill in $skills) {
        Remove-ManagedPath (Join-Path $configRoot "skills/$skill")
    }
    Write-Host "Kata removido."
    exit 0
}

New-Item -ItemType Directory -Force -Path (Join-Path $configRoot "skills") | Out-Null

foreach ($skill in $skills) {
    $source = Join-Path $kataRoot "claude-code/skills/$skill"
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "Skill não encontrada: $source"
    }
    $target = Join-Path $configRoot "skills/$skill"
    $mode = Install-Entry $source $target $true
    Write-Host "skills/$skill instalado como $mode."
}

Write-Host "Kata instalado em $configRoot. Use a skill kata no Claude Code."
