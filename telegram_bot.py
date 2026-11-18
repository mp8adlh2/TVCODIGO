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
                    f"║  ✨  *HBO MAX ATIVADO!*  ✨ ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código Pareado:* `{codigo}`\n"
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
    """Ativa SKY/DTV na TV usando sky_service com rotação e tentativas automáticas até dar certo."""
    try:
        mod = MODULES.get("sky")
        if not mod:
            return {"sucesso": False, "mensagem": "❌ Módulo SKY não disponível no momento."}

        find_func = getattr(mod, "find_sky_valid_account", None)
        activate_func = getattr(mod, "activate_sky_tv", None)
        if not find_func or not activate_func:
            return {"sucesso": False, "mensagem": "❌ Funções de ativação SKY não encontradas."}

        # Tenta até 6 contas disponíveis no estoque até conseguir
        max_tentativas = 6
        ultimo_motivo = ""

        for tentativa in range(1, max_tentativas + 1):
            account_data = find_func()
            if not account_data:
                break

            email = account_data.get("email", "")
            logger.info(f"[SKY] Tentando conta {tentativa}/{max_tentativas}: {email} para código {codigo}...")

            resultado = activate_func(tv_code=codigo, account_data=account_data, use_proxy=True)

            if isinstance(resultado, tuple):
                success = resultado[0]
                msg     = resultado[1] if len(resultado) > 1 else ""
                info    = resultado[2] if len(resultado) > 2 else {}
            else:
                success = bool(resultado)
                msg     = ""
                info    = {}

            # Se o código expirou na tela da TV, não adianta tentar outras contas
            if any(k in msg.lower() for k in ["expirad", "inválid", "não encontrado", "user_code_expired", "dtv-oidc-013"]):
                return {
                    "sucesso": False,
                    "mensagem": (
                        f"⏳ *Código da TV Expirado ou Inválido!*\n\n"
                        f"O código `{codigo}` não foi aceito pela SKY.\n"
                        f"💡 Gere um novo código na sua TV e envie novamente com /sky"
                    )
                }

            if success:
                plano = ""
                if isinstance(info, dict):
                    plano = info.get("plan", info.get("plano", ""))

                linha_plano = f"💎 Plano: {plano}\n" if plano else ""
                return {
                    "sucesso": True,
                    "mensagem": (
                        f"╔═══════════════════════════╗\n"
                        f"║  ✅  *SKY / DTV ATIVADO!*  ║\n"
                        f"╚═══════════════════════════╝\n\n"
                        f"📺 *Código:* `{codigo}`\n"
                        f"{linha_plano}"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📡 *Aproveite o SKY na sua TV!* 🍿"
                    )
                }
            else:
                ultimo_motivo = msg
                # Continua o loop para a próxima conta do estoque

        return {
            "sucesso": False,
            "mensagem": (
                f"❌ *Não foi possível ativar na SKY no momento.*\n\n"
                f"💡 Verifique se o código `{codigo}` ainda está na tela da sua TV e tente novamente em instantes."
            )
        }

    except Exception as e:
        logger.error(f"Erro ao ativar SKY: {e}")
        return {"sucesso": False, "mensagem": f"❌ Ocorreu uma instabilidade temporária. Tente novamente em instantes."}

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
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✨  *NETFLIX ATIVADO!*  ✨ ║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código Pareado:* `{codigo}`\n"
                    f"💎 *Plano:* {plano}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 *Aproveite a Netflix na TV!* 🍿"
                )
            }
        else:
            msg_amigavel = msg or "Falha na ativação"
            return {"sucesso": False, "mensagem": f"❌ *Falha na ativação Netflix*\n\nNão foi possível parear a TV com o código informado.\n\n💡 Tente novamente com /netflix"}

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
            return {
                "sucesso": True,
                "mensagem": (
                    f"╔═══════════════════════════╗\n"
                    f"║  ✨  *CLARO TV+ ATIVADO!* ✨║\n"
                    f"╚═══════════════════════════╝\n\n"
                    f"📺 *Código Pareado:* `{codigo}`\n"
                    f"💎 *Plano:* {plano}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔵 *Aproveite a Claro TV+ na sua TV!* 🍿"
                )
            }
        else:
            return {"sucesso": False, "mensagem": f"❌ *Falha na ativação Claro TV+*\n\nNão foi possível parear a TV com o código informado.\n\n💡 Tente novamente com /claro"}

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
    """
    Bloqueia uso no privado (PV).
    O bot só pode ser usado dentro de grupos ou supergrupos.
    Se ALLOWED_GROUP_IDS estiver configurado, só permite o grupo VIP específico.
    """
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False

    chat_type = chat.type  # 'private', 'group', 'supergroup', 'channel'
    user_id = user.id
    chat_id = chat.id

    # Se for mensagem no privado (PV)
    if chat_type == "private":
        # Se for administrador, libera para testes
        if ADMIN_IDS and user_id in ADMIN_IDS:
            return True
        return False

    # Se estiver em grupo/supergrupo:
    # Se configurou IDs específicos de grupo, valida se é um deles
    if ALLOWED_GROUP_IDS:
        return chat_id in ALLOWED_GROUP_IDS

    # Se ALLOWED_GROUP_IDS estiver vazio, permite qualquer grupo, mas BLOQUEIA privado
    return True


