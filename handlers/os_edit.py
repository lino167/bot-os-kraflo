import logging
import math
import pandas as pd
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.common import cancel
from database.utils import (
    get_all_user_os_paginated, get_all_user_os_count, 
    update_os_field, get_single_os_details
)

logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa ---
SELECT_OS, SELECT_FIELD, GET_NEW_VALUE, PAGINATING_EDIT_OS = range(50, 54)
OS_PER_PAGE = 5

# Mapeamento dos campos editáveis para nomes amigáveis
EDITABLE_FIELDS = {
    "equipamento_nome": "Nome do Equipamento",
    "equipamento_tag": "TAG do Equipamento",
    "localizacao": "Localização",
    "tipo_manutencao": "Tipo de Manutenção",
    "prioridade": "Prioridade",
    "descricao_problema": "Descrição do Problema",
    "diagnostico_solucao": "Diagnóstico/Solução",
    "notas_finais": "Notas Finais",
    "status_os": "Status da OS",
}

async def start_edit_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de edição, mostrando a primeira página de OS."""
    user_id = update.effective_user.id
    total_os = await get_all_user_os_count(user_id)
    if total_os == 0:
        await update.message.reply_text("Você ainda não possui nenhuma Ordem de Serviço para editar.")
        return ConversationHandler.END
    
    context.user_data['edit_total_os'] = total_os
    context.user_data['edit_current_page'] = 0
    
    await display_editable_os_page(update, context)
    return PAGINATING_EDIT_OS

async def display_editable_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe uma página de OS editáveis com botões de navegação."""
    user_id = update.effective_user.id
    current_page = context.user_data['edit_current_page']
    total_os = context.user_data['edit_total_os']
    total_pages = math.ceil(total_os / OS_PER_PAGE)

    os_list = await get_all_user_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
    
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
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_html(message, reply_markup=reply_markup)

async def navigate_editable_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processa os cliques nos botões de navegação da lista de edição."""
    query = update.callback_query
    await query.answer()
    
    _, _, page_str = query.data.split('_')
    context.user_data['edit_current_page'] = int(page_str)
    await display_editable_os_page(update, context)
    return PAGINATING_EDIT_OS

async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostra os campos editáveis para a OS selecionada, após validar as regras de negócio."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("edit_select_os_"):
        await query.edit_message_text("Ação inválida.")
        return await cancel(update, context)

    os_id = int(query.data.split('_')[-1])
    context.user_data['os_id_to_edit'] = os_id

    os_details = await get_single_os_details(os_id)
    if not os_details:
        await query.edit_message_text("Não foi possível encontrar os detalhes desta OS.")
        return await cancel(update, context)
        
    context.user_data['os_details'] = os_details

    # --- REGRA DE NEGÓCIO: SÓ PODE EDITAR OS FECHADA NO MESMO DIA ---
    status = os_details.get('status_os')
    data_fechamento = os_details.get('data_fechamento')

    if status != 'Aberta' and data_fechamento:
        data_fechamento_date = pd.to_datetime(data_fechamento).date()
        if data_fechamento_date != date.today():
            await query.edit_message_text(
                f"🚫 **Acesso Negado**\n\nA Ordem de Serviço #{os_id} foi fechada em {data_fechamento_date.strftime('%d/%m/%Y')} "
                f"e só podia ser editada nesse mesmo dia."
            )
            return ConversationHandler.END
    # --- FIM DA REGRA ---

    keyboard = []
    for field_key, field_name in EDITABLE_FIELDS.items():
        keyboard.append([InlineKeyboardButton(field_name, callback_data=f"edit_field_{field_key}")])
    keyboard.append([InlineKeyboardButton("✅ Concluir Edição", callback_data="edit_finish")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    details_text = (
        f"**Editando OS #{os_id}**\n"
        f"**Equipamento:** {os_details.get('equipamento_nome', 'N/A')}\n"
        f"**Status Atual:** {os_details.get('status_os', 'N/A')}\n\n"
        "Selecione o campo que deseja alterar:"
    )
    await query.edit_message_text(details_text, reply_markup=reply_markup, parse_mode='Markdown')
    return SELECT_FIELD

async def prompt_for_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao usuário o novo valor para o campo selecionado."""
    query = update.callback_query
    await query.answer()

    field_key = query.data.split('_')[-1]
    field_name = EDITABLE_FIELDS.get(field_key, "Desconhecido")
    
    context.user_data['field_to_edit'] = field_key
    
    current_value = context.user_data.get('os_details', {}).get(field_key, 'não preenchido')
    
    await query.edit_message_text(f"A editar: **{field_name}**\nValor atual: `{current_value}`\n\nPor favor, envie o novo valor:", parse_mode='Markdown')
    return GET_NEW_VALUE

async def update_field_and_return_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Atualiza o campo no banco de dados e volta para o menu de edição."""
    new_value = update.message.text
    os_id = context.user_data['os_id_to_edit']
    field_key = context.user_data['field_to_edit']
    
    await update.message.reply_text("A atualizar informação, aguarde...")
    success = await update_os_field(os_id, field_key, new_value)
    
    if success:
        await update.message.reply_text("✅ Campo atualizado com sucesso!")
        context.user_data.pop('os_details', None) 
    else:
        await update.message.reply_text("❌ Erro ao atualizar o campo.")
        
    class MockQuery:
        def __init__(self, msg, data):
            self.message = msg
            self.data = data
        async def answer(self): pass

    mock_query_update = Update(update.update_id, message=update.message)
    mock_query_update.callback_query = MockQuery(update.message, f"edit_select_os_{os_id}")

    return await show_edit_menu(mock_query_update, context)