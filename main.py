import logging
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Importa nossas configurações e os handlers de cada módulo
from config import TELEGRAM_TOKEN
from handlers import common, registration, service_order

# Configuração do logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Inicia o bot e configura todos os handlers."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Conversation Handler Unificado ---
    # Este handler gerencia tanto o fluxo de cadastro quanto o de abertura de OS.
    # O ponto de entrada único decide qual caminho seguir.
    unified_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🆕 Abrir OS$"), registration.start_registration_or_os)
        ],
        states={
            # Estados de Cadastro (do módulo registration)
            registration.NOME_EMPRESA: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_name)],
            registration.NOME_COMPLETO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name)],
            registration.FUNCAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role)],
            registration.SETOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save)],
            
            # Estados de Abertura de OS (do módulo service_order)
            service_order.CONFIRM_SAVE: [CallbackQueryHandler(service_order.ask_for_equipment)],
            service_order.ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_name)],
            service_order.ASK_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_tag)],
            service_order.ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_location)],
            service_order.ASK_MAINT_TYPE: [CallbackQueryHandler(service_order.get_maintenance_type)],
            service_order.ASK_PRIORITY: [CallbackQueryHandler(service_order.get_priority)],
            service_order.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_os$')],
        # Permite que o handler funcione corretamente para múltiplos usuários
        per_user=True,
        per_chat=True,
    )

    # --- Adicionando todos os handlers à aplicação ---
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(unified_conversation)

    # Placeholders para os outros botões do menu principal
    application.add_handler(MessageHandler(filters.Regex("^✅ Fechar OS$"), lambda u, c: u.message.reply_text("Funcionalidade 'Fechar OS' em desenvolvimento.")))
    application.add_handler(MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: u.message.reply_text("Funcionalidade 'Listar Abertas' em desenvolvimento.")))
    application.add_handler(MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: u.message.reply_text("Funcionalidade 'Relatórios' em desenvolvimento.")))

    print("="*50)
    print("🚀 BOT INICIADO COM SUCESSO! 🚀")
    print("O bot está online e aguardando por mensagens.")
    print("Pressione Ctrl+C para parar o bot.")
    print("="*50)
    
    application.run_polling()


if __name__ == "__main__":
    main()
