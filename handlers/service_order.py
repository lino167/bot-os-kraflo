import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from handlers.common import cancel, MAIN_MENU_MARKUP
from database.utils import get_user_data, save_new_os

logger = logging.getLogger(__name__)

# Estados da conversa de abertura de OS
(ASK_EQUIPMENT, ASK_TAG, ASK_LOCATION, ASK_MAINT_TYPE, 
 ASK_PRIORITY, ASK_PROBLEM_DESC, CONFIRM_SAVE) = range(7, 14) # Continua a numeração

# --- Funções do Fluxo de Abertura de OS ---

async def start_open_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de abertura de OS após a verificação de cadastro."""
    keyboard = [
        [InlineKeyboardButton("Sim, começar", callback_data="start_os")],
        [InlineKeyboardButton("Não, voltar", callback_data="cancel_os")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Você selecionou 'Abrir OS'. Deseja iniciar o processo?",
        reply_markup=reply_markup
    )
    return CONFIRM_SAVE # Estado inicial da conversa de OS

async def ask_for_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pergunta o nome do equipamento após confirmação."""
    query = update.callback_query
    await query.answer()

    if query.data == 'start_os':
        await query.edit_message_text(text="Ótimo! Qual equipamento ou ativo precisa de manutenção?")
        return ASK_EQUIPMENT
    else:
        await query.edit_message_text(text="Abertura de OS cancelada.")
        return await cancel(update, context)

async def get_equipment_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_equipamento_nome'] = update.message.text
    await update.message.reply_text("Entendido. Qual a TAG/identificador do equipamento?")
    return ASK_TAG

async def get_equipment_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_equipamento_tag'] = update.message.text
    await update.message.reply_text("Qual o setor ou linha de produção onde o equipamento está localizado?")
    return ASK_LOCATION

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['os_localizacao'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("🔧 Corretiva", callback_data="Corretiva")],
        [InlineKeyboardButton("📈 Preditiva", callback_data="Preditiva")],
        [InlineKeyboardButton("🗓️ Preventiva", callback_data="Preventiva")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Qual o tipo de manutenção a ser realizada?", reply_markup=reply_markup)
    return ASK_MAINT_TYPE

async def get_maintenance_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_tipo_manutencao'] = query.data
    
    keyboard = [
        [InlineKeyboardButton("🚨 Urgente", callback_data="Urgente")],
        [InlineKeyboardButton("⚠️ Alta", callback_data="Alta")],
        [InlineKeyboardButton("🔷 Média", callback_data="Média")],
        [InlineKeyboardButton("⚪ Baixa", callback_data="Baixa")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Tipo: {query.data}. Agora, qual o nível de prioridade?", reply_markup=reply_markup)
    return ASK_PRIORITY

async def get_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['os_prioridade'] = query.data
    await query.edit_message_text(text=f"Prioridade: {query.data}. Por favor, descreva o problema observado ou o plano de serviço.")
    return ASK_PROBLEM_DESC

async def get_problem_description_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Coleta a descrição final e salva a OS completa no banco."""
    context.user_data['os_descricao_problema'] = update.message.text
    user_id = update.effective_user.id

    # Busca dados do usuário (empresa_id) para vincular à OS
    user_db_data = await get_user_data(user_id)
    if not user_db_data:
        await update.message.reply_text("Erro: não foi possível encontrar seus dados de cadastro. Tente /start novamente.", reply_markup=MAIN_MENU_MARKUP)
        return ConversationHandler.END

    # Monta o dicionário com todos os dados da OS
    os_data = {
        "tipo_manutencao": context.user_data['os_tipo_manutencao'],
        "equipamento_nome": context.user_data['os_equipamento_nome'],
        "equipamento_tag": context.user_data['os_equipamento_tag'],
        "localizacao": context.user_data['os_localizacao'],
        "prioridade": context.user_data['os_prioridade'],
        "descricao_problema": context.user_data['os_descricao_problema'],
        "status_os": "Aberta",
        "tecnico_id": user_id,
        "empresa_id": user_db_data['empresa_id']
    }

    # Salva no banco de dados
    new_os_id = await save_new_os(os_data)

    if new_os_id:
        await update.message.reply_text(f"✅ Ordem de Serviço #{new_os_id} aberta com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao salvar a Ordem de Serviço. Tente novamente.", reply_markup=MAIN_MENU_MARKUP)

    context.user_data.clear()
    return ConversationHandler.END