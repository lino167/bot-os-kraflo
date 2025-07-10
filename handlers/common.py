from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Teclado do menu principal (sem alterações)
REPLY_KEYBOARD = [
    ["🆕 Abrir OS", "✅ Fechar OS"],
    ["📋 Listar Abertas", "📊 Relatórios"],
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
    
    # Se a função foi chamada por um botão (CallbackQuery)
    if query:
        # Responde ao callback para o ícone de "carregando" sumir no app do usuário
        await query.answer()
        # Edita a mensagem original do botão para confirmar o cancelamento
        await query.edit_message_text(text="Operação cancelada.")
        
    # Se a função foi chamada por um comando ou mensagem de texto
    else:
        await update.message.reply_text(
            "Operação cancelada.", reply_markup=MAIN_MENU_MARKUP
        )

    # Limpa os dados temporários da conversa, se houver
    if context.user_data:
        context.user_data.clear()
        
    # Finaliza o ConversationHandler
    return ConversationHandler.END
