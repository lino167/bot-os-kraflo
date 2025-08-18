import logging
import pandas as pd
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database.utils import get_os_by_status_and_date, delete_os_by_id
from handlers.calendar_helper import create_calendar
from handlers.common import cancel
from handlers.states import (
    CHOOSE_STATUS, SELECT_DATE, LIST_OS_FOR_DELETION, CONFIRM_DELETE
)

logger = logging.getLogger(__name__)


async def start_delete_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo perguntando o status da OS a ser deletada."""
    keyboard = [
        [InlineKeyboardButton("🔴 Abertas", callback_data="delete_status_Aberta")],
        [InlineKeyboardButton("✅ Fechadas/Pendentes", callback_data="delete_status_Fechada")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="delete_cancel_op")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🗑️ **Deletar Ordem de Serviço**\n\n"
        "Você deseja listar OS Abertas ou Fechadas para deletar?",
        reply_markup=reply_markup
    )
    return CHOOSE_STATUS

async def ask_for_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o status escolhido e pede a data."""
    query = update.callback_query
    await query.answer()

    if "cancel" in query.data:
        await query.edit_message_text("Operação cancelada.")
        return ConversationHandler.END

    status = query.data.split('_')[-1]
    context.user_data['delete_os_status'] = status
    
    await query.edit_message_text(
        f"Status selecionado: **{status}**.\n\n"
        "Agora, selecione a DATA para listar as OS:",
        reply_markup=create_calendar(),
        parse_mode='Markdown'
    )
    return SELECT_DATE

async def list_os_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lista as OS do status e data selecionados."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action, prefix = parts[0], parts[1]

    if action == "calendar" and prefix == "day":
        date_value = parts[2]
        user_id = update.effective_user.id
        status = context.user_data['delete_os_status']

        await query.edit_message_text(f"Buscando OS com status '{status}' na data selecionada...")
        os_list = await get_os_by_status_and_date(user_id, status, date_value)

        if not os_list:
            await query.edit_message_text("Nenhuma OS encontrada com esses critérios.")
            return ConversationHandler.END

        keyboard = []
        for os in os_list:
            keyboard.append([InlineKeyboardButton(
                f"#{os['id']} - {os['equipamento_nome']}", 
                callback_data=f"delete_confirm_{os['id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="delete_cancel_op")])
        
        await query.edit_message_text(
            f"Selecione a OS do dia {pd.to_datetime(date_value).strftime('%d/%m/%Y')} para deletar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM_DELETE
    
    elif prefix in ["prev", "next"]:
        year, month = map(int, parts[2].split('-'))
        await query.edit_message_text(
            "Selecione a DATA para listar as OS:",
            reply_markup=create_calendar(year, month)
        )
        return SELECT_DATE
    
    return SELECT_DATE

async def confirm_and_delete_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede a confirmação final antes de deletar."""
    query = update.callback_query
    await query.answer()

    if "cancel" in query.data:
        await query.edit_message_text("Operação cancelada.")
        return ConversationHandler.END

    os_id = int(query.data.split('_')[-1])
    context.user_data['os_id_to_delete'] = os_id

    keyboard = [
        [InlineKeyboardButton("🚨 SIM, DELETAR PERMANENTEMENTE", callback_data=f"delete_do_{os_id}")],
        [InlineKeyboardButton("Não, voltar", callback_data="delete_cancel_op")]
    ]
    await query.edit_message_text(
        f"⚠️ **ATENÇÃO!**\n\nVocê tem certeza que deseja deletar a OS #{os_id}?\n"
        "**Esta ação não pode ser desfeita.**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM_DELETE # Permanece no mesmo estado para aguardar a confirmação final

async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executa a deleção após a confirmação final."""
    query = update.callback_query
    await query.answer()

    os_id = int(query.data.split('_')[-1])
    
    await query.edit_message_text(f"Deletando OS #{os_id}, por favor aguarde...")
    success = await delete_os_by_id(os_id)

    if success:
        await query.edit_message_text(f"✅ Ordem de Serviço #{os_id} foi deletada com sucesso.")
    else:
        await query.edit_message_text(f"❌ Ocorreu um erro ao tentar deletar a OS #{os_id}.")
    
    context.user_data.clear()
    return ConversationHandler.END
