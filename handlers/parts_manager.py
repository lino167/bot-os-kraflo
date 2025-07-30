import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from database.utils import get_unique_parts_history
from handlers.common import MAIN_MENU_MARKUP

logger = logging.getLogger(__name__)

# Estados da conversa
ASK_SEARCH_TERM, SHOW_RESULTS = range(70, 72)

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
