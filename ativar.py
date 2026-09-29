import os
import sys
import time
import json
import base64
import glob
import requests
import urllib3
from playwright.sync_api import sync_playwright

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
console = Console()

PASTA_CONTAS = "CLAROTV"

def extrair_xsrf_token(avs_cookie_str):
    """Extrai o xsrfToken do payload JWT contido em avs_cookie"""
    try:
        parts = avs_cookie_str.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload_b64))
            return data.get("xsrfToken")
    except Exception:
        pass
    return None

def carregar_contas():
    """Lê todas as contas de arquivos .txt dentro da pasta CLAROTV"""
    contas = []
    if not os.path.exists(PASTA_CONTAS):
        os.makedirs(PASTA_CONTAS, exist_ok=True)

    arquivos = glob.glob(os.path.join(PASTA_CONTAS, "*.txt"))
    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha or linha.startswith("#"):
                        continue
                    if ":" in linha:
                        user, pwd = linha.split(":", 1)
                    elif "|" in linha:
                        user, pwd = linha.split("|", 1)
                    else:
                        continue
                    contas.append({"user": user.strip(), "pass": pwd.strip()})
        except Exception as e:
            console.print(f"[red]Erro ao ler arquivo {arq}: {e}[/red]")
    return contas

def banner_principal(total_contas):
    os.system("cls" if os.name == "nt" else "clear")
    conteudo = f"""[bold cyan]⚡ ATIVADOR AUTOMÁTICO CLARO TV+ ⚡[/bold cyan]
[dim]Login Seguro em Segundo Plano + Ativação via Requests[/dim]

[bold yellow]Contas carregadas:[/bold yellow] [bold green]{total_contas}[/bold green]
[dim]• Rotação automática de contas ativada[/dim]
[dim]• Digite [bold red]'sair'[/bold red] para encerrar o programa[/dim]"""
    console.print(Panel(conteudo, border_style="bright_blue", box=box.ROUNDED, expand=False))

