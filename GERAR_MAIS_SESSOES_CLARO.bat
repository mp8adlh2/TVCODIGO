@echo off
title Gerador e Renovador de Sessoes Claro TV+
color 0c
echo ==============================================================
echo    GERADOR DE SESSOES CLARO TV+ (VALIDADE ATE 2027)
echo ==============================================================
echo.
echo Este utilitario autentica as contas da pasta CLAROTV pelo seu
echo computador (IP Brasileiro) e salva as sessoes em hits/claro_sessions.json.
echo.
echo Com as sessoes salvas, as ativacoes na TV funcionam em 1 segundo
echo diretamente pela API oficial, sem precisar abrir navegador na nuvem!
echo.
set /p QUANTIDADE="Quantas contas novas deseja autenticar agora? (Padrao: 10): "
if "%QUANTIDADE%"=="" set QUANTIDADE=10

echo.
echo Autenticando %QUANTIDADE% contas... Aguarde...
echo.
python utilitarios/gerar_sessoes_claro.py %QUANTIDADE%

echo.
echo ==============================================================
echo Deseja enviar as sessoes geradas para o Render agora? (S/N)
echo ==============================================================
set /p ENVIAR="Digite S para enviar ou N para sair: "
if /i "%ENVIAR%"=="S" (
    git add hits/claro_sessions.json
    git commit -m "Novas sessoes Claro TV autenticadas e salvas"
    git push origin main
    echo.
    echo Pronto! As sessoes estao no ar no Render!
)

echo.
pause
