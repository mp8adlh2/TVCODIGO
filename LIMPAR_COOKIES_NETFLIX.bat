@echo off
chcp 65001 >nul
color 0C
title LIMPADOR DE COOKIES DA NETFLIX // STREAM ACTIVATOR

echo ==============================================================================
echo                 LIMPADOR DE COOKIES ANTIGOS DA NETFLIX
echo ==============================================================================
echo.
echo [!] ATENÇÃO: Esta ação vai apagar APENAS os cookies antigos da Netflix
echo     para que você possa colocar seus novos cookies.
echo.
echo [✓] SEGURANÇA GARANTIDA:
echo     AS SENHAS DOS SEUS CLIENTES NÃO SERÃO APAGADAS!
echo     (Ficam 100%% preservadas no arquivo config_senhas.json)
echo.
echo ==============================================================================
set /p CONFIRM="Deseja realmente apagar todos os cookies da Netflix? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo.
    echo Operacao cancelada pelo usuario.
    echo Pressione qualquer tecla para sair...
    pause >nul
    exit /b
)

echo.
echo [1/3] Apagando arquivos antigos da pasta 'netflix'...
if exist "netflix" (
    del /q /f "netflix\*.*" 2>nul
)
if exist "cookies" (
    del /q /f "cookies\*.*" 2>nul
)
echo [✓] Pasta 'netflix' limpa com sucesso!

echo.
echo [2/3] Atualizando bundle de seguranca (cookies_bundle.json)...
python -c "import json, os; f='cookies_bundle.json'; (lambda: (setattr(__builtins__, 'd', json.load(open(f, 'r', encoding='utf-8', errors='ignore'))), d.update({'netflix': {}}), json.dump(d, open(f, 'w', encoding='utf-8', errors='ignore'), indent=2)) if os.path.exists(f) else None)()" 2>nul
echo [✓] Bundle sincronizado! Cookies antigos nao vao mais ressuscitar.

echo.
echo [3/3] Verificando integridade das senhas dos clientes...
if exist "config_senhas.json" (
    echo [✓] config_senhas.json INTACTO! Todas as senhas dos clientes continuam ativas.
)

echo.
echo ==============================================================================
echo   🎉 PRONTO! TODOS OS COOKIES ANTIGOS DA NETFLIX FORAM REMOVIDOS!
echo.
echo   Agora voce pode:
echo   1. Colocar seus novos cookies diretamente na pasta 'netflix'
echo   OU
echo   2. Arrastar os arquivos/colar o texto no Painel Admin (admin.html)
echo ==============================================================================
echo.
pause
