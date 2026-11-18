"""
╔══════════════════════════════════════════════════════════╗
║           BOT TELEGRAM - ATIVADOR VIP                   ║
║   HBO Max | Netflix | SKY | Claro TV                    ║
╚══════════════════════════════════════════════════════════╝

Como usar:
  1. Coloque seu TOKEN do BotFather na variável BOT_TOKEN abaixo
  2. Instale: python -m pip install python-telegram-bot==20.7
  3. Rode: python telegram_bot.py

Comandos disponíveis no Telegram:
  /start   → Boas-vindas
  /hbo     → Ativar HBO Max/Max na TV
  /netflix → Ativar Netflix na TV
  /sky     → Ativar SKY na TV
  /claro   → Ativar Claro TV+ na TV
  /status  → Ver status do sistema
"""

import os
import sys
import asyncio
import logging
import threading

# ══════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÃO — EDITE AQUI
# ══════════════════════════════════════════════════════════

BOT_TOKEN = "9262421617:AAFqMa7PP4hJ_r7M63VkazqRzdQEPkMlF5Y"

# IDs dos administradores (podem usar /status e /admin)
# Para descobrir seu ID: fale com @userinfobot no Telegram
ADMIN_IDS = []  # Ex: [123456789, 987654321]

# ID do seu grupo VIP (deixe [] para permitir qualquer grupo)
# Para descobrir: adicione o bot no grupo e mande /start
ALLOWED_GROUP_IDS = []  # Ex: [-1001234567890]

# ══════════════════════════════════════════════════════════

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ajustar diretório base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ══════════════════════════════════════════════════════════
# 📦 IMPORTAR MÓDULOS DO SEU SISTEMA
# ══════════════════════════════════════════════════════════

def import_modules():
    """Importa os módulos existentes do seu sistema."""
    modules = {}

    # HBO Max
    try:
        import hbo
        modules["hbo"] = hbo
        logger.info("✅ Módulo HBO Max carregado")
    except Exception as e:
        logger.warning(f"⚠️ HBO Max não disponível: {e}")

    # SKY — usa sky_service (mesmo motor do site)
    try:
        import sky_service
        modules["sky"] = sky_service
        logger.info("✅ Módulo SKY carregado")
    except Exception as e:
        logger.warning(f"⚠️ SKY não disponível: {e}")

    # Netflix
    try:
        import app as netflix_app
        modules["netflix"] = netflix_app
        logger.info("✅ Módulo Netflix carregado")
    except Exception as e:
        logger.warning(f"⚠️ Netflix não disponível: {e}")

    # Claro TV
    try:
        import claro_service
        modules["claro"] = claro_service
        logger.info("✅ Módulo Claro TV carregado")
    except Exception as e:
        logger.warning(f"⚠️ Claro TV não disponível: {e}")

    return modules

MODULES = import_modules()

# ══════════════════════════════════════════════════════════
# 🔧 FUNÇÕES DE ATIVAÇÃO (chamam seu código existente)
# ══════════════════════════════════════════════════════════

