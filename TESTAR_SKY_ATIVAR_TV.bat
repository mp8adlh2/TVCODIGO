@echo off
chcp 65001 >nul
title TESTADOR DE ATIVACAO SKY+ (TV PAIRING)
color 0b

echo =====================================================================
echo           TESTADOR INDEPENDENTE DE ATIVACAO SKY+ / SMART TV
echo =====================================================================
echo.
echo Este script executara o teste isolado:
echo 1. Abre o Google Chrome/Chromium visivel na sua tela
echo 2. Acessa https://www.skymais.com.br e loga como Cliente SKY
echo 3. Navega para https://www.skymais.com.br/ativar-tv
echo 4. Preenche o codigo da TV e confirma a ativacao!
echo.
echo =====================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no seu PATH.
    echo Por favor, instale o Python e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

python testar_sky_ativartv.py

echo.
pause
