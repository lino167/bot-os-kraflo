import logging
import math
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.states import PAGINATING_OS, PAGINATING_CLOSED_OS
from handlers.ui_components import MAIN_MENU_MARKUP
from database.utils import (
    get_open_os_paginated, get_open_os_count, 
    get_closed_os_paginated, get_closed_os_count
)

logger = logging.getLogger(__name__)

OS_PER_PAGE = 5

# --- FLUXO DE LISTAGEM PAGINADA DE OS ---

async def display_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE, list_type: str):
    user_id = update.effective_user.id
    is_open_list = list_type == "open"
    page_key = 'current_page' if is_open_list else 'current_closed_page'
    total_key = 'total_os' if is_open_list else 'total_closed_os'
    
    current_page = context.user_data.get(page_key, 0)
    total_os = context.user_data.get(total_key, 0)
    total_pages = math.ceil(total_os / OS_PER_PAGE)
    
    message = ""
    os_list = []

    if is_open_list:
        os_list = await get_open_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
        message = f"📋 **Suas Ordens de Serviço Abertas (Página {current_page + 1} de {total_pages}):**\n\n"
        if os_list:
            for os in os_list:
                message += (f"🔹 **OS #{os['id']}**\n   - **Equipamento:** {os['equipamento_nome']} ({os['equipamento_tag']})\n   - **Tipo:** {os['tipo_manutencao']}\n   - **Prioridade:** {os['prioridade']}\n--------------------\n")
    else: # list_type == "closed"
        os_list = await get_closed_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
        message = f"🗂️ **Seu Histórico de OS (Página {current_page + 1} de {total_pages}):**\n\n"
        if os_list:
            for os in os_list:
                data_fechamento_str = pd.to_datetime(os['data_fechamento']).strftime('%d/%m/%Y') if os.get('data_fechamento') else "N/A"
                message += (f"🔹 **OS #{os['id']}**\n   - **Equipamento:** {os['equipamento_nome']}\n   - **Status:** {os['status_os']}\n   - **Data:** {data_fechamento_str}\n--------------------\n")
    
    if not os_list:
        message += "Nenhuma OS para exibir nesta página."

    keyboard = []
    nav_buttons = []
    callback_prefix = "list_open" if is_open_list else "list_closed"
    
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{callback_prefix}_prev_{current_page - 1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"{callback_prefix}_next_{current_page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([InlineKeyboardButton("❌ Fechar Lista", callback_data=f"{callback_prefix}_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_markdown(message, reply_markup=reply_markup)

async def start_list_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    total_os = await get_open_os_count(user_id)
    if total_os == 0:
        await update.message.reply_text("Você não possui nenhuma Ordem de Serviço aberta.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    context.user_data['total_os'] = total_os
    context.user_data['current_page'] = 0
    await display_os_page(update, context, "open")
    return PAGINATING_OS

async def navigate_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        _, _, page_str = query.data.split('_')
        page = int(page_str)
        context.user_data['current_page'] = page
        await display_os_page(update, context, "open")
        return PAGINATING_OS
    except ValueError:
        await query.edit_message_text("Ocorreu um erro na navegação. Tente novamente.")
        return ConversationHandler.END

async def start_list_closed_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    total_os = await get_closed_os_count(user_id)
    if total_os == 0:
        await update.message.reply_text("Você não possui histórico de Ordens de Serviço fechadas nas últimas 24 horas.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    context.user_data['total_closed_os'] = total_os
    context.user_data['current_closed_page'] = 0
    await display_os_page(update, context, "closed")
    return PAGINATING_CLOSED_OS

async def navigate_closed_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        _, _, page_str = query.data.split('_')
        page = int(page_str)
        context.user_data['current_closed_page'] = page
        await display_os_page(update, context, "closed")
        return PAGINATING_CLOSED_OS
    except ValueError:
        await query.edit_message_text("Ocorreu um erro na navegação. Tente novamente.")
        return ConversationHandler.END

async def cancel_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Visualização da lista encerrada.")
    return ConversationHandler.END
