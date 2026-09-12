# -*- coding: utf-8 -*-
"""
=============================================================================
             SKY TV ATIVADOR - GERENCIADOR DE ROTAÇÃO DE CONTAS
=============================================================================
Este módulo gerencia o pool de contas para ativação de TVs, garantindo que
cada TV utilize uma conta diferente da lista (rotação inteligente).
=============================================================================
"""

import os
import sys
import json
import base64
import time
import datetime
import threading
from typing import Optional, List, Dict, Tuple

# Caminhos dos arquivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HITS_DIR = os.path.join(BASE_DIR, "hits")
POOL_FILE = os.path.join(BASE_DIR, "contas_pool.json")
SKYCONTAS_FILE = os.path.join(BASE_DIR, "skycontas.txt")
ACTIVATED_FILE = os.path.join(HITS_DIR, "contas_ativadas.txt")
LOG_ATIVACAO_FILE = os.path.join(HITS_DIR, "ativacoes_tv.txt")
SSO_TOKEN_FILE = os.path.join(BASE_DIR, "sso_token.txt")
PROFILE_TOKEN_FILE = os.path.join(BASE_DIR, "profile_token.txt")

_lock = threading.Lock()

def extrair_dados_jwt(jwt_token: str) -> dict:
    """Extrai campos úteis do payload de um JWT sem verificar assinatura."""
    if not jwt_token or "." not in jwt_token:
        return {}
    try:
        parts = jwt_token.strip().split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        rem = len(payload_b64) % 4
        if rem:
            payload_b64 += "=" * (4 - rem)
        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded_bytes.decode("utf-8", errors="ignore"))
    except Exception:
        return {}

def is_valid_dtvgo_token(token: str) -> bool:
    """Verifica se o token é um JWT emitido para o serviço DTVGO/SkyMais (TBX)."""
    if not token or not str(token).startswith("ey") or "." not in str(token):
        return False
    dados = extrair_dados_jwt(token)
    if not dados:
        return False
    aud = str(dados.get("aud", "")).lower()
    iss = str(dados.get("iss", "")).lower()
    if aud == "dtvgo" or "sm-dgo" in iss:
        return True
    return False

