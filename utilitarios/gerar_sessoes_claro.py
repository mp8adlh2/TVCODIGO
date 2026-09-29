import os
import sys
import time
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import claro_service

def main(limit=5):
    accounts = claro_service.load_all_claro_accounts()
    print(f"Total de contas Claro TV carregadas: {len(accounts)}")
    
    # Carrega sessões já salvas
    claro_service._load_sessions_from_disk()
    existing_sessions = set(claro_service._CLARO_SESSIONS_CACHE.keys())
    print(f"Sessões já existentes e válidas: {len(existing_sessions)}")
    
    success_count = 0
    for i, acc in enumerate(accounts):
        if success_count >= limit:
            break
        u = acc["user"]
        u_key = u.strip().lower()
        if u_key in existing_sessions:
            print(f"[{i+1}/{len(accounts)}] Conta {u} já tem sessão ativa válida. Pulando...")
            continue
            
        print(f"\n[{i+1}/{len(accounts)}] Autenticando conta {u}...")
        ok, cookies, msg = claro_service._realizar_login_playwright(u, acc["password"])
        if ok and cookies.get("avs_cookie"):
            claro_service._CLARO_SESSIONS_CACHE[u_key] = {
                "cookies": cookies,
                "xsrf": claro_service.extrair_xsrf_token(cookies.get("avs_cookie", "")),
                "timestamp": time.time()
            }
            claro_service._save_sessions_to_disk()
            existing_sessions.add(u_key)
            success_count += 1
            print(f"✅ SUCESSO! Sessão da conta {u} gerada e salva com validade até 2027! ({success_count}/{limit})")
            time.sleep(2)
        else:
            print(f"❌ Falha na conta {u}: {msg}")
            time.sleep(1)

    print(f"\n=======================================================")
    print(f" Concluído! Total de sessões ativas prontas: {len(claro_service._CLARO_SESSIONS_CACHE)}")
    print(f"=======================================================")

if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    main(lim)
