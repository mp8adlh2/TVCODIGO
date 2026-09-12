@echo off
title Instalar Playwright Chromium no Windows
color 0A
cls
echo ===============================================================
echo      INSTALANDO PLAYWRIGHT CHROMIUM NO SEU WINDOWS
echo ===============================================================
echo.
echo [+] Instalando dependencias do requirements.txt...
pip install -r requirements.txt
echo.
echo [+] Baixando e configurando o navegador Chromium...
python -m playwright install chromium
echo.
echo ===============================================================
echo  CONCLUIDO! O Playwright esta pronto para uso no seu PC!
echo ===============================================================
pause
