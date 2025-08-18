import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler, ContextTypes,
    PicklePersistence
)

from config import TELEGRAM_TOKEN
from handlers import common, registration, service_order, reports, os_edit, os_delete, parts_manager
from database.utils import is_user_registered, get_unique_parts_history
from handlers import states
from handlers.ui_components import MAIN_MENU_MARKUP

logger = logging.getLogger(__name__)

# Defina ou importe o estado ASK_SEARCH_TERM
ASK_SEARCH_TERM = 1000  # Ou importe de handlers.states se já estiver lá


async def start_parts_consult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo de consulta de peças."""
    await update.message.reply_text(
        "⚙️ **Consulta de Histórico de Peças**\n\n"
        "Digite o nome ou código (Part Number) da peça que deseja buscar:"
    )
    return ASK_SEARCH_TERM

async def search_parts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Busca as peças no banco de dados e exibe os resultados."""
    search_term = update.message.text
    user_id = update.effective_user.id
    
    await update.message.reply_text(f"Buscando por peças que contenham '{search_term}'...")
    
    parts_history = await get_unique_parts_history(user_id, search_term)
    
    if not parts_history:
        await update.message.reply_text(
            "Nenhuma peça encontrada com esse termo em seu histórico.",
            reply_markup=MAIN_MENU_MARKUP
        )
        return ConversationHandler.END
        
    message = "📜 **Histórico de Peças Encontradas:**\n\n"
    for part in parts_history:
        message += (
            f"🔹 **Peça:** {part.get('nome_peca', 'N/A')}\n"
            f"   - **Código/PN:** `{part.get('tag_peca', 'N/A')}`\n"
            f"   - **Último Uso:** Equipamento '{part.get('equipamento_nome', 'N/A')}' em {part.get('data_uso')}\n"
            "--------------------\n"
        )
        
    await update.message.reply_markdown_v2(
        message,
        reply_markup=MAIN_MENU_MARKUP
    )
    return ConversationHandler.END
