# 🛡️ Sistema de Criptografia & Blindagem Militar (2026)

Este documento detalha toda a arquitetura de segurança, criptografia em repouso e em trânsito implementada no sistema **TVCODIGO / Cyber Deck**.

---

## 🔐 1. Como Funciona a Criptografia dos Arquivos

Todos os arquivos sensíveis de cookies, contas, combos e tokens podem ser blindados com criptografia simétrica com chave derivada via **SHA-256 (256 bits)** a partir da **Senha Mestre**.

### Arquivos Protegidos:
- `cookies_bundle.json`
- `contas_pool.json`
- `used_cookies.json`
- `skycontas.txt`, `sso_token.txt`, `profile_token.txt`
- Pastas de cookies e combos: `netflix/`, `hbomax/`, `combo/`, `hits/`

---

## 📌 2. Como Descriptografar e Criptografar (1 Clique)

| Ação | Arquivo / Comando | O que faz |
| :--- | :--- | :--- |
| **🔓 Descriptografar** | Clique duas vezes em `DESCRIPTOGRAFAR_ARQUIVOS.bat` ou execute `python gerenciador_seguranca.py decrypt` | Restaura todos os cookies e arquivos para texto plano legível para edição. |
| **🔒 Criptografar / Blindar** | Clique duas vezes em `CRIPTOGRAFAR_ARQUIVOS.bat` ou execute `python gerenciador_seguranca.py encrypt` | Criptografa todos os arquivos sensíveis com o cabeçalho seguro `CYBER_BLINDADO_V1::`. |

> [!NOTE]
> **O servidor `app.py` descriptografa tudo em memória RAM automaticamente.** Você não precisa descriptografar os arquivos para o site funcionar. O ativador de Smart TVs e o Painel Admin funcionam perfeitamente com os arquivos 100% criptografados no disco.

---

## 🛡️ 3. Camadas de Segurança Ativas

### 1. **Anti-Inspeção & Anti-DevTools no Navegador**
- Bloqueio automático de teclas de inspeção: `F12`, `Ctrl + Shift + I`, `Ctrl + Shift + J`, `Ctrl + Shift + C`, `Ctrl + U` (Exibir código-fonte) e `Ctrl + S`.
- Desativação de clique com botão direito no painel principal.
- Proteção Anti-Framing / Anti-Clickjacking (`window.top !== window.self`).

### 2. **Segurança de Sessão e Revogação em Tempo Real**
- Cada requisição de status ou ativação valida se a senha do usuário ainda existe no `config_senhas.json`.
- Ao excluir uma senha no Painel Admin, qualquer dispositivo conectado usando aquela senha é **desconectado na hora**.
- Tokens criptográficos seguros de 256 bits (`secrets.token_hex(32)`).

### 3. **Defesa Contra Ataques de Força Bruta & Timing Attacks**
- Validação constante em tempo fixo via `hmac.compare_digest` para impedir ataques de temporização.
- Bloqueio progressivo de IP com penalidades crescentes (1 minuto, 5 minutos, 15 minutos).
- Rate Limiting estrito em rotas sensíveis como `/api/activate` e `/api/admin/*`.

### 4. **Isolamento Total de Arquivos Confidenciais**
- Rotas HTTP bloqueiam estritamente qualquer acesso direto a arquivos `.txt`, `.json`, `.py`, `.git`, pastas `cookies/`, `netflix/`, `hbomax/`, etc. (retornando `403 Forbidden`).

---

## 🔑 4. Como Alterar a Chave Mestra

A chave de criptografia é gerada a partir da senha em [SENHA_MESTRE.txt](file:///c:/Users/Micro/Desktop/SITE%20DE%20ATIVACOES%20DE%20HBO%20E%20NETFLIX/SENHA_MESTRE.txt).

Para trocar a senha mestra:
1. Execute `DESCRIPTOGRAFAR_ARQUIVOS.bat` para garantir que tudo esteja legível.
2. Altere a senha no arquivo [SENHA_MESTRE.txt](file:///c:/Users/Micro/Desktop/SITE%20DE%20ATIVACOES%20DE%20HBO%20E%20NETFLIX/SENHA_MESTRE.txt).
3. Execute `CRIPTOGRAFAR_ARQUIVOS.bat` para criptografar tudo novamente com a nova chave.
