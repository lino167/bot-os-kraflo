import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler, ContextTypes,
    PicklePersistence
)

from config import TELEGRAM_TOKEN
from handlers import (
    common, registration, service_order, reports, 
    os_edit, os_delete, parts_manager, states
)
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
    if not user: return ConversationHandler.END
    if await is_user_registered(user.id):
        return await start_function(update, context)
    else:
        await update.message.reply_text("Você precisa de se registar primeiro. Use o comando /start para começar.")
        return ConversationHandler.END

def main() -> None:
    """Inicia o bot e configura todos os handlers."""
    logger.info("INICIANDO A CONFIGURAÇÃO DO BOT")
    persistence = PicklePersistence(filepath="bot_persistence")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    # --- MAPA DE ESTADOS PARA FUNÇÕES (PARA O BOTÃO 'VOLTAR') ---
    application.bot_data['state_map'] = {
        # Abertura de OS
        states.CONFIRM_SAVE: service_order.start_open_os,
        states.ASK_EQUIPMENT: service_order.ask_for_equipment,
        states.ASK_TAG: service_order.get_equipment_name,
        states.ASK_LOCATION: service_order.get_equipment_tag,
        states.ASK_MAINT_TYPE: service_order.get_location,
        states.ASK_PRIORITY: service_order.get_maintenance_type,
        states.ASK_PROBLEM_DESC: service_order.get_priority,
        states.ASK_IF_PHOTO: service_order.get_problem_description_and_ask_photo,
        states.GET_PHOTO: service_order.prompt_for_photo,
        # Fechamento de OS
        states.SELECT_OS_TO_CLOSE: service_order.start_close_os,
        states.ASK_SOLUTION: service_order.ask_for_solution,
        states.ASK_IF_PARTS: service_order.get_solution_and_ask_parts,
        states.ASK_PART_NAME: service_order.ask_part_name,
        states.ASK_PART_TAG: service_order.get_part_name,
        states.ASK_PART_QTY: service_order.get_part_tag,
        states.ASK_MORE_PARTS: service_order.get_part_qty_and_ask_more,
        states.ASK_FINAL_STATUS: service_order.ask_for_final_status,
        states.ASK_IF_ATTACHMENT: service_order.get_final_status_and_ask_if_attachment,
        states.GET_ATTACHMENT: service_order.prompt_for_attachment,
        states.ASK_IF_NOTES: service_order.prompt_for_final_notes,
    }

    # --- HANDLERS DE NAVEGAÇÃO UNIVERSAIS ---
    nav_handlers = [
        CallbackQueryHandler(common.back, pattern="^back$"),
        CallbackQueryHandler(common.cancel, pattern="^cancel_op$"),
    ]
    
    # --- MELHORIA: HANDLER UNIVERSAL PARA INPUT INVÁLIDO ---
    invalid_input_handler = MessageHandler(
        ~filters.TEXT | filters.COMMAND, common.handle_invalid_input
    )

    # --- HANDLERS DE CONVERSA ---
    
    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", common.start)],
        states={
            states.ASK_COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.ask_if_company_code), invalid_input_handler],
            states.ASK_IF_COMPANY_CODE: [
                CallbackQueryHandler(registration.prompt_for_company_code, pattern='^code_yes$'),
                CallbackQueryHandler(registration.ask_name_directly, pattern='^code_no$')
            ],
            states.GET_COMPANY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_company_code_and_ask_name), invalid_input_handler],
            states.GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_full_name_and_ask_role), invalid_input_handler],
            states.GET_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_role_and_ask_sector), invalid_input_handler],
            states.GET_SECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.get_sector_and_save), invalid_input_handler],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True
    )

    open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🆕 Abrir OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_open_os))],
        states={
            states.CONFIRM_SAVE: [CallbackQueryHandler(service_order.ask_for_equipment, pattern='^start_os$')] + nav_handlers,
            states.ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_name), invalid_input_handler],
            states.ASK_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_equipment_tag), invalid_input_handler],
            states.ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_location), invalid_input_handler],
            states.ASK_MAINT_TYPE: [CallbackQueryHandler(service_order.get_maintenance_type, pattern="^(?!back$|cancel_op$).*$")] + nav_handlers,
            states.ASK_PRIORITY: [CallbackQueryHandler(service_order.get_priority, pattern="^(?!back$|cancel_op$).*$")] + nav_handlers,
            states.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_ask_photo), invalid_input_handler],
            states.ASK_IF_PHOTO: [
                CallbackQueryHandler(service_order.prompt_for_photo, pattern='^photo_yes$'),
                CallbackQueryHandler(service_order.save_os_and_finish, pattern='^photo_no$')
            ] + nav_handlers,
            states.GET_PHOTO: [
                MessageHandler(filters.PHOTO, service_order.get_photo_and_save),
                MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.handle_invalid_photo)
            ],
            states.HANDLE_UPLOAD_ERROR: [CallbackQueryHandler(service_order.handle_upload_error, pattern="^upload_")] + nav_handlers,
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True
    )
    
    close_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✅ Fechar OS$"), lambda u, c: check_registration_and_start(u, c, service_order.start_close_os))],
        states={
            states.SELECT_OS_TO_CLOSE: [CallbackQueryHandler(service_order.ask_for_solution, pattern="^close_")] + nav_handlers,
            states.ASK_SOLUTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_solution_and_ask_parts), invalid_input_handler],
            states.ASK_IF_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')] + nav_handlers,
            states.ASK_PART_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_name), invalid_input_handler],
            states.ASK_PART_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_tag), invalid_input_handler],
            states.ASK_PART_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_part_qty_and_ask_more), invalid_input_handler],
            states.ASK_MORE_PARTS: [CallbackQueryHandler(service_order.ask_part_name, pattern='^parts_yes$'), CallbackQueryHandler(service_order.ask_for_final_status, pattern='^parts_no$')] + nav_handlers,
            states.ASK_FINAL_STATUS: [CallbackQueryHandler(service_order.get_final_status_and_ask_if_attachment, pattern="^(?!back$|cancel_op$).*$")] + nav_handlers,
            states.ASK_IF_ATTACHMENT: [CallbackQueryHandler(service_order.prompt_for_attachment, pattern='^attach_')] + nav_handlers,
            states.GET_ATTACHMENT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, service_order.get_attachment_and_ask_notes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.handle_invalid_attachment)
            ],
            states.HANDLE_ATTACHMENT_UPLOAD_ERROR: [CallbackQueryHandler(service_order.handle_attachment_upload_error, pattern="^upload_attach_")] + nav_handlers,
            states.ASK_IF_NOTES: [
                CallbackQueryHandler(service_order.get_final_notes_and_save, pattern='^notes_yes$'), 
                CallbackQueryHandler(service_order.finalize_without_notes, pattern='^notes_no$')
            ] + nav_handlers,
            states.GET_FINAL_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_final_notes_and_save), invalid_input_handler],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True
    )

    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: check_registration_and_start(u, c, reports.start_report_generation))],
        states={
            states.SELECT_START_DATE: [CallbackQueryHandler(reports.handle_start_date_selection, pattern="^calendar_")],
            states.SELECT_END_DATE: [CallbackQueryHandler(reports.handle_end_date_selection, pattern="^calendar_")],
            states.MANAGE_SELECTION: [CallbackQueryHandler(reports.manage_selection)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True,
    )

    list_open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_open_os))],
        states={states.PAGINATING_OS: [CallbackQueryHandler(service_order.navigate_os_page, pattern="^list_open")]},
        fallbacks=[
            CommandHandler("cancelar", common.cancel), 
            MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel),
            CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_open_cancel$")
        ],
        per_user=True, per_chat=True,
    )
    list_closed_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗂️ Listar Fechadas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_closed_os))],
        states={states.PAGINATING_CLOSED_OS: [CallbackQueryHandler(service_order.navigate_closed_os_page, pattern="^list_closed")]},
        fallbacks=[
            CommandHandler("cancelar", common.cancel),
            MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel),
            CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_closed_cancel$")
        ],
        per_user=True, per_chat=True,
    )

    edit_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Editar OS$"), lambda u, c: check_registration_and_start(u, c, os_edit.start_edit_os))],
        states={
            states.PAGINATING_EDIT_OS: [
                CallbackQueryHandler(os_edit.navigate_editable_os_page, pattern="^edit_nav_"),
                CallbackQueryHandler(os_edit.show_edit_menu, pattern="^edit_select_os_"),
            ],
            states.SELECT_FIELD: [
                CallbackQueryHandler(os_edit.prompt_for_new_value, pattern="^edit_field_"),
                CallbackQueryHandler(os_edit.finish_editing, pattern="^edit_finish$"),
            ],
            states.GET_NEW_VALUE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, os_edit.update_field_from_text), invalid_input_handler],
            states.GET_NEW_VALUE_BUTTON: [CallbackQueryHandler(os_edit.update_field_from_button)],
        },
        fallbacks=[
            CommandHandler("cancelar", common.cancel),
            MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel),
            CallbackQueryHandler(common.cancel, pattern="^edit_cancel$")
        ],
        per_user=True, per_chat=True,
    )
    
    delete_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗑️ Deletar OS$"), lambda u, c: check_registration_and_start(u, c, os_delete.start_delete_os))],
        states={
            states.CHOOSE_STATUS: [CallbackQueryHandler(os_delete.ask_for_date, pattern="^delete_status_")],
            states.SELECT_DATE: [CallbackQueryHandler(os_delete.list_os_for_deletion, pattern="^calendar_")],
            states.CONFIRM_DELETE: [
                CallbackQueryHandler(os_delete.confirm_and_delete_os, pattern="^delete_confirm_"),
                CallbackQueryHandler(os_delete.execute_delete, pattern="^delete_do_"),
                CallbackQueryHandler(common.cancel, pattern="^delete_cancel_op$")
            ],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True,
    )

    parts_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Consultar Peças$"), lambda u, c: check_registration_and_start(u, c, parts_manager.start_parts_consult))],
        states={
            states.ASK_SEARCH_TERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, parts_manager.search_parts), invalid_input_handler]
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), MessageHandler(filters.Regex("^❌ Cancelar$"), common.cancel)],
        per_user=True, per_chat=True,
    )
    
    # --- HANDLERS DE COMANDOS SIMPLES (FORA DE CONVERSAS) ---
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Sobre$"), common.about))

    # --- REGISTO DE TODOS OS HANDLERS DE CONVERSA NA APLICAÇÃO ---
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
