@echo off
title ENVIAR PARA O GITHUB (TVCODIGO)
color 0A
cd /d "%~dp0"
echo =======================================================
echo   ENVIANDO PARA O REPOSITORIO DO SEU SITE (TVCODIGO)
echo =======================================================
echo.
git add -A
git commit -m "Ativacao do bot Telegram VIP integrado ao site"
git push -u origin main --force
echo.
echo =======================================================
echo   ENVIADO COM SUCESSO!
echo =======================================================
pause