def obter_contagem_ativacoes() -> Dict[str, int]:
    """Lê hits/contas_ativadas.txt e retorna dict {email_lower: total_ativacoes}."""
    counts: Dict[str, int] = {}
    if os.path.exists(ACTIVATED_FILE):
        try:
            with open(ACTIVATED_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Formato: email:senha | TV: 123456 | 11/09/2026 20:09:10
                    # Ou: email | TV: 123456 ...
                    partes = line.split("|")
                    if partes:
                        conta_part = partes[0].strip()
                        em = conta_part.split(":")[0].strip().lower()
                        if em:
                            counts[em] = counts.get(em, 0) + 1
        except Exception:
            pass
    return counts

def ler_historico_ativacoes(limite: int = 50) -> List[dict]:
    """Retorna as últimas ativações registradas."""
    historico = []
    if os.path.exists(ACTIVATED_FILE):
        try:
            with open(ACTIVATED_FILE, "r", encoding="utf-8", errors="ignore") as f:
                linhas = [l.strip() for l in f if l.strip()]
                for l in reversed(linhas[-limite:]):
                    partes = [p.strip() for p in l.split("|")]
                    conta = partes[0] if len(partes) > 0 else ""
                    tv = partes[1] if len(partes) > 1 else ""
                    data = partes[2] if len(partes) > 2 else ""
                    # Remove senha se houver
                    em = conta.split(":")[0].strip()
                    tv_code = tv.replace("TV:", "").strip()
                    historico.append({
                        "email": em,
                        "tv_code": tv_code,
                        "data": data,
                        "registro": l
                    })
        except Exception:
            pass
    return historico

def inicializar_pool():
    """Garante que o contas_pool.json exista com as contas e tokens disponíveis."""
    with _lock:
        contas_pool = []
        if os.path.exists(POOL_FILE):
            try:
                with open(POOL_FILE, "r", encoding="utf-8") as f:
                    contas_pool = json.load(f)
            except Exception:
                contas_pool = []

        emails_existentes = {c.get("email", "").lower() for c in contas_pool if c.get("email")}

        # 1. Carrega token ativo de sso_token.txt se disponível
        sso_token = ""
        profile_token = ""
        if os.path.exists(SSO_TOKEN_FILE):
            try:
                with open(SSO_TOKEN_FILE, "r", encoding="utf-8") as f:
                    sso_token = f.read().strip()
            except Exception:
                pass

        if os.path.exists(PROFILE_TOKEN_FILE):
            try:
                with open(PROFILE_TOKEN_FILE, "r", encoding="utf-8") as f:
                    profile_token = f.read().strip()
            except Exception:
                pass

        if sso_token:
            payload_info = extrair_dados_jwt(sso_token)
            email_jwt = payload_info.get("email") or payload_info.get("username") or "rsgencadernacoes@yahoo.com.br"
            device_id = (payload_info.get("deviceId")
                         or payload_info.get("tbxDeviceId")
                         or "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764")

            if email_jwt.lower() not in emails_existentes:
                contas_pool.append({
                    "email": email_jwt,
                    "password": "",
                    "sso_token": sso_token,
                    "profile_token": profile_token,
                    "device_id": device_id,
                    "tipo": "sessao_ativa",
                    "ativo": True,
                    "ultima_ativacao": None,
                    "falhas_consecutivas": 0,
                    "motivo_falha": ""
                })
                emails_existentes.add(email_jwt.lower())
            else:
                # Atualiza tokens da conta existente caso estejam mais recentes
                for c in contas_pool:
                    if c.get("email", "").lower() == email_jwt.lower():
                        c["sso_token"] = sso_token
                        if profile_token:
                            c["profile_token"] = profile_token
                        c["device_id"] = device_id
                        c["ativo"] = True
        if os.path.exists(SKYCONTAS_FILE):
            try:
                with open(SKYCONTAS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if ":" in line:
                            em, pw = line.split(":", 1)
                            em, pw = em.strip(), pw.strip()
                            if not em:
                                continue
                            
                            # Atualiza senha se a conta já existir
                            conta_existente = None
                            for c in contas_pool:
                                if c.get("email", "").lower() == em.lower():
                                    conta_existente = c
                                    if pw:
                                        c["password"] = pw
                                    break
                            
                            if not conta_existente:
                                prof_local = profile_token or "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMjU2R0NNIn0.MSmD8UZt2XPAXdDRT6rT3P7RRFI6a8PZ783PJC8mJz3FGPd2wTeviBPvu2T2W-pISVqXwr6zxM3szQVLWJDDHIksfwjqyeztF3FXgBcubQHWGVcHwCKpo6sNdd4Sx-pBBYmFXKtGlg9KWWraQV3QEvTktUav40eIKuJdS4F18zHaHtlHAbwpdlWyMDSpXoAlKU-VcZWYr8pSRiymG2u3wyaIrGrzg8Fmw2BnOKDwtypgWbqSBxxjf0ssoRu0u1VqDiUW61m7QisiZhRaLAgbkLTFok2bMGBY1Z6L6ll2clnpgY-sxguHunLeLyFI-dnPy536MQc6yOUkltwjAEvvfQ.zEe1A_2WTkEAret7.ab-0a34sS3cuGkALdhvilfhq9HgvSGvIOWbo6D5Rcwy0L5DxW5GvxTB9XCpJ6z3jY1tAhorCszTUxJU9BaxJYFVAu1XQOTX_WkB6mhrszFAIFq_d7dpstZh0ALXJCVl5gEsDcykfQ6vRCErXHHFvL4ugaG2whj6ySG6MaMIyy7p3lnffYQapavGUHpLygOYBD8EmC1alII6uZyXBiA4l0vo23GFz9nlIDsJrHGLFIoVAXlsOZ1W6S86TyOtFlB3VOijs-yem5OW0GwvPh2v5UaH4w_K5Je7r7c4QzflTjQP-YcfMXInVbYDE0pfTavf9_D2lntPkfkB_PhpPJnTdBQ5diksxqXdRuWKgFnWFQw3cUgNVfZNvdiTcZ1eD_Vu0Yj2_w_-wYANq86T760Ei7Z3KKdR-l7lHwz76qoQkWTYfPrSvs91AFJhM_jX6sU1vGGbMcopTDm3OQkI-f_XTIll1xNCBlXlHWHYkJd8YXdzG6g2bspKMnbuXT1DSINo4VgZbclL2BigqCuCP__6AqS-1CerL8bKqnizGsvdZGegfRC2DzXzGfSH2GcO-gicc-GYlqILO3X7ooXzdl3vyTVQX-Su3qlSeH0tpzsigMC0ioGW-wb2MVOXeRphzdAdNZcVKxfoTj6QJgpntTWi0wGhoZ0oi-kEIn80DZym0xVQiYwxvveXCSksH5mK-Ff19ndEyuLBu9UAjc8CXhs3Win6faLv_WjAVgUKBwLqx0L06LcKbRXzqJ-QJIaZkOtLTSmNOMyRJyZiI1YLOlJVUDhL36IxxZ2y0JWTgsNTmcBJ5E1ROyFRRahpyKUEjYHNwQnXSqJaBzZAH28hrqiyOWoeHS-G9ifLrkEg35OT4GC8bMmrZSPdEsoK2niSbSs3IrooRlZKOIhmvvrOn_MbstSddTgzeAvEAmD_FIZgrkTZl60-COoaBmjfG-PJ2puXOgeWI3i7T8yzpouEBp2M-EDODKfhoSh_mYFnt69NsR_6dnYBWvzPcHOdM7RXJqvPKoaM6hn1kkfLNvebu_RQ7_0IIiJCZTYUaperZap2eioAcwz8ox15GMMzCvS2zzQ.7NXVxV6HZFsmZj5yyun0GQ"
                                dev_local = "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764"
                                contas_pool.append({
                                    "email": em,
                                    "password": pw,
                                    "sso_token": "",
                                    "profile_token": prof_local,
                                    "device_id": dev_local,
                                    "tipo": "skycontas",
                                    "ativo": True,
                                    "ultima_ativacao": None,
                                    "falhas_consecutivas": 0,
                                    "motivo_falha": ""
                                })
                                emails_existentes.add(em.lower())
            except Exception:
                pass

        # Sanitiza contas existentes: se tiver token que não é DTVGO, limpa para não dar 401
        for c in contas_pool:
            if c.get("sso_token") and not is_valid_dtvgo_token(c["sso_token"]):
                c["sso_token"] = ""
            c["ativo"] = True
            c["falhas_consecutivas"] = 0

        salvar_pool(contas_pool)
        return contas_pool

def salvar_pool(contas: List[dict]):
    """Salva a lista de contas em contas_pool.json."""
    try:
        with open(POOL_FILE, "w", encoding="utf-8") as f:
            json.dump(contas, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[GerenciadorContas] Erro ao salvar contas_pool.json: {e}")

def obter_todas_contas() -> List[dict]:
    """Retorna todas as contas com contagem atualizada de ativações."""
    if not os.path.exists(POOL_FILE):
        inicializar_pool()

    with _lock:
        try:
            with open(POOL_FILE, "r", encoding="utf-8") as f:
                contas = json.load(f)
        except Exception:
            contas = []

        counts = obter_contagem_ativacoes()
        for c in contas:
            em = c.get("email", "").strip().lower()
            c["total_ativacoes"] = counts.get(em, 0)

        return contas

def obter_proxima_conta(somente_com_token: bool = False) -> Optional[dict]:
    """
    Obtém a próxima conta da rotação inteligente:
    1. Prioriza contas com MENOR número de ativações (nunca usadas primeiro!).
    2. Garante que cada TV receba uma conta diferente do pool.
    3. Em caso de empate, ordena pela última data de ativação mais antiga (LRU).
    """
    contas = obter_todas_contas()
    if not contas:
        inicializar_pool()
        contas = obter_todas_contas()

    if not contas:
        return None

    candidatas = [c for c in contas if c.get("ativo", True)]
    if not candidatas:
        for c in contas:
            c["ativo"] = True
            c["falhas_consecutivas"] = 0
        with _lock:
            salvar_pool(contas)
        candidatas = contas

    if somente_com_token:
        com_tok = [c for c in candidatas if c.get("sso_token") and is_valid_dtvgo_token(c.get("sso_token"))]
        if com_tok:
            candidatas = com_tok

    def chave_ordenacao(c):
        # 1: Total de ativações (MENOR PRIMEIRO - garante rotação estrita!)
        ativacoes = c.get("total_ativacoes", 0)
        # 2: Falhas consecutivas
        falhas = c.get("falhas_consecutivas", 0)
        # 3: Data da última ativação (None/vazio vem primeiro)
        ult = c.get("ultima_ativacao") or ""
        return (ativacoes, falhas, ult)

    candidatas.sort(key=chave_ordenacao)
    return candidatas[0] if candidatas else None

def registrar_ativacao_sucesso(email: str, tv_code: str, detalhe: str = "TV ativada com sucesso!"):
    """Registra uma ativação bem-sucedida nos arquivos de histórico e atualiza o pool."""
    os.makedirs(HITS_DIR, exist_ok=True)
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    linha_ativadas = f"{email} | TV: {tv_code} | {agora}\n"
    linha_log = f"[SUCESSO] {email} | Codigo: {tv_code} | {detalhe}\n"

    with _lock:
        try:
            with open(ACTIVATED_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(linha_ativadas)
        except Exception:
            pass

        try:
            with open(LOG_ATIVACAO_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(linha_log)
        except Exception:
            pass

        # Atualiza pool de contas
        try:
            if os.path.exists(POOL_FILE):
                with open(POOL_FILE, "r", encoding="utf-8") as f:
                    contas = json.load(f)
                for c in contas:
                    if c.get("email", "").lower() == email.lower():
                        c["ultima_ativacao"] = agora
                        c["falhas_consecutivas"] = 0
                        c["motivo_falha"] = ""
                salvar_pool(contas)
        except Exception:
            pass

def registrar_ativacao_falha(email: str, tv_code: str, motivo: str):
    """Registra falha de ativação e incrementa contador de falhas da conta."""
    os.makedirs(HITS_DIR, exist_ok=True)
    linha_log = f"[FALHA] {email} | Codigo: {tv_code} | {motivo}\n"

    with _lock:
        try:
            with open(LOG_ATIVACAO_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(linha_log)
        except Exception:
            pass

        try:
            if os.path.exists(POOL_FILE):
                with open(POOL_FILE, "r", encoding="utf-8") as f:
                    contas = json.load(f)
                for c in contas:
                    if c.get("email", "").lower() == email.lower():
                        c["falhas_consecutivas"] = c.get("falhas_consecutivas", 0) + 1
                        c["motivo_falha"] = motivo
                        # Se falhou repetidamente por token inválido ou erro 401, marca temporariamente
                        if c["falhas_consecutivas"] >= 3:
                            c["ativo"] = False
                salvar_pool(contas)
        except Exception:
            pass

def adicionar_ou_atualizar_conta(email: str, sso_token: str, profile_token: str = "",
                                 password: str = "", device_id: str = "") -> dict:
    """Adiciona ou atualiza uma conta no pool de rotação."""
    if not email:
        # Tenta extrair do token se não fornecido
        dados = extrair_dados_jwt(sso_token)
        email = dados.get("email") or dados.get("username") or ""

    if not email:
        return {"success": False, "message": "Email da conta não informado e não encontrado no token."}

    if not device_id and sso_token:
        dados = extrair_dados_jwt(sso_token)
        device_id = dados.get("deviceId") or dados.get("tbxDeviceId") or "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764"

    contas = obter_todas_contas()
    achou = False
    with _lock:
        for c in contas:
            if c.get("email", "").lower() == email.lower():
                if sso_token:
                    c["sso_token"] = sso_token
                if profile_token:
                    c["profile_token"] = profile_token
                if password:
                    c["password"] = password
                if device_id:
                    c["device_id"] = device_id
                c["ativo"] = True
                c["falhas_consecutivas"] = 0
                c["motivo_falha"] = ""
                achou = True
                break

        if not achou:
            contas.append({
                "email": email,
                "password": password,
                "sso_token": sso_token,
                "profile_token": profile_token,
                "device_id": device_id or "226816ead4c3beb7cfd1489bdabc313bd9c43d96165a74ac9ec0f1b3acdab764",
                "tipo": "manual",
                "ativo": True,
                "ultima_ativacao": None,
                "falhas_consecutivas": 0,
                "motivo_falha": ""
            })

        salvar_pool(contas)

    return {"success": True, "message": f"Conta {email} configurada com sucesso no pool!", "email": email}

# Garante inicialização ao importar
inicializar_pool()
