@echo off
title Atualizando Git e Render...
color 0b
echo ==============================================
echo    ENVIANDO ATUALIZACOES PARA O GITHUB...
echo ==============================================
echo.

:: Vai para a pasta do script
cd /d "%~dp0"

:: Adiciona todos os arquivos alterados
git add .

:: Cria o commit com a data e hora atual
git commit -m "Auto deploy Render: %date% %time%"

:: Envia para o GitHub (tenta main e master)
git push origin main || git push origin master

echo.
echo ==============================================
echo    PRONTO! O RENDER JA ESTA ATUALIZANDO!
echo ==============================================
echo.
timeout /t 5