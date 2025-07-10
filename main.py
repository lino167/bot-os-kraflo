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
from handlers import common, registration, service_order, reports

# Configuração do logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Inicia o bot e configura todos os handlers."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- Handlers de Conversa ---
    open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 Abrir OS$"), registration.start_registration_or_os)],
        states={
            registration.NOME_EMPRESA: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_name)],
            registration.NOME_COMPLETO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name)],
            registration.FUNCAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role)],
            registration.SETOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save)],
            service_order.CONFIRM_SAVE: [CallbackQueryHandler(service_order.ask_for_equipment, pattern='^start_os$|^cancel_os$')],
            service_order.ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_name)],
            service_order.ASK_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_tag)],
            service_order.ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_location)],
            service_order.ASK_MAINT_TYPE: [CallbackQueryHandler(service_order.get_maintenance_type)],
            service_order.ASK_PRIORITY: [CallbackQueryHandler(service_order.get_priority)],
            service_order.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )

    close_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✅ Fechar OS$"), service_order.start_close_os)],
        states={
            service_order.SELECT_OS_TO_CLOSE: [CallbackQueryHandler(service_order.ask_for_solution)],
            service_order.ASK_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_solution_and_ask_parts)],
            service_order.ASK_IF_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_PART_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_name)],
            service_order.ASK_PART_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_tag)],
            service_order.ASK_PART_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_qty_and_ask_more)],
            service_order.ASK_MORE_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_FINAL_STATUS: [CallbackQueryHandler(service_order.get_final_status_and_ask_if_notes)],
            service_order.ASK_IF_NOTES: [CallbackQueryHandler(service_order.prompt_for_final_notes, pattern='^notes_yes$'), CallbackQueryHandler(service_order.finalize_without_notes, pattern='^notes_no$')],
            service_order.GET_FINAL_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_final_notes_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_close$')],
        per_user=True, per_chat=True,
    )

    # ATUALIZADO: Handler da Conversa de Geração de Relatórios (mais simples)
    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Relatórios$"), reports.start_report_generation)],
        states={
            reports.MANAGE_SELECTION: [CallbackQueryHandler(reports.manage_selection)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_report$')],
        per_user=True, per_chat=True,
    )

    # --- Adicionando todos os handlers à aplicação ---
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(open_os_conv)
    application.add_handler(close_os_conv)
    application.add_handler(report_conv)
    application.add_handler(MessageHandler(filters.Regex("^📋 Listar Abertas$"), service_order.list_open_os))
    
    print("="*50)
    print("🚀 BOT ATUALIZADO E INICIADO COM SUCESSO! 🚀")
    print("O bot está online e aguardando por mensagens.")
    print("Pressione Ctrl+C para parar o bot.")
    print("="*50)
    
    application.run_polling()


if __name__ == "__main__":
    main()
