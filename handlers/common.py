from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Teclado do menu principal atualizado com a nova opção
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "🗂️ Listar Fechadas"],
    ["📊 Relatórios"],
]
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia a mensagem de boas-vindas e o menu principal."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá, {user.mention_html()}! Bem-vindo ao Bot de OS da Kraflo.",
        reply_markup=MAIN_MENU_MARKUP,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a operação atual de forma universal, lidando com
    mensagens de texto e callbacks de botões.
    """
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.edit_message_text(text="Operação cancelada.")
    else:
        await update.message.reply_text(
            "Operação cancelada.", reply_markup=MAIN_MENU_MARKUP
        )

    if context.user_data:
        context.user_data.clear()
        
    return ConversationHandler.END