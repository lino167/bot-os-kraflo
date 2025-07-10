from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# --- Teclado do Menu Principal ---
# Define os botões que aparecerão para o usuário.
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "📊 Relatórios"],
]

# Cria o objeto de markup do teclado para ser reutilizado
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(
    REPLY_KEYBOARD, 
    resize_keyboard=True, 
    one_time_keyboard=False # O teclado não some após um clique
)

# --- Handlers Comuns ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /start. Envia uma mensagem de boas-vindas
    e exibe o menu principal.
    """
    user = update.effective_user
    await update.message.reply_html(
        f"Olá, {user.mention_html()}! Bem-vindo ao Bot de OS da Kraflo.",
        reply_markup=MAIN_MENU_MARKUP,
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a conversa atual, limpa os dados temporários do usuário
    e retorna ao menu principal.
    """
    await update.message.reply_text(
        "Operação cancelada.", reply_markup=MAIN_MENU_MARKUP
    )
    
    # Limpa qualquer dado que estivesse sendo coletado na conversa
    context.user_data.clear()
    
    # Finaliza o ConversationHandler
    return ConversationHandler.END