def ativar_hbo(codigo: str) -> dict:
    """Ativa HBO Max/Max na TV usando seu hbo.py."""
    try:
        mod = MODULES.get("hbo")
        if not mod:
            return {"sucesso": False, "mensagem": "❌ Módulo HBO Max não disponível no momento."}

        # Busca um cookie válido
        cookie_data = mod.find_next_valid_cookie()
        if not cookie_data:
            return {"sucesso": False, "mensagem": "❌ Nenhum cookie HBO Max disponível no momento.\nTente novamente em instantes."}

        st_token = cookie_data["st_token"]
        region   = cookie_data["region"]
        email    = cookie_data["email"]
        country  = cookie_data["country"]
        plan     = cookie_data["plan_name"]
        filename = cookie_data["filename"]

        # Faz a ativação
        success, status_msg = mod.activate_tv_code(st_token, codigo, region)

        if success:
            mod.record_activation(filename, st_token, email, codigo)
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✅  *HBO MAX ATIVADO!*  ✅  ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código:* `{codigo}`\n"
                    f"👤 *Conta:* `{email}`\n"
                    f"💎 *Plano:* {plan}\n"
                    f"🌍 *País:* {country}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎬 *Aproveite sua HBO Max na TV!* 🍿"
                )
            }
        else:
            msgs = {
                "invalid_code": f"❌ *Código inválido!*\n\nO código `{codigo}` foi recusado.\n💡 Verifique o código na TV e tente novamente.",
                "expired_code": f"⏳ *Código expirado!*\n\nO código `{codigo}` expirou.\n💡 Gere um novo código na sua TV.",
                "activation_failed": "❌ *Falha na ativação*\n\nTente novamente em instantes.",
            }
            return {"sucesso": False, "mensagem": msgs.get(status_msg, f"❌ Erro: {status_msg}")}

    except Exception as e:
        logger.error(f"Erro ao ativar HBO: {e}")
        return {"sucesso": False, "mensagem": f"❌ Erro interno: {str(e)}"}


def ativar_sky(codigo: str) -> dict:
    """Ativa SKY/DTV na TV usando sky_service (mesmo motor do site)."""
    try:
        mod = MODULES.get("sky")
        if not mod:
            return {"sucesso": False, "mensagem": "❌ Módulo SKY não disponível no momento."}

        # Busca conta válida (mesmo método do site)
        find_func = getattr(mod, "find_sky_valid_account", None)
        if find_func is None:
            return {"sucesso": False, "mensagem": "❌ Função de busca SKY não encontrada."}

        account_data = find_func()
        if not account_data:
            return {"sucesso": False, "mensagem": "❌ Nenhuma conta SKY disponível.\nAdicione contas no painel e tente novamente."}

        # Ativa a TV usando o mesmo motor do site: sky_service.activate_sky_tv()
        activate_func = getattr(mod, "activate_sky_tv", None)
        if activate_func is None:
            return {"sucesso": False, "mensagem": "❌ Função de ativação SKY não encontrada."}

        # Retorna Tuple[bool, str, Optional[dict]]
        resultado = activate_func(tv_code=codigo, account_data=account_data, use_proxy=True)

        if isinstance(resultado, tuple):
            success = resultado[0]
            msg     = resultado[1] if len(resultado) > 1 else ""
            info    = resultado[2] if len(resultado) > 2 else {}
        else:
            success = bool(resultado)
            msg     = ""
            info    = {}

        email = account_data.get("email", "")
        plano = ""
        if isinstance(info, dict):
            plano = info.get("plan", info.get("plano", ""))

        if success:
            linha_email = f"👤 *Conta:* `{email}`\n" if email else ""
            linha_plano = f"💎 *Plano:* {plano}\n" if plano else ""
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✅  *SKY ATIVADO!*  ✅     ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código:* `{codigo}`\n"
                    f"{linha_email}"
                    f"{linha_plano}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📡 *Aproveite o SKY na TV!* 🍿"
                )
            }
        else:
            msg_amigavel = msg or "Falha na ativação"
            return {"sucesso": False, "mensagem": f"❌ *Falha na ativação SKY*\n\n{msg_amigavel}\n\n💡 Tente novamente com /sky"}

    except Exception as e:
        logger.error(f"Erro ao ativar SKY: {e}")
        return {"sucesso": False, "mensagem": f"❌ Erro interno SKY: {str(e)}"}


