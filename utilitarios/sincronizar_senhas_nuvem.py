import urllib.request
import json
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://tvcodigo-1.onrender.com").rstrip('/')
ADMIN_PASS = "TVCODIGO#ADMIN@2026$MASTER*TITANIUM!ROOT#VIP"

CFG_FILE = os.path.join(BASE_DIR, "config_senhas.json")
CFG_BK = os.path.join(BASE_DIR, "config_senhas_backup.json")
TXT_FILE = os.path.join(BASE_DIR, "SENHAS_DE_ACESSO.txt")

def main():
    print(" [1/4] Conectando ao Render para baixar senhas em tempo real...")
    remote_keys = []
    try:
        url = f"{RENDER_URL}/api/admin/passwords/backup"
        req = urllib.request.Request(url, headers={"X-Admin-Pass": ADMIN_PASS, "User-Agent": "BackupSync/2.0"})
        with urllib.request.urlopen(req, timeout=12) as res:
            if res.status == 200:
                data = json.loads(res.read().decode('utf-8'))
                remote_keys = data.get("senhas", [])
                print(f"       [OK] {len(remote_keys)} senhas obtidas do Render.")
    except Exception as e:
        print(f"       [i] Render offline ou iniciando: {e}")

    # Carrega senhas locais atuais
    local_keys = []
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                local_keys = d.get("senhas", [])
        except Exception:
            pass

    # Merge inteligente (unifica senhas remotas e locais sem perdas)
    merged = {}
    for item in local_keys:
        p = str(item.get("senha", "")).strip()
        if p:
            merged[p.lower()] = item

    for item in remote_keys:
        p = str(item.get("senha", "")).strip()
        if p:
            merged[p.lower()] = item

    final_list = list(merged.values())

    if final_list:
        try:
            with open(CFG_FILE, "w", encoding="utf-8") as f:
                json.dump({"senhas": final_list}, f, indent=2, ensure_ascii=False)
            with open(CFG_BK, "w", encoding="utf-8") as f:
                json.dump({"senhas": final_list}, f, indent=2, ensure_ascii=False)
            
            # Sincroniza SENHAS_DE_ACESSO.txt
            lines = [
                "================================================================================",
                "   CHAVES DE ACESSO DO SISTEMA - CADASTRO OFICIAL COMPLETO (2026)",
                "================================================================================",
                ""
            ]
            for item in final_list:
                lines.append(f"- SENHA: {item.get('senha')}")
                lines.append(f"  Nome: {item.get('nome', 'Cliente VIP')}")
                lines.append(f"  Servicos: {', '.join(item.get('servicos', []))}")
                exp = item.get('expira_em_formatado') or 'Permanente (Sem Expiracao)'
                lines.append(f"  Validade: {exp}")
                lines.append("-" * 80)
            
            with open(TXT_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"       [OK] Total de {len(final_list)} senhas sincronizadas e salvas localmente!")
        except Exception as e:
            print(f"       [!] Erro ao salvar localmente: {e}")
    else:
        print("       [i] Nenhuma alteracao necessaria.")

if __name__ == "__main__":
    main()
