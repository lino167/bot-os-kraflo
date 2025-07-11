import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import supabase
from handlers.common import MAIN_MENU_MARKUP
from database.utils import is_user_registered
from handlers.service_order import start_open_os 

NOME_EMPRESA, NOME_COMPLETO, FUNCAO, SETOR = range(4)
logger = logging.getLogger(__name__)

async def start_registration_or_os(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ponto de entrada que decide entre o fluxo de cadastro ou de abertura de OS."""
    user_id = update.effective_user.id
    if not await is_user_registered(user_id):
        await update.message.reply_text(
            "Bem-vindo! Vejo que é seu primeiro acesso.\n"
            "Vamos criar seu cadastro. Primeiro, qual o nome da sua EMPRESA?",
            reply_markup=ReplyKeyboardRemove(),
        )
        return NOME_EMPRESA
    else:
        return await start_open_os(update, context)

async def get_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['nome_empresa'] = update.message.text
    await update.message.reply_text(f"Empresa: {context.user_data['nome_empresa']}.\nAgora, seu NOME COMPLETO.")
    return NOME_COMPLETO

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['nome_completo'] = update.message.text
    await update.message.reply_text("Qual a sua FUNÇÃO? (ex: Eletricista, Mecânico)")
    return FUNCAO

async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['funcao'] = update.message.text
    await update.message.reply_text("E em qual SETOR você atua?")
    return SETOR

async def get_sector_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['setor'] = update.message.text
    user = update.effective_user
    try:
        empresa_nome = context.user_data['nome_empresa']
        response = supabase.table('empresas').select('id').eq('nome_empresa', empresa_nome).execute()
        if response.data:
            empresa_id = response.data[0]['id']
        else:
            response = supabase.table('empresas').insert({"nome_empresa": empresa_nome}).execute()
            empresa_id = response.data[0]['id']
        tecnico_data = {
            "id_telegram": user.id, "nome_completo": context.user_data['nome_completo'],
            "funcao": context.user_data['funcao'], "setor": context.user_data['setor'],
            "empresa_id": empresa_id,
        }
        supabase.table('tecnicos').insert(tecnico_data).execute()
        logger.info(f"Novo técnico cadastrado: {user.id} - {context.user_data['nome_completo']}")
        await update.message.reply_text("✅ Cadastro realizado com sucesso!", reply_markup=MAIN_MENU_MARKUP)
    except Exception as e:
        logger.error(f"Erro ao salvar cadastro: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao salvar seu cadastro.", reply_markup=MAIN_MENU_MARKUP)
    finally:
        context.user_data.clear()
    return ConversationHandler.END
