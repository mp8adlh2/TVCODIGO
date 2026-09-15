# -*- coding: utf-8 -*-
"""
=============================================================================
   ATIVADOR SKY+ SMART TV VIA API PURA (LOGIN COMPLETO + ATIVAÇÃO DA TV)
=============================================================================
Fluxo 100% HTTP REST (Sem Playwright, sem Chromium, sem Janelas):
1. Faz autenticação real com Telefone/Email/CPF e Senha no https://sm-sky.vrioservices.com (CURL 1)
2. Valida credenciais e titularidade da conta via API oficial da Sky
3. Obtém os tokens da sessão de streaming e emparelhamento
4. Envia o POST de ativação com o código da TV para https://dtv-oidc.tbxapis.com (CURL 2)
=============================================================================
"""

import os
import sys
import json
import time
import secrets
import re
import base64
import subprocess
import urllib.parse
import requests
import urllib3
from typing import Optional, Dict, Any, Tuple, List

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Terminal Windows UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Solver reCAPTCHA
try:
    from recaptcha_solver import (
        get_recaptcha_web_token,
        get_recaptcha_paramount_token,
        get_recaptcha_token,
        update_payload_session_id
    )
    RECAPTCHA_OK = True
except Exception:
    RECAPTCHA_OK = False
    get_recaptcha_web_token = None
    get_recaptcha_paramount_token = None
    get_recaptcha_token = None

try:
    import kernel_logger
except ImportError:
    kernel_logger = None

def push_log(msg: str, level: str = "info"):
    """Envia log para o kernel_logger (interface web) e imprime no console."""
    if kernel_logger:
        try:
            clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', msg).strip()
            if clean_msg:
                kernel_logger.push_kernel_log(clean_msg, level=level)
        except Exception:
            pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SSO_FILE = os.path.join(BASE_DIR, "sso_token.txt")
PROFILE_FILE = os.path.join(BASE_DIR, "profile_token.txt")
PAYLOAD_WEB_FILE = os.path.join(BASE_DIR, "payload_web.b64")
PAYLOAD_PARAMOUNT_FILE = os.path.join(BASE_DIR, "payload_paramount.b64")
RAW_JSON_DIR = os.path.join(BASE_DIR, "hits", "raw_json")
BROWSER_SESSIONS_DIR = os.path.join(BASE_DIR, "hits", "browser_sessions")
SKY_SESSIONS_FILE = os.path.join(BASE_DIR, "hits", "sky_sessions.json")

os.makedirs(RAW_JSON_DIR, exist_ok=True)

# =============================================================================
# CONSTANTES EXTRAÍDAS DA API OFICIAL DA SKY
# =============================================================================
DEFAULT_LOGIN = "62999638003"
DEFAULT_PASS = "Wpx@1948"
DEVICE_ID = "u_qrPKBMa_6JYEat_jQs9mWp5bPDdrMVeO34fKhi4Y0"
BASIC_AUTH = "Basic ZHR2Z286TmQza1lhaUVHOA=="
ACTIVATE_URL = "https://dtv-oidc.tbxapis.com/v2/tv/activation"
WEB_API_KEY = "jVXvhTOQdcPV6xPZSzdFg8z61t1LTqfc"
X_APP = "skymais"
X_CLIENT_VER = "3.68.0"
X_ENVIRONMENT = "prd"
ORIGIN_SKY = "https://www.skymais.com.br"
REFERER_SKY = "https://www.skymais.com.br/"
ORIGIN_SKYUI = "https://sm-sky-ui.vrioservices.com"
USER_AGENT_WEB = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
USER_AGENT_EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

