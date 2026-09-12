import os
import re
import json
import time
import glob
import base64
import threading
from typing import Dict, Optional, Tuple, List, Set

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HITS_DIR = os.path.join(BASE_DIR, "hits")
RAW_JSON_DIR = os.path.join(HITS_DIR, "raw_json")
SKY_CONTAS_FILE = os.path.join(BASE_DIR, "skycontas.txt")
CUSTOM_SKY_FILE = os.path.join(HITS_DIR, "contas_sky.txt")
ACTIVATED_ACCOUNTS_FILE = os.path.join(HITS_DIR, "contas_ativadas.txt")
ACTIVATIONS_LOG_FILE = os.path.join(HITS_DIR, "ativacoes_tv.txt")
SSO_TOKEN_FILE = os.path.join(BASE_DIR, "sso_token.txt")
PROFILE_TOKEN_FILE = os.path.join(BASE_DIR, "profile_token.txt")
SKY_SESSIONS_FILE = os.path.join(HITS_DIR, "sky_sessions.json")
PAYLOAD_ANDROID_FILE = os.path.join(BASE_DIR, "payload.b64")
PAYLOAD_WEB_FILE = os.path.join(BASE_DIR, "payload_web.b64")

os.makedirs(HITS_DIR, exist_ok=True)

# Lock de concorrência para leitura/escrita
SKY_LOCK = threading.Lock()

# Limite máximo de ativações por conta Sky
MAX_SKY_ACTIVATIONS = 2

# Cache em memória
CACHED_SKY_ACCOUNTS: List[dict] = []
INVALID_ACCOUNTS_FILE = os.path.join(HITS_DIR, "contas_invalidas.txt")

