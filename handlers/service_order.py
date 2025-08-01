import logging
import math
import pandas as pd
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, filters

from config import supabase
from handlers.common import cancel, MAIN_MENU_MARKUP
from database.utils import (
    get_user_data, save_new_os, get_open_os_paginated, get_open_os_count, 
    close_os_in_db, get_closed_os_paginated, get_closed_os_count
)

logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa ---
# Abertura
(ASK_EQUIPMENT, ASK_TAG, ASK_LOCATION, ASK_MAINT_TYPE, 
 ASK_PRIORITY, ASK_PROBLEM_DESC, CONFIRM_SAVE, 
 ASK_IF_PHOTO, GET_PHOTO, HANDLE_UPLOAD_ERROR) = range(7, 17)
# Fechamento
(SELECT_OS_TO_CLOSE, ASK_SOLUTION, ASK_IF_PARTS, ASK_PART_NAME, 
 ASK_PART_TAG, ASK_PART_QTY, ASK_MORE_PARTS, ASK_FINAL_STATUS, 
 ASK_IF_ATTACHMENT, GET_ATTACHMENT, HANDLE_ATTACHMENT_UPLOAD_ERROR, ASK_IF_NOTES, GET_FINAL_NOTES) = range(17, 30)
# Paginação
PAGINATING_OS, PAGINATING_CLOSED_OS = range(30, 32)
OS_PER_PAGE = 5

# --- FLUXO DE ABERTURA DE OS ---

