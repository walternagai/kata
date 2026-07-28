[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Copy
)

$ErrorActionPreference = "Stop"

$kataRoot = Split-Path -Parent $PSScriptRoot
$configRoot = if ($env:OPENCODE_CONFIG_DIR) {
    $env:OPENCODE_CONFIG_DIR
} else {
    Join-Path $HOME ".config/opencode"
}

$agentSource = Join-Path $kataRoot "opencode/agent/kata.md"
$agentTarget = Join-Path $configRoot "agent/kata.md"
$skills = @(
    "kata-fit", "kata-question", "kata-think", "kata-simplify", "kata-intent",
    "kata-surgical", "kata-verify", "kata-artifact", "kata-report", "kata-judge"
)

function Remove-ManagedPath([string]$Path) {
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            Remove-Item -Force -LiteralPath $Path
        } else {
            Remove-Item -Force -Recurse -LiteralPath $Path
        }
    }
}

function Install-Entry([string]$Source, [string]$Target, [bool]$IsDirectory) {
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
    } else {
        Copy-Item -Force -Path $Source -Destination $Target
    }
    return "copy"
}

if ($Uninstall) {
    Write-Host "Removendo kata de $configRoot..."
    Remove-ManagedPath $agentTarget
    foreach ($skill in $skills) {
        Remove-ManagedPath (Join-Path $configRoot "skills/$skill")
    }
    Write-Host "Kata removido. Reinicie o OpenCode se ele estiver em execução."
    exit 0
}

if (-not (Test-Path -LiteralPath $agentSource -PathType Leaf)) {
    throw "Agente não encontrado: $agentSource"
}

New-Item -ItemType Directory -Force -Path (Join-Path $configRoot "agent") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $configRoot "skills") | Out-Null

$agentMode = Install-Entry $agentSource $agentTarget $false
Write-Host "agent/kata.md instalado como $agentMode."

foreach ($skill in $skills) {
    $source = Join-Path $kataRoot "opencode/skills/$skill"
    $target = Join-Path $configRoot "skills/$skill"
    $mode = Install-Entry $source $target $true
    Write-Host "skills/$skill instalado como $mode."
}

Write-Host "Kata instalado em $configRoot. Reinicie o OpenCode para usar @kata."
