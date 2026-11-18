@echo off
chcp 65001 >nul
title INSTALADOR DO BOT TELEGRAM - ATIVADOR VIP
color 0A

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      INSTALADOR BOT TELEGRAM VIP             ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Instalando dependencias do bot Telegram...
echo.

python -m pip install python-telegram-bot==20.7

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║           INSTALACAO CONCLUIDA!              ║
echo  ║                                              ║
echo  ║  PROXIMO PASSO:                              ║
echo  ║  1. Abra o arquivo telegram_bot.py           ║
echo  ║  2. Cole seu TOKEN na linha BOT_TOKEN        ║
echo  ║  3. Execute INICIAR_BOT_TELEGRAM.bat         ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
