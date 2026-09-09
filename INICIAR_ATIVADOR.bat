@echo off
title Ativador Streaming - Netflix & HBO Max
color 0C
cls
echo ===============================================================
echo     INICIANDO PAINEL DE ATIVACAO: NETFLIX ^& HBO MAX
echo ===============================================================
echo.
echo  [+] Finalizando processos anteriores na porta 5000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul
echo  [+] Abrindo navegador em http://localhost:5000...
echo  [+] Servidor local iniciando...
echo.
start http://localhost:5000
python app.py
pause
