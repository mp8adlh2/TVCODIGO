import os
import re
import json
import random
import glob
import requests
import time
import base64
import uuid
import sys
import shutil
import urllib3
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Set

try:
    import rich
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'rich'])
    import rich

from rich.console import Console

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
    sys.stdout.write("  \033[1;38;2;155;89;255m❯\033[0m \033[1;37m")
    sys.stdout.flush()
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\033[0m: \033[1;38;2;155;89;255m")
    sys.stdout.flush()

def render_cookie_ready_card(cookie_name: str, email: str, plan_name: str, country: str, region: str, remaining_count: int):
    console.print()
    console.print(f"  [bold #00FF66]●[/bold #00FF66] [bold white]CONTA HBO MAX PRONTA PARA ATIVAÇÃO[/bold white] [bold #00FF66]✔[/bold #00FF66]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #00E5FF]👤 CONTA:[/]     [bold white]{email}[/]")
    console.print(f"   [bold #FFD700]💎 PLANO:[/]     [bold #FFD700]{plan_name}[/] [grey50]•[/] [bold #A855F7]{region.upper()}[/] [grey50]•[/] [white]{country}[/]")
    console.print(f"   [#888888]🍪 COOKIE:[/]    [#888888]{cookie_name}[/]")
    console.print(f"   [#888888]🔄 DISPONÍVEIS:[/] [bold #00FF66]{remaining_count} cookies prontos[/]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print()

def box_success(tv_code: str, email: str, country: str, region: str, cookie_name: str, plan_name: str):
    console.print()
    console.print(f"  [bold #00FF66]✦✦✦ TV ATIVADA COM SUCESSO! ✦✦✦[/bold #00FF66]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #00E5FF]📺 CÓDIGO:[/]    [bold #00FF66]{tv_code}[/]")
    console.print(f"   [bold white]👤 TITULAR:[/]   [bold white]{email}[/]")
    console.print(f"   [bold #FFD700]💎 PLANO:[/]     [bold #FFD700]{plan_name}[/]")
    console.print(f"   [bold #00E5FF]🌍 PAÍS:[/]      [white]{country}[/]")
    console.print(f"   [bold #A855F7]📍 REGIÃO:[/]    [white]{region.upper()}[/]")
    console.print(f"   [#888888]📦 STATUS:[/]    [bold #00FF66]Ativado com sucesso (Cookie preservado)[/bold #00FF66]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print(f"   [bold #FFD700]🎬 Aproveite sua HBO Max na TV! 🎬[/bold #FFD700]")
    console.print()

def box_error(title: str, msgs: list, border: str = "#FF0033"):
    console.print()
    console.print(f"  [bold {border}]✖ {title}[/bold {border}]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    for m in msgs:
        console.print(f"   [white]• {m}[/white]")
    console.print(f"  [#444444]────────────────────────────────────────────────[/]")
    console.print()

def run_with_spinner(message: str, func, *args, **kwargs):
    with console.status(f"  [bold #A855F7]⚡[/] [white]{message}[/]", spinner="dots"):
        result = func(*args, **kwargs)
    return result

# ═══════════════════════════════════════════════════════════════
#  CONFIGURACOES HBO MAX
# ═══════════════════════════════════════════════════════════════
COOKIES_FOLDER = "hbomax" if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hbomax")) else ("cookies 01" if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies 01")) else "cookies")
USED_COOKIES_FOLDER = os.path.join(COOKIES_FOLDER, "used")
USED_REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "used_cookies.json")
REQUEST_TIMEOUT = 15
DEBUG = False

ENDPOINTS = {
    "amer": {
        "validate": "https://default.any-amer.prd.api.hbomax.com/authentication/linkDevice/validate",
        "connect": "https://default.any-amer.prd.api.hbomax.com/authentication/linkDevice/connect"
    },
    "emea": {
        "validate": "https://default.any-emea.prd.api.hbomax.com/authentication/linkDevice/validate",
        "connect": "https://default.any-emea.prd.api.hbomax.com/authentication/linkDevice/connect"
    },
    "latam": {
        "validate": "https://default.any-latam.prd.api.hbomax.com/authentication/linkDevice/validate",
        "connect": "https://default.any-latam.prd.api.hbomax.com/authentication/linkDevice/connect"
    },
    "apac": {
        "validate": "https://default.any-apac.prd.api.hbomax.com/authentication/linkDevice/validate",
        "connect": "https://default.any-apac.prd.api.hbomax.com/authentication/linkDevice/connect"
    }
}

country_codes = {
    "TR": "Turquia", "US": "Estados Unidos", "IN": "India",
    "GB": "Reino Unido", "FR": "Franca", "DE": "Alemanha",
    "ES": "Espanha", "IT": "Italia", "BR": "Brasil",
    "MX": "Mexico", "AR": "Argentina", "CA": "Canada",
    "AU": "Australia", "JP": "Japao", "KR": "Coreia do Sul",
    "TH": "Tailandia", "PL": "Polonia", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "UY": "Uruguai"
}

# ═══════════════════════════════════════════════════════════════
#  HISTORICO DE COOKIES UTILIZADOS (NUNCA REPETIR)
# ═══════════════════════════════════════════════════════════════
def load_used_tokens() -> Set[str]:
    used = set()
    if os.path.exists(USED_REGISTRY_FILE):
        try:
            with open(USED_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            if 'token_signature' in item:
                                used.add(item['token_signature'])
                            if 'filename' in item:
                                used.add(os.path.basename(item['filename']))
        except Exception:
            pass
    return used

def record_activation(filename: str, st_token: str, email: str, tv_code: str):
    base_name = os.path.basename(filename)
    token_sig = st_token[-32:] if st_token and len(st_token) >= 32 else st_token

    history = []
    if os.path.exists(USED_REGISTRY_FILE):
        try:
            with open(USED_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                if not isinstance(history, list):
                    history = []
        except Exception:
            history = []

    history.append({
        "filename": base_name,
        "token_signature": token_sig,
        "email": email,
        "tv_code": tv_code,
        "used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    try:
        with open(USED_REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  UTILITARIOS DE TOKEN E API
# ═══════════════════════════════════════════════════════════════
def decode_jwt(token: str) -> Optional[Dict]:
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            return json.loads(decoded)
        return None
    except Exception:
        return None

def extract_st_token(content: str) -> Optional[str]:
    match = re.search(r'^st:\s*(eyJ[A-Za-z0-9_\-\.]+)', content, re.MULTILINE)
    if match:
        return match.group(1)
    match = re.search(r'st=([^;\s]+)', content)
    if match:
        token = match.group(1)
        if len(token.split('.')) == 3:
            return token
    match = re.search(r'(eyJ[A-Za-z0-9_\-\.]+)', content)
    if match:
        token = match.group(1)
        if len(token.split('.')) == 3:
            return token
    return None

def get_region_from_jwt(st_token: str) -> str:
    decoded = decode_jwt(st_token)
    if decoded:
        subdivision = decoded.get('subdivision', '')
        if 'amer' in subdivision:
            return 'amer'
        elif 'emea' in subdivision:
            return 'emea'
        elif 'latam' in subdivision:
            return 'latam'
        elif 'apac' in subdivision:
            return 'apac'
    return 'amer'

def get_cookie_files() -> List[str]:
    base_d = os.path.dirname(os.path.abspath(__file__))
    folders = [os.path.join(base_d, "hbomax"), os.path.join(base_d, "cookies 01"), "hbomax", "cookies 01", "cookies"]
    all_files = []
    seen = set()
    for fold in folders:
        if os.path.exists(fold):
            for ext in ["*.txt", "*.json"]:
                for f in glob.glob(os.path.join(fold, "**", ext), recursive=True):
                    if os.path.isfile(f) and f not in seen:
                        seen.add(f)
                        all_files.append(f)
    return all_files

def get_all_available_cookies():
    files = get_cookie_files()
    if not files:
        return []

    cookies = []

    for filename in files:
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            st_token = extract_st_token(content)
            if st_token:
                decoded = decode_jwt(st_token)
                if decoded:
                    exp = decoded.get('exp', 0)
                    if exp:
                        exp_date = datetime.fromtimestamp(exp)
                        if exp_date < datetime.now():
                            continue
                cookies.append((filename, st_token, content))
        except Exception:
            pass

    random.shuffle(cookies)
    return cookies

def get_user_info(st_token: str, region: str) -> Optional[Dict]:
    url = f"https://default.beam-{region}.prd.api.hbomax.com/users/me"
    headers = {
        "accept": "*/*",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "cookie": f"st={st_token}",
        "origin": "https://play.hbomax.com",
        "referer": "https://play.hbomax.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-disco-client": "WEB:10:hbomax:7.4.0",
        "x-disco-params": "realm=bolt,bid=beam,features=ar",
        "x-device-info": "hbomax/7.4.0 (desktop/desktop; Windows/10; test/test)",
    }
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, verify=False)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def is_free_account(user_data: Dict) -> bool:
    if not user_data or 'data' not in user_data:
        return False
    attrs = user_data.get('data', {}).get('attributes', {})
    
    if attrs.get('isFree') is True or attrs.get('isTrial') is True:
        return True
    
    sub_status = str(attrs.get('subscriptionStatus', '') or attrs.get('status', '') or attrs.get('accountStatus', '')).lower()
    if sub_status in ['expired', 'inactive', 'canceled', 'cancelled', 'unsubscribed', 'suspended']:
        return True

    sub_type = str(attrs.get('subscriptionType', '')).lower()
    product_type = str(attrs.get('productType', '')).lower()
    if sub_type in ['free', 'none', 'unsubscribed'] or product_type in ['free', 'none']:
        return True

    if attrs.get('hasActiveSubscription') is False:
        return True

    return False

def get_plan_name(user_data: Dict) -> str:
    if not user_data or 'data' not in user_data:
        return "PREMIUM"
    attrs = user_data.get('data', {}).get('attributes', {})
    if is_free_account(user_data):
        return "FREE / SEM ASSINATURA"
    
    tier = attrs.get('tier', '') or attrs.get('productType', '') or attrs.get('subscriptionType', '')
    if tier and tier.lower() not in ['unknown', 'default', 'none']:
        return f"PREMIUM ({tier.upper()})"
    return "PREMIUM (Assinatura Ativa)"

def validate_and_get_info(st_token: str, region: str) -> Tuple[bool, str, str, bool, str]:
    user_data = get_user_info(st_token, region)
    if not user_data:
        return False, None, None, True, "Desconhecido"
    if 'data' in user_data and 'attributes' in user_data['data']:
        attrs = user_data['data']['attributes']
        email = attrs.get('username', '') or attrs.get('email', 'Desconhecido')
        if email and '@' not in email:
            email = f"{email}@hbomax.com"
        country = attrs.get('verifiedHomeTerritory', 'Desconhecido')
        if country in country_codes:
            country = country_codes[country]
        is_free = is_free_account(user_data)
        plan_name = get_plan_name(user_data)
        return True, email, country, is_free, plan_name
    return False, None, None, True, "Desconhecido"

def generate_device_info():
    device_id = str(uuid.uuid4())
    device_info = {
        "deviceId": device_id,
        "deviceName": "Chrome",
        "deviceModel": "Windows",
        "deviceType": "BROWSER",
        "osVersion": "10.0.0",
        "appVersion": "7.4.0",
        "manufacturer": "Google",
        "screenWidth": 1920,
        "screenHeight": 1080,
        "language": "pt-BR",
        "timezone": "America/Sao_Paulo"
    }
    return base64.b64encode(json.dumps(device_info).encode()).decode()

def activate_tv_code(st_token: str, tv_code: str, region: str) -> Tuple[bool, str]:
    device_info_b64 = generate_device_info()
    client_id = f"web_{uuid.uuid4().hex[:16]}"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "cookie": f"st={st_token}",
        "origin": "https://auth.hbomax.com",
        "referer": "https://auth.hbomax.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-disco-client": "WEB:10:hbomax:7.4.0",
        "x-disco-params": f"realm=bolt,bid=beam,features=ar,clientId={client_id}",
        "x-disco-device-info": device_info_b64,
        "x-device-info": "hbomax/7.4.0 (desktop/desktop; Windows/10; test/test)",
        "x-wbd-ace": "MjAyNi0wNi0xMVQxOTowNzo1M1p8VVMtQ0F8U0x8MVlOTg==",
        "x-wbd-device-consent": "gpc=0",
        "x-wbd-preferred-language": "pt-BR,pt",
        "x-wbd-time-zone": "America/Sao_Paulo",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    try:
        payload = {"linkingCode": tv_code}
        validate_url = ENDPOINTS[region]["validate"]
        connect_url = ENDPOINTS[region]["connect"]
        
        r1 = requests.post(validate_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT, verify=False)
        if r1.status_code in [200, 204]:
            r2 = requests.post(connect_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT, verify=False)
            if r2.status_code in [200, 204]:
                return True, "success"
            else:
                return False, "activation_failed"
        else:
            if r1.status_code == 400:
                try:
                    error_data = r1.json()
                    if 'errors' in error_data:
                        for error in error_data['errors']:
                            if error.get('code') == 'invalid.code':
                                return False, "invalid_code"
                            elif error.get('code') == 'expired.code':
                                return False, "expired_code"
                except Exception:
                    pass
            return False, "unknown_error"
    except Exception:
        return False, "exception"

# ═══════════════════════════════════════════════════════════════
#  BUSCA COM SPINNER ANIMADO (ESTILO NETFLIX)
# ═══════════════════════════════════════════════════════════════
def find_next_valid_cookie() -> Optional[dict]:
    available = get_all_available_cookies()
    total = len(available)

    if total == 0:
        return None

    with console.status("  [bold #A855F7]⚡[/bold #A855F7] [bold white]Buscando cookie com assinatura ativa...[/bold white]", spinner="dots") as status_bar:
        for idx, (filename, st_token, content) in enumerate(available, 1):
            cookie_name = os.path.basename(filename)
            disp_name = cookie_name if len(cookie_name) <= 25 else (cookie_name[:22] + "...")
            status_bar.update(f"  [bold #A855F7]⚡[/bold #A855F7] [bold white]Buscando conta com assinatura...[/bold white] [#888888](Testando {idx}/{total}: {disp_name})[/#888888]")

            region = get_region_from_jwt(st_token)
            valid, email, country, is_free, plan_name = validate_and_get_info(st_token, region)

            if valid and not is_free:
                return {
                    "filename": filename,
                    "st_token": st_token,
                    "region": region,
                    "email": email,
                    "country": country,
                    "plan_name": plan_name
                }
            elif not valid:
                pass

    return None

def run_activation_cycle():
    clear_screen()
    console.print()

    # 1. Procura com animação spinner o cookie válido
    cookie_data = find_next_valid_cookie()

    if not cookie_data:
        box_error("SEM CONTAS VÁLIDAS COM ASSINATURA", [
            "Nenhum cookie com assinatura PREMIUM ativa foi encontrado na pasta 'cookies/'.",
            "Verifique se há cookies válidos e pressione ENTER."
        ])
        console.print("  [#888888]❯ Pressione [ENTER] para tentar novamente...[/#888888]")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
        return

    # 2. Exibe o card minimalista e limpo
    filename = cookie_data["filename"]
    st_token = cookie_data["st_token"]
    region = cookie_data["region"]
    email = cookie_data["email"]
    country = cookie_data["country"]
    plan_name = cookie_data["plan_name"]
    cookie_name = os.path.basename(filename)
    remaining = len(get_all_available_cookies())

    render_cookie_ready_card(cookie_name, email, plan_name, country, region, remaining)

    # 3. Solicita o código da TV com animação
    animated_prompt_text("DIGITE O CÓDIGO DA TV")
    try:
        tv_code = input().strip()
        sys.stdout.write("\033[0m")
        sys.stdout.flush()
    except (KeyboardInterrupt, EOFError):
        return

    if tv_code.lower() in ('sair', 'exit', 'quit', 'q', 'fechar'):
        console.print("\n[#888888]Encerrando... Até logo![/#888888]\n")
        sys.exit(0)

    if not re.match(r'^\d{6}$', tv_code):
        box_error("CÓDIGO INVÁLIDO", [
            "O código deve conter exatamente 6 dígitos numéricos.",
            "Exemplo: 123456"
        ])
        time.sleep(2)
        return

    console.print()
    now = datetime.now().strftime("%H:%M:%S")
    console.print(f"  [#666666]{now}[/#666666]  [bold #00E5FF]🚀[/bold #00E5FF]  [bold white]Enviando ativação para a TV ({tv_code})...[/bold white]")

    # 4. Ativação com spinner
    success, status_msg = run_with_spinner("Pareando TV com a HBO Max...", lambda: activate_tv_code(st_token, tv_code, region))

    if success:
        record_activation(filename, st_token, email, tv_code)
        box_success(tv_code, email, country, region, cookie_name, plan_name)
    else:
        if status_msg == "invalid_code":
            box_error("CÓDIGO INVÁLIDO", [
                f"O código '{tv_code}' foi recusado pela HBO Max.",
                "Verifique o código na tela da sua TV e tente novamente."
            ])
        elif status_msg == "expired_code":
            box_error("CÓDIGO EXPIRADO", [
                f"O código '{tv_code}' expirou na tela da TV.",
                "Gere um novo código de 6 dígitos na sua TV."
            ], border="#FFD700")
        elif status_msg == "activation_failed":
            box_error("FALHA NA ATIVAÇÃO", [
                "A HBO Max não concluiu a conexão com a TV.",
                "Verifique a conexão da sua TV e tente novamente."
            ])
        else:
            box_error("ERRO NA ATIVAÇÃO", [
                f"Status: {status_msg}",
                "Tente novamente em instantes."
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
            console.print("\n  [bold #A855F7]❯[/bold #A855F7] [white]Ativador finalizado. Até logo![/white]\n")
            sys.exit(0)
        except Exception as e:
            box_error("ERRO INESPERADO", [str(e)])
            time.sleep(2)

if __name__ == "__main__":
    main()