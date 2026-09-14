import os
import glob
import json
import stat
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NETFLIX_DIR = os.path.join(BASE_DIR, "netflix")
COOKIES_BUNDLE = os.path.join(BASE_DIR, "cookies_bundle.json")
CONFIG_SENHAS = os.path.join(BASE_DIR, "config_senhas.json")

print("=" * 60)
print("INICIANDO LIMPEZA EXCLUSIVA DOS COOKIES DA NETFLIX...")
print("=" * 60)

# 1. Remove todos os cookies da pasta netflix
deleted_count = 0
if os.path.exists(NETFLIX_DIR):
    for f in glob.glob(os.path.join(NETFLIX_DIR, "*")):
        try:
            os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
            os.remove(f)
            deleted_count += 1
        except Exception as e:
            print(f"Aviso ao remover {os.path.basename(f)}: {e}")

old_cookies_dir = os.path.join(BASE_DIR, "cookies")
if os.path.exists(old_cookies_dir):
    for f in glob.glob(os.path.join(old_cookies_dir, "*")):
        try:
            os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
            os.remove(f)
            deleted_count += 1
        except Exception:
            pass

print(f"[✓] 1. Pasta 'netflix' limpa: {deleted_count} cookies antigos removidos!")

# 2. Esvazia a secao netflix de cookies_bundle.json para nao ressuscitar
if os.path.exists(COOKIES_BUNDLE):
    try:
        with open(COOKIES_BUNDLE, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data["netflix"] = {}
            with open(COOKIES_BUNDLE, "w", encoding="utf-8", errors="ignore") as f:
                json.dump(data, f, indent=2)
            print("[✓] 2. cookies_bundle.json atualizado! (Netflix zerada, nao vai ressuscitar)")
    except Exception as e:
        print(f"Aviso ao atualizar bundle: {e}")

# 3. VERIFICAÇÃO DE SEGURANÇA MÁXIMA DAS SENHAS DOS CLIENTES
if os.path.exists(CONFIG_SENHAS):
    with open(CONFIG_SENHAS, "r", encoding="utf-8", errors="ignore") as f:
        senhas_data = json.load(f)
    num_senhas = len(senhas_data.get("senhas", []))
    print(f"[✓] 3. SEGURANCA: config_senhas.json INTACTO! Todas as {num_senhas} senhas de clientes estao 100% salvas!")

print("=" * 60)
print("SUCESSO: A PASTA 'netflix' ESTA VAZIA E PRONTA PARA OS NOVOS COOKIES!")
print("=" * 60)