def executar_login_e_ativar(username, password, tv_code):
    auth_cookies = {}

    with console.status(f"[cyan]Autenticando conta [bold white]{username}[/bold white]...", spinner="dots"):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
                viewport={"width": 1366, "height": 768}
            )
            page = context.new_page()

            try:
                # Carrega o site da Claro
                page.goto("https://www.clarotvmais.com.br/?redirectUri=/usuario/minha-conta/conectar-tv", wait_until="load", timeout=60000)

                # Fecha o aviso de cookies da LGPD se aparecer para não cobrir botões
                try:
                    cookie_btn = page.locator('#onetrust-accept-btn-handler')
                    if cookie_btn.is_visible(timeout=2000):
                        cookie_btn.click()
                except Exception:
                    pass

                # Aguarda com certeza o botão de login aparecer e clica
                btn_perfil = page.wait_for_selector('.user-avatar-button, .header-profile-login, [aria-label*="usuário deslogado"]', timeout=15000)
                btn_perfil.click()

                # Aguarda o campo de usuário aparecer
                user_field = page.wait_for_selector('#username', timeout=10000)
                user_field.fill(username)

                pwd_field = page.wait_for_selector('#password', timeout=10000)
                pwd_field.fill(password)

                # Aguarda especificamente a resposta da API da Claro após clicar em Enviar
                with page.expect_response(lambda r: "/avsclient/1.2/user/auth" in r.url, timeout=30000) as response_info:
                    page.locator('input[type="submit"]').click()

                auth_response = response_info.value
                status_http = auth_response.status

                if status_http != 200:
                    try:
                        err_json = auth_response.json()
                        msg = err_json.get("message", "Usuário ou senha incorretos")
                    except Exception:
                        msg = f"HTTP {status_http}"
                    console.print(f"[bold red]✖ Erro no login Claro ({status_http}): {msg}[/bold red]")
                    browser.close()
                    return False

                # Aguarda 1 segundo para garantir que todos os cookies foram persistidos
                time.sleep(1)

                raw_cookies = context.cookies()
                for c in raw_cookies:
                    auth_cookies[c['name']] = c['value']

            except Exception as e:
                console.print(f"[bold red]✖ Falha na comunicação com a Claro: {e}[/bold red]")
                browser.close()
                return False

            browser.close()

    if not auth_cookies.get("avs_cookie"):
        console.print("[bold red]✖ Não foi possível obter o cookie de sessão da Claro.[/bold red]")
        return False

    console.print("[bold green]✔ Login realizado com sucesso![/bold green]")

    with console.status(f"[yellow]Enviando código [bold cyan]{tv_code}[/bold cyan] para a TV...", spinner="bouncingBar"):
        avs_cookie = auth_cookies.get("avs_cookie", "")
        xsrf = extrair_xsrf_token(avs_cookie)

        url_ativar = "https://www.clarotvmais.com.br/avsclient/auth/token?channel=PCTV"
        headers = {
            "host": "www.clarotvmais.com.br",
            "sec-ch-ua-platform": '"Windows"',
            "x-xsrf-token": xsrf or "",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://www.clarotvmais.com.br",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.clarotvmais.com.br/usuario/minha-conta/conectar-tv",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "priority": "u=1, i"
        }

        payload = {"token": str(tv_code).strip()}
        session = requests.Session()
        resp = session.put(url_ativar, headers=headers, cookies=auth_cookies, json=payload, verify=False)

    try:
        resultado = resp.json()
        if resp.status_code == 200 or resultado.get("status") == "OK":
            console.print(Panel(
                f"[bold green]🎉 TV ATIVADA COM SUCESSO! 🎉[/bold green]\n"
                f"[white]Código:[/white] [bold cyan]{tv_code}[/bold cyan]\n"
                f"[white]Conta Utilizada:[/white] [bold magenta]{username}[/bold magenta]\n"
                f"[white]Resposta Claro:[/white] [dim]{resultado.get('response', 'Token validate with success')}[/dim]",
                border_style="green",
                box=box.ROUNDED
            ))
            return True
        else:
            status_claro = resultado.get("status", f"HTTP {resp.status_code}")
            msg = resultado.get("message", "Erro ao validar código da TV")
            console.print(Panel(
                f"[bold red]✖ FALHA NA ATIVAÇÃO DA TV[/bold red]\n"
                f"[white]Status:[/white] [yellow]{status_claro}[/yellow]\n"
                f"[white]Mensagem:[/white] {msg}\n"
                f"[white]Código testado:[/white] [cyan]{tv_code}[/cyan]",
                border_style="red",
                box=box.ROUNDED
            ))
            return False
    except Exception as e:
        console.print(f"[bold red]Erro ao processar resposta da Claro: {e} ({resp.text})[/bold red]")
        return False

def main():
    indice_conta_atual = 0

    while True:
        contas = carregar_contas()
        if not contas:
            os.system("cls" if os.name == "nt" else "clear")
            console.print(Panel(
                "[bold red]Nenhuma conta encontrada![/bold red]\n\n"
                f"Adicione suas contas na pasta [bold cyan]'{PASTA_CONTAS}/'[/bold cyan] em um arquivo [bold white]contas.txt[/bold white].\n"
                "[yellow]Formato (uma por linha):[/yellow] [dim]usuario:senha[/dim]",
                border_style="red",
                box=box.ROUNDED
            ))
            input("\nPressione Enter após adicionar as contas...")
            continue

        banner_principal(len(contas))

        conta_selecionada = contas[indice_conta_atual % len(contas)]
        console.print(f"[bold yellow]Próxima conta ({indice_conta_atual % len(contas) + 1}/{len(contas)}):[/bold yellow] [bold magenta]{conta_selecionada['user']}[/bold magenta]")

        codigo = Prompt.ask("\n[bold cyan]Digite o Código da TV[/bold cyan]").strip()

        if not codigo:
            continue

        if codigo.lower() in ["sair", "exit", "quit", "q"]:
            console.print("\n[bold green]Encerrando o programa. Até mais![/bold green]")
            break

        # Faz o login da conta e ativa a TV
        executar_login_e_ativar(conta_selecionada["user"], conta_selecionada["pass"], codigo)

        # Alterna para a próxima conta da pasta
        indice_conta_atual = (indice_conta_atual + 1) % len(contas)

        console.print("\n[dim]Pressione Enter para ativar a próxima TV ou digite 'sair'...[/dim]")
        opcao = input().strip()
        if opcao.lower() in ["sair", "exit", "quit", "q"]:
            console.print("\n[bold green]Encerrando o programa. Até mais![/bold green]")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Programa interrompido.[/bold yellow]")
        sys.exit(0)
