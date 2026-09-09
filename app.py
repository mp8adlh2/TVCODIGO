import os
import re
import json
import glob
import random
import uuid
import base64
import urllib3
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import socketserver
import hmac
import secrets
import threading
import time
import concurrent.futures
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Set

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações de Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NETFLIX_COOKIES_FOLDER = os.path.join(BASE_DIR, "netflix")
HBO_COOKIES_FOLDER = os.path.join(BASE_DIR, "hbomax")
USED_REGISTRY_FILE = os.path.join(BASE_DIR, "used_cookies.json")
COOKIES_BUNDLE_FILE = os.path.join(BASE_DIR, "cookies_bundle.json")
PORT = int(os.environ.get("PORT", 5000))

def sync_cookies_bundle():
    """Garante suporte total às pastas netflix e hbomax (com retrocompatibilidade para cookies e cookies 01)."""
    os.makedirs(NETFLIX_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(HBO_COOKIES_FOLDER, exist_ok=True)
    
    # Migra automaticamente arquivos antigos se existirem
    old_netflix = os.path.join(BASE_DIR, "cookies")
    old_hbo = os.path.join(BASE_DIR, "cookies 01")
    if os.path.exists(old_netflix):
        for f in glob.glob(os.path.join(old_netflix, "*.*")):
            dest = os.path.join(NETFLIX_COOKIES_FOLDER, os.path.basename(f))
            if not os.path.exists(dest):
                try:
                    with open(f, 'rb') as r_in, open(dest, 'wb') as r_out:
                        r_out.write(r_in.read())
                except Exception:
                    pass

    if os.path.exists(old_hbo):
        for f in glob.glob(os.path.join(old_hbo, "*.*")):
            dest = os.path.join(HBO_COOKIES_FOLDER, os.path.basename(f))
            if not os.path.exists(dest):
                try:
                    with open(f, 'rb') as r_in, open(dest, 'wb') as r_out:
                        r_out.write(r_in.read())
                except Exception:
                    pass

    # 1. Se o bundle existir, restaura as pastas no servidor
    if os.path.exists(COOKIES_BUNDLE_FILE):
        try:
            with open(COOKIES_BUNDLE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            for fname, content in data.get("netflix", {}).items():
                dest = os.path.join(NETFLIX_COOKIES_FOLDER, fname)
                if not os.path.exists(dest):
                    with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                        out.write(content)
                        
            for fname, content in data.get("hbo", {}).items():
                dest = os.path.join(HBO_COOKIES_FOLDER, fname)
                if not os.path.exists(dest):
                    with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                        out.write(content)
        except Exception:
            pass

    # 2. Salva todos os cookies locais no arquivo único cookies_bundle.json
    bundle = {"netflix": {}, "hbo": {}}
    for n_dir in [NETFLIX_COOKIES_FOLDER, old_netflix]:
        if os.path.exists(n_dir):
            for f in glob.glob(os.path.join(n_dir, "*.txt")) + glob.glob(os.path.join(n_dir, "*.json")):
                try:
                    with open(f, 'r', encoding='utf-8', errors='ignore') as inf:
                        bundle["netflix"][os.path.basename(f)] = inf.read()
                except Exception:
                    pass

    for h_dir in [HBO_COOKIES_FOLDER, old_hbo]:
        if os.path.exists(h_dir):
            for f in glob.glob(os.path.join(h_dir, "*.txt")) + glob.glob(os.path.join(h_dir, "*.json")):
                try:
                    with open(f, 'r', encoding='utf-8', errors='ignore') as inf:
                        bundle["hbo"][os.path.basename(f)] = inf.read()
                except Exception:
                    pass

    if bundle["netflix"] or bundle["hbo"]:
        try:
            with open(COOKIES_BUNDLE_FILE, 'w', encoding='utf-8', errors='ignore') as outf:
                json.dump(bundle, outf)
        except Exception:
            pass

sync_cookies_bundle()

# Cache de cookies e estados em memória
USED_NETFLIX_COOKIES: Set[str] = set()
USED_HBO_COOKIES: Set[str] = set()

# Histórico
history_lock = threading.Lock()

def load_history() -> List[dict]:
    with history_lock:
        if os.path.exists(USED_REGISTRY_FILE):
            try:
                with open(USED_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

def record_history_entry(service: str, filename: str, email: str, tv_code: str, plan: str = "", status: str = "Sucesso"):
    with history_lock:
        history = []
        if os.path.exists(USED_REGISTRY_FILE):
            try:
                with open(USED_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history = data
            except Exception:
                history = []
        
        history.insert(0, {
            "service": service,
            "filename": os.path.basename(filename) if filename else "cookie",
            "email": email,
            "tv_code": tv_code,
            "plan": plan,
            "status": status,
            "used_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        })

        try:
            with open(USED_REGISTRY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════
#  INTEGRAÇÃO NETFLIX (MOTOR PROVADO TV2.PY COM VALIDAÇÃO REAL)
# ═══════════════════════════════════════════════════════════════
import tv2

USED_NETFLIX_COOKIES = tv2.USED_COOKIES
ACTIVE_PLAN = {"netflix": "TODOS", "hbo": "TODOS"}

# Cache de cookies testados e validados ao vivo
VALID_NETFLIX_LOCK = threading.Lock()
VALID_NETFLIX_BY_FILE: Dict[str, dict] = {}
VALID_NETFLIX_POOL: List[dict] = []
DEAD_NETFLIX_COOKIES: Set[str] = set()

# HBO Valid Pool
VALID_HBO_LOCK = threading.Lock()
VALID_HBO_BY_FILE: Dict[str, dict] = {}
VALID_HBO_POOL: List[dict] = []

def get_netflix_files() -> List[str]:
    return tv2.get_available_cookie_files()

def classify_plan(filename: str, plan_text: str = "") -> str:
    combined = f"{filename} {plan_text}".lower()
    if any(k in combined for k in ['premium', 'cao cấp', 'uhd', '4k', 'vip', 'مميزة']):
        return 'PREMIUM'
    elif any(k in combined for k in ['com anúncio', 'with ads', 'with advert', 'avec pub', 'mit werbung', 'con anuncios', 'con pubblicità', 'reklam']):
        return 'COM ANÚNCIOS'
    elif any(k in combined for k in ['padrão', 'standard', 'estándar', 'standart', 'tiêu chuẩn', 'fhd', '1080', 'giá chuẩn', 'standardowy', 'قياسية', 'סטנדרטית']):
        return 'PADRÃO'
    elif any(k in combined for k in ['básico', 'basic', 'basis', 'dasar', 'essentiel', 'mobile', 'podstawowy', 'أساسية']):
        return 'BÁSICO'
    return 'PADRÃO'

def test_netflix_cookie_file(fpath: str, timeout: float = 4.0) -> Optional[dict]:
    """Testa se o arquivo de cookie possui sessão real ativa na Netflix."""
    if not os.path.exists(fpath):
        return None
    bname = os.path.basename(fpath)
    if fpath in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or fpath in DEAD_NETFLIX_COOKIES:
        return None

    with VALID_NETFLIX_LOCK:
        if fpath in VALID_NETFLIX_BY_FILE and fpath not in DEAD_NETFLIX_COOKIES:
            return VALID_NETFLIX_BY_FILE[fpath]

    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        parsed = tv2.load_cookies(raw)
        if not parsed or "SecureNetflixId" not in parsed:
            DEAD_NETFLIX_COOKIES.add(fpath)
            return None

        # Validação real contra os servidores da Netflix
        acc_info = tv2.check_account(parsed, timeout=timeout)
        if not acc_info:
            DEAD_NETFLIX_COOKIES.add(fpath)
            return None

        cat = classify_plan(bname, acc_info.get("plan", ""))
        acc_info["category"] = cat

        entry = {
            "file": fpath,
            "parsed": parsed,
            "info": acc_info,
            "validated": True
        }

        with VALID_NETFLIX_LOCK:
            VALID_NETFLIX_BY_FILE[fpath] = entry
            if not any(e["file"] == fpath for e in VALID_NETFLIX_POOL):
                VALID_NETFLIX_POOL.append(entry)

        return entry
    except Exception:
        DEAD_NETFLIX_COOKIES.add(fpath)
        return None

def get_verified_netflix_cookies(min_count: int = 3) -> List[dict]:
    """Retorna cookies Netflix válidos usando verificação paralela ultrarrápida."""
    with VALID_NETFLIX_LOCK:
        alive = [e for e in VALID_NETFLIX_POOL if e["file"] not in DEAD_NETFLIX_COOKIES and e["file"] not in tv2.USED_COOKIES]

    if len(alive) >= min_count:
        return alive

    files = get_netflix_files()
    untested = [
        f for f in files 
        if f not in tv2.USED_COOKIES 
        and os.path.basename(f) not in tv2.USED_COOKIES 
        and f not in DEAD_NETFLIX_COOKIES 
        and not any(e["file"] == f for e in alive)
    ]

    # Testa em paralelo com ThreadPoolExecutor para ser instantâneo
    if untested:
        batch = untested[:8]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = executor.map(lambda f: test_netflix_cookie_file(f, timeout=3.5), batch)
            for res in results:
                if res and res not in alive:
                    alive.append(res)

    return alive

def find_netflix_valid_cookie(target_plan: str = "TODOS", exclude_file: str = "") -> Optional[dict]:
    """Retorna o primeiro cookie válido disponível e pronto para uso."""
    verified = get_verified_netflix_cookies(min_count=1)
    for entry in verified:
        f = entry["file"]
        bname = os.path.basename(f)
        if f in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or f in DEAD_NETFLIX_COOKIES or f == exclude_file or bname == exclude_file:
            continue
        return entry

    # Fallback se a pool estiver vazia
    files = get_netflix_files()
    for f in files:
        bname = os.path.basename(f)
        if f in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or f in DEAD_NETFLIX_COOKIES or f == exclude_file or bname == exclude_file:
            continue
        res = test_netflix_cookie_file(f, timeout=3.5)
        if res:
            return res

    return None

# Alias de compatibilidade
find_netflix_fast_cookie = find_netflix_valid_cookie

def select_netflix_cookie_by_filename(filename: str) -> Optional[dict]:
    """Seleciona com precisão o cookie solicitado pelo usuário."""
    fpath = os.path.join(NETFLIX_COOKIES_FOLDER, os.path.basename(filename))
    if not os.path.exists(fpath):
        # Tenta busca flexível por nome parcial / email
        for f in get_netflix_files():
            if filename in os.path.basename(f) or filename in f:
                fpath = f
                break

    if not os.path.exists(fpath):
        return None

    # Se já foi validado e está vivo no cache
    with VALID_NETFLIX_LOCK:
        if fpath in VALID_NETFLIX_BY_FILE and fpath not in DEAD_NETFLIX_COOKIES:
            return VALID_NETFLIX_BY_FILE[fpath]

    # Validação ao vivo
    res = test_netflix_cookie_file(fpath, timeout=5.0)
    if res:
        return res

    DEAD_NETFLIX_COOKIES.add(fpath)
    return None

# ═══════════════════════════════════════════════════════════════
#  ⚡ SESSÃO PRÉ-AQUECIDA PARA ATIVAÇÃO INSTANTÂNEA (<500ms)
# ═══════════════════════════════════════════════════════════════
PREWARMED_NETFLIX: Dict[str, dict] = {}
PREWARMED_LOCK = threading.Lock()

def prewarm_netflix_cookie(cookie_data: dict):
    """Pré-aquece a sessão da Netflix em background para ativação com zero delay."""
    if not cookie_data or "parsed" not in cookie_data:
        return
    fpath = cookie_data.get("file", "")
    try:
        session = tv2.get_session()
        tv2.set_cookies_on_session(session, cookie_data["parsed"])
        auth_url = tv2.extract_auth_url(session)
        if auth_url:
            with PREWARMED_LOCK:
                PREWARMED_NETFLIX[fpath] = {
                    "session": session,
                    "auth_url": auth_url,
                    "time": time.time()
                }
    except Exception:
        pass

def activate_netflix_tv(tv_code: str, cookie_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Ativação ultrarrápida aproveitando a sessão pré-aquecida ou fallback padrão."""
    fpath = cookie_data.get("file", "")
    prew = None
    with PREWARMED_LOCK:
        if fpath in PREWARMED_NETFLIX and (time.time() - PREWARMED_NETFLIX[fpath]["time"] < 240):
            prew = PREWARMED_NETFLIX.pop(fpath)

    if prew:
        session = prew["session"]
        auth_url = prew["auth_url"]
        ok, reason = tv2.activate_tv_code(session, tv_code, auth_url)
        if ok:
            return True, "TV pareada e ativada com sucesso na Netflix!", cookie_data.get("info")
        elif reason in ("invalid_code", "expired_code", "already_used"):
            msg_map = {
                "invalid_code": "Código inválido. Digite o código exibido na TV.",
                "expired_code": "Código expirou na TV. Gere um novo código na TV.",
                "already_used": "Código já utilizado anteriormente.",
            }
            return False, msg_map.get(reason, reason), None
        else:
            return tv2.activate_with_cookie(cookie_data, tv_code)
    else:
        return tv2.activate_with_cookie(cookie_data, tv_code)




# ═══════════════════════════════════════════════════════════════
#  LÓGICA HBO MAX
# ═══════════════════════════════════════════════════════════════
HBO_ENDPOINTS = {
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

COUNTRY_MAP = {
    "TR": "Turquia", "US": "Estados Unidos", "IN": "Índia",
    "GB": "Reino Unido", "FR": "França", "DE": "Alemanha",
    "ES": "Espanha", "IT": "Itália", "BR": "Brasil",
    "MX": "México", "AR": "Argentina", "CA": "Canadá",
    "AU": "Austrália", "JP": "Japão", "KR": "Coreia do Sul",
    "TH": "Tailândia", "PL": "Polônia", "CL": "Chile",
    "CO": "Colômbia", "PE": "Peru", "UY": "Uruguai"
}

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

def extract_hbo_st_token(content: str) -> Optional[str]:
    match = re.search(r'^st:\s*(eyJ[A-Za-z0-9_\-\.]+)', content, re.MULTILINE)
    if match:
        return match.group(1)
    match = re.search(r'st=([^;\s]+)', content)
    if match:
        t = match.group(1)
        if len(t.split('.')) == 3:
            return t
    match = re.search(r'(eyJ[A-Za-z0-9_\-\.]+)', content)
    if match:
        t = match.group(1)
        if len(t.split('.')) == 3:
            return t
    return None

def get_hbo_region_from_jwt(st_token: str) -> str:
    decoded = decode_jwt(st_token)
    if decoded:
        sub = decoded.get('subdivision', '')
        if 'amer' in sub:
            return 'amer'
        elif 'emea' in sub:
            return 'emea'
        elif 'latam' in sub:
            return 'latam'
        elif 'apac' in sub:
            return 'apac'
    return 'amer'

def get_hbo_files() -> List[str]:
    files = []
    for h_dir in [HBO_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies 01")]:
        if os.path.exists(h_dir):
            files += glob.glob(os.path.join(h_dir, "*.txt")) + glob.glob(os.path.join(h_dir, "*.json"))
    
    unique_files = []
    seen = set()
    for f in files:
        if f not in seen and f not in USED_HBO_COOKIES:
            seen.add(f)
            unique_files.append(f)
    return unique_files

def get_hbo_user_info(st_token: str, region: str) -> Optional[Dict]:
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
        res = requests.get(url, headers=headers, timeout=4, verify=False)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None

def is_hbo_free(user_data: Dict) -> bool:
    if not user_data or 'data' not in user_data:
        return True
    attrs = user_data.get('data', {}).get('attributes', {})
    if attrs.get('isFree') is True or attrs.get('isTrial') is True:
        return True
    sub_status = str(attrs.get('subscriptionStatus', '') or attrs.get('status', '') or attrs.get('accountStatus', '') or attrs.get('billingStatus', '')).lower()
    if sub_status in ['expired', 'inactive', 'canceled', 'cancelled', 'unsubscribed', 'suspended', 'past_due', 'pastdue', 'billing_issue', 'grace_period', 'hold', 'payment_failed']:
        return True
    if attrs.get('hasActiveSubscription') is False:
        return True
    return False

def get_verified_hbo_cookies(min_count: int = 3) -> List[dict]:
    """Retorna a lista de cookies HBO Max válidos e pré-testados."""
    with VALID_HBO_LOCK:
        alive = [e for e in VALID_HBO_POOL if e["file"] not in USED_HBO_COOKIES]

    if len(alive) >= min_count:
        return alive

    files = get_hbo_files()
    for filename in files:
        if len(alive) >= max(min_count, 8):
            break
        if filename in USED_HBO_COOKIES or any(e["file"] == filename for e in alive):
            continue
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            st_token = extract_hbo_st_token(content)
            if not st_token:
                USED_HBO_COOKIES.add(filename)
                continue
            decoded = decode_jwt(st_token)
            if decoded:
                exp = decoded.get('exp', 0)
                if exp and datetime.fromtimestamp(exp) < datetime.now():
                    USED_HBO_COOKIES.add(filename)
                    continue
            region = get_hbo_region_from_jwt(st_token)
            
            user_data = get_hbo_user_info(st_token, region)
            if not user_data or is_hbo_free(user_data):
                USED_HBO_COOKIES.add(filename)
                continue

            attrs = user_data.get('data', {}).get('attributes', {})
            email = attrs.get('username', '') or attrs.get('email', 'Usuario_HBO')
            if email and '@' not in email:
                email = f"{email}@hbomax.com"
            raw_country = attrs.get('verifiedHomeTerritory', 'BR')
            country = COUNTRY_MAP.get(raw_country, raw_country)
            tier = attrs.get('tier', '') or attrs.get('productType', '') or "PREMIUM"
            plan = f"HBO Max {tier.upper()}"

            entry = {
                "file": filename,
                "st_token": st_token,
                "region": region,
                "info": {
                    "email": email,
                    "plan": plan,
                    "country": country,
                    "region": region.upper()
                }
            }
            with VALID_HBO_LOCK:
                VALID_HBO_BY_FILE[filename] = entry
                if not any(e["file"] == filename for e in VALID_HBO_POOL):
                    VALID_HBO_POOL.append(entry)
            alive.append(entry)
        except Exception:
            USED_HBO_COOKIES.add(filename)
            continue
    return alive

def find_hbo_valid_cookie() -> Optional[dict]:
    verified = get_verified_hbo_cookies(min_count=1)
    if verified:
        return verified[0]
    return None

def activate_hbo_tv(tv_code: str, cookie_data: dict) -> Tuple[bool, str, Optional[dict]]:
    clean_code = re.sub(r'[^0-9]', '', tv_code)
    if len(clean_code) != 6:
        return False, "O código HBO Max deve conter exatamente 6 dígitos numéricos (ex: 123456).", None

    if not cookie_data:
        return False, "Nenhum cookie HBO Max selecionado.", None

    st_token = cookie_data["st_token"]
    region = cookie_data["region"]
    filename = cookie_data["file"]

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
    device_info_b64 = base64.b64encode(json.dumps(device_info).encode()).decode()
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
    payload = {"linkingCode": clean_code}
    try:
        val_url = HBO_ENDPOINTS[region]["validate"]
        con_url = HBO_ENDPOINTS[region]["connect"]
        r1 = requests.post(val_url, headers=headers, json=payload, timeout=15, verify=False)
        if r1.status_code in [200, 204]:
            r2 = requests.post(con_url, headers=headers, json=payload, timeout=15, verify=False)
            if r2.status_code in [200, 204]:
                USED_HBO_COOKIES.add(filename)
                record_history_entry("HBO Max", filename, cookie_data["info"]["email"], clean_code, cookie_data["info"]["plan"], "Sucesso")
                return True, "TV pareada e ativada com sucesso na HBO Max!", cookie_data["info"]
            else:
                USED_HBO_COOKIES.add(filename)
                return False, "Falha na etapa de conexão final com a TV na HBO Max.", None
        else:
            if r1.status_code == 400:
                try:
                    err = r1.json()
                    err_code = err.get('errors', [{}])[0].get('code', '')
                    if err_code == 'invalid.code':
                        return False, f"O código '{clean_code}' é inválido. Digite o código exibido na TV.", None
                    elif err_code == 'expired.code':
                        return False, f"O código '{clean_code}' expirou na TV. Gere um novo código de 6 dígitos.", None
                except Exception:
                    pass
            USED_HBO_COOKIES.add(filename)
            return False, "A sessão deste cookie HBO Max expirou. Próximo cookie pronto!", None
    except Exception as e:
        USED_HBO_COOKIES.add(filename)
        return False, f"Erro de conexão com os servidores da HBO Max: {str(e)}", None

def select_hbo_cookie_by_filename(filename: str) -> Optional[dict]:
    fpath = os.path.join(HBO_COOKIES_FOLDER, os.path.basename(filename))
    if not os.path.exists(fpath):
        return None
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        st_token = extract_hbo_st_token(content)
        if not st_token:
            return None

        bname = os.path.basename(fpath)
        email = bname.split('_')[0] if '_' in bname else bname
        country = "BR" if "_br_" in bname.lower() else "LATAM"
        plan = "HBO Max VIP"
        region = get_hbo_region_from_jwt(st_token)

        user_data = get_hbo_user_info(st_token, region)
        if user_data:
            attrs = user_data.get('data', {}).get('attributes', {})
            real_email = attrs.get('username', '') or attrs.get('email', '')
            if real_email:
                email = real_email
            raw_country = attrs.get('verifiedHomeTerritory', country)
            country = COUNTRY_MAP.get(raw_country, raw_country)
            tier = attrs.get('tier', '') or attrs.get('productType', '') or "PREMIUM"
            plan = f"HBO Max {tier.upper()}"

        return {
            "file": fpath,
            "st_token": st_token,
            "region": region,
            "info": {
                "email": email,
                "plan": plan,
                "country": country,
                "region": region.upper()
            }
        }
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════════
#  SERVIDOR HTTP & API REST
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
#  AUTENTICAÇÃO & SEGURANÇA REFORÇADA (HARDENED SECURITY)
# ═══════════════════════════════════════════════════════════════
def get_master_password() -> str:
    env_pass = os.environ.get("MASTER_PASSWORD")
    if env_pass:
        return env_pass.strip()
    return "CYBER#ROOT@9821$MATRIX*SECURE!2026"

def get_cookie_admin_password() -> str:
    env_pass = os.environ.get("COOKIE_ADMIN_PASSWORD")
    if env_pass:
        return env_pass.strip()
    return "ADMIN#COOKIES@7739$VIP*VAULT!2026"

MASTER_PASSWORD = get_master_password()
COOKIE_ADMIN_PASSWORD = get_cookie_admin_password()
TOKEN_TTL_SECONDS = int(os.environ.get("TOKEN_TTL_SECONDS", 86400)) # 24 Horas de validade por token
ACTIVE_SESSIONS: Dict[str, float] = {} # token -> expiry_timestamp
ACTIVE_ADMIN_SESSIONS: Dict[str, float] = {} # admin_token -> expiry_timestamp
SESSION_CACHE_FILE = os.path.join(BASE_DIR, ".session_cache.json")

def load_active_sessions():
    global ACTIVE_SESSIONS
    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                now = time.time()
                ACTIVE_SESSIONS = {t: float(exp) for t, exp in data.items() if float(exp) > now}
        except Exception:
            pass

def save_active_sessions():
    try:
        with open(SESSION_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(ACTIVE_SESSIONS, f)
    except Exception:
        pass

load_active_sessions()

LOGIN_LOCK = threading.Lock()
LOGIN_ATTEMPTS: Dict[str, dict] = {} # ip -> {"count": int, "blocked_until": float}
ACTIVATION_RATE_LIMIT: Dict[str, list] = {} # ip -> list of timestamps

CURRENT_NETFLIX_READY: Optional[dict] = None
CURRENT_HBO_READY: Optional[dict] = None

class AppRequestHandler(SimpleHTTPRequestHandler):
    def send_security_headers(self):
        """Cabeçalhos avançados de proteção contra XSS, Clickjacking, MIME-sniffing e Injeções."""
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy', "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://fonts.gstatic.com data:; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:;")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Auth-Token')

    def end_headers(self):
        self.send_security_headers()
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def get_client_ip(self):
        xff = self.headers.get('X-Forwarded-For')
        if xff:
            return xff.split(',')[0].strip()
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def is_authenticated(self):
        auth_header = self.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif 'X-Auth-Token' in self.headers:
            token = self.headers.get('X-Auth-Token', '').strip()
        
        if not token:
            return False

        now = time.time()
        with LOGIN_LOCK:
            # Limpeza automática de tokens expirados
            expired = [t for t, exp in ACTIVE_SESSIONS.items() if exp < now]
            for exp_token in expired:
                ACTIVE_SESSIONS.pop(exp_token, None)

            if token in ACTIVE_SESSIONS:
                if ACTIVE_SESSIONS[token] > now:
                    return True
                else:
                    ACTIVE_SESSIONS.pop(token, None)
                    return False
            return False

    def is_admin_authenticated(self):
        admin_header = self.headers.get('X-Admin-Token', '') or self.headers.get('Authorization', '')
        token = ''
        if admin_header.startswith('Bearer '):
            token = admin_header[7:].strip()
        else:
            token = admin_header.strip()
        
        if not token:
            return False

        now = time.time()
        with LOGIN_LOCK:
            if token in ACTIVE_ADMIN_SESSIONS:
                if ACTIVE_ADMIN_SESSIONS[token] > now:
                    return True
                else:
                    ACTIVE_ADMIN_SESSIONS.pop(token, None)
                    return False
            return False

    def handle_api_verify_admin_pass(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        password = req.get('password', '').strip()

        is_valid = hmac.compare_digest(password, get_cookie_admin_password())

        if is_valid:
            now = time.time()
            admin_token = secrets.token_hex(32)
            with LOGIN_LOCK:
                ACTIVE_ADMIN_SESSIONS[admin_token] = now + 43200 # 12 horas
            return self.send_json_response({
                "success": True,
                "admin_token": admin_token,
                "message": "Acesso administrativo aos cookies concedido!"
            })
        else:
            return self.send_json_response({
                "success": False,
                "message": "Senha do gerenciador de cookies incorreta!"
            }, 401)

    def handle_api_login(self):
        ip = self.get_client_ip()
        now = time.time()
        
        with LOGIN_LOCK:
            record = LOGIN_ATTEMPTS.get(ip, {"count": 0, "blocked_until": 0})
            if record["blocked_until"] > now:
                wait_sec = int(record["blocked_until"] - now)
                return self.send_json_response({
                    "success": False, 
                    "message": f"Muitas tentativas. IP bloqueado temporariamente por mais {wait_sec} segundos."
                }, 429)

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        password = req.get('password', '').strip()

        # Comparação em tempo constante para evitar Timing Attacks
        is_valid = hmac.compare_digest(password, get_master_password())

        with LOGIN_LOCK:
            if is_valid:
                LOGIN_ATTEMPTS.pop(ip, None)
                new_token = secrets.token_hex(32)
                ACTIVE_SESSIONS[new_token] = now + TOKEN_TTL_SECONDS
                save_active_sessions()
                return self.send_json_response({
                    "success": True,
                    "token": new_token,
                    "expires_in": TOKEN_TTL_SECONDS,
                    "message": "Terminal desbloqueado com sucesso."
                })
            else:
                record["count"] += 1
                # Bloqueio progressivo inteligente
                if record["count"] >= 10:
                    lock_time = 900 # 15 minutos
                elif record["count"] >= 8:
                    lock_time = 300 # 5 minutos
                elif record["count"] >= 5:
                    lock_time = 60  # 1 minuto
                else:
                    lock_time = 0

                if lock_time > 0:
                    record["blocked_until"] = now + lock_time
                    LOGIN_ATTEMPTS[ip] = record
                    return self.send_json_response({
                        "success": False,
                        "message": f"Tentativas excedidas! Terminal bloqueado por {lock_time} segundos por segurança."
                    }, 429)
                else:
                    LOGIN_ATTEMPTS[ip] = record
                    remaining = 5 - record["count"]
                    return self.send_json_response({
                        "success": False,
                        "message": f"Senha mestre incorreta. Restam {remaining} tentativas antes do bloqueio temporário."
                    }, 401)

    def handle_api_logout(self):
        auth_header = self.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif 'X-Auth-Token' in self.headers:
            token = self.headers.get('X-Auth-Token', '').strip()
        with LOGIN_LOCK:
            ACTIVE_SESSIONS.pop(token, None)
            save_active_sessions()
        return self.send_json_response({"success": True, "message": "Terminal bloqueado."})

    def handle_api_verify_token(self):
        return self.send_json_response({"authenticated": self.is_authenticated()})

    def check_rate_limit(self, max_requests: int = 15, window_seconds: int = 30) -> bool:
        """Rate limiting por IP para proteger endpoints sensíveis contra spam/DDoS."""
        ip = self.get_client_ip()
        now = time.time()
        with LOGIN_LOCK:
            timestamps = ACTIVATION_RATE_LIMIT.get(ip, [])
            timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= max_requests:
                return False
            timestamps.append(now)
            ACTIVATION_RATE_LIMIT[ip] = timestamps
            return True

    def serve_index_html(self):
        """Serve com exclusividade e segurança a página inicial index.html."""
        index_path = os.path.join(BASE_DIR, "index.html")
        if not os.path.exists(index_path):
            self.send_error(404, "Arquivo index.html não encontrado.")
            return

        try:
            with open(index_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500, "Erro interno ao carregar a interface.")

    def do_GET(self):
        # Normalização do caminho (proteção contra path traversal como /../)
        raw_path = self.path.split('?')[0]

        if raw_path == '/api/ping':
            # Keep-Alive endpoint público para evitar que a instância durma
            return self.send_json_response({
                "status": "alive",
                "uptime": "24/7",
                "timestamp": time.time(),
                "service": "CYBER_DECK_KERNEL_ONLINE"
            })
        elif raw_path == '/api/status':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_status()
        elif raw_path == '/api/admin/stats':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_admin_stats()
        elif raw_path == '/api/history':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_history()
        elif raw_path.startswith('/api/cookies'):
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_cookies()
        elif raw_path in ['/', '/index.html', '/index.htm', '']:
            self.serve_index_html()
        elif raw_path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            # 🛡️ BLOQUEIO TOTAL DE SEGURANÇA:
            # NUNCA serve arquivos como cookies/, SENHA_MESTRE.txt, app.py, tv2.py, used_cookies.json etc.
            self.send_error(403, "Acesso Proibido: Recurso confidencial e protegido.")

    def do_POST(self):
        raw_path = self.path.split('?')[0]

        if raw_path == '/api/login':
            self.handle_api_login()
        elif raw_path == '/api/logout':
            self.handle_api_logout()
        elif raw_path == '/api/verify-token':
            self.handle_api_verify_token()
        elif raw_path == '/api/admin/verify-pass':
            self.handle_api_verify_admin_pass()
        elif raw_path == '/api/activate':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            if not self.check_rate_limit(max_requests=10, window_seconds=30):
                return self.send_json_response({"success": False, "message": "Muitas ativações em sequência. Aguarde alguns instantes por segurança."}, 429)
            self.handle_api_activate()
        elif raw_path == '/api/skip-cookie':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_skip_cookie()
        elif raw_path == '/api/select-cookie':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_select_cookie()
        elif raw_path == '/api/filter-plan':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_filter_plan()
        elif raw_path == '/api/admin/upload-cookies':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_upload_cookies()
        elif raw_path == '/api/admin/reset-cache':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_reset_cache()
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, data: dict, status_code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api_status(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY

        if CURRENT_NETFLIX_READY is None or (CURRENT_NETFLIX_READY and (CURRENT_NETFLIX_READY.get("file") in DEAD_NETFLIX_COOKIES or CURRENT_NETFLIX_READY.get("file") in tv2.USED_COOKIES)):
            CURRENT_NETFLIX_READY = find_netflix_valid_cookie()
        
        if CURRENT_HBO_READY is None or (CURRENT_HBO_READY and CURRENT_HBO_READY.get("file") in USED_HBO_COOKIES):
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        verified_netflix = get_verified_netflix_cookies(min_count=3)
        active_nf_file = CURRENT_NETFLIX_READY["file"] if CURRENT_NETFLIX_READY else ""
        nf_queue = [
            {
                "filename": os.path.basename(e["file"]),
                "email": e["info"].get("email", os.path.basename(e["file"])),
                "country": e["info"].get("country", "BR"),
                "plan": e["info"].get("plan", "Premium VIP"),
                "is_selected": (e["file"] == active_nf_file)
            }
            for e in verified_netflix if e["file"] != active_nf_file
        ]

        verified_hbo = get_verified_hbo_cookies(min_count=2)
        active_hbo_file = CURRENT_HBO_READY["file"] if CURRENT_HBO_READY else ""
        hbo_queue = [
            {
                "filename": os.path.basename(e["file"]),
                "email": e["info"].get("email", "HBO Max VIP"),
                "country": e["info"].get("country", "BR"),
                "plan": e["info"].get("plan", "HBO Max VIP"),
                "is_selected": (e["file"] == active_hbo_file)
            }
            for e in verified_hbo if e["file"] != active_hbo_file
        ]

        res = {
            "netflix": {
                "available_count": len(verified_netflix),
                "has_account": CURRENT_NETFLIX_READY is not None,
                "account": CURRENT_NETFLIX_READY["info"] if CURRENT_NETFLIX_READY else None,
                "cookie_name": os.path.basename(CURRENT_NETFLIX_READY["file"]) if CURRENT_NETFLIX_READY else None,
                "cookie_queue": nf_queue
            },
            "hbo": {
                "available_count": len(verified_hbo),
                "has_account": CURRENT_HBO_READY is not None,
                "account": CURRENT_HBO_READY["info"] if CURRENT_HBO_READY else None,
                "cookie_name": os.path.basename(CURRENT_HBO_READY["file"]) if CURRENT_HBO_READY else None,
                "cookie_queue": hbo_queue
            },
            "local_ip": get_local_ip(),
            "port": PORT
        }
        self.send_json_response(res)

    def handle_api_skip_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        service = req.get('service', 'netflix')

        if service == 'netflix':
            if CURRENT_NETFLIX_READY:
                DEAD_NETFLIX_COOKIES.add(CURRENT_NETFLIX_READY["file"])
                tv2.USED_COOKIES.add(CURRENT_NETFLIX_READY["file"])
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        else:
            if CURRENT_HBO_READY:
                USED_HBO_COOKIES.add(CURRENT_HBO_READY["file"])
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        self.handle_api_status()

    def handle_api_activate(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido na requisição."}, 400)

        service = req.get('service', 'netflix')
        tv_code = req.get('code', '').strip()

        if not tv_code:
            return self.send_json_response({"success": False, "message": "Por favor, digite o código exibido na TV."}, 400)

        clean_code = re.sub(r'[^A-Za-z0-9]', '', tv_code).upper()

        if service == 'netflix':
            if CURRENT_NETFLIX_READY is None:
                CURRENT_NETFLIX_READY = find_netflix_fast_cookie()

            if not CURRENT_NETFLIX_READY:
                return self.send_json_response({
                    "success": False,
                    "message": "Nenhum cookie Netflix válido disponível no momento."
                }, 404)

            used_file = CURRENT_NETFLIX_READY["file"]
            success, msg, info = activate_netflix_tv(clean_code, CURRENT_NETFLIX_READY)
            account_info = info or CURRENT_NETFLIX_READY.get("info", {})

            if success:
                tv2.USED_COOKIES.add(used_file)
                DEAD_NETFLIX_COOKIES.add(used_file)
                record_history_entry("Netflix", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "Netflix"), "Sucesso")
                CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=used_file)
                return self.send_json_response({
                    "success": True,
                    "message": msg,
                    "account": account_info
                })
            else:
                DEAD_NETFLIX_COOKIES.add(used_file)
                tv2.USED_COOKIES.add(used_file)
                CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=used_file)
                return self.send_json_response({
                    "success": False,
                    "message": msg or "Falha ao parear com a TV."
                })

        elif service == 'hbo':
            if CURRENT_HBO_READY is None:
                CURRENT_HBO_READY = find_hbo_valid_cookie()

            if not CURRENT_HBO_READY:
                return self.send_json_response({
                    "success": False,
                    "message": "Nenhum cookie HBO Max ativo encontrado nas pastas."
                }, 404)

            used_file = CURRENT_HBO_READY["file"]
            success, msg, info = activate_hbo_tv(clean_code, CURRENT_HBO_READY)
            account_info = info or CURRENT_HBO_READY.get("info", {})

            if success:
                USED_HBO_COOKIES.add(used_file)
                record_history_entry("HBO Max", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "HBO Max VIP"), "Sucesso")
                CURRENT_HBO_READY = find_hbo_valid_cookie()
                return self.send_json_response({
                    "success": True,
                    "message": msg,
                    "account": account_info
                })
            else:
                if "expirou" in msg.lower():
                    CURRENT_HBO_READY = find_hbo_valid_cookie()
                return self.send_json_response({
                    "success": False,
                    "message": msg
                })
        else:
            return self.send_json_response({"success": False, "message": "Serviço desconhecido."}, 400)

    def handle_api_cookies(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY
        query_service = 'netflix'
        if 'service=hbo' in self.path:
            query_service = 'hbo'

        if query_service == 'netflix':
            verified = get_verified_netflix_cookies(min_count=4)
            active_file = os.path.basename(CURRENT_NETFLIX_READY["file"]) if CURRENT_NETFLIX_READY else ""
            items = []
            for entry in verified:
                bname = os.path.basename(entry["file"])
                acc = entry["info"]
                items.append({
                    "filename": bname,
                    "email": acc.get("email", bname),
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "Premium VIP"),
                    "is_selected": (bname == active_file),
                    "is_verified": True,
                    "is_dead": False
                })
            # Selecionado no topo
            items.sort(key=lambda x: not x["is_selected"])
        else:
            verified = get_verified_hbo_cookies(min_count=3)
            active_file = os.path.basename(CURRENT_HBO_READY["file"]) if CURRENT_HBO_READY else ""
            items = []
            for entry in verified:
                bname = os.path.basename(entry["file"])
                acc = entry["info"]
                items.append({
                    "filename": bname,
                    "email": acc.get("email", bname),
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "HBO Max VIP"),
                    "is_selected": (bname == active_file),
                    "is_verified": True,
                    "is_dead": False
                })
            items.sort(key=lambda x: not x["is_selected"])

        self.send_json_response({
            "service": query_service,
            "total_valid": len(items),
            "active_cookie": active_file,
            "cookies": items
        })

    def handle_api_select_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        service = req.get('service', 'netflix')
        filename = req.get('filename', '').strip()

        if not filename:
            return self.send_json_response({"success": False, "message": "Nome do arquivo ausente."}, 400)

        if service == 'netflix':
            selected = select_netflix_cookie_by_filename(filename)
            if selected:
                CURRENT_NETFLIX_READY = selected
                return self.send_json_response({
                    "success": True,
                    "message": f"Conta {selected['info'].get('email', filename)} selecionada!",
                    "account": selected["info"],
                    "cookie_name": os.path.basename(selected["file"])
                })
            else:
                return self.send_json_response({"success": False, "message": "Este cookie não está mais ativo na Netflix."}, 404)
        else:
            selected = select_hbo_cookie_by_filename(filename)
            if selected:
                CURRENT_HBO_READY = selected
                return self.send_json_response({
                    "success": True,
                    "message": f"Conta HBO {selected['info'].get('email', filename)} selecionada!",
                    "account": selected["info"],
                    "cookie_name": os.path.basename(selected["file"])
                })
            else:
                return self.send_json_response({"success": False, "message": "Não foi possível ativar este cookie HBO Max."}, 404)

    def handle_api_filter_plan(self):
        return self.send_json_response({"success": True, "message": "Plano atualizado."})

    def handle_api_history(self):
        history = load_history()
        self.send_json_response({"history": history})

    def handle_api_upload_cookies(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        service = req.get('service', 'netflix').lower()
        files = req.get('files', []) # list of {"name": "...", "content": "..."}
        raw_text = req.get('raw_text', '').strip()

        target_dir = NETFLIX_COOKIES_FOLDER if service == 'netflix' else HBO_COOKIES_FOLDER
        os.makedirs(target_dir, exist_ok=True)
        saved_count = 0

        # Processa arquivos enviados
        for item in files:
            fname = item.get('name', '').strip()
            content = item.get('content', '').strip()
            if fname and content:
                clean_name = re.sub(r'[^a-zA-Z0-9_\-\.\[\]@]', '_', os.path.basename(fname))
                if not clean_name.endswith('.txt') and not clean_name.endswith('.json'):
                    clean_name += '.txt'
                fpath = os.path.join(target_dir, clean_name)
                try:
                    with open(fpath, 'w', encoding='utf-8') as out_f:
                        out_f.write(content)
                    saved_count += 1
                    if service == 'netflix':
                        DEAD_NETFLIX_COOKIES.discard(fpath)
                        tv2.USED_COOKIES.discard(fpath)
                        tv2.USED_COOKIES.discard(clean_name)
                    else:
                        USED_HBO_COOKIES.discard(fpath)
                        USED_HBO_COOKIES.discard(clean_name)
                except Exception:
                    pass

        # Processa texto colado
        if raw_text:
            timestamp = int(time.time())
            if raw_text.startswith('[') and raw_text.endswith(']'):
                clean_name = f"web_import_{timestamp}.json"
            else:
                clean_name = f"web_import_{timestamp}.txt"
            fpath = os.path.join(target_dir, clean_name)
            try:
                with open(fpath, 'w', encoding='utf-8') as out_f:
                    out_f.write(raw_text)
                saved_count += 1
                if service == 'netflix':
                    DEAD_NETFLIX_COOKIES.discard(fpath)
                    tv2.USED_COOKIES.discard(fpath)
                    tv2.USED_COOKIES.discard(clean_name)
                else:
                    USED_HBO_COOKIES.discard(fpath)
                    USED_HBO_COOKIES.discard(clean_name)
            except Exception:
                pass

        if saved_count > 0:
            sync_cookies_bundle()
            threading.Thread(target=self._prewarm_after_upload, args=(service,), daemon=True).start()
            return self.send_json_response({
                "success": True,
                "saved_count": saved_count,
                "message": f"🎉 {saved_count} cookie(s) de {service.upper()} importado(s) com sucesso!"
            })
        else:
            return self.send_json_response({"success": False, "message": "Nenhum arquivo ou texto válido enviado."}, 400)

    def _prewarm_after_upload(self, service: str):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY
        time.sleep(0.5)
        if service == 'netflix':
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        else:
            CURRENT_HBO_READY = find_hbo_valid_cookie()

    def handle_api_reset_cache(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, DEAD_NETFLIX_COOKIES, USED_NETFLIX_COOKIES, USED_HBO_COOKIES
        DEAD_NETFLIX_COOKIES.clear()
        tv2.USED_COOKIES.clear()
        USED_HBO_COOKIES.clear()
        CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        CURRENT_HBO_READY = find_hbo_valid_cookie()
        return self.send_json_response({
            "success": True,
            "message": "Cache de cookies reinicializado! Todas as contas estão disponíveis para re-teste."
        })

    def handle_api_admin_stats(self):
        nf_files = glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.*"))
        hbo_files = glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.*"))
        verified_nf = get_verified_netflix_cookies(min_count=1)
        verified_hbo = get_verified_hbo_cookies(min_count=1)
        return self.send_json_response({
            "netflix_total": len(nf_files),
            "netflix_verified": len(verified_nf),
            "netflix_dead": len(DEAD_NETFLIX_COOKIES),
            "hbo_total": len(hbo_files),
            "hbo_verified": len(verified_hbo),
            "hbo_dead": len(USED_HBO_COOKIES),
            "keep_alive": True,
            "timestamp": time.time()
        })


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def background_verifier_loop():
    while True:
        try:
            get_verified_netflix_cookies(min_count=8)
            get_verified_hbo_cookies(min_count=4)
        except Exception:
            pass
        time.sleep(12)

def keep_alive_worker():
    """Anti-Sleep 24h: Mantém a instância do Render 100% acordada e instantânea."""
    time.sleep(15) # Espera o servidor iniciar
    while True:
        try:
            # 1. Ping interno local
            requests.get(f"http://127.0.0.1:{PORT}/api/ping", timeout=4)
        except Exception:
            pass

        try:
            # 2. Ping externo se estiver na nuvem Render
            render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://tvcodigo-1.onrender.com")
            if render_url:
                target = f"{render_url.rstrip('/')}/api/ping"
                requests.get(target, timeout=8)
        except Exception:
            pass

        time.sleep(300) # Ping a cada 5 minutos

def start_background_scanner():
    t1 = threading.Thread(target=background_verifier_loop, daemon=True)
    t1.start()
    t2 = threading.Thread(target=keep_alive_worker, daemon=True)
    t2.start()

def run_server(port=PORT):
    os.chdir(BASE_DIR)
    local_ip = get_local_ip()
    start_background_scanner()
    with ThreadedTCPServer(("", port), AppRequestHandler) as httpd:
        print(f"\n=======================================================")
        print(f" 🚀 ATIVADOR NETFLIX & HBO MAX INICIADO COM SUCESSO!")
        print(f" ⚡ Anti-Sleep 24h: ATIVADO (Render sempre acordado)")
        print(f" 💻 Acesse no PC:      http://localhost:{port}")
        print(f" 📱 Acesse no Celular: http://{local_ip}:{port}  (no mesmo Wi-Fi)")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor finalizado pelo usuário.")

if __name__ == "__main__":
    run_server()
