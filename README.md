# 📺 SKY TV ATIVADOR & CHECKER - MASTERON

Sistema automatizado de validação de contas Sky e ativação de dispositivos Smart TV (via código de 6 dígitos) com **sistema de rotação inteligente multi-contas**. Cada nova TV ativada utiliza automaticamente uma conta diferente do pool, garantindo que o limite de telas simultâneas não seja atingido na mesma conta.

---

## 📁 Estrutura de Arquivos da Pasta

```
ATIVADOR SKY/
│
├── 🚀 SCRIPTS PRINCIPAIS
│   ├── servidor_web.py         -> Painel Web e API REST com rotação automática de contas
│   ├── ativador_tv.py          -> Ativador via terminal (CLI) com rotação inteligente
│   ├── gerenciador_contas.py   -> Motor de rotação (Round-Robin / Menos Ativações Primeiro)
│   ├── sky.py                  -> Checker e validador de contas Sky (filtra por pacotes)
│   └── recaptcha_solver.py     -> Motor de resolução do reCAPTCHA (Android / Web)
│
├── 🔑 PAYLOADS & SESSÕES
│   ├── sso_token.txt           -> Token de sessão ativo atual
│   ├── profile_token.txt       -> Token de perfil criptografado
│   ├── payload.b64             -> Token base do reCAPTCHA Android (login por e-mail)
│   ├── payload_web.b64         -> Token base do reCAPTCHA Web (login por CPF/telefone)
│   └── payload_paramount.b64   -> Token base Paramount
│
├── 📋 LISTAS E CONTAS
│   ├── skycontas.txt           -> 35 contas selecionadas (20 Completas, 10 Médias, 5 Básicas)
│   └── contas_pool.json        -> Pool dinâmico de contas configuradas para rotação
│
├── 📂 DIRETÓRIOS
│   ├── combo/                  -> Listas brutas para testar no sky.py (email:senha)
│   └── hits/                   -> Contas válidas separadas por categoria e histórico
│       ├── COMPLETAS.txt       -> Combos Full, Top HD, HBO, Telecine, Premiere
│       ├── MEDIA.txt           -> Planos Super HD, Fibra, Intermediários
│       ├── BASICA.txt          -> Planos Sky Digital, Easy SD, Básicos
│       ├── Todos_Hits.txt      -> Todas as contas válidas unificadas com detalhes
│       ├── contas_ativadas.txt -> Histórico de TVs e contas utilizadas (registro de rotação)
│       ├── ativacoes_tv.txt    -> Log detalhado de ativações de TV (sucessos e falhas)
│       └── raw_json/           -> Dados completos e tokens em cache de cada conta
```

---

## ⚡ Como Usar

### 1. Pelo Navegador / Servidor Web (Recomendado):
```powershell
python servidor_web.py
```
- Acesse: `http://localhost:8080`
- **Seletor de Conta**: Escolha entre **⚡ Rotação Automática (Menos Usadas Primeiro)** ou selecione **qualquer conta específica** do pool.
- Digite o código de 6 dígitos que aparece na sua Smart TV e clique em **ATIVAR TV AGORA**.
- O sistema vincula a TV à conta selecionada ou avança o ciclo da rotação para uma conta diferente.
- **Aba 🔑 Gerenciar Sessões**: Permite colar o `ssoToken` (JWT DTVGO) do SkyMais para qualquer conta, permitindo ativações instantâneas (~0.5s) e rotação multi-contas real.
- **Abas 👥 Pool de Contas & 📋 Histórico**: Visualize o status de cada conta, quantas TVs cada uma ativou e histórico detalhado.

### 2. Pelo Terminal (Linha de Comando):
```powershell
python ativador_tv.py
```
- **Opção [0]**: Ativação Instantânea com Rotação Automática (seleciona contas com menor número de ativações).
- **Opção [1]**: Usar contas da pasta `hits/` e `skycontas.txt`.
- **Opção [2]**: Usar especificamente as contas de `skycontas.txt`.
- **Opção [5]**: Ver status completo do pool de contas e histórico de TVs ativadas.

### 3. Testar / Checar novas listas de contas:
```powershell
python sky.py
```

---

## 🔄 Como Funciona a Rotação de Contas e Por Que Parecia Ativar Sempre a Mesma

1. O endpoint oficial de ativação de Smart TVs da Sky (`dtv-oidc.tbxapis.com`) exige um token de sessão **DTVGO / SkyMais** (`aud: dtvgo`, emitido por `sm-dgo.vrioservices.com`). Tokens do aplicativo móvel Minha Sky (`sm-sky`) são rejeitados com `401: Invalid token`.
2. Quando apenas 1 conta possui sessão ativa configurada no pool (`rsgencadernacoes@yahoo.com.br`), qualquer tentativa sem sessão falhava ou usava essa conta como fallback de emergência.
3. **Agora corrigido**:
   - O painel web possui **seletor direto de conta** no topo, permitindo escolher manualmente qualquer conta cadastrada ou usar rotação automática.
   - Foi adicionada a aba **🔑 Gerenciar Sessões**, permitindo que você vincule o `ssoToken` a qualquer uma das suas 35 contas.
   - Contas com sessão ativa rotacionam estritamente por ordem de **menos ativações primeiro**, garantindo que cada TV ativada use uma conta diferente!

