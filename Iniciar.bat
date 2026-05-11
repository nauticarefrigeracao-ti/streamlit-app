@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Analise Margem e Faturamento

echo.
echo  ============================================
echo   Analise de Margem e Faturamento - NTC
echo  ============================================
echo.

:: ── 1. Verifica se Python esta instalado ──────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python nao encontrado. Instalando automaticamente...
    echo      Isso so acontece na primeira execucao. Aguarde.
    echo.

    :: Cria pasta temporaria para o instalador
    if not exist "%~dp0_setup" mkdir "%~dp0_setup"

    :: Baixa Python 3.12 para Windows 64-bit
    set "PYTHON_URL=https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
    set "PYTHON_EXE=%~dp0_setup\python_installer.exe"

    echo  [.] Baixando Python (~25MB)...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_EXE%' -UseBasicParsing"

    if not exist "%PYTHON_EXE%" (
        echo.
        echo  [ERRO] Falha ao baixar Python. Verifique sua conexao com a internet.
        echo  Pressione qualquer tecla para fechar.
        pause >nul
        exit /b 1
    )

    echo  [.] Instalando Python silenciosamente...
    "%PYTHON_EXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=0

    :: Aguarda instalacao
    timeout /t 5 /nobreak >nul

    :: Atualiza PATH para a sessao atual
    for /f "tokens=*" %%i in ('powershell -Command "[System.Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i;%PATH%"

    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRO] Instalacao do Python falhou.
        echo  Instale manualmente em: https://www.python.org/downloads/
        echo  Pressione qualquer tecla para fechar.
        pause >nul
        exit /b 1
    )
    echo  [OK] Python instalado com sucesso.
    echo.
)

:: ── 2. Instala dependencias se necessario ────────────────────────────────────
set "SENTINEL=%~dp0_setup\.deps_ok"
if not exist "%SENTINEL%" (
    if not exist "%~dp0_setup" mkdir "%~dp0_setup"
    echo  [.] Instalando dependencias (so na primeira execucao)...
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo.
        echo  [ERRO] Falha ao instalar dependencias.
        echo  Pressione qualquer tecla para fechar.
        pause >nul
        exit /b 1
    )
    echo instalado > "%SENTINEL%"
    echo  [OK] Dependencias instaladas.
    echo.
)

:: ── 3. Inicia o app ───────────────────────────────────────────────────────────
echo  [.] Iniciando o sistema...
echo  [.] O navegador abrira automaticamente em alguns segundos.
echo.
echo  Para encerrar: feche esta janela ou pressione Ctrl+C
echo.

cd /d "%~dp0"
python -m streamlit run app\main.py --server.headless false --browser.gatherUsageStats false

if %errorlevel% neq 0 (
    echo.
    echo  [ERRO] O sistema encerrou com erro.
    echo  Pressione qualquer tecla para fechar.
    pause >nul
)
