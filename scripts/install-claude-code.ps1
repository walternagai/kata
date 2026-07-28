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

$skills = @(
    "kata", "kata-fit", "kata-question", "kata-think", "kata-simplify", "kata-intent",
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
