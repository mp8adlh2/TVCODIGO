@echo off
title Enviar Atualizacoes para o GitHub - TVCODIGO
color 0B
cls
echo ===============================================================
echo        ENVIANDO ATUALIZACOES PARA O GITHUB (TVCODIGO)
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

:: 3. Sincroniza bundle de cookies e contas
echo [+] Sincronizando cookies, combos e configuracoes de senhas...
python -c "import app; app.sync_cookies_bundle()" >nul 2>&1

:: 4. Adiciona todos os arquivos
echo [+] Preparando todos os arquivos, painel admin e scripts...
git add -A

:: 5. Cria o commit com data e hora
set DATA_HORA=%date% %time%
echo [+] Criando commit das atualizacoes (%DATA_HORA%)...
git commit -m "Atualizacao: Painel Admin, exclusao de contas por topico, senhas personalizadas e correcoes (%DATA_HORA%)"

:: 6. Define branch main
git branch -M main

:: 7. Conecta ao repositorio oficial
echo [+] Configurando repositorio https://github.com/mp8adlh2/TVCODIGO.git ...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/mp8adlh2/TVCODIGO.git

:: 8. Envia para o GitHub
echo [+] Enviando atualizacoes para o GitHub...
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ===============================================================
    echo  SUCESSO! Todos os arquivos foram atualizados no GitHub!
    echo ===============================================================
    echo.
    echo Se voce usa o Render.com, as alteracoes serao aplicadas
    echo automaticamente (ou clique em 'Manual Deploy').
) else (
    echo.
    echo ===============================================================
    echo  [!] Atencao: Se abriu uma janela do GitHub, faca o login.
    echo ===============================================================
)

echo.
pause
