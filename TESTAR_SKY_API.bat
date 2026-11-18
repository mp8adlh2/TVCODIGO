@echo off
chcp 65001 >nul
title TESTADOR SKY+ ATIVACAO VIA API PURA (SEM NAVEGADOR)
color 0b

echo =====================================================================
echo           TESTADOR SKY+ SMART TV - 100%% VIA REQUISICAO HTTP API
echo             (Sem Playwright, sem Chromium, sem Janelas)
echo =====================================================================
echo.

python testar_sky_api.py

echo.
pause
