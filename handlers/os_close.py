import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.states import (
    SELECT_OS_TO_CLOSE, ASK_SOLUTION, ASK_IF_PARTS, ASK_PART_NAME, ASK_PART_TAG, 
    ASK_PART_QTY, ASK_MORE_PARTS, ASK_FINAL_STATUS, ASK_IF_ATTACHMENT, 
    GET_ATTACHMENT, HANDLE_ATTACHMENT_UPLOAD_ERROR, ASK_IF_NOTES, GET_FINAL_NOTES
)
from config import supabase
from handlers.ui_components import MAIN_MENU_MARKUP, STATUS_OS_KEYBOARD
from database.utils import get_open_os_paginated, close_os_in_db

logger = logging.getLogger(__name__)

# --- Funções Auxiliares de Navegação (Específicas deste fluxo) ---

def add_nav_buttons(keyboard: list) -> list:
    """Adiciona botões de Voltar e Cancelar a um teclado."""
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="back"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_op")
    ])
    return keyboard

def push_state(context: ContextTypes.DEFAULT_TYPE, state: int):
    """Adiciona o estado atual ao histórico de navegação."""
    history = context.user_data.setdefault('state_history', [])
    if not history or history[-1] != state:
        history.append(state)

# --- FLUXO DE FECHAMENTO DE OS ---

