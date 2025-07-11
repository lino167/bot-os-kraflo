import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos próprios módulos
from config import supabase
from handlers.ui_components import MAIN_MENU_MARKUP # <<< MUDANÇA AQUI
from database.utils import is_user_registered
# from handlers.service_order import start_open_os # Esta importação não é mais necessária aqui

logger = logging.getLogger(__name__)

# --- Definição dos Estados da Conversa de Cadastro ---
(
    ASK_COMPANY_NAME,
    ASK_IF_COMPANY_CODE,
    GET_COMPANY_CODE,
    GET_FULL_NAME,
    GET_ROLE,
    GET_SECTOR,
) = range(40, 46)

async def ask_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de cadastro pedindo o nome da empresa."""
    await update.message.reply_text(
        "Bem-vindo ao Bot de OS da Kraflo! Vejo que é o seu primeiro acesso.\n\n"
        "Vamos criar o seu cadastro. Para começar, qual o nome da sua EMPRESA?",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_COMPANY_NAME

async def ask_if_company_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o nome da empresa e pergunta se o usuário tem um código de funcionário."""
    context.user_data['registration_data'] = {'nome_empresa': update.message.text}
    keyboard = [
        [InlineKeyboardButton("Sim, tenho um código", callback_data="code_yes")],
        [InlineKeyboardButton("Não tenho", callback_data="code_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Empresa: {update.message.text}.\n\n"
        "A sua empresa forneceu um código de identificação (matrícula, ID, etc.) para usar no cadastro?",
        reply_markup=reply_markup
    )
    return ASK_IF_COMPANY_CODE

async def prompt_for_company_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pede ao usuário para digitar o código da empresa."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Entendido. Por favor, digite o seu código de identificação:")
    return GET_COMPANY_CODE

async def get_company_code_and_ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o código da empresa e pede o nome completo."""
    context.user_data['registration_data']['codigo_empresa'] = update.message.text
    await update.message.reply_text("Código salvo! Agora, por favor, digite o seu NOME COMPLETO.")
    return GET_FULL_NAME

async def ask_name_directly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pula a etapa do código e pede diretamente o nome completo."""
    query = update.callback_query
    await query.answer()
    context.user_data['registration_data']['codigo_empresa'] = None
    await query.edit_message_text(text="Sem problemas. Vamos continuar.\n\nPor favor, digite o seu NOME COMPLETO.")
    return GET_FULL_NAME

async def get_full_name_and_ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o nome completo e pede a função."""
    context.user_data['registration_data']['nome_completo'] = update.message.text
    await update.message.reply_text("Qual a sua FUNÇÃO? (ex: Eletricista, Mecânico, Operador)")
    return GET_ROLE

async def get_role_and_ask_sector(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva a função e pede o setor."""
    context.user_data['registration_data']['funcao'] = update.message.text
    await update.message.reply_text("E em qual SETOR você atua? (ex: Manutenção, Produção, Qualidade)")
    return GET_SECTOR

async def get_sector_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o setor, finaliza o cadastro no banco de dados e encerra a conversa."""
    context.user_data['registration_data']['setor'] = update.message.text
    user = update.effective_user
    reg_data = context.user_data['registration_data']

    try:
        empresa_nome = reg_data['nome_empresa']
        response = supabase.table('empresas').select('id').eq('nome_empresa', empresa_nome).execute()
        
        if response.data:
            empresa_id = response.data[0]['id']
        else:
            response = supabase.table('empresas').insert({"nome_empresa": empresa_nome}).execute()
            empresa_id = response.data[0]['id']
            
        tecnico_data = {
            "id_telegram": user.id,
            "nome_completo": reg_data['nome_completo'],
            "funcao": reg_data['funcao'],
            "setor": reg_data['setor'],
            "codigo_empresa": reg_data['codigo_empresa'],
            "empresa_id": empresa_id,
        }
        supabase.table('tecnicos').insert(tecnico_data).execute()
        logger.info(f"Novo técnico cadastrado: {user.id} - {reg_data['nome_completo']}")
        await update.message.reply_text(
            "✅ Cadastro realizado com sucesso!\n\n"
            "Agora você tem acesso a todas as funcionalidades.",
            reply_markup=MAIN_MENU_MARKUP
        )
    except Exception as e:
        logger.error(f"Erro ao salvar cadastro do usuário {user.id}: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro ao salvar seu cadastro. Por favor, tente novamente mais tarde.",
            reply_markup=MAIN_MENU_MARKUP
        )
    finally:
        context.user_data.clear()
        
    return ConversationHandler.END