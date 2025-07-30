import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler, ContextTypes
)

from config import TELEGRAM_TOKEN
from handlers import common, registration, service_order, reports, os_edit, os_delete, parts_manager
from database.utils import is_user_registered

# Configuração do logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

async def check_registration_and_start(update: Update, context: ContextTypes.DEFAULT_TYPE, start_function):
    """Função de guarda: verifica se o usuário está cadastrado antes de executar uma ação."""
    user = update.effective_user
    if not user:
        logger.warning("Não foi possível identificar o usuário na mensagem. A ação foi cancelada.")
        return ConversationHandler.END
    logger.info(f"[GUARD] Usuário {user.id} ({user.full_name}) tentando aceder à função '{start_function.__name__}'.")
    if await is_user_registered(user.id):
        logger.info(f"[GUARD] Acesso PERMITIDO para o usuário {user.id}. A iniciar '{start_function.__name__}'.")
        return await start_function(update, context)
    else:
        logger.warning(f"[GUARD] Acesso NEGADO para o usuário {user.id}. O usuário não está registado.")
        await update.message.reply_text("Você precisa de se registar primeiro. Use o comando /start para começar.")
        return ConversationHandler.END

def main() -> None:
    """Inicia o bot e configura todos os handlers."""
    logger.info("INICIANDO A CONFIGURAÇÃO DO BOT")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # --- DEFINIÇÃO DOS HANDLERS DE CONVERSA ---
    
    # 1. Handler de Cadastro
    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        states={
            registration.ASK_COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.ask_if_company_code)],
            registration.ASK_IF_COMPANY_CODE: [
                CallbackQueryHandler(registration.prompt_for_company_code, pattern='^code_yes$'),
                CallbackQueryHandler(registration.ask_name_directly, pattern='^code_no$')
            ],
            registration.GET_COMPANY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_code_and_ask_name)],
            registration.GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name_and_ask_role)],
            registration.GET_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role_and_ask_sector)],
            registration.GET_SECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )

    # 2. Handler de Abertura de OS
    open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 Abrir OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_open_os))],
        states={
            service_order.CONFIRM_SAVE: [CallbackQueryHandler(service_order.ask_for_equipment, pattern='^start_os$|^cancel_os$')],
            service_order.ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_name)],
            service_order.ASK_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_tag)],
            service_order.ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_location)],
            service_order.ASK_MAINT_TYPE: [CallbackQueryHandler(service_order.get_maintenance_type)],
            service_order.ASK_PRIORITY: [CallbackQueryHandler(service_order.get_priority)],
            service_order.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_ask_photo)],
            service_order.ASK_IF_PHOTO: [
                CallbackQueryHandler(service_order.prompt_for_photo, pattern='^photo_yes$'),
                CallbackQueryHandler(service_order.save_os_and_finish, pattern='^photo_no$')
            ],
            service_order.GET_PHOTO: [MessageHandler(filters.PHOTO, service_order.get_photo_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )
    
    # 3. Handler de Fechamento de OS
    close_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✅ Fechar OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_close_os))],
        states={
            service_order.SELECT_OS_TO_CLOSE: [CallbackQueryHandler(service_order.ask_for_solution, pattern="^close_")],
            service_order.ASK_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_solution_and_ask_parts)],
            service_order.ASK_IF_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_PART_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_name)],
            service_order.ASK_PART_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_tag)],
            service_order.ASK_PART_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_qty_and_ask_more)],
            service_order.ASK_MORE_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')],
            service_order.ASK_FINAL_STATUS: [CallbackQueryHandler(service_order.get_final_status_and_ask_if_attachment)],
            service_order.ASK_IF_ATTACHMENT: [CallbackQueryHandler(service_order.prompt_for_attachment, pattern='^attach_')],
            service_order.GET_ATTACHMENT: [MessageHandler(filters.PHOTO | filters.Document.ALL, service_order.get_attachment_and_ask_notes)],
            service_order.ASK_IF_NOTES: [CallbackQueryHandler(service_order.get_final_notes_and_save, pattern='^notes_yes$'), CallbackQueryHandler(service_order.finalize_without_notes, pattern='^notes_no$')],
            service_order.GET_FINAL_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_final_notes_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_close$')],
        per_user=True, per_chat=True,
    )

    # 4. Handler de Relatórios
    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: check_registration_and_start(u, c, reports.start_report_generation))],
        states={
            reports.SELECT_START_DATE: [CallbackQueryHandler(reports.handle_start_date_selection, pattern="^calendar_")],
            reports.SELECT_END_DATE: [CallbackQueryHandler(reports.handle_end_date_selection, pattern="^calendar_")],
            reports.MANAGE_SELECTION: [CallbackQueryHandler(reports.manage_selection)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )

    # 5. Handlers de Listagem
    list_open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_open_os))],
        states={service_order.PAGINATING_OS: [CallbackQueryHandler(service_order.navigate_os_page, pattern="^list_open")]},
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_open_cancel$")],
        per_user=True, per_chat=True,
    )
    list_closed_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗂️ Listar Fechadas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_closed_os))],
        states={service_order.PAGINATING_CLOSED_OS: [CallbackQueryHandler(service_order.navigate_closed_os_page, pattern="^list_closed")]},
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_closed_cancel$")],
        per_user=True, per_chat=True,
    )

    # 6. Handler de Edição de OS
    edit_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Editar OS$"), lambda u, c: check_registration_and_start(u, c, os_edit.start_edit_os))],
        states={
            os_edit.PAGINATING_EDIT_OS: [
                CallbackQueryHandler(os_edit.navigate_editable_os_page, pattern="^edit_nav_"),
                CallbackQueryHandler(os_edit.show_edit_menu, pattern="^edit_select_os_"),
            ],
            os_edit.SELECT_FIELD: [
                CallbackQueryHandler(os_edit.prompt_for_new_value, pattern="^edit_field_"),
                CallbackQueryHandler(os_edit.finish_editing, pattern="^edit_finish$"),
            ],
            os_edit.GET_NEW_VALUE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, os_edit.update_field_from_text)],
            os_edit.GET_NEW_VALUE_BUTTON: [CallbackQueryHandler(os_edit.update_field_from_button)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern="^edit_cancel$")],
        per_user=True, per_chat=True,
    )
    
    # 7. Handler para Deletar OS
    delete_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗑️ Deletar OS$"), lambda u, c: check_registration_and_start(u, c, os_delete.start_delete_os))],
        states={
            os_delete.SELECT_OS_TO_DELETE: [CallbackQueryHandler(os_delete.list_os_for_deletion, pattern="^calendar_")],
            os_delete.CONFIRM_DELETE: [CallbackQueryHandler(os_delete.confirm_and_delete_os, pattern="^delete_")]
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )

    # 8. Handler para Consultar Peças
    parts_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Consultar Peças$"), lambda u, c: check_registration_and_start(u, c, parts_manager.start_parts_consult))],
        states={
            parts_manager.ASK_SEARCH_TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, parts_manager.search_parts)]
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)],
        per_user=True, per_chat=True,
    )
    
    # --- REGISTO DE TODOS OS HANDLERS NA APLICAÇÃO ---
    application.add_handler(registration_conv)
    application.add_handler(open_os_conv)
    application.add_handler(close_os_conv)
    application.add_handler(report_conv)
    application.add_handler(list_open_os_conv)
    application.add_handler(list_closed_os_conv)
    application.add_handler(edit_os_conv)
    application.add_handler(delete_os_conv)
    application.add_handler(parts_conv)
    
    logger.info("Bot pronto. A iniciar o polling de atualizações...")
    application.run_polling()

if __name__ == "__main__":
    main()
