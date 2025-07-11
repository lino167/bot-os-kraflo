from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos módulos
from handlers.registration import ask_company_name
from handlers.ui_components import MAIN_MENU_MARKUP 
from database.utils import is_user_registered, get_user_data

# O ReplyKeyboardMarkup foi movido para ui_components.py

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Ponto de entrada principal do bot.
    Verifica se o usuário está cadastrado. Se estiver, mostra o menu com o nome do banco de dados.
    Se não, inicia o fluxo de cadastro.
    """
    user = update.effective_user
    if await is_user_registered(user.id):
        user_data = await get_user_data(user.id)
        
        user_name = user.mention_html() 
        
        if user_data and user_data.get('nome_completo'):
            user_name = user_data['nome_completo']

        await update.message.reply_html(
            f"Olá, {user_name}! Bem-vindo de volta.",
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