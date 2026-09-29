import os
import re
import sys
import json
import base64
import time
import glob
import random
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Set

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import kernel_logger
except ImportError:
    kernel_logger = None

def push_claro_log(msg: str, level: str = "info"):
    if kernel_logger:
        try:
            kernel_logger.push_kernel_log(msg, level=level)
        except Exception:
            pass
    print(f"[*] [Claro TV+] {msg}", flush=True)

# ==============================================================================
#  CONFIGURAÇÕES & DIRETÓRIOS
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLARO_DIR = os.path.join(BASE_DIR, "CLAROTV")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
HITS_DIR = os.path.join(BASE_DIR, "hits")
CLARO_ACTIVATED_FILE = os.path.join(RESULTS_DIR, "claro_tv_ativadas.txt")
CLARO_SESSIONS_FILE = os.path.join(HITS_DIR, "claro_sessions.json")
CLARO_INVALID_FILE = os.path.join(HITS_DIR, "contas_claro_invalidas.txt")
ACTIVATIONS_LOG_FILE = os.path.join(HITS_DIR, "ativacoes_tv.txt")

os.makedirs(CLARO_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(HITS_DIR, exist_ok=True)

# Lock de concorrência para operações de login e escrita
_CLARO_LOCK = threading.Lock()
_CLARO_BROWSER_LOCK = threading.Lock()

DEAD_CLARO_ACCOUNTS: Set[str] = set()
DEAD_CLARO_TIMESTAMPS: Dict[str, float] = {}
DEAD_FAIL_COOLDOWN = 600  # 10 minutos de cooldown se senha falhar

USED_CLARO_ACCOUNTS: Set[str] = set()
CLARO_LAST_USED_AT: Dict[str, float] = {}

# Cache em memória de sessões autenticadas: {user: {"cookies": dict, "xsrf": str, "timestamp": float}}
_CLARO_SESSIONS_CACHE: Dict[str, dict] = {}

def extrair_xsrf_token(avs_cookie_str: str) -> Optional[str]:
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

def _load_sessions_from_disk():
    global _CLARO_SESSIONS_CACHE
    if os.path.exists(CLARO_SESSIONS_FILE):
        try:
            with open(CLARO_SESSIONS_FILE, "r", encoding="utf-8") as f:
                _CLARO_SESSIONS_CACHE = json.load(f)
        except Exception:
            _CLARO_SESSIONS_CACHE = {}

def _save_sessions_to_disk():
    try:
        with open(CLARO_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_CLARO_SESSIONS_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Inicializa sessões salvas
_load_sessions_from_disk()

def is_account_dead(user: str) -> bool:
    u = str(user or "").strip().lower()
    if u in DEAD_CLARO_ACCOUNTS:
        fail_ts = DEAD_CLARO_TIMESTAMPS.get(u, 0.0)
        if time.time() - fail_ts > DEAD_FAIL_COOLDOWN:
            DEAD_CLARO_ACCOUNTS.discard(u)
            DEAD_CLARO_TIMESTAMPS.pop(u, None)
            return False
        return True
    return False

def mark_account_dead(user: str, reason: str = ""):
    u = str(user or "").strip().lower()
    if u:
        DEAD_CLARO_ACCOUNTS.add(u)
        DEAD_CLARO_TIMESTAMPS[u] = time.time()
        try:
            with open(CLARO_INVALID_FILE, "a", encoding="utf-8") as f:
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                f.write(f"{user} | {reason} | {now_str}\n")
        except Exception:
            pass

def record_claro_account_used(user: str):
    u = str(user or "").strip().lower()
    if u:
        USED_CLARO_ACCOUNTS.add(u)
        CLARO_LAST_USED_AT[u] = time.time()

def record_claro_activated(user: str, tv_code: str, details: str = ""):
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    entry = f"{user} | TV: {tv_code} | {details} | {now_str}\n"
    try:
        with open(CLARO_ACTIVATED_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    try:
        with open(ACTIVATIONS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[CLARO TV+] {entry}")
    except Exception:
        pass

# ==============================================================================
#  CARREGAMENTO E GESTÃO DE CONTAS CLARO TV+
# ==============================================================================
def load_all_claro_accounts(force_reload: bool = False) -> List[dict]:
    """Lê todas as contas de arquivos .txt e .csv dentro da pasta CLAROTV e hits/"""
    files = (
        glob.glob(os.path.join(CLARO_DIR, "*.txt")) +
        glob.glob(os.path.join(CLARO_DIR, "*.csv")) +
        glob.glob(os.path.join(HITS_DIR, "contas_claro*.txt"))
    )

    seen_paths = set()
    unique_files = []
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        norm = os.path.normcase(os.path.abspath(f))
        if norm not in seen_paths and not norm.endswith(".py") and "invalidas" not in norm and "ativadas" not in norm:
            seen_paths.add(norm)
            unique_files.append(f)

    seen_users = set()
    accounts = []

    for f in unique_files:
        fname = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for l in fh:
                    l = l.strip()
                    if not l or l.startswith("#"):
                        continue
                    user, pwd = None, None
                    if ":" in l:
                        user, pwd = l.split(":", 1)
                    elif "|" in l:
                        user, pwd = l.split("|", 1)
                    
                    if user and pwd:
                        user = user.strip()
                        pwd = pwd.strip()
                        u_low = user.lower()
                        if u_low not in seen_users:
                            seen_users.add(u_low)
                            accounts.append({
                                "file": fname,
                                "user": user,
                                "email": user,  # Compatibilidade com interface padrão
                                "password": pwd,
                                "info": {
                                    "email": user,
                                    "plan": "Claro TV+ 4K",
                                    "country": "BR",
                                    "flag": "🇧🇷"
                                },
                                "validated": False
                            })
        except Exception as e:
            push_claro_log(f"Erro ao ler contas de {f}: {e}", level="warn")

    # Ordenação justa Round-Robin:
    # 1. Contas ativas (fora do cooldown de erro)
    # 2. Contas menos recentemente usadas
    def sort_key(acc):
        u = acc["user"].lower()
        dead_score = 1000000000.0 if is_account_dead(u) else 0.0
        used_score = 100000.0 if u in USED_CLARO_ACCOUNTS else 0.0
        last_used = CLARO_LAST_USED_AT.get(u, 0.0)
        return (dead_score, used_score, last_used)

    accounts.sort(key=sort_key)
    return accounts

def find_claro_valid_account() -> Optional[dict]:
    """Retorna a próxima conta Claro TV+ pronta para ativação."""
    accounts = load_all_claro_accounts()
    if not accounts:
        return None

    healthy = [acc for acc in accounts if not is_account_dead(acc["user"])]
    if healthy:
        return healthy[0]

    # Se todas em cooldown, perdoa e tenta a primeira
    DEAD_CLARO_ACCOUNTS.clear()
    DEAD_CLARO_TIMESTAMPS.clear()
    return accounts[0]

def select_claro_account_by_identifier(identifier: str) -> Optional[dict]:
    """Seleciona conta por usuário/CPF ou nome do arquivo."""
    accounts = load_all_claro_accounts()
    target = identifier.strip().lower()
    for acc in accounts:
        if (acc["user"].lower() == target or
            acc["file"].lower() == target or
            target in acc["user"].lower()):
            return acc
    return None

def add_claro_single_account(user: str, password: str) -> bool:
    """Adiciona uma conta Claro TV+ ao arquivo CLAROTV/contas.txt."""
    fpath = os.path.join(CLARO_DIR, "contas.txt")
    try:
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(f"{user.strip()}:{password.strip()}\n")
        return True
    except Exception:
        return False

def add_claro_combos(raw_text: str) -> Tuple[int, str]:
    """Importa lista de contas Claro TV+ (usuario:senha)."""
    lines = raw_text.splitlines()
    valid_lines = []
    for l in lines:
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        if ":" in l:
            u, p = l.split(":", 1)
            valid_lines.append(f"{u.strip()}:{p.strip()}")
        elif "|" in l:
            u, p = l.split("|", 1)
            valid_lines.append(f"{u.strip()}:{p.strip()}")

    if not valid_lines:
        return 0, "Nenhuma conta válida no formato usuario:senha encontrada."

    fpath = os.path.join(CLARO_DIR, "contas.txt")
    try:
        with open(fpath, "a", encoding="utf-8") as f:
            for vl in valid_lines:
                f.write(vl + "\n")
        return len(valid_lines), f"{len(valid_lines)} contas Claro TV+ adicionadas com sucesso!"
    except Exception as e:
        return 0, f"Erro ao salvar arquivo: {e}"

def delete_claro_account(identifier: str) -> bool:
    """Remove uma conta específica de todos os arquivos em CLAROTV/ e hits/."""
    target = identifier.strip().lower()
    files = (
        glob.glob(os.path.join(CLARO_DIR, "*.txt")) +
        glob.glob(os.path.join(CLARO_DIR, "*.csv")) +
        glob.glob(os.path.join(HITS_DIR, "contas_claro*.txt"))
    )
    removed = False
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            new_lines = []
            for l in lines:
                l_strip = l.strip()
                if not l_strip or l_strip.startswith("#"):
                    new_lines.append(l)
                    continue
                user = ""
                if ":" in l_strip:
                    user = l_strip.split(":", 1)[0].strip()
                elif "|" in l_strip:
                    user = l_strip.split("|", 1)[0].strip()
                if user and (user.lower() == target or target in user.lower() or target in l_strip.lower()):
                    removed = True
                    continue
                new_lines.append(l)
            if removed:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
        except Exception:
            pass
    return removed

# ==============================================================================
#  AUTENTICAÇÃO PLAYWRIGHT & REQUISIÇÃO REST DE ATIVAÇÃO
# ==============================================================================
_PLAYWRIGHT_INSTALL_LOCK = threading.Lock()
_PLAYWRIGHT_INSTALLED = False

def ensure_playwright_browsers() -> bool:
    """Verifica e garante que o binário do Chromium para o Playwright esteja baixado no ambiente."""
    global _PLAYWRIGHT_INSTALLED
    if _PLAYWRIGHT_INSTALLED:
        return True

    with _PLAYWRIGHT_INSTALL_LOCK:
        if _PLAYWRIGHT_INSTALLED:
            return True
        try:
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    b = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    b.close()
                    _PLAYWRIGHT_INSTALLED = True
                    return True
            except Exception as e:
                err_str = str(e)
                if "Executable doesn't exist" in err_str or "playwright install" in err_str:
                    push_claro_log("Binário Chromium do Playwright ausente. Iniciando download automático...", level="warn")
                    import subprocess
                    cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    push_claro_log(f"Resultado do download Chromium: code={res.returncode}")
                    if res.returncode == 0:
                        _PLAYWRIGHT_INSTALLED = True
                        return True
                    cmd_fallback = ["playwright", "install", "chromium"]
                    res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=300)
                    if res2.returncode == 0:
                        _PLAYWRIGHT_INSTALLED = True
                        return True
        except Exception as ex:
            push_claro_log(f"Falha ao verificar/instalar navegador Playwright: {ex}", level="error")
        return False

def _realizar_login_playwright(username: str, password: str) -> Tuple[bool, dict, str]:
    """Executa login em segundo plano via Playwright headless e obtém cookies de sessão."""
    from playwright.sync_api import sync_playwright

    auth_cookies = {}
    push_claro_log(f"Iniciando navegador headless para autenticar conta '{username}'...")

    with _CLARO_BROWSER_LOCK:
        try:
            with sync_playwright() as p:
                common_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox"
                ]

                try:
                    browser = p.chromium.launch(headless=True, args=common_args)
                except Exception as launch_err:
                    err_msg = str(launch_err)
                    if "Executable doesn't exist" in err_msg or "playwright install" in err_msg:
                        push_claro_log("Navegador Playwright ausente detectado no momento da ativação. Baixando agora...", level="warn")
                        ensure_playwright_browsers()
                        browser = p.chromium.launch(headless=True, args=common_args)
                    else:
                        raise launch_err

                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
                    viewport={"width": 1366, "height": 768}
                )
                page = context.new_page()

                try:
                    try:
                        page.goto("https://www.clarotvmais.com.br/?redirectUri=/usuario/minha-conta/conectar-tv", wait_until="domcontentloaded", timeout=40000)
                    except Exception as goto_err:
                        push_claro_log(f"Aviso no goto Claro ({goto_err}), prosseguindo...")

                    # 1. Trata e remove banner de LGPD / OneTrust para não cobrir a tela
                    try:
                        cookie_btn = page.locator('#onetrust-accept-btn-handler')
                        if cookie_btn.is_visible(timeout=2000):
                            cookie_btn.click()
                    except Exception:
                        pass
                    try:
                        page.evaluate("() => { const ot = document.getElementById('onetrust-consent-sdk'); if (ot) ot.remove(); }")
                    except Exception:
                        pass

                    # 2. Se o campo #username ainda não estiver visível, clica no avatar/login
                    if not page.locator('#username').is_visible():
                        try:
                            page.locator('.user-avatar-button, .header-profile-login').first.click(timeout=6000)
                        except Exception:
                            page.evaluate('''() => {
                                const btn = document.querySelector('.user-avatar-button, .header-profile-login, [class*="avatar"]');
                                if (btn) btn.click();
                            }''')

                    # 3. Preenche usuário e senha
                    user_field = page.wait_for_selector('#username', timeout=15000)
                    user_field.fill(username)

                    pwd_field = page.wait_for_selector('#password', timeout=10000)
                    pwd_field.fill(password)

                    # 4. Envia o formulário e aguarda a autenticação
                    with page.expect_response(lambda r: "/avsclient/1.2/user/auth" in r.url, timeout=30000) as response_info:
                        page.locator('input[type="submit"], button[type="submit"]').first.click()

                    auth_response = response_info.value
                    status_http = auth_response.status

                    if status_http != 200:
                        try:
                            err_json = auth_response.json()
                            msg = err_json.get("message", "Usuário ou senha incorretos na Claro")
                        except Exception:
                            msg = f"HTTP {status_http}"
                        browser.close()
                        return False, {}, msg

                    time.sleep(1)

                    raw_cookies = context.cookies()
                    for c in raw_cookies:
                        auth_cookies[c['name']] = c['value']

                except Exception as e:
                    browser.close()
                    return False, {}, f"Erro de comunicação com portal Claro: {str(e)}"

                browser.close()

        except Exception as e:
            return False, {}, f"Erro ao executar Playwright: {str(e)}"

    if not auth_cookies.get("avs_cookie"):
        return False, {}, "Não foi possível obter o cookie de sessão 'avs_cookie'."

    return True, auth_cookies, "Login realizado com sucesso!"

def _enviar_codigo_tv(tv_code: str, auth_cookies: dict) -> Tuple[bool, str, dict]:
    """Envia código de ativação da TV via requisição PUT com headers e cookies de sessão."""
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

    try:
        resp = session.put(url_ativar, headers=headers, cookies=auth_cookies, json=payload, verify=False, timeout=25)
    except Exception as e:
        return False, f"Falha de conexão com API Claro: {str(e)}", {}

    if resp.status_code in (401, 403):
        return False, "SESSAO_EXPIRADA", {}

    try:
        resultado = resp.json()
    except Exception:
        resultado = {}

    status_txt = str(resultado.get("status", "")).upper()
    resp_txt = str(resultado.get("response", "")).lower()

    if resp.status_code == 200 or status_txt == "OK" or "success" in resp_txt or "validate with success" in resp_txt:
        return True, "🎉 TV ATIVADA COM SUCESSO NA CLARO TV+!", resultado
    else:
        msg = resultado.get("message") or resultado.get("response") or f"Falha na ativação ({resp.status_code})"
        return False, msg, resultado

def activate_claro_tv(tv_code: str, account_data: Optional[dict] = None) -> Tuple[bool, str, Optional[dict]]:
    """
    Ativa uma Smart TV na Claro TV+:
    1. Tenta sessão salva em cache (super rápido).
    2. Se não houver sessão ou estiver expirada, autentica via Playwright headless.
    3. Envia o código da Smart TV e valida resposta.
    """
    clean_code = re.sub(r'[^A-Za-z0-9]', '', str(tv_code)).upper()
    if not clean_code:
        return False, "Código de TV inválido.", None

    if not account_data:
        account_data = find_claro_valid_account()

    if not account_data:
        return False, "Nenhuma conta Claro TV+ disponível no momento. Adicione mais contas no painel.", None

    user = account_data.get("user") or account_data.get("email") or ""
    pwd = account_data.get("password") or ""
    user_key = user.strip().lower()

    push_claro_log(f"Iniciando pareamento Claro TV+ para TV {clean_code} com conta '{user}'...")

    # 1. Tenta sessão em cache se tiver menos de 8 horas
    cached_session = _CLARO_SESSIONS_CACHE.get(user_key)
    if cached_session and isinstance(cached_session, dict):
        cookies = cached_session.get("cookies", {})
        saved_at = cached_session.get("timestamp", 0)
        if cookies and (time.time() - saved_at < 28800):  # 8 horas
            push_claro_log(f"Usando sessão persistida para conta '{user}'...")
            succ, msg, res_json = _enviar_codigo_tv(clean_code, cookies)
            if succ:
                record_claro_account_used(user)
                record_claro_activated(user, clean_code, "Via sessão em cache")
                push_claro_log(f"✅ TV {clean_code} ativada com sucesso usando sessão em cache!", level="success")
                return True, "TV pareada e ativada com sucesso na Claro TV+!", account_data["info"]
            elif msg != "SESSAO_EXPIRADA":
                # Erro no código da TV
                push_claro_log(f"⚠️ Resposta da Claro TV+: {msg}", level="warn")
                return False, msg, None

    # 2. Login completo via Playwright headless
    push_claro_log(f"Autenticando conta Claro TV+ '{user}' via navegador...")
    login_ok, auth_cookies, login_msg = _realizar_login_playwright(user, pwd)
    if not login_ok:
        push_claro_log(f"❌ Falha no login Claro TV+: {login_msg}", level="error")
        mark_account_dead(user, login_msg)
        return False, f"Falha ao autenticar conta Claro: {login_msg}", None

    # Salva sessão autenticada em cache
    _CLARO_SESSIONS_CACHE[user_key] = {
        "cookies": auth_cookies,
        "xsrf": extrair_xsrf_token(auth_cookies.get("avs_cookie", "")),
        "timestamp": time.time()
    }
    _save_sessions_to_disk()

    # 3. Envia o código da TV
    push_claro_log(f"Enviando código TV {clean_code} para Claro TV+...")
    succ, msg, res_json = _enviar_codigo_tv(clean_code, auth_cookies)
    if succ:
        record_claro_account_used(user)
        record_claro_activated(user, clean_code, "Via Playwright login")
        push_claro_log(f"⚡ [Claro TV+] [SUCESSO] TV {clean_code} pareada e ativada com sucesso!", level="success")
        return True, "TV pareada e ativada com sucesso na Claro TV+!", account_data["info"]
    else:
        push_claro_log(f"⚠️ [Claro TV+] Falha ao parear TV: {msg}", level="warn")
        return False, msg or "Falha ao validar código na Claro TV+.", None