def banner():
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════════════╗
║             ATIVADOR SKY+ SMART TV - 100% VIA API HTTP               ║
║              (Login com Email/Senha -> Ativação na TV)               ║
╚══════════════════════════════════════════════════════════════════════╝{C.RESET}
""")

def carregar_tokens_locais():
    sso = ""
    profile = ""
    if os.path.exists(SSO_FILE):
        try:
            with open(SSO_FILE, "r", encoding="utf-8") as f:
                sso = f.read().strip()
        except Exception:
            pass
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                profile = f.read().strip()
        except Exception:
            pass
    return sso, profile

def salvar_tokens(sso: str, profile: str = ""):
    """Salva os tokens de sessao nos arquivos locais."""
    try:
        with open(SSO_FILE, "w", encoding="utf-8") as f:
            f.write(sso)
    except Exception:
        pass
    if profile:
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                f.write(profile)
        except Exception:
            pass

def decodificar_token_jwt(token: str) -> Dict[str, Any]:
    """Decodifica as claims do JWT da sessão sem validar assinatura."""
    try:
        if not token or "." not in token:
            return {}
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        data = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(data.decode("utf-8", errors="ignore"))
    except Exception:
        return {}

def obter_identidade_token(token: str) -> str:
    """Retorna uma string legivel identificando o titular e a conta contidos no JWT."""
    if not token:
        return "Token Vazio"
    # Token opaco (nao-JWT)
    if not token.startswith("ey") or "." not in token:
        return f"device_token ({token[:20]}...)"
    claims = decodificar_token_jwt(token)
    if not claims:
        return "Token Invalido"
    nome = claims.get("name") or f"{claims.get('givenName', '')} {claims.get('familyName', '')}".strip()
    acc = claims.get("serviceProviderAccountId") or claims.get("email") or claims.get("phoneNumber") or claims.get("sub") or ""
    if acc.startswith("sky_"):
        acc = acc[4:]
    if nome and acc:
        return f"{nome} ({acc})"
    elif nome:
        return nome
    elif acc:
        return acc
    return "Conta Sky+"

def token_expirado(token: str) -> bool:
    """Verifica se o JWT ja expirou verificando o campo 'exp'."""
    claims = decodificar_token_jwt(token)
    exp = claims.get("exp")
    if exp:
        return int(time.time()) >= int(exp)
    return False

def _gerar_recaptcha_web(tentativas: int = 3) -> Optional[str]:
    """Gera token reCAPTCHA Enterprise (Sky Web) com multiplas tentativas."""
    if not RECAPTCHA_OK or not get_recaptcha_web_token:
        print(f"{C.RED}[!] recaptcha_solver nao disponivel.{C.RESET}")
        return None
    payload_web = ""
    if os.path.exists(PAYLOAD_WEB_FILE):
        try:
            with open(PAYLOAD_WEB_FILE, "r", encoding="utf-8") as f:
                payload_web = f.read().strip()
        except Exception:
            pass
    if not payload_web:
        print(f"{C.RED}[!] payload_web.b64 nao encontrado.{C.RESET}")
        return None
    for i in range(1, tentativas + 1):
        try:
            print(f"{C.YELLOW}[*] Gerando reCAPTCHA (tentativa {i}/{tentativas})...{C.RESET}")
            tok = get_recaptcha_web_token(payload_web)
            if tok and len(tok) > 50:
                print(f"{C.GREEN}[OK] reCAPTCHA gerado: {tok[:32]}...{C.RESET}")
                return tok
            print(f"{C.YELLOW}[!] Token vazio/curto, tentando novamente...{C.RESET}")
        except Exception as e:
            print(f"{C.YELLOW}[!] Tentativa {i} falhou: {e}{C.RESET}")
            time.sleep(1.5)
    print(f"{C.RED}[!] Nao foi possivel gerar reCAPTCHA apos {tentativas} tentativas.{C.RESET}")
    return None

def buscar_sessao_salva(usuario: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Busca sessao nao expirada em cache para o usuario especificado."""
    u_clean = re.sub(r'[^a-zA-Z0-9]', '', usuario.lower())

    # 1. Busca em browser_sessions
    if os.path.exists(BROWSER_SESSIONS_DIR):
        for fn in os.listdir(BROWSER_SESSIONS_DIR):
            if fn.endswith('.json'):
                f_clean = re.sub(r'[^a-zA-Z0-9]', '', fn.lower().replace('.json', ''))
                if u_clean in f_clean or f_clean in u_clean:
                    fp = os.path.join(BROWSER_SESSIONS_DIR, fn)
                    try:
                        with open(fp, 'r', encoding='utf-8') as rf:
                            d = json.load(rf)
                        sso = None
                        prof = None
                        for orig in d.get('origins', []):
                            for item in orig.get('localStorage', []):
                                if item.get('name') == 'sessionToken':
                                    sso = item.get('value')
                                elif item.get('name') == 'profile':
                                    try:
                                        p_data = json.loads(item.get('value', '{}'))
                                        prof = p_data.get('profileToken')
                                    except Exception:
                                        pass
                                elif item.get('name') == 'profileToken':
                                    prof = item.get('value')
                        if sso and not token_expirado(sso):
                            ident = obter_identidade_token(sso)
                            return sso, prof, f"Cache ({fn})", ident
                    except Exception:
                        pass

    # 2. Busca em sky_sessions.json
    if os.path.exists(SKY_SESSIONS_FILE):
        try:
            with open(SKY_SESSIONS_FILE, 'r', encoding='utf-8') as rf:
                sessions = json.load(rf)
            for s in sessions:
                acc = str(s.get('account') or s.get('email') or '').lower()
                acc_clean = re.sub(r'[^a-zA-Z0-9]', '', acc)
                if u_clean in acc_clean or acc_clean in u_clean:
                    sso = s.get('sso_token')
                    prof = s.get('profile_token')
                    if sso and not token_expirado(sso):
                        ident = obter_identidade_token(sso) if sso else acc
                        return sso, prof, f"Pool ({acc})", ident
        except Exception:
            pass

    # 3. Verifica se o sso_token.txt atual pertence a este usuario e nao expirou
    cached_sso, cached_prof = carregar_tokens_locais()
    if cached_sso and not token_expirado(cached_sso):
        ident = obter_identidade_token(cached_sso)
        id_clean = re.sub(r'[^a-zA-Z0-9]', '', ident.lower())
        if u_clean in id_clean or id_clean in u_clean:
            return cached_sso, cached_prof, "sso_token.txt", ident

    return None, None, None, None