def ativar_netflix(codigo: str) -> dict:
    """Ativa Netflix na TV usando cookies via app.py + tv2.py."""
    try:
        mod = MODULES.get("netflix")
        if not mod:
            return {"sucesso": False, "mensagem": "❌ Módulo Netflix não disponível no momento."}

        # Busca cookie válido
        find_func = getattr(mod, "find_netflix_valid_cookie", None)
        if find_func is None:
            return {"sucesso": False, "mensagem": "❌ Função Netflix não encontrada."}

        cookie_info = find_func()
        if not cookie_info:
            return {"sucesso": False, "mensagem": "❌ Nenhum cookie Netflix válido disponível.\nTente novamente mais tarde."}

        # Chama ativação — retorna TUPLA: (success, msg, info)
        activate_func = getattr(mod, "activate_netflix_tv", None)
        if activate_func is None:
            return {"sucesso": False, "mensagem": "❌ Função de ativação Netflix não encontrada."}

        resultado = activate_func(codigo, cookie_info)

        # Desempacota a tupla (bool, str, dict_ou_None)
        if isinstance(resultado, tuple):
            success = resultado[0]
            msg     = resultado[1] if len(resultado) > 1 else ""
            info    = resultado[2] if len(resultado) > 2 else {}
        else:
            success = bool(resultado)
            msg     = ""
            info    = {}

        email = ""
        plano = "Netflix"
        if isinstance(info, dict):
            email = info.get("email", "")
            plano = info.get("plan", info.get("plano", "Netflix"))

        if success:
            linha_email = f"👤 *Conta:* `{email}`\n" if email else ""
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✅  *NETFLIX ATIVADO!*  ✅  ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código:* `{codigo}`\n"
                    f"{linha_email}"
                    f"💎 *Plano:* {plano}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 *Aproveite a Netflix na TV!* 🍿"
                )
            }
        else:
            msg_amigavel = msg or "Falha na ativação"
            return {"sucesso": False, "mensagem": f"❌ *Falha na ativação Netflix*\n\n{msg_amigavel}\n\n💡 Tente novamente com /netflix"}

    except Exception as e:
        logger.error(f"Erro ao ativar Netflix: {e}")
        return {"sucesso": False, "mensagem": f"❌ Erro interno: {str(e)}"}


def ativar_claro(codigo: str) -> dict:
    """Ativa Claro TV+ na TV usando claro_service.activate_claro_tv."""
    try:
        mod = MODULES.get("claro")
        if not mod:
            return {"sucesso": False, "mensagem": "❌ Módulo Claro TV não disponível no momento."}

        activate_func = getattr(mod, "activate_claro_tv", None)
        if activate_func is None:
            return {"sucesso": False, "mensagem": "❌ Função de ativação Claro não encontrada."}

        # activate_claro_tv retorna Tuple[bool, str, Optional[dict]]
        resultado = activate_func(codigo)

        if isinstance(resultado, tuple):
            success = resultado[0]
            msg     = resultado[1] if len(resultado) > 1 else ""
            info    = resultado[2] if len(resultado) > 2 else {}
        else:
            success = bool(resultado)
            msg     = ""
            info    = {}

        email = ""
        plano = "Claro TV+"
        if isinstance(info, dict):
            email = info.get("user", info.get("email", info.get("username", "")))
            plano = info.get("plan", info.get("plano", "Claro TV+"))

        if success:
            linha_email = f"👤 *Conta:* `{email}`\n" if email else ""
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✅  *CLARO TV+ ATIVADO!* ✅ ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código:* `{codigo}`\n"
                    f"{linha_email}"
                    f"💎 *Plano:* {plano}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔵 *Aproveite a Claro TV+ na sua TV!* 🍿"
                )
            }
        else:
            msg_amigavel = msg or "Falha na ativação"
            return {"sucesso": False, "mensagem": f"❌ *Falha na ativação Claro TV+*\n\n{msg_amigavel}\n\n💡 Tente novamente com /claro"}

    except Exception as e:
        logger.error(f"Erro ao ativar Claro: {e}")
        return {"sucesso": False, "mensagem": f"❌ Erro interno: {str(e)}"}


# ══════════════════════════════════════════════════════════
# 🤖 BOT TELEGRAM
# ══════════════════════════════════════════════════════════

