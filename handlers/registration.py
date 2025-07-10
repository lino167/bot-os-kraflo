import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Importações dos nossos próprios módulos
from config import supabase
from handlers.common import MAIN_MENU_MARKUP
from database.utils import is_user_registered

# --- Definição dos Estados da Conversa ---
# Usamos números para definir cada passo da conversa de cadastro.
(
    NOME_EMPRESA, 
    NOME_COMPLETO, 
    FUNCAO, 
    SETOR
) = range(4)

# Configura o logger para este módulo
logger = logging.getLogger(__name__)


async def start_registration_or_os(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ponto de entrada principal. Verifica se o usuário é cadastrado.
    Se não for, inicia o fluxo de cadastro.
    Se já for, futuramente iniciará o fluxo de abertura de OS.
    """
    user_id = update.effective_user.id
    
    if not await is_user_registered(user_id):
        # Usuário não cadastrado, inicia o processo de registro
        await update.message.reply_text(
            "Bem-vindo! Vejo que é seu primeiro acesso.\n"
            "Vamos criar seu cadastro. Primeiro, qual o nome da sua EMPRESA?",
            reply_markup=ReplyKeyboardRemove(),  # Remove o teclado principal temporariamente
        )
        return NOME_EMPRESA
    else:
        # Usuário já cadastrado, a lógica de abrir OS virá aqui
        await update.message.reply_text(
            "Funcionalidade 'Abrir OS' em desenvolvimento.", 
            reply_markup=MAIN_MENU_MARKUP
        )
        return ConversationHandler.END


async def get_company_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o nome da empresa e pede o nome completo."""
    context.user_data['nome_empresa'] = update.message.text
    await update.message.reply_text(
        f"Empresa: {context.user_data['nome_empresa']}.\n"
        "Agora, por favor, digite seu NOME COMPLETO."
    )
    return NOME_COMPLETO


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o nome completo e pede a função."""
    context.user_data['nome_completo'] = update.message.text
    await update.message.reply_text("Qual a sua FUNÇÃO? (ex: Eletricista, Mecânico)")
    return FUNCAO


async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva a função e pede o setor."""
    context.user_data['funcao'] = update.message.text
    await update.message.reply_text("E em qual SETOR você atua?")
    return SETOR


async def get_sector_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Salva o setor, finaliza o cadastro no banco de dados e encerra a conversa."""
    context.user_data['setor'] = update.message.text
    user = update.effective_user

    try:
        # Passo 1: Verificar se a empresa já existe ou criá-la.
        empresa_nome = context.user_data['nome_empresa']
        
        # Busca pela empresa no banco
        response = supabase.table('empresas').select('id').eq('nome_empresa', empresa_nome).execute()
        
        if response.data:
            # Empresa já existe, pega o ID
            empresa_id = response.data[0]['id']
        else:
            # Empresa não existe, insere e pega o ID retornado
            response = supabase.table('empresas').insert({"nome_empresa": empresa_nome}).execute()
            empresa_id = response.data[0]['id']
            logger.info(f"Nova empresa '{empresa_nome}' cadastrada com ID: {empresa_id}")

        # Passo 2: Inserir o novo técnico no banco de dados.
        tecnico_data = {
            "id_telegram": user.id,
            "nome_completo": context.user_data['nome_completo'],
            "funcao": context.user_data['funcao'],
            "setor": context.user_data['setor'],
            "empresa_id": empresa_id,
        }
        supabase.table('tecnicos').insert(tecnico_data).execute()
        
        logger.info(f"Novo técnico cadastrado: {user.id} - {context.user_data['nome_completo']}")
        
        await update.message.reply_text(
            "✅ Cadastro realizado com sucesso!\n"
            "Agora você já pode usar todas as funções do bot.",
            reply_markup=MAIN_MENU_MARKUP,
        )

    except Exception as e:
        logger.error(f"Erro ao salvar cadastro: {e}")
        await update.message.reply_text(
            "❌ Ocorreu um erro ao salvar seu cadastro. Por favor, tente novamente mais tarde.",
            reply_markup=MAIN_MENU_MARKUP,
        )
    finally:
        # Limpa os dados temporários da conversa
        context.user_data.clear()

    # Encerra a conversa
    return ConversationHandler.END