def autenticar_conta_sky(usuario: str, senha: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Login HTTP na API Sky (v2/oauth2/authenticate). 100% REST, sem navegador.
    Tenta ate 4 vezes com novo reCAPTCHA em caso de INVALID_CAPTCHA.
    """
    print(f"\n{C.CYAN}[ETAPA 1] Login HTTP na Sky ({usuario})...{C.RESET}")

    headers_auth = {
        "host": "sm-sky.vrioservices.com",
        "x-environment": "prd",
        "x-user-id": "SiteSKY",
        "x-api-key": WEB_API_KEY,
        "x-consumer-system": "SiteSKY",
        "x-client-type": "web",
        "content-type": "application/json",
        "origin": "https://www.sky.com.br",
        "referer": "https://www.sky.com.br/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    body_base: Dict[str, Any] = {"grantType": "password", "password": senha}
    clean_user = usuario.strip()
    if "@" in clean_user:
        body_base["email"] = clean_user
        print(f"[*] Identificador: Email ({clean_user})")
    else:
        apenas_num = re.sub(r'\D', '', clean_user)
        if len(apenas_num) in [10, 11] and (len(apenas_num) == 10 or apenas_num[2] == '9'):
            body_base["telephoneNumber"] = apenas_num
            print(f"[*] Identificador: Telefone ({apenas_num})")
        else:
            cpf_num = apenas_num.zfill(11)
            body_base["cpf"] = cpf_num
            print(f"[*] Identificador: CPF ({cpf_num})")

    MAX_TENTATIVAS = 4
    sess = requests.Session()
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        tok = _gerar_recaptcha_web(tentativas=2)
        if not tok:
            return False, None
        body = dict(body_base)
        body["g-recaptcha-response"] = tok
        try:
            resp = sess.post(
                "https://sm-sky.vrioservices.com/v2/oauth2/authenticate",
                headers=headers_auth, json=body, timeout=25, verify=False
            )
            print(f"[*] HTTP {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                cust = data.get("customer", {})
                nome = f"{cust.get('name', '')} {cust.get('secondName', '')}".strip()
                cpf = cust.get("cpf", "")
                main_sig = data.get("mainSignature", "")
                acc_tok = data.get("accessToken", "")
                prod_name = "Assinatura Sky+"
                for sig in data.get("signatures", []):
                    if str(sig.get("id")) == str(main_sig) or sig.get("productStatus") == "A":
                        prod_name = sig.get("productName", prod_name)
                        break
                print(f"{C.GREEN}{C.BOLD}[OK] AUTENTICACAO REALIZADA COM SUCESSO NA SKY!{C.RESET}")
                print(f"{C.GREEN}    Titular: {nome} | CPF: {cpf} | Plano: {prod_name}{C.RESET}")
                id_tok = _obter_id_token(sess, headers_auth, acc_tok, main_sig)
                if id_tok:
                    data["_id_token"] = id_tok
                data["_sess"] = sess
                _salvar_hit(usuario, senha, acc_tok, id_tok, data)
                return True, data
            elif resp.status_code in [400, 401]:
                try:
                    err_data = resp.json()
                except Exception:
                    err_data = {"raw": resp.text[:300]}
                print(f"{C.RED}[!] Falha: {err_data}{C.RESET}")
                if "CAPTCHA" in str(err_data).upper():
                    print(f"{C.YELLOW}[!] CAPTCHA invalido. Tentativa {tentativa}/{MAX_TENTATIVAS} — gerando novo...{C.RESET}")
                    time.sleep(2)
                    continue
                else:
                    return False, None
            else:
                print(f"{C.RED}[!] Status {resp.status_code}: {resp.text[:200]}{C.RESET}")
                return False, None
        except Exception as e:
            print(f"{C.RED}[!] Erro de conexao: {e}{C.RESET}")
            if tentativa < MAX_TENTATIVAS:
                time.sleep(2)
            else:
                return False, None
    print(f"{C.RED}[!] {MAX_TENTATIVAS} tentativas esgotadas (CAPTCHA invalido).{C.RESET}")
    print(f"{C.YELLOW}[*] Dica: Atualize o payload_web.b64 com nova sessao do navegador.{C.RESET}")
    return False, None

def _obter_id_token(sess: requests.Session, headers: dict, acc_tok: str, sig: str) -> Optional[str]:
    """
    Obtem o id_token JWT via /v2/oauth2/token.
    Tenta sm-sky-ui.vrioservices.com (retorna aud=dtvgo) E sm-sky.vrioservices.com.
    O token com aud=dtvgo e o aceito pelo dtv-oidc.tbxapis.com.
    """
    print(f"{C.YELLOW}[*] Obtendo id_token JWT da Sky (aud=dtvgo)...{C.RESET}")

    # Endpoints para tentar (sm-sky-ui primeiro pois retorna aud=dtvgo)
    endpoints = [
        ("sm-sky-ui", "https://sm-sky-ui.vrioservices.com/v2/oauth2/token",
         "https://www.skymais.com.br", "sm-sky-ui.vrioservices.com"),
        ("sm-sky",    "https://sm-sky.vrioservices.com/v2/oauth2/token",
         "https://www.sky.com.br",     "sm-sky.vrioservices.com"),
    ]

    best_tok = None  # Guarda o melhor token encontrado
    for ep_name, token_url, origin, host in endpoints:
        tok_sig = _gerar_recaptcha_web(tentativas=2)
        if not tok_sig:
            continue
        t_payload = {
            "grantType": "authorizationSignature",
            "signature": str(sig),
            "accessToken": acc_tok,
            "g-recaptcha-response": tok_sig
        }
        ep_headers = dict(headers)
        ep_headers["host"]    = host
        ep_headers["origin"]  = origin
        ep_headers["referer"] = origin + "/"
        try:
            r = sess.post(token_url, headers=ep_headers, json=t_payload,
                          timeout=20, verify=False)
            print(f"{C.YELLOW}    [{ep_name}] HTTP {r.status_code}{C.RESET}")
            if r.status_code == 200:
                id_tok = r.json().get("id_token") or r.json().get("accessToken")
                if id_tok:
                    claims = decodificar_token_jwt(id_tok)
                    aud = claims.get("aud", "")
                    iss = claims.get("iss", "")
                    print(f"{C.GREEN}    [{ep_name}] id_token: {id_tok[:30]}... aud={aud} iss={iss}{C.RESET}")
                    if aud == "dtvgo":
                        # Token ideal — retorna imediatamente
                        return id_tok
                    elif not best_tok:
                        best_tok = id_tok  # Guarda como fallback
            else:
                print(f"{C.YELLOW}    [{ep_name}] {r.text[:80]}{C.RESET}")
        except Exception as e:
            print(f"{C.YELLOW}    [{ep_name}] Erro: {e}{C.RESET}")

    if best_tok:
        print(f"{C.YELLOW}[!] Nenhum token com aud=dtvgo, usando fallback...{C.RESET}")
        return best_tok
    return None


def _salvar_hit(usuario: str, senha: str, acc_tok: str, id_tok: Optional[str], data: dict):
    """Salva dados da autenticacao em hits/raw_json/."""
    try:
        save_data = {
            "email": usuario, "password": senha,
            "access_token": acc_tok, "jwt_token": id_tok or "", "raw_data": data
        }
        save_path = os.path.join(RAW_JSON_DIR, f"{re.sub(r'[^a-zA-Z0-9]', '_', usuario)}.json")
        with open(save_path, "w", encoding="utf-8") as wf:
            json.dump(save_data, wf, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _salvar_sessao_sky(usuario: str, sso_token: str, fr_token: Optional[str], titular: str, raw_dgo: dict):
    """Salva a nova sessao DTVGO em sky_sessions.json e browser_sessions para cache persistente."""
    try:
        os.makedirs(BROWSER_SESSIONS_DIR, exist_ok=True)
        u_clean = re.sub(r'[^a-zA-Z0-9]', '_', usuario.lower())
        b_file = os.path.join(BROWSER_SESSIONS_DIR, f"{u_clean}.json")
        session_obj = {
            "usuario": usuario,
            "titular": titular,
            "data_criacao": time.strftime("%Y-%m-%d %H:%M:%S"),
            "origins": [
                {
                    "origin": "https://www.skymais.com.br",
                    "localStorage": [
                        {"name": "sessionToken", "value": sso_token},
                        {"name": "frToken", "value": fr_token or ""},
                        {"name": "isSky", "value": "true"},
                        {"name": "user", "value": json.dumps({"email": usuario, "titular": titular})}
                    ]
                }
            ]
        }
        with open(b_file, "w", encoding="utf-8") as f:
            json.dump(session_obj, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        sessions = []
        if os.path.exists(SKY_SESSIONS_FILE):
            try:
                with open(SKY_SESSIONS_FILE, "r", encoding="utf-8") as rf:
                    sessions = json.load(rf)
            except Exception:
                sessions = []
        updated = False
        for s in sessions:
            if s.get("account") == usuario or s.get("email") == usuario:
                s["sso_token"] = sso_token
                s["titular"] = titular
                s["atualizado_em"] = time.strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break
        if not updated:
            sessions.append({
                "account": usuario,
                "email": usuario,
                "sso_token": sso_token,
                "profile_token": "",
                "titular": titular,
                "criado_em": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        with open(SKY_SESSIONS_FILE, "w", encoding="utf-8") as wf:
            json.dump(sessions, wf, indent=2, ensure_ascii=False)
    except Exception:
        pass

def obter_ssotoken_dtvgo(usuario: str, senha: str, sess: requests.Session,
                         headers_sky: dict) -> Optional[str]:
    """
    Obtém o ssoToken real do DTVGO via fluxo OAuth completo:
      1. POST /v2/oauth2/authorize?cp_convert=dtvgo em sm-sky.vrioservices.com
         -> retorna auth_code Sky
      2. POST/GET /v2/auth/oauth2/assert em sp.tbxnet.com com auth_code
         -> retorna ssoToken com aud=dtvgo (emitido por sm-dgo.vrioservices.com)
    Este token é o único aceito pelo dtv-oidc.tbxapis.com/v2/tv/activation.
    """
    import secrets as _secrets
    print(f"{C.YELLOW}[*] Iniciando fluxo DTVGO OAuth para obter ssoToken ({usuario})...{C.RESET}")

    # ── ETAPA 0: Inicia sessao TBX para obter state oficial ──
    state = _secrets.token_hex(16)
    tbx_init_url = (
        "https://sp.tbxnet.com/v2/auth/authorize?"
        "client_id=dtvgo&response_type=code&"
        "redirect_uri=https%3A%2F%2Fwww.skymais.com.br%2Fativar&"
        "idp=sky_br&country=BR"
    )
    try:
        resp_init = sess.get(
            tbx_init_url,
            headers={
                "host": "sp.tbxnet.com",
                "user-agent": USER_AGENT_WEB,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "referer": ORIGIN_SKY + "/",
                "accept-language": "pt-BR,pt;q=0.9",
            },
            allow_redirects=False,
            timeout=20,
            verify=False
        )
        loc_init = resp_init.headers.get("Location") or resp_init.headers.get("location", "")
        if loc_init and "state=" in loc_init:
            import urllib.parse as _up
            qp_init = _up.parse_qs(_up.urlparse(loc_init).query)
            state = qp_init.get("state", [state])[0]
            print(f"{C.GREEN}    [TBX Init] State: {state[:25]}...{C.RESET}")
    except Exception as e:
        print(f"{C.YELLOW}    [TBX Init] Falhou ({e}) — usando state gerado{C.RESET}")

    # ── ETAPA 1: Authorize com cp_convert=dtvgo ──
    oauth_url = (
        f"https://sm-sky.vrioservices.com/v2/oauth2/authorize?"
        f"client_id=sky_br&country=BR&cp_convert=dtvgo&"
        f"failureRedirect=https%3A%2F%2Fwww.skymais.com.br%2Fativar&"
        f"redirect_uri=https%3A%2F%2Fsp.tbxnet.com%2Fv2%2Fauth%2Foauth2%2Fassert&"
        f"response_type=code&state={state}"
    )

    tok_rcap = _gerar_recaptcha_web(tentativas=3)
    if not tok_rcap:
        print(f"{C.RED}    [DTVGO OAuth] Sem reCAPTCHA para o authorize.{C.RESET}")
        return None

    auth_body: Dict[str, Any] = {
        "grantType": "password",
        "client_id": "sky_br",
        "countryCode": "br",
        "password": senha,
        "g-recaptcha-response": tok_rcap,
        "redirect_uri": "https://sp.tbxnet.com/v2/auth/oauth2/assert",
        "response_type": "code",
        "state": state,
        "cp_convert": "dtvgo",
    }
    clean_user = usuario.strip()
    if "@" in clean_user:
        auth_body["email"] = clean_user
    else:
        apenas_num = re.sub(r'\D', '', clean_user)
        if len(apenas_num) in [10, 11]:
            auth_body["telephoneNumber"] = apenas_num
        else:
            auth_body["cpf"] = apenas_num.zfill(11)

    auth_code = None
    state_ret = state
    try:
        resp_oauth = sess.post(
            oauth_url,
            headers={
                **headers_sky,
                "origin": ORIGIN_SKYUI,
                "referer": ORIGIN_SKYUI + "/",
                "accept": "application/json, text/html, */*",
            },
            json=auth_body,
            timeout=25,
            allow_redirects=False,
            verify=False
        )
        loc_oauth = resp_oauth.headers.get("Location") or resp_oauth.headers.get("location", "")
        print(f"{C.YELLOW}    [Authorize DTVGO] HTTP {resp_oauth.status_code} -> {loc_oauth[:80] if loc_oauth else resp_oauth.text[:80]}{C.RESET}")

        # Tenta extrair auth_code do JSON ou do Location
        try:
            j = resp_oauth.json()
            auth_code = j.get("code")
            state_ret = j.get("state") or state
        except Exception:
            pass
        if not auth_code and loc_oauth:
            import urllib.parse as _up
            qp_loc = _up.parse_qs(_up.urlparse(loc_oauth).query)
            auth_code = qp_loc.get("code", [None])[0]
            state_ret = qp_loc.get("state", [state])[0]
    except Exception as e:
        print(f"{C.RED}    [Authorize DTVGO] Erro: {e}{C.RESET}")
        return None

    if not auth_code:
        print(f"{C.RED}    [Authorize DTVGO] auth_code nao obtido.{C.RESET}")
        return None

    print(f"{C.GREEN}    [Authorize DTVGO] auth_code: {auth_code[:35]}...{C.RESET}")

    # ── ETAPA 2: Assert POST em sp.tbxnet.com ──
    assert_headers = {
        "authorization": BASIC_AUTH,
        "x-environment": X_ENVIRONMENT,
        "x-app": X_APP,
        "x-client-version": X_CLIENT_VER,
        "user-agent": USER_AGENT_WEB,
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json, text/html, */*",
        "origin": ORIGIN_SKY,
        "referer": REFERER_SKY,
    }
    assert_body = {
        "client_id": "sky_br",
        "country": "BR",
        "cp_convert": "dtvgo",
        "code": auth_code,
        "state": state_ret,
    }
    try:
        resp_assert = sess.post(
            "https://sp.tbxnet.com/v2/auth/oauth2/assert",
            headers=assert_headers,
            data=assert_body,
            timeout=25,
            allow_redirects=False,
            verify=False
        )
        loc_assert = resp_assert.headers.get("Location") or resp_assert.headers.get("location", "")
        print(f"{C.YELLOW}    [TBX Assert POST] HTTP {resp_assert.status_code} -> {loc_assert[:80] if loc_assert else resp_assert.text[:120]}{C.RESET}")

        # Tenta extrair ssoToken da resposta (JSON, cookies, URL)
        sso_cand = None
        try:
            j_assert = resp_assert.json()
            for k in ["ssoToken", "sso_token", "id_token", "idToken", "access_token"]:
                if j_assert.get(k):
                    sso_cand = str(j_assert[k]).strip('"\' ')
                    break
        except Exception:
            pass

        # Verifica cookies
        if not sso_cand:
            for ck in list(resp_assert.cookies) + list(sess.cookies):
                cname = (ck.name or "").lower()
                if any(w in cname for w in ["ssotoken", "sso_token", "tbxsso", "dtv_token"]):
                    sso_cand = ck.value.strip('"\' ')
                    break

        # Verifica Location URL
        if not sso_cand and loc_assert:
            import urllib.parse as _up
            parsed_loc = _up.urlparse(loc_assert)
            for qs in [parsed_loc.query, parsed_loc.fragment]:
                if not qs:
                    continue
                qp = _up.parse_qs(qs)
                for k, vals in qp.items():
                    if any(w in k.lower() for w in ["ssotoken", "sso_token", "token", "id_token"]):
                        sso_cand = vals[0].strip('"\' ')
                        break
                if sso_cand:
                    break

        if sso_cand and sso_cand.startswith("ey") and len(sso_cand) > 50:
            # Verifica se o iss é sm-dgo (token correto para DTVGO)
            claims = decodificar_token_jwt(sso_cand)
            iss = claims.get("iss", "")
            aud = claims.get("aud", "")
            titular = obter_identidade_token(sso_cand)
            print(f"{C.GREEN}[OK] ssoToken DTVGO obtido! iss={iss} aud={aud} | {titular}{C.RESET}")
            salvar_tokens(sso_cand)
            return sso_cand
        elif sso_cand:
            print(f"{C.YELLOW}    [Assert POST] Token candidato (nao JWT): {str(sso_cand)[:60]}{C.RESET}")

    except Exception as e:
        print(f"{C.RED}    [Assert POST] Erro: {e}{C.RESET}")

    # ── ETAPA 3: Assert GET — extrai TBX dtvgo code da URL final ──
    import urllib.parse as _up
    sso_cand = None
    tbx_code = None
    try:
        resp_assert_g = sess.get(
            "https://sp.tbxnet.com/v2/auth/oauth2/assert",
            params={"code": auth_code, "state": state_ret,
                    "client_id": "sky_br", "country": "BR", "cp_convert": "dtvgo"},
            headers={
                "user-agent": USER_AGENT_WEB,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "origin": ORIGIN_SKY,
                "referer": REFERER_SKY,
            },
            timeout=25,
            allow_redirects=True,
            verify=False
        )
        final_url = resp_assert_g.url
        print(f"{C.YELLOW}    [Assert GET] HTTP {resp_assert_g.status_code} -> URL: {final_url[:100]}{C.RESET}")

        # Procura ssoToken JWT em cookies
        for ck in list(resp_assert_g.cookies) + list(sess.cookies):
            cname = (ck.name or "").lower()
            if any(w in cname for w in ["ssotoken", "sso_token", "tbxsso"]):
                sso_cand = ck.value.strip('"\' ')
                if sso_cand and sso_cand.startswith("ey") and len(sso_cand) > 50:
                    print(f"{C.GREEN}[OK] ssoToken DTVGO via cookie: {sso_cand[:40]}...{C.RESET}")
                    salvar_tokens(sso_cand)
                    return sso_cand

        # Extrai TBX dtvgo code da URL final (/ativar?code=XXXX)
        all_history_urls = [final_url] + [r.url for r in getattr(resp_assert_g, 'history', [])]
        for turl in all_history_urls:
            if turl and "code=" in turl:
                parsed_tu = _up.urlparse(turl)
                for qs2 in [parsed_tu.query, parsed_tu.fragment]:
                     if qs2:
                         qp2 = _up.parse_qs(qs2)
                         if "code" in qp2:
                             tbx_code = qp2["code"][0]
                             break
            if tbx_code:
                break

    except Exception as e:
        print(f"{C.RED}    [Assert GET] Erro: {e}{C.RESET}")

    # ── ETAPA 4: Troca do TBX dtvgo code por ssoToken oficial via sm-dgo ──
    if tbx_code:
        print(f"{C.GREEN}    [TBX dtvgo code] {tbx_code[:45]}{C.RESET}")
        print(f"{C.YELLOW}[*] Trocando TBX code por ssoToken via sm-dgo.vrioservices.com/v3/oauth2/token...{C.RESET}")
        try:
            dgo_url = "https://sm-dgo.vrioservices.com/v3/oauth2/token"
            dgo_headers = {
                "Authorization": "Basic ZHR2Z286TmQza1lhaUVHOA==",
                "Metadata-BusinessUnit": "SKY-DTH",
                "x-client-type": "web",
                "x-device-id": DEVICE_ID,
                "x-app": "skymais",
                "origin": "https://www.skymais.com.br",
                "referer": "https://www.skymais.com.br/acessar",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT_WEB,
            }
            dgo_payload = {
                "code": tbx_code,
                "grantType": "authorizationCode"
            }
            r_dgo = sess.post(dgo_url, headers=dgo_headers, json=dgo_payload, timeout=20, verify=False)
            print(f"{C.YELLOW}    [sm-dgo /v3/oauth2/token] HTTP {r_dgo.status_code}: {r_dgo.text.strip()[:150]}{C.RESET}")
            if r_dgo.status_code == 200:
                dgo_json = r_dgo.json()
                id_tok = dgo_json.get("id_token")
                if id_tok and id_tok.startswith("ey"):
                    claims = decodificar_token_jwt(id_tok)
                    iss = claims.get("iss", "")
                    aud = claims.get("aud", "")
                    titular = obter_identidade_token(id_tok)
                    print(f"{C.GREEN}[OK] ssoToken DTVGO OFICIAL OBTIDO! iss={iss} aud={aud} | {titular}{C.RESET}")
                    salvar_tokens(id_tok)
                    _salvar_sessao_sky(usuario, id_tok, dgo_json.get("access_token"), titular, dgo_json)
                    return id_tok
        except Exception as e_dgo:
            print(f"{C.RED}    [sm-dgo /v3/oauth2/token] Erro: {e_dgo}{C.RESET}")

        token_exchanges = [
            {
                "grant_type": "authorization_code",
                "code": tbx_code,
                "client_id": "dtvgo",
                "client_secret": "Nd3kYaiEG8",
                "redirect_uri": "https://www.skymais.com.br/ativar",
                "device_id": DEVICE_ID,
                "scope": "openid profile",
            },
            {
                "grant_type": "authorization_code",
                "code": tbx_code,
                "client_id": "dtvgo",
                "client_secret": "Nd3kYaiEG8",
                "redirect_uri": "https://www.skymais.com.br/ativar",
            },
        ]
        for ex_body in token_exchanges:
            for mode in ["form", "json"]:
                try:
                    tok_hdrs = {
                        "authorization": BASIC_AUTH,
                        "x-environment": X_ENVIRONMENT,
                        "x-app": X_APP,
                        "x-client-version": X_CLIENT_VER,
                        "user-agent": USER_AGENT_WEB,
                        "origin": ORIGIN_SKY,
                        "referer": REFERER_SKY,
                    }
                    if mode == "json":
                        tok_hdrs["content-type"] = "application/json"
                        tok_hdrs["accept"] = "application/json"
                        r_tok = sess.post("https://sp.tbxnet.com/v2/auth/token",
                                          headers=tok_hdrs, json=ex_body,
                                          timeout=15, verify=False)
                    else:
                        tok_hdrs["content-type"] = "application/x-www-form-urlencoded"
                        tok_hdrs["accept"] = "application/json"
                        r_tok = sess.post("https://sp.tbxnet.com/v2/auth/token",
                                          headers=tok_hdrs, data=ex_body,
                                          timeout=15, verify=False)

                    print(f"{C.YELLOW}    [/token {mode}] HTTP {r_tok.status_code}: {r_tok.text.strip()[:150]}{C.RESET}")
                    try:
                        tok_json = r_tok.json()
                        for k_sso in ["ssoToken", "sso_token", "id_token", "idToken"]:
                            if tok_json.get(k_sso):
                                sso_val = str(tok_json[k_sso]).strip('"\'  ')
                                if sso_val and len(sso_val) > 30 and sso_val.startswith("ey"):
                                    claims = decodificar_token_jwt(sso_val)
                                    iss = claims.get("iss", "")
                                    aud = claims.get("aud", "")
                                    titular = obter_identidade_token(sso_val)
                                    print(f"{C.GREEN}[OK] ssoToken DTVGO JWT ({k_sso}): iss={iss} aud={aud} | {titular}{C.RESET}")
                                    salvar_tokens(sso_val)
                                    return sso_val
                        # Captura device_token para sonda posterior
                        at = tok_json.get("access_token") or tok_json.get("token", "")
                        ttype = str(tok_json.get("token_type", "")).lower()
                        if at and len(str(at)) > 15:
                            device_tok_candidate = str(at).strip('"\'  ')
                            if "device" in ttype:
                                print(f"{C.YELLOW}    [device_token] {device_tok_candidate[:40]}... Sondando endpoints...{C.RESET}")
                                # ── Sonda endpoints DTVGO e TBX com o device_token ──
                                probe_headers_variants = [
                                    {"authorization": f"Bearer {device_tok_candidate}", "x-device-id": DEVICE_ID},
                                    {"authorization": BASIC_AUTH, "x-device-token": device_tok_candidate, "x-device-id": DEVICE_ID},
                                    {"authorization": BASIC_AUTH, "ssotoken": device_tok_candidate, "x-device-id": DEVICE_ID},
                                ]
                                probe_endpoints = [
                                    ("GET tbx /userinfo",   "GET", "https://sp.tbxnet.com/v2/auth/userinfo"),
                                    ("GET tbx /token/info", "GET", "https://sp.tbxnet.com/v2/auth/token/info"),
                                    ("GET dtv /user",       "GET", "https://dtv-oidc.tbxapis.com/v2/user"),
                                    ("GET dtv /profiles",   "GET", "https://dtv-oidc.tbxapis.com/v2/profiles"),
                                    ("GET dtv /session",    "GET", "https://dtv-oidc.tbxapis.com/v2/session"),
                                    ("POST dtv /session",   "POST","https://dtv-oidc.tbxapis.com/v2/session"),
                                ]
                                found_jwt = None
                                for plabel, pmethod, purl in probe_endpoints:
                                    if found_jwt:
                                        break
                                    for ph in probe_headers_variants:
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
                                                "content-type":     "application/json",
                                            }
                                            if pmethod == "POST":
                                                r_pb = sess.post(purl, headers=all_h,
                                                                 json={"deviceId": DEVICE_ID},
                                                                 timeout=10, verify=False)
                                            else:
                                                r_pb = sess.get(purl, headers=all_h, timeout=10, verify=False)
                                            # Loga TODOS os resultados (incluindo não-200)
                                            status_color = C.GREEN if r_pb.status_code in (200, 201) else C.YELLOW
                                            print(f"{status_color}    [{plabel}] HTTP {r_pb.status_code}: {r_pb.text.strip()[:100]}{C.RESET}")
                                            if r_pb.status_code in (200, 201):
                                                try:
                                                    pb_json = r_pb.json()
                                                    for pk in ["ssoToken", "sso_token", "id_token", "idToken", "sessionToken"]:
                                                        pv = pb_json.get(pk)
                                                        if pv and str(pv).startswith("ey") and len(str(pv)) > 50:
                                                            found_jwt = str(pv).strip('"\'  ')
                                                            claims_p = decodificar_token_jwt(found_jwt)
                                                            iss_p = claims_p.get("iss", "")
                                                            aud_p = claims_p.get("aud", "")
                                                            tit_p = obter_identidade_token(found_jwt)
                                                            print(f"{C.GREEN}[OK] ssoToken DTVGO via {plabel} ({pk}): iss={iss_p} aud={aud_p} | {tit_p}{C.RESET}")
                                                            salvar_tokens(found_jwt)
                                                            return found_jwt
                                                except Exception:
                                                    pass
                                        except Exception as pe:
                                            print(f"{C.YELLOW}    [{plabel}] Erro: {pe}{C.RESET}")
                                        break  # Testa so a primeira variante por endpoint para economizar tempo

                                # Fallback: usa o device_token diretamente para ativacao
                                # (ativador_tv.py linha 1031-1033: retorna device_token como ultimo recurso)
                                print(f"{C.YELLOW}[!] Nenhum JWT obtido. Usando device_token diretamente como ssoToken...{C.RESET}")
                                print(f"{C.YELLOW}    (O DTVGO pode aceitar device_token TBX para ativacao)  {C.RESET}")
                                return device_tok_candidate
                    except Exception:
                        pass
                except Exception as ex:
                    print(f"{C.RED}    [/token {mode}] Erro: {ex}{C.RESET}")
    else:
        print(f"{C.YELLOW}    [DTVGO OAuth] TBX code nao encontrado na URL de redirect.{C.RESET}")

    print(f"{C.RED}    [DTVGO OAuth] Nao foi possivel obter ssoToken DTVGO.{C.RESET}")
    return None


def obter_token_ativacao(usuario: str, auth_data: Optional[Dict[str, Any]],
                         senha: str = "", _sess: Optional[requests.Session] = None,
                         allow_gateway: bool = True, interactive: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Determina o melhor ssoToken para ativacao da Smart TV.
    Prioridade:
      1. Sessao salva especifica do usuario logado (browser_sessions, sky_sessions.json, sso_token.txt)
      2. id_token retornado pelo login HTTP (conta correta, sem necessidade de sessao pre-existente)
      3. Token do gateway em cache (pode ser de outro usuario — avisa o operador)
    """
    push_log(f"🔑 [Sky+ API] Obtendo ssoToken para ativacao da Smart TV ({usuario})...")
    print(f"\n{C.CYAN}[*] Obtendo ssoToken para ativacao da Smart TV...{C.RESET}")

    # ─── Obtém headers da Sky para reutilizar na troca de token ───
    headers_sky_auth = {
        "host": "sm-sky.vrioservices.com",
        "x-environment": X_ENVIRONMENT,
        "x-user-id": "SiteSKY",
        "x-api-key": WEB_API_KEY,
        "x-consumer-system": "SiteSKY",
        "x-client-type": "web",
        "content-type": "application/json",
        "origin": "https://www.sky.com.br",
        "referer": "https://www.sky.com.br/",
        "user-agent": USER_AGENT_WEB,
    }

    # 1. Sessao especifica salva para este usuario
    sso, prof, desc, titular = buscar_sessao_salva(usuario)
    if sso:
        push_log(f"⚡ [Sky+ Cache] Sessão pronta encontrada para '{usuario}': {desc} | {titular}", level="success")
        print(f"{C.GREEN}[OK] ssoToken encontrado para '{usuario}': {desc} | {titular}{C.RESET}")
        return sso, prof, titular

    # 1.5 id_token com aud=dtvgo — obtido via sm-sky-ui (token correto sem precisar do fluxo TBX)
    if auth_data:
        id_tok = auth_data.get("_id_token")
        if id_tok and id_tok.startswith("ey") and len(id_tok) > 50:
            claims_id = decodificar_token_jwt(id_tok)
            if claims_id.get("aud") == "dtvgo":
                titular_id = obter_identidade_token(id_tok)
                push_log(f"✅ [Sky+ OAuth] Token aud=dtvgo obtido: {titular_id}", level="success")
                print(f"{C.GREEN}[OK] id_token com aud=dtvgo obtido! Usando como ssoToken.{C.RESET}")
                print(f"{C.GREEN}    Conta: {titular_id} | iss={claims_id.get('iss')}{C.RESET}")
                salvar_tokens(id_tok)
                return id_tok, None, titular_id

    # 2. Troca de token DTVGO via OAuth authorize + TBX assert (fluxo correto)
    if auth_data and senha:
        push_log(f"📡 [Sky+ OAuth] Trocando código DTVGO (cp_convert=dtvgo)...")
        print(f"{C.CYAN}[*] Realizando troca de token DTVGO (OAuth cp_convert=dtvgo)...{C.RESET}")
        sess_reuse = _sess if _sess else (auth_data.get("_sess") if auth_data else None)
        if not sess_reuse:
            sess_reuse = requests.Session()
        sso_dtvgo = obter_ssotoken_dtvgo(usuario, senha, sess_reuse, headers_sky_auth)
        if sso_dtvgo:
            titular_dtvgo = obter_identidade_token(sso_dtvgo)
            push_log(f"✅ [Sky+ OAuth] Token DTVGO gerado com sucesso: {titular_dtvgo}", level="success")
            return sso_dtvgo, None, titular_dtvgo

    # 3. Fallback: gateway em cache (pode ser de outro usuario)
    cached_sso, cached_prof = carregar_tokens_locais()
    if cached_sso and not token_expirado(cached_sso):
        tit_gw = obter_identidade_token(cached_sso)
        if interactive:
            print(f"\n{C.YELLOW}" + "!" * 68 + f"{C.RESET}")
            print(f"{C.YELLOW}[!] CONTA SEM SESSAO SKY+ DTVGO GERADA{C.RESET}")
            print(f"{C.WHITE}'{usuario}' autenticada mas sem sessao Sky+ Smart TV ativa.{C.RESET}")
            print(f"{C.WHITE}Token em cache: {C.CYAN}{tit_gw}{C.RESET}")
            print(f"{C.YELLOW}" + "!" * 68 + f"{C.RESET}")
            escolha = input(f"\n{C.YELLOW}Usar Gateway ({tit_gw})? [S/n]: {C.RESET}").strip().lower()
            if escolha not in ["n", "nao", "no"]:
                return cached_sso, cached_prof, f"{tit_gw} (Gateway)"
            return None, None, None
        elif allow_gateway:
            push_log(f"⚡ [Sky+ Gateway] Utilizando sessão ativa do Gateway ({tit_gw})...")
            return cached_sso, cached_prof, f"{tit_gw} (Gateway)"

    push_log(f"❌ [Sky+ API] Nenhum token válido disponível para {usuario}.", level="error")
    print(f"{C.RED}[!] Nenhum token disponivel.{C.RESET}")
    return None, None, None

def ativar_tv(tv_code: str, sso_token: str, profile_token: Optional[str] = None, titular: str = "") -> Tuple[bool, str, Optional[dict]]:
    """Executa o POST para ativar a TV via API oficial TBX."""
    tv_code = tv_code.strip().upper()
    titular_real = obter_identidade_token(sso_token) if sso_token else "Desconhecido"

    push_log(f"🚀 [TBX API] Injetando código {tv_code} na API oficial Sky+...")
    print(f"\n{C.CYAN}[ETAPA 2] Enviando CURL 2 para ativar Smart TV (Código: {tv_code})...{C.RESET}")
    print(f"{C.CYAN}[*] Titular do Token que será enviado à Smart TV: {titular_real}{C.RESET}")

    headers = {
        "host": "dtv-oidc.tbxapis.com",
        "x-environment": "prd",
        "sec-ch-ua-platform": '"Windows"',
        "authorization": BASIC_AUTH,
        "x-device-id": DEVICE_ID,
        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
        "sec-ch-ua-mobile": "?0",
        "ssotoken": sso_token,
        "x-app": "skymais",
        "user-agent": USER_AGENT_EDGE,
        "accept": "application/json, text/plain, */*",
        "x-client-version": "3.68.0",
        "content-type": "application/json",
        "x-client-id": "web",
        "origin": "https://www.skymais.com.br",
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://www.skymais.com.br/",
        "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    }

    if profile_token:
        headers["x-profile-token"] = profile_token

    body = {"userCode": tv_code}

    inicio = time.time()
    try:
        resp = requests.post(ACTIVATE_URL, headers=headers, json=body, timeout=15, verify=False)
        duracao = round(time.time() - inicio, 2)

        try:
            dados = resp.json()
        except Exception:
            dados = {"resposta": resp.text if resp.text else "Ativação Confirmada"}

        print("\n" + "=" * 65)
        if resp.status_code in [200, 201, 204]:
            msg_ok = f"Smart TV ativada com sucesso em {duracao}s! ({titular_real})"
            push_log(f"🎉 [SUCESSO] {msg_ok}", level="success")
            print(f"{C.GREEN}{C.BOLD}🎉 SUCESSO ABSOLUTO! SMART TV ATIVADA EM {duracao}s!{C.RESET}")
            print(f"{C.GREEN}Status HTTP:            {resp.status_code}{C.RESET}")
            print(f"{C.GREEN}{C.BOLD}Conta Vinculada na TV:  {titular_real}{C.RESET}")
            if titular and titular != titular_real:
                print(f"{C.YELLOW}Login Informado:        {titular}{C.RESET}")
            print(f"{C.WHITE}Código Pareado:         {tv_code}{C.RESET}")
            print(f"{C.WHITE}Resposta da API:        {dados}{C.RESET}")
            print(f"{C.GREEN}{C.BOLD}Pode olhar a sua Smart TV, ela foi liberada com sucesso!{C.RESET}")
            return True, msg_ok, {
                "email": titular_real,
                "plan": "Sky+ Pay-TV HD",
                "client_name": titular_real,
                "country": "BR",
                "duration_seconds": duracao,
                "raw_response": dados
            }
        elif resp.status_code == 404:
            msg_err = f"Código {tv_code} não encontrado ou expirado na Smart TV (HTTP 404)."
            push_log(f"❌ [ERRO] {msg_err}", level="error")
            print(f"{C.RED}{C.BOLD}❌ CÓDIGO NÃO ENCONTRADO (HTTP 404):{C.RESET}")
            print(f"{C.RED}O código '{tv_code}' expirou ou não existe na TV.{C.RESET}")
            return False, msg_err, None
        elif resp.status_code in [401, 403]:
            msg_err = f"Erro de autenticação nos servidores Sky (HTTP {resp.status_code})."
            push_log(f"❌ [ERRO] {msg_err}", level="error")
            print(f"{C.RED}{C.BOLD}❌ ERRO DE AUTENTICAÇÃO (HTTP {resp.status_code}):{C.RESET}")
            return False, msg_err, None
        else:
            msg_err = f"Status {resp.status_code} retornado pelos servidores Sky: {dados}"
            push_log(f"⚠️ {msg_err}", level="warn")
            print(f"{C.RED}{C.BOLD}⚠️ STATUS {resp.status_code}:{C.RESET}")
            return False, msg_err, None
    except Exception as e:
        msg_err = f"Erro de conexão ao ativar TV na Sky: {e}"
        push_log(f"❌ {msg_err}", level="error")
        print(f"{C.RED}[!] Erro de conexão ao ativar TV: {e}{C.RESET}")
        return False, msg_err, None
    finally:
        print("=" * 65)

def executar_ativacao_completa(tv_code: str, usuario: str = "", senha: str = "",
                               sso_token_direto: str = "", profile_token_direto: str = "",
                               allow_gateway: bool = True) -> Tuple[bool, str, Optional[dict]]:
    """
    Função unificada 100% via API REST pura para ser chamada pelo site ou por scripts:
    1. Utiliza token direto ou busca sessão em cache salva para 'usuario'.
    2. Se não houver sessão salva, realiza login REST (autenticar_conta_sky) + troca DTVGO OAuth.
    3. Injeta código da TV via API TBX (ativar_tv).
    """
    clean_code = re.sub(r'[^A-Za-z0-9]', '', str(tv_code)).upper()
    if len(clean_code) < 5:
        return False, "O código de ativação da TV deve ter pelo menos 5 caracteres.", None

    # Caso 1: Token direto fornecido
    if sso_token_direto and not token_expirado(sso_token_direto):
        tit_direto = obter_identidade_token(sso_token_direto)
        push_log(f"⚡ [Sky+ API] Usando token direto de {tit_direto} (300ms)...")
        return ativar_tv(clean_code, sso_token_direto, profile_token_direto, titular=tit_direto)

    # Caso 2: Sessão em cache para o usuário
    if usuario:
        sso_cached, prof_cached, desc, tit_cached = buscar_sessao_salva(usuario)
        if sso_cached and not token_expirado(sso_cached):
            push_log(f"⚡ [Sky+ API] Usando sessão em cache ({desc}): {tit_cached} (300ms)...")
            return ativar_tv(clean_code, sso_cached, prof_cached, titular=tit_cached)

    # Caso 3: Login REST com credenciais fornecidas
    if usuario and senha:
        push_log(f"🔑 [Sky+ API] Realizando autenticação HTTP REST na Sky ({usuario})...")
        sucesso_login, auth_data = autenticar_conta_sky(usuario, senha)
        if sucesso_login and auth_data:
            sess_auth = auth_data.get("_sess")
            sso, prof, titular = obter_token_ativacao(usuario, auth_data, senha=senha, _sess=sess_auth, allow_gateway=allow_gateway, interactive=False)
            if sso:
                return ativar_tv(clean_code, sso, prof, titular=titular)
        else:
            push_log(f"⚠️ [Sky+ API] Falha no login da conta {usuario}.", level="warn")

    # Caso 4: Fallback no token do Gateway
    if allow_gateway:
        cached_sso, cached_prof = carregar_tokens_locais()
        if cached_sso and not token_expirado(cached_sso):
            tit_gw = obter_identidade_token(cached_sso)
            push_log(f"⚡ [Sky+ API] Fallback no Gateway ({tit_gw})...")
            return ativar_tv(clean_code, cached_sso, cached_prof, titular=f"{tit_gw} (Gateway)")

    return False, f"Não foi possível obter sessão ativa da Sky+ para a conta {usuario or 'solicitada'}.", None

def main():
    banner()

    # 1. Configuração de Login
    print(f"{C.WHITE}{C.BOLD}Configuração de Login Sky:{C.RESET}")
    user_in = input(f"Digite o Telefone, Email ou CPF [Padrão: {DEFAULT_LOGIN}]: ").strip()
    login_user = user_in if user_in else DEFAULT_LOGIN

    pass_in = input(f"Digite a Senha Sky [Padrão: {DEFAULT_PASS}]: ").strip()
    login_pass = pass_in if pass_in else DEFAULT_PASS

    # 2. Código da TV
    tv_code = ""
    if len(sys.argv) >= 2:
        arg_code = sys.argv[1].strip().upper()
        if arg_code not in ["SEU_CODIGO_AQUI", "NOVO_CODIGO_AQUI"] and len(arg_code) >= 5 and arg_code.isalnum():
            tv_code = arg_code

    while not tv_code or len(tv_code) < 5 or not tv_code.isalnum():
        tv_code = input(f"\n{C.YELLOW}{C.BOLD}Digite o CÓDIGO QUE ESTÁ NA SUA SMART TV (Ex: 224731):{C.RESET} ").strip().upper()

    # 3. Executa a ativação completa
    success, msg, acc_info = executar_ativacao_completa(tv_code, usuario=login_user, senha=login_pass, allow_gateway=True)
    if not success:
        print(f"\n{C.RED}[!] {msg}{C.RESET}")
    input("\nPressione [ENTER] para finalizar...")

if __name__ == "__main__":
    main()

