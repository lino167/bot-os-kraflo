import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)

from config import TELEGRAM_TOKEN
from handlers import common, registration, service_order, reports
from database.utils import is_user_registered

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def check_registration_and_start(update: Update, context: ContextTypes.DEFAULT_TYPE, start_function):
    """Verifica se o usuário está cadastrado antes de iniciar um fluxo."""
    if await is_user_registered(update.effective_user.id):
        return await start_function(update, context)
    else:
        # Apenas o fluxo de abrir OS pode iniciar o cadastro
        if start_function == registration.start_registration_or_os:
            return await start_function(update, context)
        else:
            await update.message.reply_text("Você precisa se cadastrar primeiro. Clique em '🆕 Abrir OS' para iniciar.")
            return ConversationHandler.END

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
            service_order.ASK_PROBLEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_problem_description_and_ask_photo)],
            service_order.ASK_IF_PHOTO: [CallbackQueryHandler(service_order.prompt_for_photo, pattern='^photo_yes$'), CallbackQueryHandler(service_order.save_os_and_finish, pattern='^photo_no$')],
            service_order.GET_PHOTO: [MessageHandler(filters.PHOTO, service_order.get_photo_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel)], per_user=True, per_chat=True,
    )

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
            service_order.ASK_FINAL_STATUS: [CallbackQueryHandler(service_order.get_final_status_and_ask_if_notes)],
            service_order.ASK_IF_NOTES: [CallbackQueryHandler(service_order.prompt_for_final_notes, pattern='^notes_yes$'), CallbackQueryHandler(service_order.finalize_without_notes, pattern='^notes_no$')],
            service_order.GET_FINAL_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_order.get_final_notes_and_save)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_close$')], per_user=True, per_chat=True,
    )

    report_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📊 Relatórios$"), lambda u, c: check_registration_and_start(u, c, reports.start_report_generation))],
        states={
            reports.CHOOSE_FILTER_TYPE: [CallbackQueryHandler(reports.handle_filter_choice)],
            reports.SELECT_START_DATE: [CallbackQueryHandler(reports.handle_start_date_selection)],
            reports.SELECT_END_DATE: [CallbackQueryHandler(reports.handle_end_date_selection)],
            reports.MANAGE_SELECTION: [CallbackQueryHandler(reports.manage_selection)],
        },
        fallbacks=[CommandHandler("cancelar", common.cancel), CallbackQueryHandler(common.cancel, pattern='^cancel_report$')],
        per_user=True, per_chat=True,
    )

    list_open_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Listar Abertas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_open_os))],
        states={
            service_order.PAGINATING_OS: [CallbackQueryHandler(service_order.navigate_os_page)],
        },
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_open_cancel$")],
        per_user=True, per_chat=True,
    )

    list_closed_os_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗂️ Listar Fechadas$"), lambda u, c: check_registration_and_start(u, c, service_order.start_list_closed_os))],
        states={
            service_order.PAGINATING_CLOSED_OS: [CallbackQueryHandler(service_order.navigate_closed_os_page)],
        },
        fallbacks=[CallbackQueryHandler(service_order.cancel_pagination, pattern="^list_closed_cancel$")],
        per_user=True, per_chat=True,
    )

    # --- Adicionando todos os handlers à aplicação ---
    application.add_handler(CommandHandler("start", common.start))
    application.add_handler(open_os_conv)
    application.add_handler(close_os_conv)
    application.add_handler(report_conv)
    application.add_handler(list_open_os_conv)
    application.add_handler(list_closed_os_conv)
    
    print("="*50)
    print("🚀 BOT INICIADO COM SUCESSO! 🚀")
    print("="*50)
    
    application.run_polling()

if __name__ == "__main__":
    main()