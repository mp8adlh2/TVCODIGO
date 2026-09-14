import sys
import io
import time
import json
import os
from datetime import datetime

# Garante compatibilidade com Windows CP1252
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Importa as funcoes principais do app.py
from app import (
    check_item_expiration,
    find_access_role,
    load_access_keys,
    atomic_save_config_senhas,
    CONFIG_SENHAS_FILE
)

print("=" * 60)
print("[TESTE] INICIANDO TESTES AUTOMATIZADOS DO SISTEMA DE VALIDADE")
print("=" * 60)

now = time.time()

# 1. Teste de item permanente
perm_item = {"senha": "TESTE_PERMANENTE", "nome": "Cliente Permanente", "expira_em": None}
res_perm = check_item_expiration(perm_item)
assert res_perm["expired"] is False, "Falha: Permanente nao deve expirar"
assert res_perm["is_permanent"] is True, "Falha: Flag is_permanent incorreta"
print("[OK] 1. Teste de Senha Permanente: OK (Nao expira)")

# 2. Teste de senha ativa com 30 dias
exp_30d = now + (30 * 86400)
item_30d = {
    "senha": "TESTE_30D",
    "nome": "Cliente 30 Dias",
    "expira_em": exp_30d,
    "expira_em_formatado": datetime.fromtimestamp(exp_30d).strftime('%d/%m/%Y as %H:%M')
}
res_30d = check_item_expiration(item_30d)
assert res_30d["expired"] is False, "Falha: Senha de 30 dias nao deve estar expirada"
assert 29 <= res_30d["days_remaining"] <= 31, f"Falha: Dias restantes incorretos ({res_30d['days_remaining']})"
print(f"[OK] 2. Teste de Senha de 30 Dias: OK (Dias restantes: {res_30d['days_remaining']}, Expira em: {res_30d['expira_em_formatado']})")

# 3. Teste de senha com 200 dias
exp_200d = now + (200 * 86400)
item_200d = {
    "senha": "TESTE_200D",
    "nome": "Cliente 200 Dias",
    "expira_em": exp_200d,
    "expira_em_formatado": datetime.fromtimestamp(exp_200d).strftime('%d/%m/%Y as %H:%M')
}
res_200d = check_item_expiration(item_200d)
assert res_200d["expired"] is False
assert 199 <= res_200d["days_remaining"] <= 201
print(f"[OK] 3. Teste de Senha de 200 Dias: OK (Dias restantes: {res_200d['days_remaining']}, Expira em: {res_200d['expira_em_formatado']})")

# 4. Teste de senha com 360 dias
exp_360d = now + (360 * 86400)
item_360d = {
    "senha": "TESTE_360D",
    "nome": "Cliente 360 Dias",
    "expira_em": exp_360d,
    "expira_em_formatado": datetime.fromtimestamp(exp_360d).strftime('%d/%m/%Y as %H:%M')
}
res_360d = check_item_expiration(item_360d)
assert res_360d["expired"] is False
assert 359 <= res_360d["days_remaining"] <= 361
print(f"[OK] 4. Teste de Senha de 360 Dias: OK (Dias restantes: {res_360d['days_remaining']}, Expira em: {res_360d['expira_em_formatado']})")

# 5. Teste de senha EXPIRADA (passada)
exp_passado = now - 3600  # Expirou ha 1 hora
item_exp = {
    "senha": "TESTE_EXPIRADO",
    "nome": "Cliente Vencido",
    "expira_em": exp_passado,
    "expira_em_formatado": datetime.fromtimestamp(exp_passado).strftime('%d/%m/%Y as %H:%M')
}
res_exp = check_item_expiration(item_exp)
assert res_exp["expired"] is True, "Falha: Senha passada deve ser detectada como expired=True"
assert res_exp["days_remaining"] == 0, "Falha: Senha expirada deve ter 0 dias restantes"
print(f"[OK] 5. Teste de Bloqueio por Expiracao: OK (expired={res_exp['expired']}, data={res_exp['expira_em_formatado']})")

# 6. Teste de persistencia e busca no find_access_role
keys = load_access_keys()
test_keys = [k for k in keys if k.get("senha") not in ["TESTE_EXPIRADO", "TESTE_30D"]]
test_keys.append(item_exp)
test_keys.append(item_30d)
atomic_save_config_senhas(test_keys)

# Valida busca da senha expirada
role_exp = find_access_role("TESTE_EXPIRADO")
assert role_exp is not None, "Falha: find_access_role deve encontrar a senha"
assert role_exp.get("expired") is True, "Falha: Senha expirada deve retornar expired=True no find_access_role"
print("[OK] 6. Teste de Bloqueio no find_access_role(): OK (Bloqueia login de senha vencida)")

# Valida busca da senha de 30 dias
role_30d = find_access_role("TESTE_30D")
assert role_30d is not None, "Falha: find_access_role deve encontrar senha ativa"
assert role_30d.get("expired") is False, "Falha: Senha ativa nao deve estar expirada"
assert role_30d.get("days_remaining") >= 29, "Falha: Dias restantes devem ser calculados"
print(f"[OK] 7. Teste de Senha Ativa no find_access_role(): OK (Liberada com {role_30d.get('days_remaining')} dias)")

# 7. Teste de Renovacao (+30 dias na senha expirada)
keys_to_renew = load_access_keys()
renewed = False
for k in keys_to_renew:
    if k.get("senha") == "TESTE_EXPIRADO":
        k["expira_em"] = now + (30 * 86400)
        k["expira_em_formatado"] = datetime.fromtimestamp(k["expira_em"]).strftime('%d/%m/%Y as %H:%M')
        renewed = True
        break
assert renewed is True, "Falha ao encontrar senha para renovacao"
atomic_save_config_senhas(keys_to_renew)

# Valida apos renovacao
role_renewed = find_access_role("TESTE_EXPIRADO")
assert role_renewed.get("expired") is False, "Falha: Senha renovada nao deve mais estar expirada"
assert role_renewed.get("days_remaining") >= 29, "Falha: Dias restantes devem refletir a renovacao"
print("[OK] 8. Teste de Renovacao (+30 dias): OK (Senha antes expirada agora esta 100% ativa)")

# Limpa senhas de teste
clean_keys = [k for k in load_access_keys() if k.get("senha") not in ["TESTE_EXPIRADO", "TESTE_30D"]]
atomic_save_config_senhas(clean_keys)
print("[OK] 9. Limpeza de registros de teste: OK")

print("=" * 60)
print("SUCESSO ABSOLUTO: TODOS OS 9 TESTES DE VALIDADE FORAM APROVADOS!")
print("=" * 60)