async def cmd_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Comando /start"""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    # Se mandar /start no privado
    if chat.type == "private" and (not ADMIN_IDS or user.id not in ADMIN_IDS):
        await update.message.reply_text(
            "🔒 *Acesso Exclusivo para o Grupo VIP!*\n\n"
            "Olá! Este robô de ativação automática funciona exclusivamente dentro do nosso *Grupo VIP*.\n\n"
            "👉 Por favor, envie os comandos e códigos diretamente lá no grupo!",
            parse_mode="Markdown"
        )
        return

    if not checar_permissao(update):
        return

    nome = update.effective_user.first_name or "Cliente"

    servicos_disponiveis = []
    if "hbo" in MODULES:
        servicos_disponiveis.append("🎬 HBO Max / Max")
    if "netflix" in MODULES:
        servicos_disponiveis.append("🔴 Netflix")
    if "sky" in MODULES:
        servicos_disponiveis.append("📡 SKY / DTV")
    if "claro" in MODULES:
        servicos_disponiveis.append("🔵 Claro TV+")

    lista_str = "\n".join(servicos_disponiveis) if servicos_disponiveis else "Nenhum serviço disponível"

    texto = (
        "╔═══════════════════════════╗\n"
        "║  ✨  *SISTEMA ATIVADOR VIP* ✨  ║\n"
        "╚═══════════════════════════╝\n\n"
        f"👋 Olá, *{nome}*! Seja bem-vindo ao ativador oficial!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📺 *SERVIÇOS DISPONÍVEIS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{lista_str}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *PASSO A PASSO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ Abra o aplicativo na sua Smart TV\n"
        "2️⃣ Anote o código de ativação na tela\n"
        "3️⃣ Clique no botão do serviço abaixo\n"
        "4️⃣ Digite o código aqui no chat → Ativado! ✅\n\n"
        "⚡ *Selecione o serviço para ativar agora:*"
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
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=reply_markup)


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
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    # Se alguém tentar mandar mensagem no PV/Privado do bot
    if chat.type == "private" and (not ADMIN_IDS or user.id not in ADMIN_IDS):
        await update.message.reply_text(
            "⛔ *Acesso Restrito!*\n\n"
            "Este bot não realiza ativações no privado.\n"
            "👉 Utilize os comandos diretamente no nosso *Grupo VIP*!",
            parse_mode="Markdown"
        )
        return

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
    """Inicia o bot do Telegram em processo independente usando subprocess para evitar conflitos de thread/asyncio."""
    if not BOT_TOKEN or "COLOQUE_SEU_TOKEN" in BOT_TOKEN:
        print("[Telegram Bot] Token não configurado. Bot do Telegram não iniciado.", flush=True)
        return

    import subprocess
    cmd = [sys.executable, os.path.join(BASE_DIR, "telegram_bot.py")]
    print(f"[Telegram Bot] 🚀 Iniciando processo dedicado do Bot Telegram na nuvem: {' '.join(cmd)}", flush=True)
    try:
        proc = subprocess.Popen(cmd, cwd=BASE_DIR)
        print(f"[Telegram Bot] ✅ Processo do Bot iniciado com sucesso (PID: {proc.pid})!", flush=True)
        return proc
    except Exception as e:
        print(f"[Telegram Bot] ❌ Falha ao iniciar processo do Bot: {e}", flush=True)

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
