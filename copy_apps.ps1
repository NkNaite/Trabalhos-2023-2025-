$ErrorActionPreference = 'Stop'

$repoRoot = "D:\caça de emprego\Trabalhos\Projetos_Automacao_Backend"
New-Item -ItemType Directory -Force -Path $repoRoot

# ----------------------------------------------------
# 1. PaxDei_Tool
# ----------------------------------------------------
$paxDest = "$repoRoot\PaxDei_Market_App"
New-Item -ItemType Directory -Force -Path $paxDest

$paxSrc = "D:\PaxDei_Tool"

# Pastas a copiar
$paxFolders = @("src", "etl", "scripts")
foreach ($folder in $paxFolders) {
    if (Test-Path "$paxSrc\$folder") {
        Copy-Item -Path "$paxSrc\$folder" -Destination "$paxDest" -Recurse -Force
    }
}

# Arquivos raiz a copiar
$paxFiles = @("Guia_Estoque_Crafting.md", "mapeamento_regioes.md", "README.md", "start_dashboard.bat", "stop_dashboard.bat")
foreach ($file in $paxFiles) {
    if (Test-Path "$paxSrc\$file") {
        Copy-Item -Path "$paxSrc\$file" -Destination "$paxDest" -Force
    }
}

# ----------------------------------------------------
# 2. Sucram
# ----------------------------------------------------
$sucDest = "$repoRoot\Sucram_Video_Scene_Finder"
New-Item -ItemType Directory -Force -Path $sucDest

$sucSrc = "D:\Sucram\video-scene-finder"

# Arquivos raiz a copiar
$sucFiles = @(
    "gui_app.py", "main.py", "download_clip.py", "download_to_drive.py",
    "README.md", "PASSO_A_PASSO_CONFIGURACAO.md", "analise_downloader.md", 
    "requirements.txt", "build.bat"
)
foreach ($file in $sucFiles) {
    if (Test-Path "$sucSrc\$file") {
        Copy-Item -Path "$sucSrc\$file" -Destination "$sucDest" -Force
    }
}

Write-Host "Copy completed successfully."
