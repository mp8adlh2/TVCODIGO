@echo off
title Enviar Projeto para o GitHub - TVCODIGO
color 0B
cls
echo ===============================================================
echo        ENVIANDO ARQUIVOS PARA O GITHUB (TVCODIGO)
echo ===============================================================
echo.

:: 1. Configura usuario padrao do Git caso nao exista
git config user.name >nul 2>&1
if %errorlevel% neq 0 (
    git config --global user.name "Ativador"
    git config --global user.email "ativador@local.com"
)

:: 2. Inicializa o Git se necessario
if not exist ".git" (
    echo [+] Inicializando repositorio Git local...
    git init
)

:: 3. Adiciona todos os arquivos
echo [+] Preparando todos os arquivos e pastas de cookies...
git add -A

:: 4. Cria o commit inicial
echo [+] Criando commit...
git commit -m "Deploy Painel Ativador Netflix e HBO Max"

:: 5. Define branch main
git branch -M main

:: 6. Conecta ao repositorio
echo [+] Conectando ao repositorio https://github.com/mp8adlh2/TVCODIGO.git ...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/mp8adlh2/TVCODIGO.git

:: 7. Envia para o GitHub
echo [+] Enviando tudo para o GitHub...
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ===============================================================
    echo  SUCESSO! Todos os arquivos e cookies estao no GitHub!
    echo ===============================================================
    echo.
    echo Agora va no https://render.com e clique em 'Manual Deploy' ou crie o Web Service!
) else (
    echo.
    echo [!] Se abrir uma janela do GitHub no navegador, clique em 'Authorize/Sign in'.
)

echo.
pause
