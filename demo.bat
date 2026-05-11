@echo off
title NTC — Demo Analise de Margem
cd /d %~dp0

echo.
echo  ============================================
echo   Grupo Nautica Refrigeracao -- Demo ao vivo
echo  ============================================
echo.
echo  [1/2] Iniciando Streamlit...
start "Streamlit NTC" cmd /k streamlit run app/main.py

echo  Aguardando app subir (6s)...
timeout /t 6 /nobreak > nul

echo.
echo  [2/2] Abrindo tunnel Cloudflare...
echo  Procure a linha "trycloudflare.com" abaixo e mande essa URL pro seu chefe!
echo  NAO feche esta janela enquanto o demo estiver rodando.
echo.

where cloudflared >nul 2>&1
if %errorlevel% == 0 (
    cloudflared tunnel --url http://localhost:8501
) else (
    "%LOCALAPPDATA%\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel --url http://localhost:8501
)