async def start_close_os(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    context.user_data.clear()
    push_state(context, SELECT_OS_TO_CLOSE)
    user_id = update.effective_user.id
    open_os_list = await get_open_os_paginated(user_id, 0, 50) 
    if not open_os_list:
        await update.message.reply_text("Você não possui nenhuma Ordem de Serviço aberta.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"#{os['id']} - {os['equipamento_nome']} ({os['equipamento_tag']})", callback_data=f"close_{os['id']}")] for os in open_os_list]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_op")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "Selecione a Ordem de Serviço que deseja fechar:"
    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        
    return SELECT_OS_TO_CLOSE

async def ask_for_solution(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()

    if not is_back:
        push_state(context, ASK_SOLUTION)
        os_id = int(query.data.split('_')[1])
        context.user_data['os_id_to_close'] = os_id
    else:
        os_id = context.user_data['os_id_to_close']

    await query.edit_message_text(text=f"Fechando OS #{os_id}.\n\nDescreva o diagnóstico final e a solução aplicada.")
    return ASK_SOLUTION

async def get_solution_and_ask_parts(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_IF_PARTS)
        context.user_data['close_solution'] = update.message.text
        context.user_data['parts_list'] = []

    keyboard = [[InlineKeyboardButton("✅ Sim", callback_data="parts_yes")], [InlineKeyboardButton("❌ Não", callback_data="parts_no")]]
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(keyboard))
    await update.message.reply_text("Houve troca de peças nesta manutenção?", reply_markup=reply_markup)
    return ASK_IF_PARTS

async def ask_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()
    
    if not is_back:
        if query.data == 'parts_no':
            return await ask_for_final_status(update, context)
        push_state(context, ASK_PART_NAME)
    
    num_peca = len(context.user_data.get('parts_list', [])) + 1
    await query.edit_message_text(text=f"Ok, vamos adicionar as peças trocadas.\n\nPara a Peça {num_peca}, qual o nome dela?")
    return ASK_PART_NAME

async def get_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_PART_TAG)
        context.user_data['current_part_name'] = update.message.text
    await update.message.reply_text("Qual o TAG/Código (Part Number) dessa peça?")
    return ASK_PART_TAG

async def get_part_tag(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_PART_QTY)
        context.user_data['current_part_tag'] = update.message.text
    await update.message.reply_text("Qual a quantidade utilizada desta peça?")
    return ASK_PART_QTY

async def get_part_qty_and_ask_more(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        try:
            qty = int(update.message.text)
            part = {"nome_peca": context.user_data['current_part_name'], "tag_peca": context.user_data['current_part_tag'], "quantidade": qty}
            context.user_data['parts_list'].append(part)
        except (ValueError, KeyError):
            await update.message.reply_text("Entrada inválida. Por favor, digite apenas números para a quantidade.")
            return ASK_PART_QTY
        push_state(context, ASK_MORE_PARTS)
    
    part_name = context.user_data.get('parts_list', [{'nome_peca': ''}])[-1]['nome_peca']
    keyboard = [[InlineKeyboardButton("➕ Sim", callback_data="parts_yes")], [InlineKeyboardButton("👍 Não, continuar", callback_data="parts_no")]]
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(keyboard))
    await update.message.reply_text(f"✅ Peça '{part_name}' adicionada.\nDeseja adicionar outra peça?", reply_markup=reply_markup)
    return ASK_MORE_PARTS

async def ask_for_final_status(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()

    if not is_back:
        push_state(context, ASK_FINAL_STATUS)

    reply_markup = InlineKeyboardMarkup(add_nav_buttons(STATUS_OS_KEYBOARD.copy()))
    await query.edit_message_text(text="Entendido. Qual o status final desta Ordem de Serviço?", reply_markup=reply_markup)
    return ASK_FINAL_STATUS

async def get_final_status_and_ask_if_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()

    if not is_back:
        push_state(context, ASK_IF_ATTACHMENT)
        context.user_data['final_status'] = query.data

    keyboard = [[InlineKeyboardButton("📎 Sim, anexar", callback_data="attach_yes")], [InlineKeyboardButton("👍 Não, pular", callback_data="attach_no")]]
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(keyboard))
    await query.edit_message_text(text=f"Status definido como '{context.user_data['final_status']}'.\n\nDeseja anexar um arquivo (foto, PDF) ao fechamento?", reply_markup=reply_markup)
    return ASK_IF_ATTACHMENT

async def prompt_for_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()
    
    if not is_back:
        if query.data == 'attach_no':
            return await prompt_for_final_notes(update, context)
        push_state(context, GET_ATTACHMENT)
        
    await query.edit_message_text("Ok, por favor, envie o anexo agora.")
    return GET_ATTACHMENT

async def get_attachment_and_ask_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    attachment = update.message.document or update.message.photo[-1]
    file = await attachment.get_file()
    await update.message.reply_text("Recebi o anexo. Fazendo upload, aguarde...")
    try:
        file_bytearray = await file.download_as_bytearray()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = attachment.file_name if hasattr(attachment, 'file_name') else f"{timestamp}.jpg"
        file_path = f"{user.id}/fechamento_{timestamp}_{original_filename}"
        context.user_data['upload_data'] = {'bytes': bytes(file_bytearray), 'path': file_path}
        supabase.storage.from_("anexos-os").upload(file=context.user_data['upload_data']['bytes'], path=file_path)
        public_url = supabase.storage.from_("anexos-os").get_public_url(file_path)
        context.user_data.setdefault('close_data', {})['url_arquivo_fechamento'] = public_url
        logger.info(f"Anexo de fechamento salvo em: {public_url}")
    except Exception as e:
        logger.error(f"Erro no upload do anexo de fechamento: {e}")
        keyboard = [
            [InlineKeyboardButton("Tentar novamente", callback_data="upload_attach_retry")],
            [InlineKeyboardButton("Continuar sem anexo", callback_data="upload_attach_skip")]
        ]
        await update.message.reply_text(
            "Desculpe, ocorreu um erro ao salvar seu anexo. Deseja tentar novamente?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return HANDLE_ATTACHMENT_UPLOAD_ERROR
    return await prompt_for_final_notes(update, context)

async def handle_invalid_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Isso não é um anexo válido. Por favor, envie uma foto ou documento, ou use o botão '❌ Cancelar'."
    )
    return GET_ATTACHMENT

async def handle_attachment_upload_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "upload_attach_retry":
        await query.edit_message_text("Tentando o upload novamente...")
        try:
            upload_data = context.user_data['upload_data']
            supabase.storage.from_("anexos-os").upload(file=upload_data['bytes'], path=upload_data['path'])
            public_url = supabase.storage.from_("anexos-os").get_public_url(upload_data['path'])
            context.user_data.setdefault('close_data', {})['url_arquivo_fechamento'] = public_url
            return await prompt_for_final_notes(update, context)
        except Exception as e:
            logger.error(f"Segunda tentativa de upload de anexo falhou: {e}")
            await query.edit_message_text("A segunda tentativa também falhou. Continuando sem o anexo.")
            return await prompt_for_final_notes(update, context)
    else: # upload_attach_skip
        await query.edit_message_text("Ok, continuando o fechamento sem o anexo.")
        return await prompt_for_final_notes(update, context)

async def prompt_for_final_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("✍️ Sim, adicionar", callback_data="notes_yes")],
        [InlineKeyboardButton("👍 Não, finalizar", callback_data="notes_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "Deseja adicionar notas finais, observações ou recomendações?"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup)
        
    return ASK_IF_NOTES

async def get_final_notes_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query and update.callback_query.data == 'notes_yes':
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text="Ok. Por favor, digite as notas finais agora.")
        return GET_FINAL_NOTES
    
    context.user_data['final_notes'] = update.message.text
    return await _save_and_end_closing_conversation(update, context)

async def finalize_without_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Ok, finalizando o fechamento...")
    context.user_data['final_notes'] = ''
    return await _save_and_end_closing_conversation(update, context)

async def _save_and_end_closing_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    os_id = context.user_data['os_id_to_close']
    close_data = context.user_data.get('close_data', {})
    close_data.update({
        "diagnostico_solucao": context.user_data.get('close_solution', 'N/A'), 
        "status_os": context.user_data.get('final_status', 'Fechada'), 
        "notas_finais": context.user_data.get('final_notes', ''), 
        "data_fechamento": datetime.now().isoformat()
    })
    parts_data = context.user_data.get('parts_list', [])
    success = await close_os_in_db(os_id, close_data, parts_data)
    chat_id = update.effective_chat.id
    if success:
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Ordem de Serviço #{os_id} fechada com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    else:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Ocorreu um erro ao fechar a OS #{os_id}.", reply_markup=MAIN_MENU_MARKUP)
    context.user_data.clear()
    return ConversationHandler.END
