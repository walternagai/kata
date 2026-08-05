[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$Copy
)

$ErrorActionPreference = "Stop"

# Posse de caminho — tabela de decisão de Test-ManagedPath:
#
#   estado do destino                     instalar        desinstalar
#   ------------------------------------  --------------  ----------------
#   não existe                            cria            nada a fazer
#   link/junction (nosso)                 substitui       remove
#   cópia nossa (está no manifesto)       recopia         remove
#   diretório com marcador legado         recopia         remove
#   qualquer outra coisa (do usuário)     throw           avisa e preserva
#
# Verificação: este script não foi executado — não há PowerShell no ambiente
# em que foi escrito. A tabela acima é o contrato a conferir.


$kataRoot = Split-Path -Parent $PSScriptRoot
$configRoot = if ($env:OPENCODE_CONFIG_DIR) {
    $env:OPENCODE_CONFIG_DIR
} else {
    Join-Path $HOME ".config/opencode"
}

$agentSource = Join-Path $kataRoot "opencode/agent/kata.md"
$agentTarget = Join-Path $configRoot "agent/kata.md"
# A lista vem do filesystem — ver comentário equivalente nos scripts .sh.
$skillsRoot = Join-Path $kataRoot "opencode/skills"
$skills = Get-ChildItem -Directory -Path $skillsRoot | Select-Object -ExpandProperty Name | Sort-Object
if ($skills.Count -eq 0) { throw "Nenhuma skill encontrada em $skillsRoot" }

# O instalador REGISTRA o que criou, em vez de tentar inferir do filesystem.
# Inferir não funcionava para arquivo: o marcador só podia ser gravado dentro
# de um diretório, então a cópia do agente não era reconhecida pelo próprio
# instalador — não se conseguia desinstalar (avisava "Preservado") nem
# reinstalar (`throw`), travando o modo -Copy após a primeira instalação.
$managedMarker = ".kata-managed"   # legado: instalações antigas marcavam por dentro
$manifestPath = Join-Path $configRoot ".kata-manifest"

function Get-Manifest() {
    if (Test-Path -LiteralPath $manifestPath) {
        return @(Get-Content -LiteralPath $manifestPath | Where-Object { $_ -ne "" })
    }
    return @()
}

function Add-ToManifest([string]$Path) {
    $atual = Get-Manifest
    if ($atual -notcontains $Path) {
        Set-Content -LiteralPath $manifestPath -Value (@($atual) + $Path)
    }
}

function Test-ManagedPath([string]$Path, [string]$ExpectedSource = "") {
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -eq $item) { return $true }                                    # não existe: livre
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        if ([string]::IsNullOrWhiteSpace($ExpectedSource)) { return $false }
        $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue).Path
        $expected = (Resolve-Path -LiteralPath $ExpectedSource -ErrorAction SilentlyContinue).Path
        return $resolved -and $expected -and $resolved -ieq $expected
    }
    if ((Get-Manifest) -contains $Path) { return $true }                     # cópia nossa
    # Compatibilidade com instalações anteriores, que marcavam o diretório.
    return ($item -is [IO.DirectoryInfo]) -and
           (Test-Path -LiteralPath (Join-Path $Path $managedMarker))
}

# Remove apenas o que o instalador criou. A versão anterior fazia
# `Remove-Item -Recurse` em qualquer coisa que estivesse no destino,
# apagando sem aviso um diretório do usuário — inclusive no -Uninstall.
function Remove-ManagedPath([string]$Path, [string]$ExpectedSource = "") {
    $item = Get-Item -Force -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($null -eq $item) { return }
    if (-not (Test-ManagedPath $Path $ExpectedSource)) {
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
    if (-not (Test-ManagedPath $Target $Source)) {
        throw "'$Target' já existe e não foi criado pelo instalador. Remova ou renomeie e rode de novo."
    }
    Remove-ManagedPath $Target $Source
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
    Add-ToManifest $Target
    return "copy"
}

if ($Uninstall) {
    Write-Host "Removendo kata de $configRoot..."
    Remove-ManagedPath $agentTarget $agentSource
    foreach ($skill in $skills) {
        Remove-ManagedPath (Join-Path $configRoot "skills/$skill") (Join-Path $kataRoot "opencode/skills/$skill")
    }
    # O manifesto registra cópias; depois de removê-las ele não deve
    # sobreviver apontando para caminhos que já não existem.
    if (Test-Path -LiteralPath $manifestPath) { Remove-Item -Force -LiteralPath $manifestPath }
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
