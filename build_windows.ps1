#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$VenvDir   = Join-Path $env:TEMP '.hives_build_venv'
$DistDir   = Join-Path $ScriptDir 'dist'

# Buscar un intérprete de Python 3
$PyExe  = $null
$PyArgs = @()

if ($env:PYTHON) {
    $PyExe = $env:PYTHON
}

# Probar py -3.x (launcher de Windows)
if (-not $PyExe -and (Get-Command 'py' -ErrorAction SilentlyContinue)) {
    $PyExe  = 'py'
}

# Probar python directamente
if (-not $PyExe -and (Get-Command 'python' -ErrorAction SilentlyContinue)) {
    $PyExe = 'python'
}

if (-not $PyExe) {
    Write-Host "No se encontró un intérprete de Python."
    if (-not (Get-Command 'uv' -ErrorAction SilentlyContinue)) {
        Write-Host "Instalando uv para provisionar Python..."
        Invoke-RestMethod 'https://astral.sh/uv/install.ps1' | Invoke-Expression
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    Write-Host "Descargando Python 3 con uv..."
    & uv python install 3
    $PyExe = (& uv python find 3).Trim()
}

$verStr = (& $PyExe @PyArgs --version 2>&1)
Write-Host "Usando interprete: $PyExe $($PyArgs -join ' ') ($verStr)"

$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if (Test-Path $VenvDir) {
    Remove-Item -Recurse -Force $VenvDir
}

Write-Host "Creando entorno virtual..."
& $PyExe @PyArgs -m venv $VenvDir

$VenvPip = Join-Path $VenvDir 'Scripts\pip.exe'

& $VenvPython -m pip install --upgrade pip -q
& $VenvPip install -r (Join-Path $ScriptDir 'requirements.txt') -q
& $VenvPip install pyinstaller -q

Write-Host "Ejecutando PyInstaller..."
& (Join-Path $VenvDir 'Scripts\pyinstaller.exe') (Join-Path $ScriptDir 'HIVES.spec') --clean --noconfirm

Write-Host ""
Write-Host "Ejecutable en: $DistDir\HIVES\HIVES.exe"