def get_invalid_sky_accounts() -> Set[str]:
    """Retorna conjunto de emails conhecidos com senha incorreta/inválida."""
    inv = set()
    if os.path.exists(INVALID_ACCOUNTS_FILE):
        try:
            with open(INVALID_ACCOUNTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        acc = line.split("|")[0].split(":")[0].strip().lower()
                        if acc and "@" in acc:
                            inv.add(acc)
        except Exception:
            pass
    return inv

def record_invalid_sky_account(email: str, reason: str = ""):
    """Registra conta com senha incorreta ou inválida para ser ignorada automaticamente."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return
    clean_reason = re.sub(r'[\r\n]+', ' ', str(reason)).strip()[:100]
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        os.makedirs(HITS_DIR, exist_ok=True)
        with open(INVALID_ACCOUNTS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{email} | {clean_reason} | {now_str}\n")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# LEITURA DE CONTAGEM DE ATIVAÇÕES (MÁXIMO 2 TVs POR CONTA)
# ═══════════════════════════════════════════════════════════════
def get_activation_counts() -> Dict[str, int]:
    """Retorna dict {email_lower: quantidade_de_ativacoes} lendo hits/contas_ativadas.txt e used_cookies.json de forma consistente."""
    counts: Dict[str, int] = {}
    seen_events: Set[Tuple[str, str]] = set()

    if os.path.exists(ACTIVATED_ACCOUNTS_FILE):
        try:
            with open(ACTIVATED_ACCOUNTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if ":" in line and "|" in line:
                        acc = line.split("|")[0].strip()
                        em = acc.split(":")[0].strip().lower()
                        tv = ""
                        m = re.search(r'TV:\s*([A-Za-z0-9]+)', line)
                        if m:
                            tv = m.group(1).upper()
                        if em:
                            event_key = (em, tv or line)
                            if event_key not in seen_events:
                                seen_events.add(event_key)
                                counts[em] = counts.get(em, 0) + 1
        except Exception:
            pass

    used_reg = os.path.join(BASE_DIR, "used_cookies.json")
    if os.path.exists(used_reg):
        try:
            with open(used_reg, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if item.get("service") == "Sky" and item.get("status") == "Sucesso":
                            em = item.get("email", "").strip().lower()
                            tv = str(item.get("tv_code") or item.get("code") or "").strip().upper()
                            if em:
                                event_key = (em, tv or str(item.get("used_at", "")))
                                if event_key not in seen_events:
                                    seen_events.add(event_key)
                                    counts[em] = counts.get(em, 0) + 1
        except Exception:
            pass
    return counts

def record_account_activated(email: str, password: str, tv_code: str):
    """Registra conta utilizada para ativar uma TV e invalida o cache para rotação imediata."""
    global CACHED_SKY_TIMESTAMP
    os.makedirs(HITS_DIR, exist_ok=True)
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"{email}:{password} | TV: {tv_code} | {now_str}\n"
    try:
        with open(ACTIVATED_ACCOUNTS_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass
    # Invalida cache imediatamente para que a próxima chamada de find_sky_valid_account()
    # veja os contadores atualizados sem esperar o timeout de 15 segundos
    CACHED_SKY_TIMESTAMP = 0.0

def save_activation_log(email: str, password: str, tv_code: str, success: bool, message: str):
    """Salva log detalhado da ativação."""
    os.makedirs(HITS_DIR, exist_ok=True)
    status = "SUCESSO" if success else "FALHA"
    import datetime
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    line = f"[{status}] {now_str} | {email}:{password} | Codigo: {tv_code} | {message}\n"
    try:
        with open(ACTIVATIONS_LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# PARSERS DE CONTAS E HITS SKY
# ═══════════════════════════════════════════════════════════════
def _clean_plan_name(raw: str) -> str:
    """Higieniza e simplifica o nome do plano da Sky para exibição elegante."""
    if not raw:
        return "Sky TV VIP"
    clean = raw.strip()
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    clean = clean.replace('- P', '').replace('- Pre', '').strip(' -')
    clean = re.sub(r'\s+', ' ', clean)
    return clean or "Sky TV VIP"

def _extract_state_from_text(text: str) -> str:
    """Extrai UF brasileiro (SP, RJ, etc.) ou retorna BR."""
    m = re.search(r'-\s*([A-Z]{2})\b', text)
    if m:
        return m.group(1).upper()
    m2 = re.search(r'\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b', text.upper())
    if m2:
        return m2.group(1).upper()
    return "BR"

def parse_hit_block(block: str, source_file: str = "hits") -> Optional[dict]:
    """Extrai metadados completos de um bloco de hit formatado do Sky Checker."""
    login_match = re.search(r"Login:\s*([^\s:]+):([^\r\n]+)", block)
    if not login_match:
        login_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+):([^\s\r\n]+)", block)
        if not login_match:
            return None

    email = login_match.group(1).strip()
    password = login_match.group(2).strip()
    # Remove qualquer caractere residual de moldura como ║ ou ╚
    password = re.sub(r'[\u2550-\u256c║╚╝╔╗╠╣]', '', password).strip()
    if not email or not password:
        return None

    # Cliente & CPF
    client_name = ""
    cpf = ""
    cliente_match = re.search(r"Cliente:\s*([^|\r\n]+)(?:\|\s*CPF:\s*(\d+))?", block)
    if cliente_match:
        client_name = cliente_match.group(1).strip()
        cpf = (cliente_match.group(2) or "").strip()

    # Assinatura / Plano
    plan = "Sky TV VIP"
    plan_match = re.search(r"Assinatura\s*\d*:\s*([^(\r\n]+)", block)
    if plan_match:
        plan = _clean_plan_name(plan_match.group(1))

    # Localidade / Estado
    state = "BR"
    local_match = re.search(r"Local:\s*([^|\r\n]+)", block)
    if local_match:
        state = _extract_state_from_text(local_match.group(1))

    # Adicionais (Telecine, HBO, Premiere, etc.)
    adicionais = []
    for add_line in re.findall(r"(?:Inclusos|Adicionais):\s*(.+)", block):
        adicionais.append(add_line.strip())

    return {
        "file": source_file,
        "email": email,
        "password": password,
        "info": {
            "email": email,
            "plan": plan,
            "country": state,
            "client_name": client_name,
            "cpf": cpf,
            "adicionais": adicionais,
            "source": source_file
        },
        "validated": False
    }

def load_hits_from_text_file(filepath: str) -> List[dict]:
    """Lê blocos ou linhas de um arquivo .txt com suporte transparente a criptografia."""
    if not os.path.exists(filepath):
        return []
    content = ""
    try:
        import gerenciador_seguranca
        with open(filepath, "rb") as f:
            raw_b = f.read()
        plain_b = gerenciador_seguranca.decrypt_bytes(raw_b, gerenciador_seguranca.get_master_key())
        content = plain_b.decode('utf-8', errors='ignore') if plain_b is not None else raw_b.decode('utf-8', errors='ignore')
    except Exception:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            pass

    if not content:
        try:
            with open(filepath, "r", encoding="latin-1", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

    fname = os.path.basename(filepath)
    accounts = []
    seen = set()

    # Se contém blocos de hit (delimitador ╔═══ ou [Sky Checker)
    if "\u2554" in content or "[Sky Checker" in content:
        delim = r"\u2554" if "\u2554" in content else r"\[Sky Checker"
        for block in re.split(delim, content):
            parsed = parse_hit_block(block, source_file=fname)
            if parsed:
                key = parsed["email"].lower()
                if key not in seen:
                    seen.add(key)
                    accounts.append(parsed)
        if accounts:
            return accounts

    # Formato simples email:senha ou combo
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line or "|" in line:
            sep = ":" if ":" in line else "|"
            parts = line.split(sep, 1)
            em, pw = parts[0].strip(), parts[1].strip()
            if "login:" in em.lower():
                em = re.sub(r'(?i)login\s*:\s*', '', em).strip()
            # Remove molduras residuais
            pw = re.sub(r'[\u2550-\u256c║╚╝╔╗╠╣]', '', pw).strip()
            if em and pw and ("@" in em or len(re.sub(r"\D", "", em)) >= 10):
                key = em.lower()
                if key not in seen:
                    seen.add(key)
                    accounts.append({
                        "file": fname,
                        "email": em,
                        "password": pw,
                        "info": {
                            "email": em,
                            "plan": "Sky TV VIP",
                            "country": "BR",
                            "client_name": "",
                            "cpf": "",
                            "adicionais": [],
                            "source": fname
                        },
                        "validated": False
                    })
    return accounts

def load_raw_json_accounts() -> List[dict]:
    """Carrega contas com dados completos cacheados em hits/raw_json/."""
    if not os.path.exists(RAW_JSON_DIR):
        return []

    accounts = []
    seen = set()
    try:
        for fname in os.listdir(RAW_JSON_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(RAW_JSON_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    continue

                em = data.get("email") or ""
                pw = data.get("password") or ""

                raw_data = data.get("raw_data") if isinstance(data.get("raw_data"), dict) else {}
                customer = raw_data.get("customer") if isinstance(raw_data.get("customer"), dict) else (data.get("customer") if isinstance(data.get("customer"), dict) else {})
                
                # Se email principal não tiver @ mas customer tiver email real
                if "@" not in em and customer and isinstance(customer, dict) and "@" in customer.get("email", ""):
                    em = customer.get("email", "")

                if not em:
                    continue

                key = em.lower()
                if key in seen:
                    continue
                seen.add(key)

                client_name = f"{customer.get('name', '')} {customer.get('secondName', '')}".strip() if isinstance(customer, dict) else ""
                cpf = customer.get("cpf", "") if isinstance(customer, dict) else ""

                signatures = raw_data.get("signatures") or data.get("signatures") or []
                plan = "Sky TV VIP"
                state = "BR"

                if signatures and isinstance(signatures, list) and len(signatures) > 0 and isinstance(signatures[0], dict):
                    sig = signatures[0]
                    plan = _clean_plan_name(sig.get("productName", "Sky TV VIP"))
                    addr = sig.get("addressInstallation") or sig.get("addressBilling") or {}
                    if isinstance(addr, dict):
                        state = addr.get("state") or "BR"

                accounts.append({
                    "file": f"raw_json/{fname}",
                    "email": em,
                    "password": pw,
                    "jwt_token": data.get("jwt_token"),
                    "access_token": data.get("access_token"),
                    "info": {
                        "email": em,
                        "plan": plan,
                        "country": state,
                        "client_name": client_name,
                        "cpf": cpf,
                        "adicionais": [],
                        "source": "raw_json"
                    },
                    "validated": bool(data.get("jwt_token"))
                })
            except Exception:
                pass
    except Exception:
        pass
    return accounts

def parse_sso_jwt(token: str) -> dict:
    """Decodifica payload do JWT sso_token com segurança."""
    if not token or "ey" not in token:
        return {}
    parts = token.split(".")
    if len(parts) >= 2:
        p = parts[1]
        rem = len(p) % 4
        if rem:
            p += "=" * (4 - rem)
        try:
            return json.loads(base64.urlsafe_b64decode(p))
        except Exception:
            pass
    return {}

def get_all_active_sso_sessions() -> List[dict]:
    """
    Carrega todas as sessões ativas com sso_token e profile_token.
    Lê hits/sky_sessions.json e complementa com sso_token.txt / profile_token.txt.
    Cada sessão é 100% isolada e possui seus próprios tokens sem vazamento entre contas.
    """
    sessions: List[dict] = []
    seen_emails: Set[str] = set()

    # 1. Lê sessões cadastradas no arquivo hits/sky_sessions.json
    if os.path.exists(SKY_SESSIONS_FILE):
        try:
            with open(SKY_SESSIONS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    sso = (item.get("sso_token") or "").strip()
                    prof = (item.get("profile_token") or "").strip()
                    if not sso or "ey" not in sso:
                        continue
                    payload = parse_sso_jwt(sso)
                    em = (item.get("email") or payload.get("email") or payload.get("sub") or "").strip()
                    if em.startswith("sky_"):
                        em = em[4:]
                    em_low = em.lower()
                    if not em_low or em_low in seen_emails:
                        continue
                    seen_emails.add(em_low)

                    given = payload.get("givenName", "")
                    family = payload.get("familyName", "")
                    client_name = item.get("client_name") or f"{given} {family}".strip() or payload.get("name", "Assinante Sky+")
                    plan_name = item.get("plan") or "PAY-TV + FIBRA // SUPER HD II ⚡"
                    exp = payload.get("exp", 0)
                    dev_id = item.get("device_id") or payload.get("deviceId", "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764")

                    sessions.append({
                        "email": em,
                        "password": "",
                        "sso_token": sso,
                        "profile_token": prof,
                        "is_session": True,
                        "exp": exp,
                        "device_id": dev_id,
                        "file": "sky_sessions.json",
                        "info": {
                            "email": em,
                            "plan": plan_name,
                            "country": payload.get("iso2Code", "BR"),
                            "client_name": client_name,
                            "cpf": payload.get("accountId", ""),
                            "adicionais": ["Ativação Instantânea (300ms)", "Tokens Oficiais TBX"],
                            "source": "Sessão Sky+ Ativa",
                            "is_session": True
                        }
                    })
        except Exception as e:
            print(f"[Sky Sessions] Erro ao ler sky_sessions.json: {e}")

    # 2. Complementa com sso_token.txt e profile_token.txt na raiz se ainda não incluído
    if os.path.exists(SSO_TOKEN_FILE):
        try:
            with open(SSO_TOKEN_FILE, "r", encoding="utf-8") as f:
                sso_root = f.read().strip()
            prof_root = ""
            if os.path.exists(PROFILE_TOKEN_FILE):
                with open(PROFILE_TOKEN_FILE, "r", encoding="utf-8") as pf:
                    prof_root = pf.read().strip()

            if sso_root and "ey" in sso_root:
                payload = parse_sso_jwt(sso_root)
                em_root = (payload.get("email") or payload.get("sub") or "sessao_sky@skymais.com.br").strip()
                if em_root.startswith("sky_"):
                    em_root = em_root[4:]
                if em_root.lower() not in seen_emails:
                    seen_emails.add(em_root.lower())
                    given = payload.get("givenName", "")
                    family = payload.get("familyName", "")
                    client_name = f"{given} {family}".strip() or payload.get("name", "Assinante Sky+")
                    dev_id = payload.get("deviceId", "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764")

                    sessions.append({
                        "email": em_root,
                        "password": "",
                        "sso_token": sso_root,
                        "profile_token": prof_root,
                        "is_session": True,
                        "exp": payload.get("exp", 0),
                        "device_id": dev_id,
                        "file": "sso_token.txt",
                        "info": {
                            "email": em_root,
                            "plan": "PAY-TV + FIBRA // SUPER HD II ⚡",
                            "country": payload.get("iso2Code", "BR"),
                            "client_name": client_name,
                            "cpf": payload.get("accountId", ""),
                            "adicionais": ["Ativação Instantânea (300ms)", "Tokens Oficiais TBX"],
                            "source": "sso_token.txt",
                            "is_session": True
                        }
                    })
        except Exception:
            pass

    return sessions

def get_active_sso_session() -> Optional[dict]:
    """Retorna a primeira sessão ativa disponível para compatibilidade."""
    sessions = get_all_active_sso_sessions()
    return sessions[0] if sessions else None

# ═══════════════════════════════════════════════════════════════
# CARREGAMENTO GLOBAL DE CONTAS SKY (PRIORIDADE: skycontas.txt)
# ═══════════════════════════════════════════════════════════════
def load_all_sky_accounts(force_reload: bool = False) -> List[dict]:
    """
    Carrega e consolida todas as contas Sky priorizando diretamente as sessões ativas e skycontas.txt.
    Enriquece metadados (plano, cliente, tokens) a partir de hits/ e raw_json de forma 100% segura.
    """
    global CACHED_SKY_ACCOUNTS, CACHED_SKY_TIMESTAMP

    now = time.time()
    with SKY_LOCK:
        if not force_reload and CACHED_SKY_ACCOUNTS and (now - CACHED_SKY_TIMESTAMP < 15.0):
            return list(CACHED_SKY_ACCOUNTS)

        all_accounts: List[dict] = []
        seen_keys: Set[str] = set()
        invalid_accounts = get_invalid_sky_accounts()

        def add_acc(acc: dict):
            if not isinstance(acc, dict):
                return
            em = acc.get("email", "").strip().lower()
            if not em or em in seen_keys or em in invalid_accounts:
                return
            if not acc.get("info") or not isinstance(acc["info"], dict):
                acc["info"] = {
                    "email": acc.get("email", ""),
                    "plan": "Sky TV VIP",
                    "country": "BR",
                    "client_name": "",
                    "cpf": "",
                    "adicionais": [],
                    "source": acc.get("file", "skycontas.txt")
                }
            seen_keys.add(em)
            all_accounts.append(acc)

        # 0. ⚡ PRIORIDADE MÁXIMA ABSOLUTA: Todas as Sessões Ativas em sky_sessions.json / sso_token.txt
        active_sessions = get_all_active_sso_sessions()
        for active_sess in active_sessions:
            em = active_sess["email"].strip().lower()
            if em not in seen_keys:
                all_accounts.append(active_sess)
                seen_keys.add(em)

        # 1. 🌟 PRIORIDADE 1: skycontas.txt na raiz (exatamente o arquivo solicitado pelo usuário!)
        if os.path.exists(SKY_CONTAS_FILE):
            try:
                for acc in load_hits_from_text_file(SKY_CONTAS_FILE):
                    add_acc(acc)
            except Exception:
                pass

        # 2. Contas adicionadas pelo painel (hits/contas_sky.txt)
        if os.path.exists(CUSTOM_SKY_FILE):
            try:
                for acc in load_hits_from_text_file(CUSTOM_SKY_FILE):
                    add_acc(acc)
            except Exception:
                pass

        # 3. Enriquece contas com dados de hits/ (COMPLETAS.txt, MEDIA.txt, BASICA.txt, Todos_Hits.txt)
        priority_files = [
            "COMPLETAS.txt",
            "MEDIA.txt",
            "BASICA.txt",
            "Todos_Hits.txt"
        ]
        for fname in priority_files:
            fpath = os.path.join(HITS_DIR, fname)
            if os.path.exists(fpath):
                try:
                    for acc in load_hits_from_text_file(fpath):
                        em = acc.get("email", "").strip().lower()
                        if em in seen_keys:
                            # Enriquece conta já existente do skycontas.txt com metadados do hit
                            for existing in all_accounts:
                                if existing.get("email", "").strip().lower() == em:
                                    if acc.get("info") and isinstance(acc["info"], dict):
                                        if acc["info"].get("plan") and acc["info"]["plan"] != "Sky TV VIP":
                                            existing["info"]["plan"] = acc["info"]["plan"]
                                        if acc["info"].get("client_name"):
                                            existing["info"]["client_name"] = acc["info"]["client_name"]
                                        if acc["info"].get("cpf"):
                                            existing["info"]["cpf"] = acc["info"]["cpf"]
                                        if acc["info"].get("country") and acc["info"]["country"] != "BR":
                                            existing["info"]["country"] = acc["info"]["country"]
                                    break
                except Exception:
                    pass

        # 4. Enriquece contas com dados de raw_json (tokens salvos jwt_token, nome do cliente, etc.)
        try:
            raw_accounts = load_raw_json_accounts()
            for raw_acc in raw_accounts:
                em = raw_acc.get("email", "").strip().lower()
                if em in seen_keys:
                    for existing in all_accounts:
                        if existing.get("email", "").strip().lower() == em:
                            if raw_acc.get("jwt_token"):
                                existing["jwt_token"] = raw_acc["jwt_token"]
                                existing["validated"] = True
                            if raw_acc.get("info") and isinstance(raw_acc["info"], dict):
                                if raw_acc["info"].get("client_name") and not existing["info"].get("client_name"):
                                    existing["info"]["client_name"] = raw_acc["info"]["client_name"]
                                if raw_acc["info"].get("plan") and existing["info"].get("plan") == "Sky TV VIP":
                                    existing["info"]["plan"] = raw_acc["info"]["plan"]
                                if raw_acc["info"].get("country") and existing["info"].get("country") == "BR":
                                    existing["info"]["country"] = raw_acc["info"]["country"]
                            break
        except Exception:
            pass

        # 6. Ordena por contagem de ativações reais (máximo 2 TVs por conta)
        try:
            act_counts = get_activation_counts()
            for acc in all_accounts:
                em = acc.get("email", "").strip().lower()
                if "info" not in acc or not isinstance(acc["info"], dict):
                    acc["info"] = {
                        "email": acc.get("email", ""),
                        "plan": "Sky TV VIP",
                        "country": "BR",
                        "client_name": "",
                        "cpf": "",
                        "adicionais": []
                    }
                cnt = act_counts.get(em, 0)
                acc["info"]["activations"] = cnt
                acc["info"]["max_activations"] = MAX_SKY_ACTIVATIONS
                if cnt >= MAX_SKY_ACTIVATIONS:
                    acc["info"]["status_badge"] = f"Esgotada ({cnt}/{MAX_SKY_ACTIVATIONS} TVs)"
                elif cnt == 1:
                    acc["info"]["status_badge"] = f"1/{MAX_SKY_ACTIVATIONS} TV (Ativa mais 1 TV)"
                else:
                    acc["info"]["status_badge"] = f"0/{MAX_SKY_ACTIVATIONS} TVs (Pronta)"

            all_accounts.sort(key=lambda a: (
                1 if a.get("info", {}).get("activations", 0) >= MAX_SKY_ACTIVATIONS else 0,
                0 if a.get("is_session") or a.get("sso_token") else 1,
                a.get("info", {}).get("activations", 0)
            ))
        except Exception:
            pass

        CACHED_SKY_ACCOUNTS = all_accounts
        CACHED_SKY_TIMESTAMP = now
        return list(CACHED_SKY_ACCOUNTS)

def get_all_sky_accounts() -> List[dict]:
    """Retorna todas as contas Sky formatadas para a fila e modal da interface."""
    return load_all_sky_accounts()

def find_sky_valid_account(used_accounts: Set[str], dead_accounts: Set[str]) -> Optional[dict]:
    """Retorna a melhor conta Sky disponível para o próximo pareamento (máximo 2 TVs por conta)."""
    accounts = load_all_sky_accounts()
    if not accounts:
        return None

    act_counts = get_activation_counts()
    normalized_dead = {str(d).strip().lower() for d in dead_accounts if d}
    normalized_dead.update(get_invalid_sky_accounts())
    normalized_used = {str(u).strip().lower() for u in used_accounts if u}

    # Contas que já atingiram o limite de 2 TVs são consideradas usadas/esgotadas
    for em, cnt in act_counts.items():
        if cnt >= MAX_SKY_ACTIVATIONS:
            normalized_used.add(em)

    # 1. Prioridade: Contas vivas que ainda têm vaga (< 2 ativações)
    candidates = []
    for acc in accounts:
        em = acc.get("email", "").strip().lower()
        if not em or em in normalized_dead or em in normalized_used:
            continue
        cnt = act_counts.get(em, 0)
        candidates.append((acc, cnt))

    if candidates:
        def _score(item):
            acc, cnt = item
            is_sess = 0 if (acc.get("is_session") or acc.get("sso_token")) else 1
            plan = str(acc.get("info", {}).get("plan", "")).upper()
            has_fibra = 0 if ("FIBRA" in plan or "PLUS TOTAL" in plan or "SUPER HD" in plan) else 1
            # Se já tem 1 ativação (< 2), prioriza para completar a 2ª TV antes de passar para outra
            fill_batch = -1 if cnt == 1 else 0
            return (is_sess, fill_batch, has_fibra, cnt)

        candidates.sort(key=_score)
        return candidates[0][0]

    # 2. Se todas as contas atingiram o limite, rotaciona pegando a com menor contagem
    valid_alive = [
        a for a in accounts
        if a.get("email", "").strip().lower() and a.get("email", "").strip().lower() not in normalized_dead
    ]
    if valid_alive:
        valid_alive.sort(key=lambda a: (
            act_counts.get(a.get("email", "").strip().lower(), 0),
            0 if a.get("is_session") or a.get("sso_token") else 1
        ))
        return valid_alive[0]

    return accounts[0]

def select_sky_account_by_identifier(identifier: str) -> Optional[dict]:
    """Busca conta específica por email, login ou arquivo."""
    target = identifier.strip().lower()
    accounts = load_all_sky_accounts()
    for acc in accounts:
        em = acc.get("email", "").strip().lower()
        if em == target or target in em:
            return acc
    return None

# ═══════════════════════════════════════════════════════════════
# ATIVAÇÃO OFICIAL DE SMART TV (dtv-oidc.tbxapis.com)
# ═══════════════════════════════════════════════════════════════
def activate_sky_tv(tv_code: str, account_data: dict, use_proxy: bool = False) -> Tuple[bool, str, Optional[dict]]:
    """
    Executa a ativação oficial da Smart TV Sky via Playwright Chromium com Stealth,
    resolução automática de reCAPTCHA por áudio e injeção direta de código no DOM.
    """
    clean_code = re.sub(r'[^A-Za-z0-9]', '', str(tv_code)).upper()
    if len(clean_code) < 6:
        return False, "O código de ativação da TV deve ter 6 dígitos/caracteres.", None

    if not account_data or "email" not in account_data:
        return False, "Nenhuma conta Sky selecionada ou pronta no estoque.", None

    email = account_data["email"].strip()
    password = account_data.get("password", "").strip()

    if not password:
        return False, f"A conta {email} não possui senha cadastrada para autenticação no Sky+.", None

    try:
        import automacao_playwright
        res = automacao_playwright.ativar_tv_playwright(
            email=email,
            password=password,
            tv_code=clean_code,
            headless=True,
            timeout_ms=55000,
            usar_proxy=use_proxy
        )

        # Se o Google bloqueou o IP local, retenta automaticamente com Proxy Residencial DataImpulse
        if res.get("motivo") == "IP_BLOQUEADO_GOOGLE" and not use_proxy:
            print("[*] Google reCAPTCHA bloqueou IP local, ativando Proxy Residencial DataImpulse (BR)...")
            res = automacao_playwright.ativar_tv_playwright(
                email=email,
                password=password,
                tv_code=clean_code,
                headless=True,
                timeout_ms=55000,
                usar_proxy=True
            )

        success = res.get("success", False)
        msg = res.get("message", "TV verificada")

        if success:
            save_activation_log(email, password, clean_code, True, msg)
            record_account_activated(email, password, clean_code)
            return True, msg, account_data.get("info")
        else:
            if "credenciais" in msg.lower() or "inválid" in msg.lower() or "incorret" in msg.lower() or "não encontrada" in msg.lower():
                record_invalid_sky_account(email, msg)
            save_activation_log(email, password, clean_code, False, msg)
            return False, msg, None

    except Exception as e:
        save_activation_log(email, password, clean_code, False, f"Exceção: {e}")
        return False, f"Erro durante a ativação Sky com Playwright: {e}", None

# ═══════════════════════════════════════════════════════════════
# SALVAMENTO E IMPORTAÇÃO DE CONTAS SKY PELO PAINEL
# ═══════════════════════════════════════════════════════════════
def save_single_sky_account(email: str, password: str, plan: str = "Sky TV VIP") -> bool:
    """Salva uma conta única direta em hits/contas_sky.txt e skycontas.txt."""
    email = email.strip()
    password = password.strip()
    if not email or not password:
        return False

    line = f"{email}:{password}\n"
    os.makedirs(HITS_DIR, exist_ok=True)
    try:
        with open(CUSTOM_SKY_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        with open(SKY_CONTAS_FILE, "a", encoding="utf-8") as f:
            f.write(line)

        # Invalida cache para recarregar instantaneamente
        load_all_sky_accounts(force_reload=True)
        return True
    except Exception:
        return False

def save_sky_hits(raw_text: str) -> int:
    """Salva lote de contas ou blocos de hit colados pelo usuário."""
    text = raw_text.strip()
    if not text:
        return 0

    os.makedirs(HITS_DIR, exist_ok=True)
    count = 0

    # Se for blocos de hit do checker
    if "\u2554" in text or "Login:" in text:
        blocks = re.split(r"\u2554", text)
        for b in blocks:
            if "Login:" in b:
                count += 1
        try:
            with open(CUSTOM_SKY_FILE, "a", encoding="utf-8") as f:
                f.write("\n" + text + "\n")
        except Exception:
            pass
        # Extrai e salva formato simples em skycontas.txt também
        try:
            extracted_combos = []
            for b in blocks:
                lm = re.search(r"Login:\s*([^\s:]+):([^\r\n]+)", b)
                if lm:
                    e_acc = lm.group(1).strip()
                    p_acc = re.sub(r'[\u2550-\u256c║╚╝╔╗╠╣]', '', lm.group(2)).strip()
                    if e_acc and p_acc:
                        extracted_combos.append(f"{e_acc}:{p_acc}")
            if extracted_combos:
                with open(SKY_CONTAS_FILE, "a", encoding="utf-8") as f:
                    f.write("\n" + "\n".join(extracted_combos) + "\n")
        except Exception:
            pass
    else:
        # Se for lista email:senha
        lines = [l.strip() for l in text.splitlines() if l.strip() and (":" in l or "|" in l)]
        count = len(lines)
        try:
            with open(CUSTOM_SKY_FILE, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(lines) + "\n")
            with open(SKY_CONTAS_FILE, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(lines) + "\n")
        except Exception:
            pass

    load_all_sky_accounts(force_reload=True)
    return max(1, count)

def save_sky_session(sso_token: str, profile_token: str = "") -> bool:
    """Salva ou adiciona uma sessão ativa em hits/sky_sessions.json e sso_token.txt."""
    sso_token = sso_token.strip()
    profile_token = profile_token.strip()
    if not sso_token:
        return False

    payload = parse_sso_jwt(sso_token)
    email = payload.get("email") or payload.get("sub") or "sessao_sky@skymais.com.br"
    if email.startswith("sky_"):
        email = email[4:]
    given = payload.get("givenName", "")
    family = payload.get("familyName", "")
    client_name = f"{given} {family}".strip() or payload.get("name", "Assinante Sky+")
    dev_id = payload.get("deviceId", "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764")

    existing_sessions = []
    if os.path.exists(SKY_SESSIONS_FILE):
        try:
            with open(SKY_SESSIONS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                d = json.load(f)
                if isinstance(d, list):
                    existing_sessions = d
        except Exception:
            existing_sessions = []

    # Atualiza se o email já existir, ou adiciona se for novo
    found = False
    for item in existing_sessions:
        if isinstance(item, dict) and item.get("email", "").strip().lower() == email.strip().lower():
            item["sso_token"] = sso_token
            if profile_token:
                item["profile_token"] = profile_token
            item["client_name"] = client_name
            item["device_id"] = dev_id
            found = True
            break

    if not found:
        existing_sessions.append({
            "email": email,
            "sso_token": sso_token,
            "profile_token": profile_token,
            "client_name": client_name,
            "device_id": dev_id,
            "plan": "PAY-TV + FIBRA // SUPER HD II ⚡",
            "created_at": time.strftime("%d/%m/%Y %H:%M")
        })

    try:
        with open(SKY_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Sky Sessions] Erro ao salvar sky_sessions.json: {e}")

    # Também atualiza os arquivos raiz para compatibilidade
    try:
        with open(SSO_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(sso_token)
        if profile_token:
            with open(PROFILE_TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(profile_token)
    except Exception:
        pass

    try:
        import ativador_tv
        ativador_tv.reload_tokens()
    except Exception:
        pass

    load_all_sky_accounts(force_reload=True)
    return True

def save_sso_token(token: str, profile_token: str = "") -> bool:
    """Salva token SSO de sessão ativa para ativação instantânea sem captcha."""
    return save_sky_session(token, profile_token)

def save_profile_token(token: str) -> bool:
    """Salva Profile Token de sessão ativa para ativação instantânea."""
    token = token.strip()
    if not token:
        return False
    try:
        with open(PROFILE_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception:
        pass

    # Também atualiza na primeira sessão de sky_sessions.json se houver
    if os.path.exists(SKY_SESSIONS_FILE):
        try:
            with open(SKY_SESSIONS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                d = json.load(f)
            if isinstance(d, list) and d:
                d[0]["profile_token"] = token
                with open(SKY_SESSIONS_FILE, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    try:
        import ativador_tv
        ativador_tv.reload_tokens()
    except Exception:
        pass
    load_all_sky_accounts(force_reload=True)
    return True

def get_tokens_status() -> dict:
    """Retorna detalhes do status de sso_token.txt e profile_token.txt."""
    sso_exists = os.path.exists(SSO_TOKEN_FILE)
    prof_exists = os.path.exists(PROFILE_TOKEN_FILE)
    sso_val = ""
    prof_val = ""
    if sso_exists:
        try:
            with open(SSO_TOKEN_FILE, "r", encoding="utf-8") as f:
                sso_val = f.read().strip()
        except Exception:
            pass
    if prof_exists:
        try:
            with open(PROFILE_TOKEN_FILE, "r", encoding="utf-8") as f:
                prof_val = f.read().strip()
        except Exception:
            pass

    email = ""
    client_name = ""
    exp_ts = 0
    is_valid = False
    if sso_val and "ey" in sso_val:
        parts = sso_val.split(".")
        if len(parts) >= 2:
            p = parts[1]
            rem = len(p) % 4
            if rem:
                p += "=" * (4 - rem)
            try:
                data = json.loads(base64.urlsafe_b64decode(p))
                email = data.get("email") or data.get("sub", "")
                if email.startswith("sky_"):
                    email = email[4:]
                given = data.get("givenName", "")
                family = data.get("familyName", "")
                client_name = f"{given} {family}".strip() or data.get("name", "")
                exp_ts = data.get("exp", 0)
                is_valid = (exp_ts > time.time()) if exp_ts else True
            except Exception:
                pass

    return {
        "sso_exists": sso_exists and bool(sso_val),
        "sso_size": len(sso_val),
        "sso_preview": (sso_val[:20] + "..." + sso_val[-15:]) if len(sso_val) > 40 else sso_val,
        "profile_exists": prof_exists and bool(prof_val),
        "profile_size": len(prof_val),
        "profile_preview": (prof_val[:20] + "..." + prof_val[-15:]) if len(prof_val) > 40 else prof_val,
        "email": email,
        "client_name": client_name,
        "exp": exp_ts,
        "is_valid": is_valid,
        "expires_in_hours": round((exp_ts - time.time()) / 3600, 1) if exp_ts else None
    }

def remove_sky_account(target_email: str) -> bool:
    """Remove uma conta Sky pelo email de todas as listas e arquivos de hits."""
    if not target_email:
        return False
    target_clean = target_email.strip().lower()
    removed_any = False

    with SKY_LOCK:
        # 1. Limpa skycontas.txt
        if os.path.exists(SKY_CONTAS_FILE):
            try:
                with open(SKY_CONTAS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                new_lines = [l for l in lines if target_clean not in l.lower()]
                if len(new_lines) != len(lines):
                    with open(SKY_CONTAS_FILE, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    removed_any = True
            except Exception:
                pass

        # 2. Limpa arquivos de texto em hits/
        if os.path.exists(HITS_DIR):
            for ext in ["*.txt", "*.log"]:
                for fpath in glob.glob(os.path.join(HITS_DIR, ext)):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        if target_clean in content.lower():
                            if "\u2554" in content or "[Sky Checker" in content:
                                delim = r"\u2554" if "\u2554" in content else r"\[Sky Checker"
                                blocks = re.split(delim, content)
                                kept = [b for b in blocks if target_clean not in b.lower()]
                                sep = "\u2554" if "\u2554" in content else "[Sky Checker"
                                new_content = sep.join(kept)
                                with open(fpath, "w", encoding="utf-8") as f:
                                    f.write(new_content)
                                removed_any = True
                            else:
                                lines = content.splitlines()
                                new_lines = [l for l in lines if target_clean not in l.lower()]
                                with open(fpath, "w", encoding="utf-8") as f:
                                    f.write("\n".join(new_lines))
                                removed_any = True
                    except Exception:
                        pass

        # 3. Limpa raw_json
        if os.path.exists(RAW_JSON_DIR):
            for jfile in glob.glob(os.path.join(RAW_JSON_DIR, "*.json")):
                try:
                    with open(jfile, "r", encoding="utf-8") as f:
                        jdata = json.load(f)
                    if jdata.get("email", "").strip().lower() == target_clean:
                        os.remove(jfile)
                        removed_any = True
                except Exception:
                    pass

    load_all_sky_accounts(force_reload=True)
    return removed_any