async def start_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton("Sim, começar", callback_data="start_os")], [InlineKeyboardButton("Não, voltar", callback_data="cancel_os")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Você selecionou 'Abrir OS'. Deseja iniciar o processo?", reply_markup=reply_markup)
    return CONFIRM_SAVE

async def ask_for_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'start_os':
        await query.edit_message_text(text="Ótimo! Qual equipamento ou ativo precisa de manutenção?")
        return ASK_EQUIPMENT
    else:
        await query.edit_message_text(text="Abertura de OS cancelada.")
        return await cancel(update, context)

async def get_equipment_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data'] = {'equipamento_nome': update.message.text}
    await update.message.reply_text("Entendido. Qual a TAG/identificador do equipamento?")
    return ASK_TAG

async def get_equipment_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['equipamento_tag'] = update.message.text
    await update.message.reply_text("Qual o setor ou linha de produção onde o equipamento está localizado?")
    return ASK_LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['localizacao'] = update.message.text
    keyboard = [[InlineKeyboardButton("🔧 Corretiva", callback_data="Corretiva")], [InlineKeyboardButton("📈 Preditiva", callback_data="Preditiva")], [InlineKeyboardButton("🗓️ Preventiva", callback_data="Preventiva")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qual o tipo de manutenção a ser realizada?", reply_markup=reply_markup)
    return ASK_MAINT_TYPE

async def get_maintenance_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_data']['tipo_manutencao'] = query.data
    keyboard = [[InlineKeyboardButton("🚨 Urgente", callback_data="Urgente")], [InlineKeyboardButton("⚠️ Alta", callback_data="Alta")], [InlineKeyboardButton("🔷 Média", callback_data="Média")], [InlineKeyboardButton("⚪ Baixa", callback_data="Baixa")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Tipo: {query.data}. Agora, qual o nível de prioridade?", reply_markup=reply_markup)
    return ASK_PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_data']['prioridade'] = query.data
    await query.edit_message_text(text=f"Prioridade: {query.data}. Por favor, descreva o problema observado ou o plano de serviço.")
    return ASK_PROBLEM_DESC

async def get_problem_description_and_ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_data']['descricao_problema'] = update.message.text
    keyboard = [[InlineKeyboardButton("📷 Sim, anexar foto", callback_data="photo_yes")], [InlineKeyboardButton("👍 Não, pular", callback_data="photo_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Descrição salva. Deseja anexar uma foto do problema?", reply_markup=reply_markup)
    return ASK_IF_PHOTO

async def prompt_for_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Ok, por favor, envie a foto agora.")
    return GET_PHOTO

async def get_photo_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    photo_file = await update.message.photo[-1].get_file()
    await update.message.reply_text("Recebi a foto. Fazendo upload para o servidor, aguarde...")
    
    try:
        photo_bytearray = await photo_file.download_as_bytearray()
        file_path = f"{user.id}/abertura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        context.user_data['upload_data'] = {'bytes': bytes(photo_bytearray), 'path': file_path}
        
        supabase.storage.from_("anexos-os").upload(file=context.user_data['upload_data']['bytes'], path=file_path, file_options={"content-type": "image/jpeg"})
        public_url = supabase.storage.from_("anexos-os").get_public_url(file_path)
        context.user_data['os_data']['url_foto'] = public_url
        logger.info(f"Foto enviada por {user.id} salva em: {public_url}")

    except Exception as e:
        logger.error(f"Erro no upload da foto para o Supabase: {e}")
        keyboard = [
            [InlineKeyboardButton("Tentar novamente", callback_data="upload_retry")],
            [InlineKeyboardButton("Continuar sem foto", callback_data="upload_skip")]
        ]
        await update.message.reply_text(
            "Desculpe, ocorreu um erro ao salvar sua foto. Deseja tentar novamente?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return HANDLE_UPLOAD_ERROR

    return await save_os_and_finish(update, context)

async def handle_invalid_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com casos em que o usuário envia algo que não é uma foto."""
    await update.message.reply_text(
        "Isso não é uma foto. Por favor, envie uma imagem válida ou digite /cancelar para sair."
    )
    return GET_PHOTO

async def handle_upload_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a decisão do usuário após uma falha de upload."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "upload_retry":
        await query.edit_message_text("Tentando o upload novamente...")
        try:
            upload_data = context.user_data['upload_data']
            supabase.storage.from_("anexos-os").upload(file=upload_data['bytes'], path=upload_data['path'], file_options={"content-type": "image/jpeg"})
            public_url = supabase.storage.from_("anexos-os").get_public_url(upload_data['path'])
            context.user_data['os_data']['url_foto'] = public_url
            return await save_os_and_finish(update, context)
        except Exception as e:
            logger.error(f"Segunda tentativa de upload falhou: {e}")
            await query.edit_message_text("A segunda tentativa também falhou. Continuando sem a foto.")
            return await save_os_and_finish(update, context)
            
    else: # upload_skip
        await query.edit_message_text("Ok, continuando o registro sem a foto.")
        return await save_os_and_finish(update, context)

async def save_os_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Ok, registrando a Ordem de Serviço...")
    user_id = update.effective_user.id
    user_db_data = await get_user_data(user_id)
    if not user_db_data:
        await context.bot.send_message(chat_id=user_id, text="Erro: não foi possível encontrar seus dados de cadastro.")
        return ConversationHandler.END
    os_data = context.user_data.get('os_data', {})
    os_data.update({
        "status_os": "Aberta", 
        "tecnico_id": user_id, 
        "empresa_id": user_db_data['empresa_id'],
        "data_abertura": datetime.now().isoformat() 
    })
    new_os = await save_new_os(os_data)
    if new_os and 'id' in new_os:
        await context.bot.send_message(chat_id=user_id, text=f"✅ Ordem de Serviço #{new_os['id']} aberta com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ Ocorreu um erro ao salvar a Ordem de Serviço.", reply_markup=MAIN_MENU_MARKUP)
    context.user_data.clear()
    return ConversationHandler.END

# --- FLUXO DE FECHAMENTO DE OS ---

async def start_close_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    open_os_list = await get_open_os_paginated(user_id, 0, 50) 
    if not open_os_list:
        await update.message.reply_text("Você não possui nenhuma Ordem de Serviço aberta.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"#{os['id']} - {os['equipamento_nome']} ({os['equipamento_tag']})", callback_data=f"close_{os['id']}")] for os in open_os_list]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel_close")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecione a Ordem de Serviço que deseja fechar:", reply_markup=reply_markup)
    return SELECT_OS_TO_CLOSE

async def ask_for_solution(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'cancel_close':
        await query.edit_message_text(text="Fechamento de OS cancelado.")
        return await cancel(update, context)
    os_id = int(query.data.split('_')[1])
    context.user_data['os_id_to_close'] = os_id
    await query.edit_message_text(text=f"Fechando OS #{os_id}.\n\nDescreva o diagnóstico final e a solução aplicada.")
    return ASK_SOLUTION

async def get_solution_and_ask_parts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['close_solution'] = update.message.text
    context.user_data['parts_list'] = []
    keyboard = [[InlineKeyboardButton("✅ Sim", callback_data="parts_yes")], [InlineKeyboardButton("❌ Não", callback_data="parts_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Houve troca de peças nesta manutenção?", reply_markup=reply_markup)
    return ASK_IF_PARTS

async def ask_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    num_peca = len(context.user_data.get('parts_list', [])) + 1
    await query.edit_message_text(text=f"Ok, vamos adicionar as peças trocadas.\n\nPara a Peça {num_peca}, qual o nome dela?")
    return ASK_PART_NAME

async def get_part_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_part_name'] = update.message.text
    await update.message.reply_text("Qual o TAG/Código (Part Number) dessa peça?")
    return ASK_PART_TAG

async def get_part_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['current_part_tag'] = update.message.text
    await update.message.reply_text("Qual a quantidade utilizada desta peça?")
    return ASK_PART_QTY

async def get_part_qty_and_ask_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text)
        part = {"nome_peca": context.user_data['current_part_name'], "tag_peca": context.user_data['current_part_tag'], "quantidade": qty}
        context.user_data['parts_list'].append(part)
        keyboard = [[InlineKeyboardButton("➕ Sim", callback_data="parts_yes")], [InlineKeyboardButton("👍 Não, continuar", callback_data="parts_no")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"✅ Peça '{part['nome_peca']}' adicionada.\nDeseja adicionar outra peça?", reply_markup=reply_markup)
        return ASK_MORE_PARTS
    except ValueError:
        await update.message.reply_text("Quantidade inválida. Por favor, digite apenas números.")
        return ASK_PART_QTY

async def ask_for_final_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("✅ Concluída", callback_data="Concluída")], [InlineKeyboardButton("⏳ Pendente", callback_data="Pendente")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Entendido. Qual o status final desta Ordem de Serviço?", reply_markup=reply_markup)
    return ASK_FINAL_STATUS

async def get_final_status_and_ask_if_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['final_status'] = query.data
    keyboard = [[InlineKeyboardButton("📎 Sim, anexar", callback_data="attach_yes")], [InlineKeyboardButton("👍 Não, pular", callback_data="attach_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Status definido como '{query.data}'.\n\nDeseja anexar um arquivo (foto, PDF) ao fechamento?", reply_markup=reply_markup)
    return ASK_IF_ATTACHMENT

async def prompt_for_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'attach_yes':
        await query.edit_message_text("Ok, por favor, envie o anexo agora.")
        return GET_ATTACHMENT
    else:
        return await prompt_for_final_notes(update, context)

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
    """Lida com casos em que o usuário envia algo que não é um anexo válido."""
    await update.message.reply_text(
        "Isso não é um anexo válido. Por favor, envie uma foto ou documento, ou digite /cancelar."
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

# --- FLUXO DE LISTAGEM PAGINADA DE OS ---
async def display_os_page(update: Update, context: ContextTypes.DEFAULT_TYPE, list_type: str):
    user_id = update.effective_user.id
    is_open_list = list_type == "open"
    page_key = 'current_page' if is_open_list else 'current_closed_page'
    total_key = 'total_os' if is_open_list else 'total_closed_os'
    current_page = context.user_data.get(page_key, 0)
    total_os = context.user_data.get(total_key, 0)
    total_pages = math.ceil(total_os / OS_PER_PAGE)
    if is_open_list:
        os_list = await get_open_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
        message = f"📋 **Suas Ordens de Serviço Abertas (Página {current_page + 1} de {total_pages}):**\n\n"
        if os_list:
            for os in os_list:
                message += (f"🔹 **OS #{os['id']}**\n   - **Equipamento:** {os['equipamento_nome']} ({os['equipamento_tag']})\n   - **Tipo:** {os['tipo_manutencao']}\n   - **Prioridade:** {os['prioridade']}\n--------------------\n")
    else:
        os_list = await get_closed_os_paginated(user_id, page=current_page, page_size=OS_PER_PAGE)
        message = f"🗂️ **Seu Histórico de OS (Página {current_page + 1} de {total_pages}):**\n\n"
        if os_list:
            for os in os_list:
                data_fechamento_str = pd.to_datetime(os['data_fechamento']).strftime('%d/%m/%Y') if os.get('data_fechamento') else "N/A"
                message += (f"🔹 **OS #{os['id']}**\n   - **Equipamento:** {os['equipamento_nome']}\n   - **Status:** {os['status_os']}\n   - **Data:** {data_fechamento_str}\n--------------------\n")
    if not os_list: message += "Nenhuma OS para exibir nesta página."
    keyboard = []
    nav_buttons = []
    callback_prefix = "list_open" if is_open_list else "list_closed"
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"{callback_prefix}_prev_{current_page - 1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Próxima ➡️", callback_data=f"{callback_prefix}_next_{current_page + 1}"))
    if nav_buttons: keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("❌ Fechar Lista", callback_data=f"{callback_prefix}_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_html(message, reply_markup=reply_markup)

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
        await update.message.reply_text("Você não possui histórico de Ordens de Serviço fechadas hoje.", reply_markup=MAIN_MENU_MARKUP)
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
