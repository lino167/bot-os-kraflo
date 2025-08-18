import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.states import (
    CONFIRM_SAVE, ASK_EQUIPMENT, ASK_TAG, ASK_LOCATION, ASK_MAINT_TYPE, 
    ASK_PRIORITY, ASK_PROBLEM_DESC, ASK_IF_PHOTO, GET_PHOTO, HANDLE_UPLOAD_ERROR
)
from config import supabase
from handlers.ui_components import MAIN_MENU_MARKUP, TIPO_MANUTENCAO_KEYBOARD, PRIORIDADE_KEYBOARD
from database.utils import get_user_data, save_new_os

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

# --- FLUXO DE ABERTURA DE OS ---

async def start_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    context.user_data.clear()
    push_state(context, CONFIRM_SAVE)
    keyboard = [[InlineKeyboardButton("Sim, começar", callback_data="start_os")], [InlineKeyboardButton("Não, cancelar", callback_data="cancel_op")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "Você selecionou 'Abrir OS'. Deseja iniciar o processo?"
    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        
    return CONFIRM_SAVE

async def ask_for_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()
    
    if not is_back:
        push_state(context, ASK_EQUIPMENT)
    
    await query.edit_message_text(text="Ótimo! Qual equipamento ou ativo precisa de manutenção?")
    return ASK_EQUIPMENT

async def get_equipment_name(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_TAG)
        context.user_data.setdefault('os_data', {})['equipamento_nome'] = update.message.text
    
    await update.message.reply_text("Entendido. Qual a TAG/identificador do equipamento?")
    return ASK_TAG

async def get_equipment_tag(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_LOCATION)
        context.user_data['os_data']['equipamento_tag'] = update.message.text
    await update.message.reply_text("Qual o setor ou linha de produção onde o equipamento está localizado?")
    return ASK_LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_MAINT_TYPE)
        context.user_data['os_data']['localizacao'] = update.message.text
    
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(TIPO_MANUTENCAO_KEYBOARD))
    message_text = "Qual o tipo de manutenção a ser realizada?"

    if is_back:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

    return ASK_MAINT_TYPE

async def get_maintenance_type(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()
    
    if not is_back:
        push_state(context, ASK_PRIORITY)
        context.user_data['os_data']['tipo_manutencao'] = query.data
    
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(PRIORIDADE_KEYBOARD))
    message = f"Tipo: {context.user_data['os_data']['tipo_manutencao']}.\nAgora, qual o nível de prioridade?"
    await query.edit_message_text(text=message, reply_markup=reply_markup)
    return ASK_PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()

    if not is_back:
        push_state(context, ASK_PROBLEM_DESC)
        context.user_data['os_data']['prioridade'] = query.data
    
    await query.edit_message_text(text=f"Prioridade: {context.user_data['os_data']['prioridade']}. Por favor, descreva o problema observado ou o plano de serviço.")
    return ASK_PROBLEM_DESC

async def get_problem_description_and_ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    if not is_back:
        push_state(context, ASK_IF_PHOTO)
        context.user_data['os_data']['descricao_problema'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("📷 Sim, anexar foto", callback_data="photo_yes")],
        [InlineKeyboardButton("👍 Não, pular", callback_data="photo_no")]
    ]
    reply_markup = InlineKeyboardMarkup(add_nav_buttons(keyboard))
    await update.message.reply_text("Descrição salva. Deseja anexar uma foto do problema?", reply_markup=reply_markup)
    return ASK_IF_PHOTO

async def prompt_for_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, is_back: bool = False) -> int:
    query = update.callback_query
    await query.answer()

    if not is_back:
        if query.data == 'photo_no':
            return await save_os_and_finish(update, context)
        push_state(context, GET_PHOTO)
    
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
        reply_markup = InlineKeyboardMarkup(add_nav_buttons(keyboard))
        await update.message.reply_text(
            "Desculpe, ocorreu um erro ao salvar sua foto. Deseja tentar novamente?",
            reply_markup=reply_markup
        )
        return HANDLE_UPLOAD_ERROR

    return await save_os_and_finish(update, context)

async def handle_invalid_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Isso não é uma foto. Por favor, envie uma imagem válida ou use o botão '❌ Cancelar'."
    )
    return GET_PHOTO

async def handle_upload_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
