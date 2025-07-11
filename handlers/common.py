from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos módulos
from database.utils import is_user_registered
from handlers.registration import ask_company_name
from handlers.ui_components import MAIN_MENU_MARKUP # <<< MUDANÇA AQUI

# O ReplyKeyboardMarkup foi movido para ui_components.py

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Ponto de entrada principal do bot.
    Verifica se o usuário está cadastrado. Se estiver, mostra o menu.
    Se não, inicia o fluxo de cadastro.
    """
    user_id = update.effective_user.id
    if await is_user_registered(user_id):
        await update.message.reply_html(
            f"Olá, {update.effective_user.mention_html()}! Bem-vindo de volta.",
            reply_markup=MAIN_MENU_MARKUP,
        )
        return ConversationHandler.END
    else:
        return await ask_company_name(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a operação atual de forma universal."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text="Operação cancelada.")
    else:
        await update.message.reply_text("Operação cancelada.", reply_markup=MAIN_MENU_MARKUP)
    if context.user_data:
        context.user_data.clear()
    return ConversationHandler.END