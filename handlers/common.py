import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos módulos do projeto
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
        # Garante que um novo fluxo de cadastro comece com um histórico limpo
        context.user_data.pop('state_history', None)
        return await ask_company_name(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela a operação atual de forma universal. Limpa os dados da conversa,
    notifica o usuário e exibe o menu principal.
    """
    query = update.callback_query
    message_text = "Operação cancelada."
    
    # Se a função foi chamada por um clique de botão, edita a mensagem original.
    if query:
        await query.answer()
        try:
            await query.edit_message_text(text=message_text)
        except Exception as e:
            # Loga o erro se a mensagem não puder ser editada (ex: já foi removida)
            logger.info(f"Não foi possível editar a mensagem ao cancelar: {e}")

    # Envia uma nova mensagem com o menu principal para garantir que o usuário não fique "preso"
    # sem o teclado principal.
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Você está no menu principal.",
        reply_markup=MAIN_MENU_MARKUP
    )
    
    # Limpa todos os dados da conversa para evitar estados inconsistentes em futuros fluxos.
    context.user_data.clear()
    return ConversationHandler.END

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Retorna ao passo anterior da conversa.
    Utiliza um histórico de estados (state_history) e um mapa de estados para funções (state_map).
    """
    query = update.callback_query
    await query.answer()
    
    state_history = context.user_data.get('state_history', [])
    
    # Remove o estado atual do histórico para revelar o passo anterior.
    if state_history:
        state_history.pop() 
    
    # Se o histórico ficar vazio, não há para onde voltar, então cancela a operação.
    if not state_history:
        await query.edit_message_text("Não há para onde voltar. A operação será cancelada.")
        return await cancel(update, context)
        
    # Pega o novo último estado do histórico, que é para onde queremos voltar.
    previous_state = state_history[-1]
    
    # Busca o mapa de "estado -> função" que foi configurado no main.py
    state_map = context.application.bot_data.get('state_map', {})
    handler_function = state_map.get(previous_state)
    
    if handler_function:
        # Chama a função correspondente ao estado anterior, passando is_back=True
        # para que ela saiba que deve apenas re-renderizar a pergunta, sem processar novos dados.
        return await handler_function(update, context, is_back=True)
    else:
        # Fallback de segurança caso o estado não seja encontrado no mapa.
        logger.warning(f"Função não encontrada no state_map para o estado: {previous_state}")
        await query.edit_message_text("Ocorreu um erro ao tentar voltar. A operação será cancelada.")
        return await cancel(update, context)
