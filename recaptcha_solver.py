import os
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import base64
import gzip
import uuid
import time
import cloudscraper
from blackboxprotobuf import decode_message, encode_message

# ============================================================
# Headers exatos capturados via Reqable do app Sky Android
# ============================================================

RECAPTCHA_HEADERS = {
    "Content-Type": "application/x-protobuffer",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; moto g(100) Build/S1RTS32.41-20-16-1-11)",
    "Host": "www.recaptcha.net",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
}

RECAPTCHA_BASE = "https://www.recaptcha.net/recaptcha/api3"


def _decode_b64(b64_str: str) -> bytes:
    fixed = b64_str.replace('-', '+').replace('_', '/')
    fixed += "=" * ((4 - len(fixed) % 4) % 4)
    return base64.b64decode(fixed)


def _encode_b64(data: bytes) -> str:
    return base64.b64encode(data).decode().replace('+', '-').replace('/', '_').rstrip('=')


def _build_proxies(proxy):
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _new_scraper(proxy=None):
    """Cria um cloudscraper configurado como browser mobile com velocidade máxima."""
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "android",
            "desktop": False,
        }
    )
    if proxy:
        scraper.proxies.update({"http": proxy, "https": proxy})
    return scraper


def update_payload_session_id(payload_b64, new_session_id=None):
    """Atualiza o session ID em TODOS os lugares do payload"""

    if new_session_id is None:
        new_session_id = str(uuid.uuid4())

    data = _decode_b64(payload_b64)
    msg, typedef = decode_message(data)

    # campo principal
    msg['8']['1'] = new_session_id.encode()

    # fingerprint interno (campo 8.7.1)
    data_2 = _decode_b64(msg['8']['7']['1'].decode())
    msg_2, typedef_2 = decode_message(data_2)
    msg_2['2'] = new_session_id.encode()

    inner_encoded = encode_message(msg_2, typedef_2)
    if isinstance(inner_encoded, tuple):
        inner_encoded = inner_encoded[0]

    msg['8']['7']['1'] = _encode_b64(inner_encoded).encode()

    final_encoded = encode_message(msg, typedef)
    if isinstance(final_encoded, tuple):
        final_encoded = final_encoded[0]

    return _encode_b64(final_encoded), new_session_id


def _do_mri(session_obj, payload_bytes: bytes, proxy=None):
    """
    STEP 1 — POST /mri
    Inicialização da sessão reCAPTCHA.
    """
    resp = session_obj.post(
        f"{RECAPTCHA_BASE}/mri",
        headers=RECAPTCHA_HEADERS,
        data=payload_bytes,
        timeout=30,
    )

    # /mri aceita 200, 204 ou até 400 (depende do estado)
    if resp.status_code >= 500:
        raise Exception(f"/mri HTTP {resp.status_code}")

    return resp


def _do_mlg(session_obj, payload_bytes: bytes, proxy=None):
    """
    STEP 2 — POST /mlg
    Envio do fingerprint/telemetria do dispositivo.
    """
    resp = session_obj.post(
        f"{RECAPTCHA_BASE}/mlg",
        headers=RECAPTCHA_HEADERS,
        data=payload_bytes,
        timeout=30,
    )

    if resp.status_code not in (200, 204):
        raise Exception(f"/mlg HTTP {resp.status_code}")

    return resp


def _do_mrr(session_obj, payload_bytes: bytes, proxy=None) -> str:
    """
    STEP 3 — POST /mrr
    Obtém o token reCAPTCHA final.
    """
    resp = session_obj.post(
        f"{RECAPTCHA_BASE}/mrr",
        headers=RECAPTCHA_HEADERS,
        data=payload_bytes,
        timeout=30,
    )

    if resp.status_code != 200:
        raise Exception(f"/mrr HTTP {resp.status_code}")

    resp_data = resp.content
    if len(resp_data) >= 2 and resp_data[:2] == b'\x1f\x8b':
        resp_data = gzip.decompress(resp_data)

    msg, _ = decode_message(resp_data)
    token_bytes = msg.get('1')

    if not token_bytes:
        raise Exception("Token não encontrado na resposta do /mrr")

    return token_bytes.decode()


