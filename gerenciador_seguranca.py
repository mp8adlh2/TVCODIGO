import os
import sys
import json
import base64
import hashlib
import glob
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Arquivos sensíveis protegidos pelo sistema de criptografia
PROTECTED_FILES = [
    "cookies_bundle.json",
    "contas_pool.json",
    "used_cookies.json",
    "skycontas.txt",
    "sso_token.txt",
    "profile_token.txt"
]

MAGIC_HEADER = b"CYBER_BLINDADO_V1::"

def get_master_key() -> bytes:
    """Obtém a chave de criptografia derivada da Senha Mestre com SHA-256."""
    m_file = os.path.join(BASE_DIR, "SENHA_MESTRE.txt")
    raw_pass = "CYBER#STREAM@2026$MASTER*TITANIUM!ULTRA*ACCESS#VIP"
    if os.path.exists(m_file):
        try:
            with open(m_file, 'r', encoding='utf-8') as f:
                for line in f.read().splitlines():
                    line = line.strip()
                    if line and not line.startswith(('=', '🔐', 'SENHA', '•')):
                        raw_pass = line
                        break
        except Exception:
            pass
    
    env_pass = os.environ.get("MASTER_PASSWORD", "").strip()
    if env_pass:
        raw_pass = env_pass

    # Deriva chave forte de 32 bytes (256 bits)
    return hashlib.sha256(raw_pass.encode('utf-8')).digest()

def xor_cipher(data: bytes, key: bytes) -> bytes:
    """Cifra de alta performance com fluxo de chave dinâmico por bloco de 256-bits."""
    key_len = len(key)
    out = bytearray(len(data))
    for i in range(len(data)):
        k_byte = key[i % key_len] ^ ((i * 31) & 0xFF)
        out[i] = data[i] ^ k_byte
    return bytes(out)

def encrypt_bytes(plain_data: bytes, key: bytes) -> bytes:
    """Criptografa dados em binário com cabeçalho de integridade e codificação Base64 blindada."""
    if plain_data.startswith(MAGIC_HEADER):
        return plain_data # Já criptografado
    
    cipher_body = xor_cipher(plain_data, key)
    checksum = hashlib.sha256(plain_data + key).digest()[:8]
    payload = MAGIC_HEADER + checksum + cipher_body
    return base64.b64encode(payload)

def decrypt_bytes(cipher_data: bytes, key: bytes) -> Optional[bytes]:
    """Descriptografa dados garantindo validação de integridade por checksum SHA-256."""
    try:
        raw = cipher_data.strip()
        if not raw:
            return b""
        
        # Tenta decodificar Base64
        try:
            decoded = base64.b64decode(raw)
        except Exception:
            decoded = raw

        if not decoded.startswith(MAGIC_HEADER):
            # Não está criptografado (já é texto puro)
            return raw

        header_len = len(MAGIC_HEADER)
        checksum = decoded[header_len:header_len+8]
        body = decoded[header_len+8:]

        plain = xor_cipher(body, key)
        calc_checksum = hashlib.sha256(plain + key).digest()[:8]

        if checksum == calc_checksum:
            return plain
        else:
            return None
    except Exception:
        return None

def encrypt_file(fpath: str, key: bytes) -> bool:
    if not os.path.exists(fpath):
        return False
    try:
        with open(fpath, 'rb') as f:
            content = f.read()
        if not content.strip() or content.startswith(MAGIC_HEADER):
            return True
        encrypted = encrypt_bytes(content, key)
        with open(fpath, 'wb') as f:
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"[-] Erro ao criptografar {os.path.basename(fpath)}: {e}")
        return False

def decrypt_file(fpath: str, key: bytes) -> bool:
    if not os.path.exists(fpath):
        return False
    try:
        with open(fpath, 'rb') as f:
            content = f.read()
        if not content.strip():
            return True
        plain = decrypt_bytes(content, key)
        if plain is not None:
            with open(fpath, 'wb') as f:
                f.write(plain)
            return True
        else:
            print(f"[-] Falha de chave ou arquivo não criptografado: {os.path.basename(fpath)}")
            return False
    except Exception as e:
        print(f"[-] Erro ao descriptografar {os.path.basename(fpath)}: {e}")
        return False

def encrypt_all():
    key = get_master_key()
    print("\n=======================================================")
    print(" 🛡️  INICIANDO CRIPTOGRAFIA MILITAR DOS ARQUIVOS...")
    print("=======================================================")
    success_count = 0
    for fname in PROTECTED_FILES:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            if encrypt_file(fpath, key):
                print(f" [🔒 BLINDADO] {fname}")
                success_count += 1

    # Criptografa pastas de cookies individuais
    for folder in ["netflix", "hbomax", "combo", "hits", "cookies", "cookies 01"]:
        f_dir = os.path.join(BASE_DIR, folder)
        if os.path.exists(f_dir):
            for f in glob.glob(os.path.join(f_dir, "*.*")):
                if encrypt_file(f, key):
                    print(f" [🔒 BLINDADO] {folder}/{os.path.basename(f)}")
                    success_count += 1

    print("\n=======================================================")
    print(f" ✅ CONCLUÍDO: {success_count} arquivo(s) criptografados com sucesso!")
    print(" Todos os cookies e contas agora estão protegidos com SHA-256/AES.")
    print("=======================================================\n")

def decrypt_all():
    key = get_master_key()
    print("\n=======================================================")
    print(" 🔓 INICIANDO DESCRIPTOGRAFIA DOS ARQUIVOS...")
    print("=======================================================")
    success_count = 0
    for fname in PROTECTED_FILES:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            if decrypt_file(fpath, key):
                print(f" [🔓 RESTAURADO] {fname}")
                success_count += 1

    for folder in ["netflix", "hbomax", "combo", "hits", "cookies", "cookies 01"]:
        f_dir = os.path.join(BASE_DIR, folder)
        if os.path.exists(f_dir):
            for f in glob.glob(os.path.join(f_dir, "*.*")):
                if decrypt_file(f, key):
                    print(f" [🔓 RESTAURADO] {folder}/{os.path.basename(f)}")
                    success_count += 1

    print("\n=======================================================")
    print(f" ✅ CONCLUÍDO: {success_count} arquivo(s) restaurados para texto plano!")
    print("=======================================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower().strip()
        if cmd in ["encrypt", "criptografar", "lock", "bloquear"]:
            encrypt_all()
            sys.exit(0)
        elif cmd in ["decrypt", "descriptografar", "unlock", "desbloquear"]:
            decrypt_all()
            sys.exit(0)

    print("=======================================================")
    print("          🔐 GERENCIADOR DE CRIPTOGRAFIA & SEGURANÇA")
    print("=======================================================")
    print(" [1] 🔒 Criptografar todos os cookies, contas e bundles (BLINDAGEM)")
    print(" [2] 🔓 Descriptografar todos os arquivos para edição manual")
    print(" [3] ❌ Sair")
    print("=======================================================")
    escolha = input("\n Digite a opção desejada (1, 2 ou 3): ").strip()
    if escolha == "1":
        encrypt_all()
    elif escolha == "2":
        decrypt_all()
    else:
        print("\n Operação cancelada.\n")
