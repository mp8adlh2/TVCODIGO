@echo off
chcp 65001 >nul
title ENVIAR ARQUIVOS PARA O GITHUB
color 0A

echo.
echo ========================================================
echo   ENVIANDO PROJETO COMPLETO PARA O SEU GITHUB PRIVADO
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/4] Adicionando arquivos e pastas...
git add .

echo [2/4] Gravando alterações...
git commit -m "Atualizacao completa do site e bot telegram"

echo [3/4] Conectando com seu repositorio mp8adlh2/ATIVAR...
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/mp8adlh2/ATIVAR.git

echo [4/4] Enviando arquivos...
echo Se abrir uma janela do navegador, confirme o login do seu GitHub.
echo.
git push -u origin main --force

echo.
echo ========================================================
echo   FINALIZADO COM SUCESSO!
echo ========================================================
echo.
pause
