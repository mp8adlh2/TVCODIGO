@echo off
title Atualizando Git e Render...
color 0b
echo ===============================================================
echo     SINCRONIZANDO SENHAS E ENVIANDO PARA O GITHUB / RENDER
echo ===============================================================
echo.

:: Vai para a pasta do script
cd /d "%~dp0"

:: 1. Baixa e unifica as senhas mais recentes do Render para nunca perder senhas de clientes
python utilitarios\sincronizar_senhas_nuvem.py

echo.
echo  [2/4] Indexando arquivos com senhas protegidas...
git add .

echo  [3/4] Criando commit...
git commit -m "Auto deploy Render com senhas sincronizadas: %date% %time%"

echo  [4/4] Enviando para o GitHub...
git push origin main || git push origin master

echo.
echo ===============================================================
echo    PRONTO! AS SENHAS FORAM PRESERVADAS E O RENDER JA ATUALIZOU!
echo ===============================================================
echo.
timeout /t 5