#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$VenvDir   = Join-Path $env:TEMP '.hives_build_venv'
$DistDir   = Join-Path $ScriptDir 'dist'

#Versiones compatibles de python para TensoreFlow
$TF_MIN_MINOR = 9
$TF_MAX_MINOR = 13

function Get-PyMinor {
    param([string]$Exe, [string[]]$ExeArgs = @())
    try {
        $out = & $Exe @ExeArgs -c 'import sys; print(sys.version_info[1])' 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        return [int]($out | Select-Object -First 1)
    } catch {
        return $null
    }
}

function Test-Compatible {
    param([string]$Exe, [string[]]$ExeArgs = @())
    $minor = Get-PyMinor -Exe $Exe -ExeArgs $ExeArgs
    if ($null -eq $minor) { return $false }
    return ($minor -ge $TF_MIN_MINOR) -and ($minor -le $TF_MAX_MINOR)
}

$PyExe  = $null
$PyArgs = @()

#Vemos compatiblidad de la versión de python instalada
if ($env:PYTHON) {
    if (Test-Compatible -Exe $env:PYTHON) {
        $PyExe = $env:PYTHON
    } else {
        Write-Error "`$env:PYTHON ($($env:PYTHON)) no es compatible con TensorFlow (requiere 3.$TF_MIN_MINOR-3.$TF_MAX_MINOR)."
        exit 1
    }
}

#Probamos si hay más versioens instaladas
if (-not $PyExe -and (Get-Command 'py' -ErrorAction SilentlyContinue)) {
    foreach ($minor in $TF_MAX_MINOR..$TF_MIN_MINOR) {
        $verArg = @("-3.$minor")
        if (Test-Compatible -Exe 'py' -ExeArgs $verArg) {
            $PyExe  = 'py'
            $PyArgs = $verArg
            break
        }
    }
}

#Proamos otros nombres 
if (-not $PyExe) {
    foreach ($cand in @('python', 'python3')) {
        if ((Get-Command $cand -ErrorAction SilentlyContinue) -and (Test-Compatible -Exe $cand)) {
            $PyExe = $cand
            break
        }
    }
}

# Si no hemos encontrado una verisón compatible, la instamaos con uv
if (-not $PyExe) {
    Write-Host "No se encontro un Python compatible con TensorFlow (3.$TF_MIN_MINOR-3.$TF_MAX_MINOR)."
    if (-not (Get-Command 'uv' -ErrorAction SilentlyContinue)) {
        Write-Host "Instalando uv para provisionar Python 3.$TF_MAX_MINOR..."
        Invoke-RestMethod 'https://astral.sh/uv/install.ps1' | Invoke-Expression
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    }
    Write-Host "Descargando Python 3.$TF_MAX_MINOR con uv..."
    & uv python install "3.$TF_MAX_MINOR"
    $PyExe = (& uv python find "3.$TF_MAX_MINOR").Trim()
}

$verStr = (& $PyExe @PyArgs --version 2>&1)
Write-Host "Usando interprete: $PyExe $($PyArgs -join ' ') ($verStr)"

$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
if ((Test-Path $VenvDir) -and -not (Test-Compatible -Exe $VenvPython)) {
    Write-Host "El venv existente usa un Python incompatible; recreandolo..."
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creando entorno virtual..."
    & $PyExe @PyArgs -m venv $VenvDir
}

$VenvPip = Join-Path $VenvDir 'Scripts\pip.exe'

& $VenvPython -m pip install --upgrade pip -q
& $VenvPip install -r (Join-Path $ScriptDir 'requirements.txt') -q
& $VenvPip install pyinstaller -q

Write-Host "Ejecutando PyInstaller..."
& (Join-Path $VenvDir 'Scripts\pyinstaller.exe') (Join-Path $ScriptDir 'HIVES.spec') --clean --noconfirm

Write-Host ""
Write-Host "Ejecutable en: $DistDir\HIVES\HIVES.exe"
