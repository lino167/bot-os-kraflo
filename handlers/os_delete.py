import logging
import pandas as pd
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database.utils import get_all_os_for_report, delete_os_by_id
from handlers.calendar_helper import create_calendar
from handlers.common import cancel

logger = logging.getLogger(__name__)

# Estados da conversa
SELECT_OS_TO_DELETE, CONFIRM_DELETE = range(60, 62)

async def start_delete_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de deleção pedindo uma data."""
    await update.message.reply_text(
        "🗑️ **Deletar Ordem de Serviço**\n\n"
        "Selecione a DATA para listar as OS que você deseja deletar. "
        "Apenas OS da data selecionada serão mostradas.",
        reply_markup=create_calendar()
    )
    return SELECT_OS_TO_DELETE

async def list_os_for_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lista as OS da data selecionada para o usuário escolher qual deletar."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    action = parts[0]

    if action != "calendar":
        return SELECT_OS_TO_DELETE

    prefix = parts[1]
    if prefix == "day":
        date_value = parts[2]
        user_id = update.effective_user.id
        start_date = pd.to_datetime(date_value).strftime("%Y-%m-%d 00:00:00")
        end_date = pd.to_datetime(date_value).strftime("%Y-%m-%d 23:59:59")

        await query.edit_message_text("Buscando Ordens de Serviço na data selecionada...")
        os_list = await get_all_os_for_report(user_id, start_date, end_date)

        if not os_list:
            await query.edit_message_text("Nenhuma OS encontrada para esta data.")
            return ConversationHandler.END

        keyboard = []
        for os in os_list:
            keyboard.append([InlineKeyboardButton(
                f"#{os['id']} - {os['equipamento_nome']} ({os['status_os']})", 
                callback_data=f"delete_os_{os['id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="delete_cancel")])
        
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
        return SELECT_OS_TO_DELETE
    
    return SELECT_OS_TO_DELETE


async def confirm_and_delete_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma e executa a deleção da OS selecionada."""
    query = update.callback_query
    await query.answer()

    if query.data == "delete_cancel":
        await query.edit_message_text("Operação cancelada.")
        return ConversationHandler.END

    os_id = int(query.data.split('_')[-1])
    
    await query.edit_message_text(f"Deletando OS #{os_id}, por favor aguarde...")
    success = await delete_os_by_id(os_id)

    if success:
        await query.edit_message_text(f"✅ Ordem de Serviço #{os_id} foi deletada com sucesso.")
    else:
        await query.edit_message_text(f"❌ Ocorreu um erro ao tentar deletar a OS #{os_id}.")
    
    return ConversationHandler.END
