import logging
import math
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.common import cancel
from database.utils import (
    get_editable_os_paginated, get_editable_os_count,
    update_os_field, get_single_os_details
)
from handlers.ui_components import (
    PRIORIDADE_KEYBOARD, TIPO_MANUTENCAO_KEYBOARD, STATUS_OS_KEYBOARD
)
from handlers.states import (
    PAGINATING_EDIT_OS, SELECT_FIELD, GET_NEW_VALUE_TEXT, GET_NEW_VALUE_BUTTON
)

logger = logging.getLogger(__name__)

OS_PER_PAGE = 5

ALL_EDITABLE_FIELDS = {
    "equipamento_nome": "Nome do Equipamento", "equipamento_tag": "TAG do Equipamento",
    "localizacao": "Localização", "tipo_manutencao": "Tipo de Manutenção",
    "prioridade": "Prioridade", "descricao_problema": "Descrição do Problema",
    "diagnostico_solucao": "Diagnóstico/Solução", "notas_finais": "Notas Finais",
    "status_os": "Status da OS",
}
FIELDS_FOR_OPEN_OS = [
    "equipamento_nome", "equipamento_tag", "localizacao",
    "tipo_manutencao", "prioridade", "descricao_problema"
]
FIELDS_WITH_BUTTONS = {
    "tipo_manutencao": TIPO_MANUTENCAO_KEYBOARD,
    "prioridade": PRIORIDADE_KEYBOARD,
    "status_os": STATUS_OS_KEYBOARD
}

async def start_edit_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de edição, mostrando a primeira página de OS editáveis."""
    user_id = update.effective_user.id
    total_os = await get_editable_os_count(user_id)
    if total_os == 0:
        await update.message.reply_text("Você não possui Ordens de Serviço abertas ou que foram fechadas nas últimas 24 horas para editar.")
        return ConversationHandler.END
    
    context.user_data['edit_total_os'] = total_os
    context.user_data['edit_current_page'] = 0
    
    await display_editable_os_page(update, context)
    return PAGINATING_EDIT_OS

async def display_editable_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe uma página de OS editáveis com botões de navegação."""
    user_id = update.effective_user.id
    current_page = context.user_data.get('edit_current_page', 0)
    total_os = context.user_data.get('edit_total_os', 0)
    total_pages = math.ceil(total_os / OS_PER_PAGE)

    os_list = await get_editable_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
    
    message = f"✏️ **Editar Ordem de Serviço (Página {current_page + 1} de {total_pages})**\n\nSelecione a OS que deseja modificar:"
    
    keyboard = []
    if os_list:
        for os in os_list:
            keyboard.append([InlineKeyboardButton(f"#{os['id']} - {os['equipamento_nome']} ({os['status_os']})", callback_data=f"edit_select_os_{os['id']}")])
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"edit_nav_prev_{current_page - 1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"edit_nav_next_{current_page + 1}"))
    if nav_buttons: keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("❌ Cancelar Edição", callback_data="edit_cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_markdown(message, reply_markup=reply_markup)

async def navigate_editable_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa os cliques nos botões de navegação da lista de edição."""
    query = update.callback_query
    await query.answer()
    
    _, _, page_str = query.data.split('_')
    context.user_data['edit_current_page'] = int(page_str)
    await display_editable_os_page(update, context)
    return PAGINATING_EDIT_OS

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra os campos editáveis para a OS selecionada, aplicando as regras de negócio."""
    query = update.callback_query
    os_id = context.user_data.get('os_id_to_edit')

    if query:
        await query.answer()
        if query.data.startswith("edit_select_os_"):
            os_id = int(query.data.split('_')[-1])
            context.user_data['os_id_to_edit'] = os_id

    os_details = await get_single_os_details(os_id)
    if not os_details:
        error_message = "Não foi possível encontrar os detalhes desta OS."
        if query: await query.edit_message_text(error_message)
        else: await update.message.reply_text(error_message)
        return await cancel(update, context)
        
    context.user_data['os_details'] = os_details

    status = os_details.get('status_os')
    
    allowed_fields = {}
    if status == 'Aberta':
        for key in FIELDS_FOR_OPEN_OS:
            allowed_fields[key] = ALL_EDITABLE_FIELDS[key]
    else:
        for key, value in ALL_EDITABLE_FIELDS.items():
            if key != 'status_os':
                allowed_fields[key] = value

    keyboard = []
    for field_key, field_name in allowed_fields.items():
        keyboard.append([InlineKeyboardButton(field_name, callback_data=f"edit_field_{field_key}")])
    keyboard.append([InlineKeyboardButton("✅ Concluir Edição", callback_data="edit_finish")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    details_text = (
        f"**Editando OS #{os_id}**\n"
        f"**Equipamento:** {os_details.get('equipamento_nome', 'N/A')}\n"
        f"**Status Atual:** {status}\n\n"
        "Selecione o campo que deseja alterar:"
    )
    
    if query:
        await query.edit_message_text(details_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_markdown(details_text, reply_markup=reply_markup)
        
    return SELECT_FIELD

async def prompt_for_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    _, _, field_key = query.data.partition('edit_field_')
    context.user_data['field_to_edit'] = field_key
    
    field_name = ALL_EDITABLE_FIELDS.get(field_key, "Desconhecido")
    current_value = context.user_data.get('os_details', {}).get(field_key, 'não preenchido')
    
    prompt_message = (
        f"A editar: **{field_name}**\n"
        f"Valor atual: `{current_value}`\n\n"
    )

    if field_key in FIELDS_WITH_BUTTONS:
        keyboard = FIELDS_WITH_BUTTONS[field_key].copy()
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            prompt_message + "Selecione o novo valor:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return GET_NEW_VALUE_BUTTON
    else:
        await query.edit_message_text(
            prompt_message + "Por favor, envie o novo valor:",
            parse_mode='Markdown'
        )
        return GET_NEW_VALUE_TEXT

async def update_field_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    new_value = query.data
    os_id = context.user_data['os_id_to_edit']
    field_key = context.user_data['field_to_edit']

    await query.edit_message_text("Atualizando campo, aguarde...")
    success = await update_os_field(os_id, field_key, new_value)
    
    if success:
        await query.edit_message_text("✅ Campo atualizado com sucesso!")
    else:
        await query.edit_message_text("❌ Erro ao atualizar o campo.")
        
    await asyncio.sleep(1.5)
    return await show_edit_menu(update, context)

async def update_field_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    os_id = context.user_data['os_id_to_edit']
    field_key = context.user_data['field_to_edit']
    
    last_message = await update.message.reply_text("Processando...")
    
    success = await update_os_field(os_id, field_key, new_value)
    
    if success:
        await last_message.edit_text("✅ Campo atualizado com sucesso!")
    else:
        await last_message.edit_text("❌ Erro ao atualizar o campo.")
    
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)

    await asyncio.sleep(1.5)
    return await show_edit_menu(update, context)

async def finish_editing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="✅ Edição concluída com sucesso!",
        reply_markup=None 
    )
    if context.user_data:
        context.user_data.clear()
        
    return ConversationHandler.END
