import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from handlers.registration import ask_company_name
from handlers.ui_components import MAIN_MENU_MARKUP 
from database.utils import is_user_registered, get_user_data

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Ponto de entrada principal do bot. Verifica o registro do usuário e direciona
    para o menu principal ou para o fluxo de cadastro.
    """
    user = update.effective_user
    if await is_user_registered(user.id):
        user_data = await get_user_data(user.id)
        user_name = user_data.get('nome_completo') if user_data else user.mention_html()
        await update.message.reply_html(
            f"Olá, {user_name}! Bem-vindo de volta.",
            reply_markup=MAIN_MENU_MARKUP,
        )
        return ConversationHandler.END
    else:
        context.user_data.pop('state_history', None)
        return await ask_company_name(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a operação atual de forma universal. Limpa os dados da conversa,
    notifica o usuário e exibe o menu principal.
    """
    query = update.callback_query
    message_text = "Operação cancelada."
    
    if query:
        await query.answer()
        try:
            await query.edit_message_text(text=message_text)
        except Exception as e:
            logger.info(f"Não foi possível editar a mensagem ao cancelar: {e}")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Você está no menu principal.",
        reply_markup=MAIN_MENU_MARKUP
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Retorna ao passo anterior da conversa.
    """
    query = update.callback_query
    await query.answer()
    
    state_history = context.user_data.get('state_history', [])
    
    if state_history:
        state_history.pop() 
    
    if not state_history:
        await query.edit_message_text("Não há para onde voltar. A operação será cancelada.")
        return await cancel(update, context)
        
    previous_state = state_history[-1]
    
    state_map = context.application.bot_data.get('state_map', {})
    handler_function = state_map.get(previous_state)
    
    if handler_function:
        return await handler_function(update, context, is_back=True)
    else:
        logger.warning(f"Função não encontrada no state_map para o estado: {previous_state}")
        await query.edit_message_text("Ocorreu um erro ao tentar voltar. A operação será cancelada.")
        return await cancel(update, context)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envia uma mensagem com informações sobre o projeto.
    """
    about_text = (
        "ℹ️ **Sobre o Kraflo OS Bot**\n\n"
        "Este bot foi desenvolvido como uma solução moderna e eficiente para otimizar o fluxo de trabalho de técnicos de manutenção no chão de fábrica.\n\n"
        "**Funcionalidades Principais:**\n"
        "- Gestão completa de Ordens de Serviço\n"
        "- Controlo de peças utilizadas\n"
        "- Upload de fotos e anexos\n"
        "- Geração de relatórios em PDF e CSV\n\n"
        "**Tecnologias:** Python, `python-telegram-bot`, Supabase (PostgreSQL).\n\n"
        "Criado por Zacarias Ramos."
    )
    await update.message.reply_text(about_text, reply_markup=MAIN_MENU_MARKUP, parse_mode='Markdown')

async def handle_invalid_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Lida com inputs de texto inesperados (ex: botões) quando o bot espera texto livre.
    Avisa o utilizador e mantém a conversa no estado atual.
    """
    state_history = context.user_data.get('state_history', [])
    
    if not state_history:
        return await cancel(update, context)

    current_state = state_history[-1]
    
    await update.message.reply_text(
        "⚠️ Ops! Parece que você clicou num botão, mas eu estava à espera que digitasse uma informação.\n\n"
        "Por favor, envie a informação que pedi em formato de texto. "
        "Se quiser sair, pode usar o botão '❌ Cancelar' abaixo."
    )
    
    return current_state