def get_recaptcha_token(payload_b64: str, proxy=None) -> str:
    """
    Fluxo COMPLETO de 3 requests como o app Sky real (capturado via Reqable):

      STEP 1: POST /recaptcha/api3/mri   <- inicializa sessão
      STEP 2: POST /recaptcha/api3/mlg   <- envia fingerprint/telemetria
      STEP 3: POST /recaptcha/api3/mrr   <- obtém token final

    Usa cloudscraper para bypass de proteções Cloudflare.
    """
    payload_bytes = _decode_b64(payload_b64)

    # Cria sessão cloudscraper única para os 3 steps
    session_obj = _new_scraper(proxy=proxy)

    # STEP 1: /mri
    _do_mri(session_obj, payload_bytes, proxy=proxy)

    # STEP 2: /mlg
    _do_mlg(session_obj, payload_bytes, proxy=proxy)

    # STEP 3: /mrr -> token
    token = _do_mrr(session_obj, payload_bytes, proxy=proxy)

    return token


import ssl
import urllib.request
def get_recaptcha_web_token(payload_web_b64: str, proxy=None) -> str:
    """Gera o token reCAPTCHA Enterprise oficial da Web da SKY com renovação dinâmica a cada chamada."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url_anchor = "https://www.google.com/recaptcha/enterprise/anchor?ar=1&k=6Lc_7gUqAAAAAO0Kfv_fCbRrDrbW0jBh1ihU3s2o&co=aHR0cHM6Ly93d3cuc2t5LmNvbS5icjo0NDM.&hl=pt-BR&v=ox8dsmiqR62P1bqhciWOn7Fg&size=invisible"
    headers_anchor = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "*/*",
    }

    # 1. Obtém anchor token fresco (cada token só pode ser usado 1 vez no reload)
    req_anchor = urllib.request.Request(url_anchor, headers=headers_anchor, method="GET")
    resp_anchor = None
    if proxy:
        try:
            proxy_handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
            opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
            resp_anchor = opener.open(req_anchor, timeout=12)
        except Exception:
            resp_anchor = None

    if resp_anchor is None:
        resp_anchor = urllib.request.urlopen(req_anchor, context=ctx, timeout=12)

    with resp_anchor as r:
        html = r.read().decode("utf-8", errors="ignore")

    token_match = re.search(r'id="recaptcha-token"\s+value="([^"]+)"', html)
    if not token_match:
        m = re.findall(r'(03AF[a-zA-Z0-9_-]{50,})', html)
        if m:
            anchor_token = m[0]
        else:
            raise Exception("Não foi possível extrair o anchor token da Google")
    else:
        anchor_token = token_match.group(1)

    # 2. Injeta anchor token no Campo 2 do payload
    raw_bytes = _decode_b64(payload_web_b64)
    msg, typedef = decode_message(raw_bytes)
    msg['2'] = anchor_token.encode('utf-8')
    new_raw_bytes = encode_message(msg, typedef)
    if isinstance(new_raw_bytes, tuple):
        new_raw_bytes = new_raw_bytes[0]

    # 3. Dispara para o reload da Google
    url_reload = "https://www.google.com/recaptcha/enterprise/reload?k=6Lc_7gUqAAAAAO0Kfv_fCbRrDrbW0jBh1ihU3s2o"
    headers_reload = {
        "host": "www.google.com",
        "sec-ch-ua-platform": '"Windows"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "content-type": "application/x-protobuffer",
        "accept": "*/*",
        "origin": "https://www.google.com",
        "referer": url_anchor,
    }

    req_reload = urllib.request.Request(url_reload, data=new_raw_bytes, headers=headers_reload, method="POST")
    resp_reload = None
    if proxy:
        try:
            proxy_handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
            opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
            resp_reload = opener.open(req_reload, timeout=20)
        except Exception:
            resp_reload = None

    if resp_reload is None:
        resp_reload = urllib.request.urlopen(req_reload, context=ctx, timeout=20)

    with resp_reload as r:
        content = r.read()

    if content.startswith(b"\x1f\x8b"):
        content = gzip.decompress(content)

    text = content.decode("utf-8", errors="ignore")
    tok_m = re.search(r'(0cAF[a-zA-Z0-9_-]{100,})', text)
    if tok_m:
        return tok_m.group(1)
    matches = re.findall(r'([a-zA-Z0-9_-]{150,})', text)
    if matches:
        return matches[0]
    raise Exception("Token Web reCAPTCHA não encontrado na resposta do reload")


# ============================================================
# SOLVER RECAPTCHA ESPECÍFICO PARA PARAMOUNT+ (sm-sky-ui.vrioservices.com)
# ============================================================
PARAMOUNT_SITEKEY = "6LejrVMnAAAAANWgfaouxDOYUxCgbplMGzLaZBkm"
PARAMOUNT_DOMAIN_CO = "aHR0cHM6Ly9zbS1za3ktdWkudnJpb3NlcnZpY2VzLmNvbTo0NDM."
PARAMOUNT_VERSION = "8x-4t2pegToiW8KmThtO4AQt"
PARAMOUNT_REQABLE_PATH = r"C:\Users\Micro\AppData\Roaming\Reqable\tmp\111993cb-a142-40a0-8219-f30b119d5f68"

_cached_paramount_version = None

def _get_paramount_recaptcha_version() -> str:
    """Busca a versão REAL do reCAPTCHA api2 usada pelo site Paramount/SKY.
    Faz GET no script api2.js com o sitekey específico para pegar a versão correta.
    """
    global _cached_paramount_version
    if _cached_paramount_version:
        return _cached_paramount_version
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Busca o api2.js com o sitekey correto — retorna a versão atual usada pela Google para esse domínio
        url = f"https://www.google.com/recaptcha/api2/anchor?ar=1&k={PARAMOUNT_SITEKEY}&co={PARAMOUNT_DOMAIN_CO}&hl=pt-BR&size=invisible"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            raw = resp.read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            html = raw.decode("utf-8", errors="ignore")
            # A versão aparece na URL dos scripts embutidos: /recaptcha/releases/<versao>/
            m = re.search(r'/recaptcha/releases/([a-zA-Z0-9_-]+)/', html)
            if m:
                _cached_paramount_version = m.group(1)
                return _cached_paramount_version
    except Exception:
        pass
    return PARAMOUNT_VERSION


def get_latest_recaptcha_version() -> str:
    """Alias para compatibilidade com outros solvers — retorna versão api2 da Paramount."""
    return _get_paramount_recaptcha_version()


def get_recaptcha_paramount_token(proxy=None) -> str:
    """Gera o token reCAPTCHA api2 para a Paramount+ via SKY.
    Usa cloudscraper (simula browser real) para anchor + reload na mesma sessão.
    Isso evita detecção de bot pelo Google e garante score alto no token.
    """
    # ── Sessão cloudscraper como browser desktop ──
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
        }
    )
    if proxy:
        scraper.proxies.update({"http": proxy, "https": proxy})
    scraper.verify = False

    # ── PASSO 1: Anchor sem v= → Google responde com HTML que embute a versão atual ──
    url_anchor_probe = (
        f"https://www.google.com/recaptcha/api2/anchor"
        f"?ar=1&k={PARAMOUNT_SITEKEY}&co={PARAMOUNT_DOMAIN_CO}&hl=pt-BR&size=invisible"
    )
    r1 = scraper.get(url_anchor_probe, timeout=15)
    anchor_html = r1.text

    # Extrai versão real dos scripts embutidos no HTML
    vm = re.search(r'/recaptcha/releases/([a-zA-Z0-9_-]+)/', anchor_html)
    version = vm.group(1) if vm else PARAMOUNT_VERSION

    # Tenta extrair anchor token desta primeira resposta
    anchor_token = ""
    tm = re.search(r'id="recaptcha-token"\s+value="([^"]+)"', anchor_html)
    if tm:
        anchor_token = tm.group(1)
    else:
        fm = re.findall(r'(03AF[a-zA-Z0-9_-]{50,})', anchor_html)
        if fm:
            anchor_token = fm[0]

    # ── PASSO 2: Se não achou token, refaz anchor com v= explícito ──
    if not anchor_token:
        url_anchor = (
            f"https://www.google.com/recaptcha/api2/anchor"
            f"?ar=1&k={PARAMOUNT_SITEKEY}&co={PARAMOUNT_DOMAIN_CO}"
            f"&hl=pt-BR&v={version}&size=invisible"
        )
        r2 = scraper.get(url_anchor, timeout=15)
        anchor_html = r2.text
        tm2 = re.search(r'id="recaptcha-token"\s+value="([^"]+)"', anchor_html)
        if tm2:
            anchor_token = tm2.group(1)
        else:
            fm2 = re.findall(r'(03AF[a-zA-Z0-9_-]{50,})', anchor_html)
            if fm2:
                anchor_token = fm2[0]
            else:
                raise Exception(f"Anchor token Paramount não encontrado (v={version}). HTML: {anchor_html[:200]}")

    # ── PASSO 3: Carrega payload e injeta anchor token no Campo 2 ──
    payload_file = "payload_paramount.b64"
    raw_bytes = None
    if os.path.exists(payload_file):
        try:
            with open(payload_file, "r") as f:
                raw_bytes = _decode_b64(f.read().strip())
        except Exception:
            pass

    if raw_bytes is None and os.path.exists(PARAMOUNT_REQABLE_PATH):
        try:
            with open(PARAMOUNT_REQABLE_PATH, "rb") as rf:
                raw_bytes = rf.read()
            with open(payload_file, "w") as wf:
                wf.write(_encode_b64(raw_bytes))
        except Exception:
            pass

    if not raw_bytes:
        raise Exception("payload_paramount.b64 não encontrado")

    msg, typedef = decode_message(raw_bytes)
    msg['2'] = anchor_token.encode('utf-8')
    new_raw_bytes = encode_message(msg, typedef)
    if isinstance(new_raw_bytes, tuple):
        new_raw_bytes = new_raw_bytes[0]

    # ── PASSO 4: Reload na MESMA sessão cloudscraper (cookie/fingerprint consistente) ──
    url_reload = f"https://www.google.com/recaptcha/api2/reload?k={PARAMOUNT_SITEKEY}"
    headers_reload = {
        "content-type": "application/x-protobuffer",
        "origin": "https://www.google.com",
        "referer": (
            f"https://www.google.com/recaptcha/api2/bframe"
            f"?hl=pt-BR&v={version}&k={PARAMOUNT_SITEKEY}&bft={anchor_token}"
        ),
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
    }
    r3 = scraper.post(url_reload, data=new_raw_bytes, headers=headers_reload, timeout=20)
    content = r3.content
    if content.startswith(b"\x1f\x8b"):
        content = gzip.decompress(content)

    text = content.decode("utf-8", errors="ignore")
    rresp_m = re.search(r'\["rresp","([^"]+)"', text)
    if rresp_m:
        return rresp_m.group(1)
    tok_m = re.search(r'(03AF[a-zA-Z0-9_-]{100,})', text)
    if tok_m:
        return tok_m.group(1)
    tok_m2 = re.search(r'(0cAF[a-zA-Z0-9_-]{100,})', text)
    if tok_m2:
        return tok_m2.group(1)
    matches = re.findall(r'([a-zA-Z0-9_-]{150,})', text)
    if matches:
        return matches[0]

    raise Exception(f"Token Paramount reCAPTCHA não encontrado. v={version}. Resp: {text[:300]}")