# Estado dos usuários (aguardando código)
# formato: {user_id: "servico"}
AGUARDANDO_CODIGO = {}
AGUARDANDO_LOCK = threading.Lock()

# Lock global para evitar colisão de ativações simultâneas por serviço
ATIVACAO_LOCKS = {
    "hbo":     threading.Semaphore(3),  # máx 3 ativações HBO ao mesmo tempo
    "netflix": threading.Semaphore(3),  # máx 3 ativações Netflix ao mesmo tempo
    "sky":     threading.Semaphore(2),  # máx 2 ativações SKY ao mesmo tempo
    "claro":   threading.Semaphore(2),  # máx 2 ativações Claro ao mesmo tempo
}

# Fila de espera por serviço (para informar ao cliente)
FILA_ESPERA: dict = {"hbo": 0, "netflix": 0, "sky": 0, "claro": 0}

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters
    )
    TELEGRAM_OK = True
except ImportError:
    TELEGRAM_OK = False
    logger.error("❌ python-telegram-bot não instalado!")
    logger.error("   Rode: python -m pip install python-telegram-bot==20.7")


def checar_permissao(update: "Update") -> bool:
    """Verifica se o usuário/grupo tem permissão de usar o bot."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Se não há grupos configurados, permite todos
    if not ALLOWED_GROUP_IDS:
        return True

    # Permite admins sempre
    if user_id in ADMIN_IDS:
        return True

    # Permite apenas grupos configurados
    return chat_id in ALLOWED_GROUP_IDS


async def cmd_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /start"""
    if not checar_permissao(update):
        return

    nome = update.effective_user.first_name or "Cliente"

    texto = (
        f"╔═══════════════════════════╗\n"
        f"║   🎬  *ATIVADOR VIP*  🎬   ║\n"
        f"╚═══════════════════════════╝\n\n"
        f"👋 Olá, *{nome}*\\! Seja bem\\-vindo\\!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 *SERVIÇOS DISPONÍVEIS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{'🎬 HBO Max / Max' if 'hbo' in MODULES else ''}\n"
        f"{'🔴 Netflix' if 'netflix' in MODULES else ''}\n"
        f"{'📡 SKY / DTV' if 'sky' in MODULES else ''}\n"
        f"{'🔵 Claro TV\\+' if 'claro' in MODULES else ''}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *COMO USAR*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*1\\)* Ligue a TV e abra o app\n"
        f"*2\\)* Anote o código que aparece\n"
        f"*3\\)* Toque no botão do serviço\n"
        f"*4\\)* Envie o código → TV ativada\\! ✅\n\n"
        f"⬇️ *Escolha o serviço abaixo:*"
    )

    keyboard = []
    row1, row2 = [], []
    if "hbo" in MODULES:     row1.append(InlineKeyboardButton("🎬  HBO Max", callback_data="btn_hbo"))
    if "netflix" in MODULES: row1.append(InlineKeyboardButton("🔴  Netflix", callback_data="btn_netflix"))
    if row1: keyboard.append(row1)
    if "sky" in MODULES:     row2.append(InlineKeyboardButton("📡  SKY / DTV", callback_data="btn_sky"))
    if "claro" in MODULES:   row2.append(InlineKeyboardButton("🔵  Claro TV+", callback_data="btn_claro"))
    if row2: keyboard.append(row2)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(texto, parse_mode="MarkdownV2", reply_markup=reply_markup)


async def cmd_hbo(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /hbo"""
    if not checar_permissao(update):
        return
    if "hbo" not in MODULES:
        await update.message.reply_text("❌ HBO Max não disponível no momento.")
        return

    user_id = update.effective_user.id
    with AGUARDANDO_LOCK:
        AGUARDANDO_CODIGO[user_id] = "hbo"

    await update.message.reply_text(
        "╔═══════════════════════════╗\n"
        "║  🎬  *HBO MAX — ATIVAÇÃO*  ║\n"
        "╚═══════════════════════════╝\n\n"
        "📺 Abra o app *HBO Max* na TV\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔢 *Digite o código de 6 dígitos*\n"
        "     que aparece na tela da TV\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 _Exemplo: 123456_",
        parse_mode="Markdown"
    )


async def cmd_netflix(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /netflix"""
    if not checar_permissao(update):
        return
    if "netflix" not in MODULES:
        await update.message.reply_text("❌ Netflix não disponível no momento.")
        return

    user_id = update.effective_user.id
    with AGUARDANDO_LOCK:
        AGUARDANDO_CODIGO[user_id] = "netflix"

    await update.message.reply_text(
        "╔═══════════════════════════╗\n"
        "║  🔴  *NETFLIX — ATIVAÇÃO*  ║\n"
        "╚═══════════════════════════╝\n\n"
        "📺 Abra o app *Netflix* na TV\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔢 *Digite o código* que aparece\n"
        "     na tela da TV\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 _Exemplo: TV-ABCD1 ou 12345678_",
        parse_mode="Markdown"
    )


async def cmd_sky(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /sky"""
    if not checar_permissao(update):
        return
    if "sky" not in MODULES:
        await update.message.reply_text("❌ SKY não disponível no momento.")
        return

    user_id = update.effective_user.id
    with AGUARDANDO_LOCK:
        AGUARDANDO_CODIGO[user_id] = "sky"

    await update.message.reply_text(
        "╔═══════════════════════════╗\n"
        "║  📡  *SKY / DTV — ATIVAÇÃO* ║\n"
        "╚═══════════════════════════╝\n\n"
        "📺 Abra o app *SKY+* ou *DTV Go* na TV\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔢 *Digite o código de 6 dígitos*\n"
        "     que aparece na tela da TV\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 _Exemplo: 654321_",
        parse_mode="Markdown"
    )


async def cmd_claro(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /claro"""
    if not checar_permissao(update):
        return
    if "claro" not in MODULES:
        await update.message.reply_text("❌ Claro TV+ não disponível no momento.")
        return

    user_id = update.effective_user.id
    with AGUARDANDO_LOCK:
        AGUARDANDO_CODIGO[user_id] = "claro"

    await update.message.reply_text(
        "╔═══════════════════════════╗\n"
        "║  🔵  *CLARO TV+ — ATIVAÇÃO* ║\n"
        "╚═══════════════════════════╝\n\n"
        "📺 Abra o app *Claro TV+* na TV\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔢 *Digite o código* que aparece\n"
        "     na tela da TV\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 _Exemplo: 123456_",
        parse_mode="Markdown"
    )


async def cmd_status(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /status — só para admins"""
    if not checar_permissao(update):
        return
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Acesso negado.")
        return

    linhas = ["📊 *STATUS DO SISTEMA*\n"]
    for nome, emoji in [("hbo","🎬"), ("netflix","🔴"), ("sky","📡"), ("claro","🔵")]:
        status = "✅ Online" if nome in MODULES else "❌ Offline"
        linhas.append(f"{emoji} {nome.upper()}: {status}")

    # Contar cookies disponíveis
    hbomax_folder = os.path.join(BASE_DIR, "hbomax")
    netflix_folder = os.path.join(BASE_DIR, "netflix")
    import glob
    hbo_count = len(glob.glob(os.path.join(hbomax_folder, "*.txt")) + glob.glob(os.path.join(hbomax_folder, "*.json")))
    nf_count  = len(glob.glob(os.path.join(netflix_folder, "*.txt")) + glob.glob(os.path.join(netflix_folder, "*.json")))

    linhas.append(f"\n🍪 *Cookies HBO:* {hbo_count} disponíveis")
    linhas.append(f"🍪 *Cookies Netflix:* {nf_count} disponíveis")
    linhas.append(f"\n👥 *Usuários aguardando:* {len(AGUARDANDO_CODIGO)}")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")


async def handle_botoes(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Lida com os botões inline."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    mapa_servico = {
        "btn_hbo":     "hbo",
        "btn_netflix": "netflix",
        "btn_sky":     "sky",
        "btn_claro":   "claro",
    }

    mapa_texto = {
        "btn_hbo":     "🎬 *HBO MAX — ATIVAÇÃO NA TV*\n\n📺 Abra o app HBO Max/Max na TV\n🔢 Digite o *código de 6 dígitos* que aparece na tela:\n\n_(Ex: 123456)_",
        "btn_netflix": "🔴 *NETFLIX — ATIVAÇÃO NA TV*\n\n📺 Abra o app Netflix na TV\n🔢 Digite o *código* que aparece na tela:\n\n_(Ex: TV-ABCD1 ou 123456)_",
        "btn_sky":     "📡 *SKY / DTV — ATIVAÇÃO NA TV*\n\n📺 Abra o app SKY+ ou DTV Go na TV\n🔢 Digite o *código de 6 dígitos* que aparece na tela:\n\n_(Ex: 654321)_",
        "btn_claro":   "🔵 *CLARO TV+ — ATIVAÇÃO NA TV*\n\n📺 Abra o app Claro TV+ na TV\n🔢 Digite o *código* que aparece na tela:\n\n_(Ex: 123456)_",
    }

    servico = mapa_servico.get(query.data)
    texto   = mapa_texto.get(query.data)

    if servico and texto:
        with AGUARDANDO_LOCK:
            AGUARDANDO_CODIGO[user_id] = servico
        await query.message.reply_text(texto, parse_mode="Markdown")


async def handle_mensagem(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Recebe o código enviado pelo usuário e faz a ativação."""
    if not checar_permissao(update):
        return

    user_id = update.effective_user.id
    texto   = update.message.text.strip() if update.message.text else ""
    nome    = update.effective_user.first_name or "Cliente"

    # Verificar se está aguardando código
    with AGUARDANDO_LOCK:
        servico = AGUARDANDO_CODIGO.get(user_id)

    if not servico:
        # Não está aguardando código — ignorar ou sugerir comando
        if any(c.isdigit() for c in texto) and len(texto) >= 4:
            await update.message.reply_text(
                "❓ Qual serviço você quer ativar?\n\n"
                "• /hbo — HBO Max\n"
                "• /netflix — Netflix\n"
                "• /sky — SKY\n"
                "• /claro — Claro TV+"
            )
        return

    # Remover estado
    with AGUARDANDO_LOCK:
        AGUARDANDO_CODIGO.pop(user_id, None)

    codigo = texto.upper().replace(" ", "")

    # Mensagem de processando
    icones = {"hbo": "🎬", "netflix": "🔴", "sky": "📡", "claro": "🔵"}
    icone  = icones.get(servico, "⚡")

    msg_proc = await update.message.reply_text(
        f"⏳ *Aguarde...*\n\n"
        f"{icone} Ativando *{servico.upper()}* na TV\n"
        f"🔢 Código: `{codigo}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 _Conectando com o servidor..._",
        parse_mode="Markdown"
    )

    # Executar ativação em thread separada (não bloqueia o bot)
    loop = asyncio.get_event_loop()

    funcoes = {
        "hbo":     ativar_hbo,
        "netflix": ativar_netflix,
        "sky":     ativar_sky,
        "claro":   ativar_claro,
    }

    func_ativar = funcoes.get(servico)
    if not func_ativar:
        await msg_proc.edit_text("❌ Serviço inválido.")
        return

    # Verifica se há vagas disponíveis (semáforo por serviço)
    lock_servico = ATIVACAO_LOCKS.get(servico)
    pode_ativar  = lock_servico.acquire(blocking=False) if lock_servico else True

    if not pode_ativar:
        await msg_proc.edit_text(
            f"⏳ *Sistema ocupado!*\n\n"
            f"Muitos clientes ativando ao mesmo tempo.\n"
            f"Aguarde *30 segundos* e tente novamente com /{servico}",
            parse_mode="Markdown"
        )
        return

    try:
        resultado = await loop.run_in_executor(None, func_ativar, codigo)
    finally:
        if lock_servico and pode_ativar:
            lock_servico.release()

    # Editar mensagem com resultado
    await msg_proc.edit_text(resultado["mensagem"], parse_mode="Markdown")

    # Log da ativação
    status = "✅ SUCESSO" if resultado["sucesso"] else "❌ FALHA"
    logger.info(f"[{status}] {nome} (ID:{user_id}) | Serviço: {servico.upper()} | Código: {codigo}")


# ══════════════════════════════════════════════════════════
# 🚀 INICIAR O BOT
# ══════════════════════════════════════════════════════════

def run_bot_threaded():
    """Inicia o bot do Telegram em uma thread separada sem bloquear o servidor web."""
    if not TELEGRAM_OK:
        print("[Telegram Bot] python-telegram-bot não instalado. Bot do Telegram não iniciado.", flush=True)
        return
    if not BOT_TOKEN or "COLOQUE_SEU_TOKEN" in BOT_TOKEN:
        print("[Telegram Bot] Token não configurado. Bot do Telegram não iniciado.", flush=True)
        return

    def _worker():
        try:
            print("[Telegram Bot] 🚀 Iniciando polling do Telegram...", flush=True)
            application = (
                Application.builder()
                .token(BOT_TOKEN)
                .build()
            )

            application.add_handler(CommandHandler("start",   cmd_start))
            application.add_handler(CommandHandler("hbo",     cmd_hbo))
            application.add_handler(CommandHandler("netflix", cmd_netflix))
            application.add_handler(CommandHandler("sky",     cmd_sky))
            application.add_handler(CommandHandler("claro",   cmd_claro))
            application.add_handler(CommandHandler("status",  cmd_status))
            application.add_handler(CallbackQueryHandler(handle_botoes))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensagem))

            print("[Telegram Bot] ✅ Bot do Telegram VIP conectado e pronto para receber mensagens na nuvem!", flush=True)
            application.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True, stop_signals=None)
        except Exception as e:
            print(f"[Telegram Bot] ❌ Erro no bot do Telegram: {e}", flush=True)

    t = threading.Thread(target=_worker, name="TelegramBotThread", daemon=True)
    t.start()
    return t

def main():
    if not TELEGRAM_OK:
        print("\n❌ ERRO: python-telegram-bot não está instalado!")
        print("   Execute: python -m pip install python-telegram-bot==20.7\n")
        sys.exit(1)

    if BOT_TOKEN == "COLOQUE_SEU_TOKEN_AQUI":
        print("\n❌ ERRO: Você precisa colocar o TOKEN do bot!")
        print("   Abra telegram_bot.py e substitua COLOQUE_SEU_TOKEN_AQUI pelo token real\n")
        sys.exit(1)

    print("\n" + "═" * 55)
    print("  🤖 BOT TELEGRAM - ATIVADOR VIP")
    print("  Serviços:", ", ".join(MODULES.keys()) or "Nenhum")
    print("═" * 55)

    app = Application.builder().token(BOT_TOKEN).build()

    # Registrar handlers
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("hbo",     cmd_hbo))
    app.add_handler(CommandHandler("netflix", cmd_netflix))
    app.add_handler(CommandHandler("sky",     cmd_sky))
    app.add_handler(CommandHandler("claro",   cmd_claro))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CallbackQueryHandler(handle_botoes))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mensagem))

    print("  ✅ Bot iniciado! Aguardando mensagens...")
    print("  💡 Pressione Ctrl+C para parar\n")

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
